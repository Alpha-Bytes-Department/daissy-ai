from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import uuid
import os
import shutil
from typing import Dict, Any, List
from pydantic import BaseModel

try:
    from .transcribe import AudioProcessor
    from .chroma import ChromaDBManager
    from .chat import RAGChatBot
except ImportError:
    from transcribe import AudioProcessor
    from chroma import ChromaDBManager
    from chat import RAGChatBot

router = APIRouter()

# Initialize processors
audio_processor = AudioProcessor()
chroma_manager = ChromaDBManager()
chat_bot = RAGChatBot()

# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    query: str
    sources_count: int
    audio_files: List[Dict[str, Any]]  # Will contain at most 1 audio file
    context_used: List[Dict[str, Any]]

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
        
        # Get chat response with audio references (using default 3 sources)
        chat_result = chat_bot.chat(request.query, n_results=3)
        
        return ChatResponse(
            response=chat_result["response"],
            query=chat_result["query"],
            sources_count=chat_result["sources_count"],
            audio_files=chat_result["audio_files"],
            context_used=chat_result["context_used"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.get("/chat")
async def chat_with_audio_get(query: str) -> Dict[str, Any]:
    """
    Chat with the AI consultant using GET request.
    The AI acts as both a resource finder and an active consultant.
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Get chat response with audio references (using default 3 sources)
        chat_result = chat_bot.chat(query, n_results=3)
        
        return {
            "success": True,
            "response": chat_result["response"],
            "query": chat_result["query"],
            "sources_count": chat_result["sources_count"],
            "audio_files": chat_result["audio_files"],
            "context_used": chat_result["context_used"]
        }
        
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
async def reset_conversation() -> Dict[str, Any]:
    """
    Reset the conversation history to start a new consultation session
    """
    try:
        result = chat_bot.reset_conversation()
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@router.get("/chat/status")
async def get_chat_status() -> Dict[str, Any]:
    """
    Get current conversation status and length
    """
    try:
        conversation_length = chat_bot.get_conversation_length()
        return {
            "success": True,
            "conversation_length": conversation_length,
            "status": "active" if conversation_length > 0 else "new_session"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "audio-processing-api"}