# Audio Processing API

A FastAPI-based service for processing audio files with transcription, summarization, and vector storage capabilities.

## Features

- 🎵 **Audio File Upload**: Supports MP3, WAV, M4A, FLAC, and OGG formats
- 🔊 **Audio Transcription**: Uses OpenAI Whisper for accurate speech-to-text conversion
- 📝 **Text Summarization**: Leverages OpenAI GPT-3.5-turbo for intelligent summarization
- 🔍 **Vector Search**: Stores embeddings in ChromaDB for semantic similarity search
- 🔑 **Unique ID Management**: Assigns unique IDs to audio files for easy retrieval

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API Key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd daissy-ai
```

2. Create a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
   - Update the `.env` file with your OpenAI API key
   - The API key is already configured in your `.env` file

### Running the API

```bash
python run.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation.

## API Endpoints

### 1. Upload Audio File
**POST** `/api/v1/upload-audio`

Upload an audio file for processing.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: Audio file (MP3, WAV, M4A, FLAC, OGG)

**Response:**
```json
{
  "success": true,
  "audio_id": "uuid-string",
  "filename": "unique-filename.mp3",
  "original_filename": "original-name.mp3",
  "transcription": "Full transcribed text...",
  "summary": "Summarized content...",
  "message": "Audio file processed and stored successfully"
}
```

### 2. Search Similar Summaries
**GET** `/api/v1/search?query=<text>&limit=<number>`

Search for similar audio summaries using semantic search.

**Parameters:**
- `query` (required): Search text
- `limit` (optional): Number of results (1-20, default: 5)

**Response:**
```json
{
  "success": true,
  "query": "search text",
  "results": {
    "documents": ["summary1", "summary2"],
    "metadatas": [{"audio_id": "id1"}, {"audio_id": "id2"}],
    "distances": [0.1, 0.2],
    "ids": ["id1", "id2"]
  }
}
```

### 3. Get Audio Summary by ID
**GET** `/api/v1/audio/<audio_id>`

Retrieve summary and metadata by audio ID.

**Response:**
```json
{
  "success": true,
  "audio_id": "uuid-string",
  "summary": "Summary text...",
  "metadata": {
    "audio_id": "uuid-string",
    "summary_length": 150,
    "has_transcription": true
  }
}
```

### 4. Health Check
**GET** `/api/v1/health`

Check API health status.

## Usage Examples

### Using curl

```bash
# Upload an audio file
curl -X POST "http://localhost:8000/api/v1/upload-audio" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@audio.mp3"

# Search for similar summaries
curl -X GET "http://localhost:8000/api/v1/search?query=meeting notes&limit=3"

# Get summary by audio ID
curl -X GET "http://localhost:8000/api/v1/audio/your-audio-id"
```

### Using Python requests

```python
import requests

# Upload audio file
with open("audio.mp3", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/upload-audio",
        files={"file": f}
    )
    result = response.json()
    audio_id = result["audio_id"]

# Search for similar content
search_response = requests.get(
    "http://localhost:8000/api/v1/search",
    params={"query": "meeting discussion", "limit": 5}
)

# Retrieve by ID
summary_response = requests.get(f"http://localhost:8000/api/v1/audio/{audio_id}")
```

## File Storage

- Audio files are stored in the `uploads/` directory
- Files are renamed with unique UUIDs to prevent conflicts
- Original filenames are preserved in the API response
- Vector embeddings and summaries are stored in ChromaDB (persistent storage in `./chroma_db`)

## Technologies Used

- **FastAPI**: Modern, fast web framework for building APIs
- **OpenAI Whisper**: Speech recognition model for transcription
- **OpenAI GPT-3.5-turbo**: Language model for summarization
- **OpenAI Embeddings**: Text embedding model for vector similarity
- **ChromaDB**: Vector database for storing and searching embeddings
- **Uvicorn**: ASGI server for running the FastAPI application

## Error Handling

The API includes comprehensive error handling for:
- Invalid file formats
- Missing API keys
- Transcription failures
- Summarization errors
- Database storage issues
- File system errors

## Security Considerations

- Configure CORS properly for production use
- Implement file size limits
- Add authentication for production deployment
- Secure the OpenAI API key
- Consider rate limiting for production use

