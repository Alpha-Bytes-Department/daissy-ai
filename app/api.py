from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import FileResponse
import uuid
import os
import shutil
from typing import Dict, Any, Optional, List
from transcribe import AudioProcessor
from chroma import ChromaDBManager
from chat import SimpleChatBot, AudioProvider
from schema import SimpleChatResponse,AudioProviderResponse,ChatHistoryResponse,AudioListResponse,AudioMetadata

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
UPLOAD_DIR = "voices"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

def is_allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

@router.post("/upload-audio")
async def upload_audio(
    title: str = Form(...), 
    category: str = Form(...), 
    use_case: str = Form(...),
    emotion: str = Form(...),
    file: UploadFile = File(...)
    ) -> Dict[str, Any]:
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
            duration = audio_processor.get_media_duration(file_path)
            transcription, summary = audio_processor.process_audio(file_path)
        except Exception as e:
            # Clean up the uploaded file if processing fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
        
        # Store summary in ChromaDB and metadata in SQL database
        try:
            # Store embeddings and summary in ChromaDB (minimal metadata)
            chroma_manager.store_summary(audio_id, summary)
            
            # Store metadata in SQL database
            from database import get_database_manager
            db_manager = get_database_manager()
            db_manager.save_audio_data(audio_id, title, category, use_case, emotion, duration)
            
        except Exception as e:
            # Clean up the uploaded file if storage fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Failed to store audio data: {str(e)}")
        
        return {
            "success": True,
            "audio_id": audio_id,
            "filename": unique_filename,
            "original_filename": file.filename,
            "transcription": transcription,
            "summary": summary,
            "title": title,
            "category": category,
            "use_case": use_case,
            "emotion": emotion,
            "duration": duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/chat")
async def chat(query: str, user_id: str) -> SimpleChatResponse:
    """
    Simple text-based chat with AI assistant - no audio functionality.
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Get or create simple chat bot for user
        chat_bot = get_or_create_chat_bot(user_id)
        
        # Get chat response
        chat_result = chat_bot.chat(query)
        
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
async def get_audio_for_query(query: str) -> AudioProviderResponse:
    """Get relevant audio file for user query"""
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Use the stateless audio provider
        result = audio_provider.get_audio_and_suggestion(query)
        
        # Handle case where no audio file was found
        audio_path = None
        if result["audio_file"] is not None:
            audio_path = UPLOAD_DIR + "/" + result["audio_file"]["filename"]
        
        return AudioProviderResponse(
            suggestion=result["suggestion"],
            audio_file=audio_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio chat failed: {str(e)}")

@router.get("/chat/history")
async def get_chat_history(
    user_id: str, 
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page (max 100)")
) -> ChatHistoryResponse:
    """
    Get paginated chat history for a user - optimized to use direct DB query
    """
    try:
        # Get history directly from database without loading full chat bot
        from database import get_database_manager
        db_manager = get_database_manager()
        
        # Get paginated chat history
        result = db_manager.get_user_history_paginated(user_id, page, limit)
        
        # Check if user exists but has no messages
        if result["pagination"]["total_messages"] == 0:
            raise HTTPException(status_code=404, detail="No conversation found for user")
        
        # Check if page is out of range
        if page > result["pagination"]["total_pages"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Page {page} not found. Total pages: {result['pagination']['total_pages']}"
            )
        
        return ChatHistoryResponse(
            history=result["history"],
            pagination=result["pagination"]
        )
            
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

@router.get("/audios")
async def get_all_audios(query: str = None) -> List[AudioMetadata]:
    """
    Get all audios from ChromaDB with their metadata
    """
    try:
        if query:
            # Use get_audio_by_query method for metadata-based filtering
            audios_data = chroma_manager.get_audio_by_query(query)
        else: 
            # Get all audios from ChromaDB
            audios_data = chroma_manager.get_all_audios()
        
        # Convert to response format - return simple list of AudioMetadata
        audio_items = []
        for audio_data in audios_data:
            audio_item = AudioMetadata(**audio_data["metadata"])
            audio_items.append(audio_item)
        
        return audio_items
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audios: {str(e)}")

@router.put("/change-audio-status")
async def change_audio_status(audio_id: str) -> Dict[str, Any]:
    """
    Toggle audio status between 'active' and 'inactive'
    """
    try:
        from database import get_database_manager
        db_manager = get_database_manager()
        
        # Get current audio data (including inactive ones for status change)
        audio_data = db_manager.get_audio_data_by_id(audio_id, include_inactive=True)
        
        if not audio_data:
            raise HTTPException(status_code=404, detail="Audio not found")
        
        # Determine new status
        current_status = audio_data.get("status", "active")
        new_status = "inactive" if current_status == "active" else "active"
        
        # Update the status
        success = db_manager.update_audio_data(audio_id, status=new_status)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update audio status")
        
        return {
            "success": True,
            "audio_id": audio_id,
            "previous_status": current_status,
            "new_status": new_status,
            "message": f"Audio status changed from '{current_status}' to '{new_status}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change audio status: {str(e)}")

@router.delete("/delete-audio")
async def delete_audio(audio_id: str) -> Dict[str, Any]:
    """
    Delete an audio file and its record completely from filesystem, ChromaDB and SQL database
    """
    try:
        # First, check if audio exists in SQL database (including inactive ones)
        from database import get_database_manager
        db_manager = get_database_manager()
        audio_data = db_manager.get_audio_data_by_id(audio_id, include_inactive=True)
        
        if not audio_data:
            raise HTTPException(status_code=404, detail="Audio not found")
        
        # Find and delete the audio file from filesystem
        audio_deleted = False
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(audio_id):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    os.remove(file_path)
                    audio_deleted = True
                    break
                except OSError as e:
                    # File might not exist or permission error
                    print(f"Warning: Could not delete file {file_path}: {str(e)}")
        
        # Delete from both ChromaDB and SQL database (hard delete)
        chroma_deleted = chroma_manager.delete_audio(audio_id)
        
        if not chroma_deleted:
            raise HTTPException(status_code=404, detail="Audio record not found in vector database")
        
        return {
            "success": True,
            "audio_id": audio_id,
            "message": "Audio permanently deleted from all systems",
            "file_deleted": audio_deleted,
            "database_deleted": chroma_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete audio: {str(e)}")
