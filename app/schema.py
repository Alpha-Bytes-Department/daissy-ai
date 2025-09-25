from pydantic import BaseModel
from typing import Dict, Any, Optional

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

