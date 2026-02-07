from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys
from dotenv import load_dotenv

# Add app directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from .api import router
except ImportError:
    from api import router

# Load environment variables
load_dotenv()

# Check if running in production
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"


# Create FastAPI app
app = FastAPI(
    title="Audio Processing & Consultation Finder API",
    description="API for uploading, processing consultation audio files and helping users find relevant consultations",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for LAN development - restrict for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/ai", tags=["audio"])

# Mount static files directory for audio files
# Create voices directory if it doesn't exist
VOICES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voices")
os.makedirs(VOICES_DIR, exist_ok=True)

# Mount the voices directory to serve audio files
app.mount("/voices", StaticFiles(directory=VOICES_DIR), name="voices")

if __name__ == "__main__":
    import uvicorn
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )