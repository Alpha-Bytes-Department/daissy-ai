from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    user_id: str

class SimpleChatResponse(BaseModel):
    response: str
    query: str
    conversation_length: int
    user_id: str

class AudioProviderRequest(BaseModel):
    query: str

class AudioProviderResponse(BaseModel):
    suggestion: str
    audio_file: Optional[str] = None

# Pagination models
class PaginationInfo(BaseModel):
    page: int
    limit: int
    total_messages: int
    total_pages: int
    has_next: bool
    has_previous: bool

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatHistoryResponse(BaseModel):
    history: List[ChatMessage]
    pagination: PaginationInfo

# Audio metadata models
class AudioMetadata(BaseModel):
    audio_id: str
    title: str
    category: str
    use_case: str
    emotion: str
    duration: str
    status: str
    created_at: datetime
    updated_at: datetime

class AudioListResponse(BaseModel):
    audios: List[AudioMetadata]

