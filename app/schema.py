from pydantic import BaseModel
from typing import Dict, Any, Optional

# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class SimpleChatResponse(BaseModel):
    response: str
    query: str
    conversation_length: int
    session_id: str

class AudioProviderRequest(BaseModel):
    query: str

class AudioProviderResponse(BaseModel):
    suggestion: str
    audio_file: Optional[Dict[str, Any]]
