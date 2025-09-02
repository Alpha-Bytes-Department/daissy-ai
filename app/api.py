from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
import uuid
import os
import shutil
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from transcribe import AudioProcessor
from chroma import ChromaDBManager
from chat import RAGChatBot

router = APIRouter()

# Initialize processors
audio_processor = AudioProcessor()
chroma_manager = ChromaDBManager()

# Chat bots will be managed per session
chat_bots = {}

def get_or_create_chat_bot(session_id: Optional[str] = None) -> RAGChatBot:
    """Get existing chat bot for session or create new one"""
    if session_id is None:
        # Create new session
        return RAGChatBot()
    
    if session_id not in chat_bots:
        # Create chat bot for existing session
        chat_bots[session_id] = RAGChatBot(session_id=session_id)
    
    return chat_bots[session_id]

# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    query: str
    audio_files: List[Dict[str, Any]]  # Will contain at most 1 audio file
    audio_provided: bool
    conversation_length: int
    session_id: str

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

def is_allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload an audio file, transcribe it, summarize the transcription,
    and store the summary with embeddings in ChromaDB
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file name provided")
        
        if not is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Generate unique ID for the audio file
        audio_id = str(uuid.uuid4())
        
        # Get file extension
        file_extension = os.path.splitext(file.filename)[1]
        
        # Create unique filename
        unique_filename = f"{audio_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the audio file
        try:
            transcription, summary = audio_processor.process_audio(file_path)
        except Exception as e:
            # Clean up the uploaded file if processing fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
        
        # Store summary in ChromaDB
        try:
            stored_id = chroma_manager.store_summary(audio_id, summary, transcription)
        except Exception as e:
            # Clean up the uploaded file if storage fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Failed to store in vector database: {str(e)}")
        
        return {
            "success": True,
            "audio_id": audio_id,
            "filename": unique_filename,
            "original_filename": file.filename,
            "transcription": transcription,
            "summary": summary,
            "message": "Audio file processed and stored successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/search")
async def search_summaries(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Search for similar audio summaries using semantic search
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if limit < 1 or limit > 20:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 20")
        
        results = chroma_manager.search_similar(query, limit)
        
        return {
            "success": True,
            "query": query,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/audio/{audio_id}")
async def get_audio_summary(audio_id: str) -> Dict[str, Any]:
    """
    Retrieve summary and metadata by audio ID
    """
    try:
        result = chroma_manager.get_by_audio_id(audio_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Audio summary not found")
        
        return {
            "success": True,
            "audio_id": audio_id,
            "summary": result["document"],
            "metadata": result["metadata"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

@router.post("/chat")
async def chat_with_audio(request: ChatRequest) -> ChatResponse:
    """
    Chat with the AI consultant that can find relevant consultation audio files and continue conversations.
    The AI acts as both a resource finder and an active consultant.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Get or create chat bot for session
        chat_bot = get_or_create_chat_bot(request.session_id)
        
        # Get chat response with audio references
        chat_result = chat_bot.chat(request.query)
        
        return ChatResponse(
            response=chat_result["response"],
            query=chat_result["query"],
            audio_files=chat_result["audio_files"],
            audio_provided=chat_result["audio_provided"],
            conversation_length=chat_result["conversation_length"],
            session_id=chat_result["session_id"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/download-audio/{audio_id}")
async def download_audio(audio_id: str):
    """
    Download audio file by audio ID
    """
    try:
        # Find the audio file in uploads directory
        uploads_dir = "uploads"
        audio_file_path = None
        
        if not os.path.exists(uploads_dir):
            raise HTTPException(status_code=404, detail="Uploads directory not found")
        
        for filename in os.listdir(uploads_dir):
            if filename.startswith(audio_id):
                audio_file_path = os.path.join(uploads_dir, filename)
                break
        
        if not audio_file_path or not os.path.exists(audio_file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Return the file for download
        return FileResponse(
            path=audio_file_path,
            media_type="audio/mpeg",
            filename=os.path.basename(audio_file_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/audio-file-info/{audio_id}")
async def get_audio_file_info(audio_id: str) -> Dict[str, Any]:
    """
    Get audio file information without downloading
    """
    try:
        uploads_dir = "uploads"
        
        if not os.path.exists(uploads_dir):
            raise HTTPException(status_code=404, detail="Uploads directory not found")
        
        for filename in os.listdir(uploads_dir):
            if filename.startswith(audio_id):
                file_path = os.path.join(uploads_dir, filename)
                if os.path.exists(file_path):
                    file_stats = os.stat(file_path)
                    return {
                        "success": True,
                        "audio_id": audio_id,
                        "filename": filename,
                        "file_size": file_stats.st_size,
                        "file_path": file_path,
                        "exists": True
                    }
        
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File info retrieval failed: {str(e)}")

@router.post("/chat/reset")
async def reset_conversation(session_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """
    Reset the conversation history to start a new consultation session
    """
    try:
        chat_bot = get_or_create_chat_bot(session_id)
        result = chat_bot.reset_conversation()
        
        # Remove from active chat bots if it exists
        if session_id and session_id in chat_bots:
            del chat_bots[session_id]
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@router.get("/chat/status")
async def get_chat_status(session_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """
    Get current conversation status and length
    """
    try:
        chat_bot = get_or_create_chat_bot(session_id)
        conversation_length = chat_bot.get_conversation_length()
        session_stats = chat_bot.get_session_stats()
        
        return {
            "success": True,
            "session_id": chat_bot.get_session_id(),
            "conversation_length": conversation_length,
            "status": "active" if conversation_length > 0 else "new_session",
            "session_stats": session_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str) -> Dict[str, Any]:
    """
    Get the complete chat history for a session
    """
    try:
        chat_bot = get_or_create_chat_bot(session_id)
        history = chat_bot.get_full_conversation_history()
        
        return {
            "success": True,
            "session_id": session_id,
            "history": history,
            "message_count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")

@router.post("/chat/load-session")
async def load_chat_session(session_id: str = Query(...)) -> Dict[str, Any]:
    """
    Load an existing chat session
    """
    try:
        chat_bot = get_or_create_chat_bot()
        result = chat_bot.load_session(session_id)
        
        if result.get("success"):
            # Store in active chat bots
            chat_bots[session_id] = chat_bot
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session load failed: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "audio-processing-api"}