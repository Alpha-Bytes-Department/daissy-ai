from pydantic import BaseModel
from typing import Dict, Any, Optional

# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class SimpleChatResponse(BaseModel):
    response: str
    query: str
    conversation_length: int
    session_id: str
    user_id: Optional[str] = None

class AudioProviderRequest(BaseModel):
    query: str

class AudioProviderResponse(BaseModel):
    suggestion: str
    audio_file: str

class UserSession(BaseModel):
    id: int
    session_id: str
    user_id: Optional[str] = None
    created_at: str
    updated_at: str
    is_active: bool

class UserSessionsResponse(BaseModel):
    success: bool
    user_id: str
    sessions: list[UserSession]
    total_sessions: int
    message_count: Optional[int] = None
