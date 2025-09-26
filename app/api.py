from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
import uuid
import os
import shutil
from typing import Dict, Any, Optional
from transcribe import AudioProcessor
from chroma import ChromaDBManager
from chat import SimpleChatBot, AudioProvider
from schema import ChatRequest,SimpleChatResponse,AudioProviderRequest,AudioProviderResponse

router = APIRouter()

# Initialize processors
audio_processor = AudioProcessor()
chroma_manager = ChromaDBManager()

# Chat bots will be managed per session, audio provider is stateless
simple_chat_bots = {}

# Create a single audio provider instance since it's stateless
audio_provider = AudioProvider()

def get_or_create_chat_bot(user_id: str) -> SimpleChatBot:
    """Get existing simple chat bot for user or create new one"""
    # Check if we already have this chat bot in memory
    if user_id in simple_chat_bots:
        return simple_chat_bots[user_id]
    
    # Create new chat bot and cache it
    chat_bot = SimpleChatBot(user_id=user_id)
    simple_chat_bots[user_id] = chat_bot
    return chat_bot

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

@router.post("/chat")
async def chat(request: ChatRequest) -> SimpleChatResponse:
    """
    Simple text-based chat with AI assistant - no audio functionality.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not request.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Get or create simple chat bot for user
        chat_bot = get_or_create_chat_bot(request.user_id)
        
        # Get chat response
        chat_result = chat_bot.chat(request.query)
        
        return SimpleChatResponse(
            response=chat_result["response"],
            query=chat_result["query"],
            conversation_length=chat_result["conversation_length"],
            user_id=chat_result["user_id"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.post("/chat-audio")
async def get_audio_for_query(request: AudioProviderRequest) -> AudioProviderResponse:
    """Get relevant audio file for user query"""
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Use the stateless audio provider
        result = audio_provider.get_audio_and_suggestion(request.query)
        
        return AudioProviderResponse(
            suggestion=result["suggestion"],
            audio_file=UPLOAD_DIR+"/"+result["audio_file"]["filename"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio chat failed: {str(e)}")

@router.get("/chat/history/{user_id}")
async def get_chat_history(user_id: str) -> Dict[str, Any]:
    """
    Get the complete chat history for a user - optimized to use direct DB query
    """
    try:
        # Get history directly from database without loading full chat bot
        from database import get_database_manager
        db_manager = get_database_manager()
        
        # Get simple chat history (role, content only)
        history = db_manager.get_user_history(user_id)
        
        if not history:
            # Check if user has any conversation
            user_stats = db_manager.get_user_stats(user_id)
            if user_stats["message_count"] == 0:
                raise HTTPException(status_code=404, detail="No conversation found for user")
        
        return {
            "history": history
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")

@router.delete("/delete/conversation")
async def delete_user_conversation(user_id: str) -> Dict[str, Any]:
    """Delete the entire conversation for a user"""
    try:
        from database import get_database_manager
        db_manager = get_database_manager()
        
        # Delete all messages for the user
        success = db_manager.delete_user_conversation(user_id)
        
        # Clean up from active chat bots cache
        if user_id in simple_chat_bots:
            del simple_chat_bots[user_id]
        
        return {
            "success": success,
            "message": f"Conversation for user {user_id} deleted successfully" if success else "No conversation found to delete"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
