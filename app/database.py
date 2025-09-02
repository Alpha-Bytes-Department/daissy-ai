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

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
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
        
        # Cache for session existence to avoid repeated checks
        self._session_cache = set()
        
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
    
    def create_chat_session_if_not_exists(self, session_id: str) -> bool:
        """Create a new chat session only if it doesn't exist. Returns True if created, False if exists."""
        # Check cache first
        if session_id in self._session_cache:
            return False
            
        with self.get_db_session() as db:
            # Check if session already exists
            existing_session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if existing_session:
                self._session_cache.add(session_id)
                return False
            
            chat_session = ChatSession(session_id=session_id)
            db.add(chat_session)
            self._session_cache.add(session_id)
            return True
    
    def save_messages_batch(self, messages_data: List[Dict[str, Any]]) -> List[ChatMessage]:
        """Save multiple messages in a single transaction"""
        with self.get_db_session() as db:
            messages = []
            for msg_data in messages_data:
                # Ensure session exists (but only check once per batch)
                session_id = msg_data["session_id"]
                if session_id not in self._session_cache:
                    self.create_chat_session_if_not_exists(session_id)
                
                message = ChatMessage(
                    session_id=msg_data["session_id"],
                    message_id=msg_data["message_id"],
                    role=msg_data["role"],
                    content=msg_data["content"],
                    audio_files=msg_data.get("audio_files"),
                    function_calls=msg_data.get("function_calls"),
                    extra_data=msg_data.get("extra_data")
                )
                db.add(message)
                messages.append(message)
            
            return messages
    
    def save_message(self, session_id: str, message_id: str, role: str, content: str, 
                    audio_files: Optional[List[Dict]] = None, 
                    function_calls: Optional[List[Dict]] = None,
                    extra_data: Optional[Dict] = None) -> ChatMessage:
        """Save a single chat message to the database"""
        return self.save_messages_batch([{
            "session_id": session_id,
            "message_id": message_id,
            "role": role,
            "content": content,
            "audio_files": audio_files,
            "function_calls": function_calls,
            "extra_data": extra_data
        }])[0]
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get all messages for a session, optionally limited to recent messages"""
        with self.get_db_session() as db:
            query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
            
            if limit:
                # Get the most recent messages
                query = query.order_by(ChatMessage.timestamp.desc()).limit(limit)
                messages = query.all()
                messages.reverse()  # Return in chronological order
                return messages
            else:
                query = query.order_by(ChatMessage.timestamp.asc())
                return query.all()
    
    def get_session_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get session history in chat format (role, content) - optimized single query"""
        messages = self.get_session_messages(session_id, limit)
        
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def end_session(self, session_id: str) -> bool:
        """Mark a session as inactive"""
        with self.get_db_session() as db:
            result = db.query(ChatSession).filter(ChatSession.session_id == session_id).update({
                "is_active": False,
                "updated_at": datetime.utcnow()
            })
            return result > 0
    
    def get_active_sessions(self) -> List[ChatSession]:
        """Get all active chat sessions"""
        with self.get_db_session() as db:
            return db.query(ChatSession).filter(ChatSession.is_active == True).all()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        with self.get_db_session() as db:
            # Delete messages first
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
            
            # Delete session
            session_deleted = db.query(ChatSession).filter(ChatSession.session_id == session_id).delete()
            
            # Remove from cache
            self._session_cache.discard(session_id)
            
            return session_deleted > 0
    
    def get_session_stats_optimized(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session with optimized single query"""
        with self.get_db_session() as db:
            # Single query to get session info and message stats
            from sqlalchemy import func, case
            
            result = db.query(
                ChatSession.session_id,
                ChatSession.created_at,
                ChatSession.updated_at,
                ChatSession.is_active,
                func.count(ChatMessage.id).label('message_count'),
                func.min(ChatMessage.timestamp).label('first_message_time'),
                func.max(ChatMessage.timestamp).label('last_message_time')
            ).outerjoin(
                ChatMessage, ChatSession.session_id == ChatMessage.session_id
            ).filter(
                ChatSession.session_id == session_id
            ).group_by(
                ChatSession.id, ChatSession.session_id, ChatSession.created_at, 
                ChatSession.updated_at, ChatSession.is_active
            ).first()
            
            if not result:
                return {"error": "Session not found"}
            
            return {
                "session_id": result.session_id,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
                "is_active": result.is_active,
                "message_count": result.message_count or 0,
                "first_message_time": result.first_message_time,
                "last_message_time": result.last_message_time
            }
    
    # Keep the old method for backward compatibility
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session (uses optimized version)"""
        return self.get_session_stats_optimized(session_id)

# Global database manager instance
db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get or create the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
