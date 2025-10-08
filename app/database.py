import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from dotenv import load_dotenv

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

class AudioData(Base):
    __tablename__ = "audio_data"
    
    id = Column(Integer, primary_key=True, index=True)
    audio_id = Column(String(255), unique=True, index=True, nullable=False)  # UUID for audio file identification
    title = Column(String(500), nullable=False, index=True)  # Audio title for searchability
    category = Column(String(100), nullable=False, index=True)  # Audio category
    use_case = Column(String(200), nullable=False, index=True)  # Use case description
    emotion = Column(String(100), nullable=False, index=True)  # Emotion tag
    duration = Column(String(50), nullable=False)  # Duration as string (e.g., "2:30")
    status = Column(String(20), nullable=False, default="active", index=True)  # Status (active, deleted, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    
    def save_message(self, user_id: str, message_id: str, role: str, content: str) -> Dict[str, Any]:
        """Save a single chat message to the database - returns dict data"""
        with self.get_db_session() as db:
            message = ChatMessage(
                user_id=user_id,
                message_id=message_id,
                role=role,
                content=content
            )
            db.add(message)
            
            # Convert to dict immediately to avoid detached instance issues
            return {
                "user_id": message.user_id,
                "message_id": message.message_id,
                "role": message.role,
                "content": message.content
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
                    "timestamp": msg.timestamp
                }
                for msg in messages
            ]
    
    def get_user_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get user conversation history in chat format (role, content) - optimized single query"""
        messages = self.get_user_messages(user_id, limit)
        
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    def get_user_history_paginated(self, user_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """Get paginated user conversation history with pagination metadata"""
        with self.get_db_session() as db:
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get total count for pagination metadata
            total_count = db.query(ChatMessage).filter(ChatMessage.user_id == user_id).count()
            
            # Get paginated messages
            messages = db.query(ChatMessage).filter(
                ChatMessage.user_id == user_id
            ).order_by(ChatMessage.timestamp.asc()).offset(offset).limit(limit).all()
            
            # Convert to chat format
            history = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            # Calculate pagination metadata
            total_pages = (total_count + limit - 1) // limit  # Ceiling division
            has_next = page < total_pages
            has_previous = page > 1
            
            return {
                "history": history,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_messages": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_previous": has_previous
                }
            }
    
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
    
    # Audio Data Management Methods
    def save_audio_data(self, audio_id: str, title: str, category: str, use_case: str, 
                       emotion: str, duration: str, status: str = "active") -> Dict[str, Any]:
        """Save audio metadata to the database"""
        with self.get_db_session() as db:
            audio_data = AudioData(
                audio_id=audio_id,
                title=title,
                category=category,
                use_case=use_case,
                emotion=emotion,
                duration=duration,
                status=status
            )
            db.add(audio_data)
            
            # Convert to dict immediately to avoid detached instance issues
            return {
                "audio_id": audio_data.audio_id,
                "title": audio_data.title,
                "category": audio_data.category,
                "use_case": audio_data.use_case,
                "emotion": audio_data.emotion,
                "duration": audio_data.duration,
                "status": audio_data.status,
                "created_at": audio_data.created_at,
                "updated_at": audio_data.updated_at
            }
    
    def get_audio_data_by_id(self, audio_id: str, include_inactive: bool = False) -> Optional[Dict[str, Any]]:
        """Get audio data by audio_id"""
        with self.get_db_session() as db:
            query = db.query(AudioData).filter(AudioData.audio_id == audio_id)
            
            # Only filter by active status if include_inactive is False
            if not include_inactive:
                query = query.filter(AudioData.status == "active")
            
            audio_data = query.first()
            
            if not audio_data:
                return None
            
            return {
                "audio_id": audio_data.audio_id,
                "title": audio_data.title,
                "category": audio_data.category,
                "use_case": audio_data.use_case,
                "emotion": audio_data.emotion,
                "duration": audio_data.duration,
                "status": audio_data.status,
                "created_at": audio_data.created_at,
                "updated_at": audio_data.updated_at
            }
    
    def get_all_audio_data(self) -> List[Dict[str, Any]]:
        """Get all audio data regardless of status"""
        with self.get_db_session() as db:
            audio_records = db.query(AudioData).order_by(AudioData.created_at.desc()).all()
            
            return [
                {
                    "audio_id": audio.audio_id,
                    "title": audio.title,
                    "category": audio.category,
                    "use_case": audio.use_case,
                    "emotion": audio.emotion,
                    "duration": audio.duration,
                    "status": audio.status,
                    "created_at": audio.created_at,
                    "updated_at": audio.updated_at
                }
                for audio in audio_records
            ]
    
    def search_audio_data(self, query: str) -> List[Dict[str, Any]]:
        """Search audio data by query string matching title, category, use_case, or emotion"""
        with self.get_db_session() as db:
            query_lower = f"%{query.lower()}%"
            
            audio_records = db.query(AudioData).filter(
                db.or_(
                    AudioData.title.ilike(query_lower),
                    AudioData.category.ilike(query_lower),
                    AudioData.use_case.ilike(query_lower),
                    AudioData.emotion.ilike(query_lower)
                )
            ).order_by(AudioData.created_at.desc()).all()
            
            return [
                {
                    "audio_id": audio.audio_id,
                    "title": audio.title,
                    "category": audio.category,
                    "use_case": audio.use_case,
                    "emotion": audio.emotion,
                    "duration": audio.duration,
                    "status": audio.status,
                    "created_at": audio.created_at,
                    "updated_at": audio.updated_at
                }
                for audio in audio_records
            ]
    
    def update_audio_data(self, audio_id: str, title: Optional[str] = None, 
                         category: Optional[str] = None, use_case: Optional[str] = None,
                         emotion: Optional[str] = None, duration: Optional[str] = None,
                         status: Optional[str] = None) -> bool:
        """Update audio metadata"""
        with self.get_db_session() as db:
            audio_data = db.query(AudioData).filter(AudioData.audio_id == audio_id).first()
            
            if not audio_data:
                return False
            
            # Update only provided fields
            if title is not None:
                audio_data.title = title
            if category is not None:
                audio_data.category = category
            if use_case is not None:
                audio_data.use_case = use_case
            if emotion is not None:
                audio_data.emotion = emotion
            if duration is not None:
                audio_data.duration = duration
            if status is not None:
                audio_data.status = status
            
            # updated_at will be automatically set by onupdate
            return True
    
    def delete_audio_data(self, audio_id: str) -> bool:
        """Soft delete audio data by setting status to 'deleted'"""
        return self.update_audio_data(audio_id, status="deleted")
    
    def hard_delete_audio_data(self, audio_id: str) -> bool:
        """Permanently delete audio data from database"""
        with self.get_db_session() as db:
            deleted_count = db.query(AudioData).filter(AudioData.audio_id == audio_id).delete()
            return deleted_count > 0

# Global database manager instance
db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get or create the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
