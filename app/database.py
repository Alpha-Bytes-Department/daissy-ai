import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from dotenv import load_dotenv
import json

load_dotenv()

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Primary conversation identifier
    message_id = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Additional fields for storing context
    audio_files = Column(JSON, nullable=True)  # Store audio file information if any
    function_calls = Column(JSON, nullable=True)  # Store function call data if any
    extra_data = Column(JSON, nullable=True)  # Store any additional metadata

class DatabaseManager:
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Optimized engine with connection pooling
        self.engine = create_engine(
            self.connection_string,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_db_session(self):
        """Context manager for database sessions"""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def save_message(self, user_id: str, message_id: str, role: str, content: str, 
                    audio_files: Optional[List[Dict]] = None, 
                    function_calls: Optional[List[Dict]] = None,
                    extra_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Save a single chat message to the database - returns dict data"""
        with self.get_db_session() as db:
            message = ChatMessage(
                user_id=user_id,
                message_id=message_id,
                role=role,
                content=content,
                audio_files=audio_files,
                function_calls=function_calls,
                extra_data=extra_data
            )
            db.add(message)
            
            # Convert to dict immediately to avoid detached instance issues
            return {
                "user_id": message.user_id,
                "message_id": message.message_id,
                "role": message.role,
                "content": message.content,
                "audio_files": message.audio_files,
                "function_calls": message.function_calls,
                "extra_data": message.extra_data
            }
    
    def get_user_messages(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all messages for a user, optionally limited to recent messages - returns dict data"""
        with self.get_db_session() as db:
            query = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)
            
            if limit:
                # Get the most recent messages
                query = query.order_by(ChatMessage.timestamp.desc()).limit(limit)
                messages = query.all()
                messages.reverse()  # Return in chronological order
            else:
                query = query.order_by(ChatMessage.timestamp.asc())
                messages = query.all()
            
            # Convert to dict while session is active to avoid detached instance errors
            return [
                {
                    "id": msg.id,
                    "user_id": msg.user_id,
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "audio_files": msg.audio_files,
                    "function_calls": msg.function_calls,
                    "extra_data": msg.extra_data
                }
                for msg in messages
            ]
    
    def get_user_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get user conversation history in chat format (role, content) - optimized single query"""
        messages = self.get_user_messages(user_id, limit)
        
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    def get_full_user_messages(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get complete message data including metadata for a user - returns full message details"""
        messages = self.get_user_messages(user_id, limit)
        return messages  # Already converted to dict format with all fields
    
    def delete_user_conversation(self, user_id: str) -> bool:
        """Delete all messages for a user"""
        with self.get_db_session() as db:
            # Delete all messages for the user
            messages_deleted = db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
            return messages_deleted > 0
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user's conversation with optimized single query"""
        with self.get_db_session() as db:
            # Single query to get user message stats
            from sqlalchemy import func
            
            result = db.query(
                func.count(ChatMessage.id).label('message_count'),
                func.min(ChatMessage.timestamp).label('first_message_time'),
                func.max(ChatMessage.timestamp).label('last_message_time')
            ).filter(
                ChatMessage.user_id == user_id
            ).first()
            
            if not result or result.message_count == 0:
                return {
                    "user_id": user_id,
                    "message_count": 0,
                    "first_message_time": None,
                    "last_message_time": None
                }
            
            return {
                "user_id": user_id,
                "message_count": result.message_count or 0,
                "first_message_time": result.first_message_time,
                "last_message_time": result.last_message_time
            }

# Global database manager instance
db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get or create the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
