from pydantic import BaseModel
from typing import Dict, Any, Optional, List

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
    audio_file: str

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

