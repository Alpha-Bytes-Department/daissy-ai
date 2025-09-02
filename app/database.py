import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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
        
        self.engine = create_engine(self.connection_string)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
    
    def get_db(self) -> Session:
        """Get database session"""
        db = self.SessionLocal()
        try:
            return db
        except Exception:
            db.close()
            raise
    
    def create_chat_session(self, session_id: str) -> ChatSession:
        """Create a new chat session"""
        db = self.get_db()
        try:
            # Check if session already exists
            existing_session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if existing_session:
                return existing_session
            
            chat_session = ChatSession(session_id=session_id)
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)
            return chat_session
        finally:
            db.close()
    
    def save_message(self, session_id: str, message_id: str, role: str, content: str, 
                    audio_files: Optional[List[Dict]] = None, 
                    function_calls: Optional[List[Dict]] = None,
                    extra_data: Optional[Dict] = None) -> ChatMessage:
        """Save a chat message to the database"""
        db = self.get_db()
        try:
            # Ensure session exists
            self.create_chat_session(session_id)
            
            message = ChatMessage(
                session_id=session_id,
                message_id=message_id,
                role=role,
                content=content,
                audio_files=audio_files,
                function_calls=function_calls,
                extra_data=extra_data
            )
            
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
        finally:
            db.close()
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get all messages for a session, optionally limited to recent messages"""
        db = self.get_db()
        try:
            query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.asc())
            
            if limit:
                # Get the most recent messages
                query = query.order_by(ChatMessage.timestamp.desc()).limit(limit)
                messages = query.all()
                messages.reverse()  # Return in chronological order
                return messages
            
            return query.all()
        finally:
            db.close()
    
    def get_session_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get session history in chat format (role, content)"""
        messages = self.get_session_messages(session_id, limit)
        
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return history
    
    def end_session(self, session_id: str) -> bool:
        """Mark a session as inactive"""
        db = self.get_db()
        try:
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if session:
                session.is_active = False
                session.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def get_active_sessions(self) -> List[ChatSession]:
        """Get all active chat sessions"""
        db = self.get_db()
        try:
            return db.query(ChatSession).filter(ChatSession.is_active == True).all()
        finally:
            db.close()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        db = self.get_db()
        try:
            # Delete messages first
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
            
            # Delete session
            session_deleted = db.query(ChatSession).filter(ChatSession.session_id == session_id).delete()
            
            db.commit()
            return session_deleted > 0
        finally:
            db.close()
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        db = self.get_db()
        try:
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if not session:
                return {"error": "Session not found"}
            
            message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
            
            first_message = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.asc()).first()
            last_message = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.desc()).first()
            
            return {
                "session_id": session_id,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "is_active": session.is_active,
                "message_count": message_count,
                "first_message_time": first_message.timestamp if first_message else None,
                "last_message_time": last_message.timestamp if last_message else None
            }
        finally:
            db.close()

# Global database manager instance
db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get or create the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
