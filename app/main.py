from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .api import router
except ImportError:
    from api import router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Audio Processing & Consultation Finder API",
    description="API for uploading, processing consultation audio files and helping users find relevant consultations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["audio"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Audio Processing & Consultation Finder API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "upload_audio": "/api/v1/upload-audio",
            "search": "/api/v1/search",
            "chat": "/api/v1/chat",
            "chat_reset": "/api/v1/chat/reset",
            "chat_status": "/api/v1/chat/status",
            "download_audio": "/api/v1/download-audio/{audio_id}",
            "get_audio": "/api/v1/audio/{audio_id}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set")
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )