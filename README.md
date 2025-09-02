# DAISSY AI - Audio Processing & Consultation Chat API

A comprehensive FastAPI-based service for processing audio files with transcription, summarization, vector storage, and intelligent chat consultation capabilities with persistent conversation history.

## 🚀 Features

### Audio Processing
- 🎵 **Audio File Upload**: Supports MP3, WAV, M4A, FLAC, and OGG formats
- 🔊 **Audio Transcription**: Uses OpenAI Whisper for accurate speech-to-text conversion
- 📝 **Text Summarization**: Leverages OpenAI GPT models for intelligent summarization
- 🔍 **Vector Search**: Stores embeddings in ChromaDB for semantic similarity search
- � **Audio Download**: Retrieve processed audio files by ID

### AI Chat Consultation
- 🤖 **Intelligent Chat Bot**: AI consultant that provides professional guidance
- 🎯 **Context-Aware Responses**: Automatically finds relevant audio resources when helpful
- 💾 **Persistent Chat History**: All conversations saved to PostgreSQL database
- 🔗 **Session Management**: Multiple concurrent chat sessions with unique IDs
- 📊 **Conversation Analytics**: Track session statistics and history

### Database Integration
- 🗄️ **PostgreSQL Storage**: Persistent storage for chat sessions and messages
- 🔄 **Session Continuity**: Resume conversations across server restarts
- 📈 **Analytics Ready**: Track user engagement and conversation patterns
- 🔐 **Multi-user Support**: Isolated sessions for concurrent users

## 📋 Prerequisites

- Python 3.8+
- OpenAI API Key
- PostgreSQL Database (for chat history storage)

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd daissy-ai
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file:
```bash
copy .env.example .env  # Windows
# or
cp .env.example .env    # Linux/Mac
```

Configure your `.env` file:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# PostgreSQL Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/daissy_ai
```

### 5. Database Setup

For chat history functionality, set up PostgreSQL:
```bash
# Install PostgreSQL dependencies (if not already installed)
pip install psycopg2-binary sqlalchemy alembic

# Run database migration
python migrate_db.py
```

### 6. Start the Application
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Root Endpoint**: `http://localhost:8000/` (API overview)

## 🔌 API Endpoints

All endpoints are prefixed with `/api/v1`

### 🎵 Audio Processing Endpoints

#### 1. Upload Audio File
**POST** `/api/v1/upload-audio`

Upload and process an audio file (transcription + summarization).

**Request:**
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Body**: Audio file (MP3, WAV, M4A, FLAC, OGG)

**Response:**
```json
{
  "success": true,
  "audio_id": "uuid-string",
  "filename": "unique-filename.mp3",
  "original_filename": "original-name.mp3",
  "transcription": "Full transcribed text from audio...",
  "summary": "AI-generated summary of the content...",
  "message": "Audio file processed and stored successfully"
}
```

#### 2. Search Audio Summaries
**GET** `/api/v1/search`

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

#### 3. Get Audio Summary
**GET** `/api/v1/audio/{audio_id}`

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

#### 4. Download Audio File
**GET** `/api/v1/download-audio/{audio_id}`

Download the original audio file by ID.

**Response:** Binary audio file with appropriate headers.

#### 5. Get Audio File Info
**GET** `/api/v1/audio-file-info/{audio_id}`

Get file information without downloading.

**Response:**
```json
{
  "success": true,
  "audio_id": "uuid-string",
  "filename": "filename.mp3",
  "file_size": 1024000,
  "file_path": "uploads/filename.mp3",
  "exists": true
}
```

### 🤖 Chat & Consultation Endpoints

#### 6. Chat with AI Consultant
**POST** `/api/v1/chat`

Chat with the AI consultant that provides guidance and finds relevant audio resources.

**Request Body:**
```json
{
  "query": "I need advice on project management",
  "session_id": "optional-existing-session-id"
}
```

**Response:**
```json
{
  "response": "AI consultant response with guidance...",
  "query": "User's question",
  "audio_files": [
    {
      "audio_id": "uuid",
      "filename": "relevant-audio.mp3",
      "relevance_score": 0.85,
      "summary": "Summary of relevant audio content"
    }
  ],
  "audio_provided": true,
  "conversation_length": 3,
  "session_id": "unique-session-id"
}
```

#### 7. Get Chat Status
**GET** `/api/v1/chat/status`

Get current conversation status and statistics.

**Parameters:**
- `session_id` (optional): Specific session ID to check

**Response:**
```json
{
  "success": true,
  "session_id": "current-session-id",
  "conversation_length": 5,
  "status": "active",
  "session_stats": {
    "session_id": "uuid",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:30:00",
    "is_active": true,
    "message_count": 10,
    "first_message_time": "2024-01-01T10:00:00",
    "last_message_time": "2024-01-01T10:30:00"
  }
}
```

#### 8. Reset Chat Session
**POST** `/api/v1/chat/reset`

Reset conversation history and start a new session.

**Parameters:**
- `session_id` (optional): Specific session to reset

**Response:**
```json
{
  "success": true,
  "message": "Conversation history cleared. Ready for new consultation session.",
  "new_session_id": "new-uuid"
}
```

#### 9. Get Chat History
**GET** `/api/v1/chat/history/{session_id}`

Retrieve complete conversation history for a session.

**Response:**
```json
{
  "success": true,
  "session_id": "session-uuid",
  "history": [
    {
      "role": "user",
      "content": "Hello, I need help"
    },
    {
      "role": "assistant", 
      "content": "I'd be happy to help you..."
    }
  ],
  "message_count": 4
}
```

#### 10. Load Existing Session
**POST** `/api/v1/chat/load-session`

Load and resume an existing chat session.

**Parameters:**
- `session_id` (required): Session ID to load

**Response:**
```json
{
  "success": true,
  "session_id": "loaded-session-id",
  "conversation_length": 6,
  "message": "Loaded session successfully"
}
```

#### 11. Health Check
**GET** `/api/v1/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "audio-processing-api"
}
```

## 💻 Usage Examples

### 🔧 Using cURL

#### Upload and Process Audio
```bash
# Upload an audio file for processing
curl -X POST "http://localhost:8000/api/v1/upload-audio" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@consultation-audio.mp3"
```

#### Search for Relevant Content
```bash
# Search for similar audio summaries
curl -X GET "http://localhost:8000/api/v1/search?query=project%20management&limit=3"
```

#### Start a Chat Consultation
```bash
# Start chatting with AI consultant
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"query": "I need advice on handling difficult team members"}'
```

#### Continue Existing Chat Session
```bash
# Continue conversation with session ID
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Can you provide more specific strategies?",
       "session_id": "existing-session-uuid"
     }'
```

#### Get Chat History
```bash
# Retrieve conversation history
curl -X GET "http://localhost:8000/api/v1/chat/history/session-uuid"
```

### 🐍 Using Python

#### Complete Workflow Example
```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 1. Upload and process audio file
def upload_audio(file_path):
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/upload-audio",
            files={"file": f}
        )
    return response.json()

# 2. Start a consultation chat
def start_consultation(question):
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"query": question}
    )
    return response.json()

# 3. Continue consultation with session
def continue_consultation(question, session_id):
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "query": question,
            "session_id": session_id
        }
    )
    return response.json()

# 4. Search for relevant audio content
def search_audio(query, limit=5):
    response = requests.get(
        f"{BASE_URL}/search",
        params={"query": query, "limit": limit}
    )
    return response.json()

# 5. Get session history
def get_chat_history(session_id):
    response = requests.get(f"{BASE_URL}/chat/history/{session_id}")
    return response.json()

# Example usage
if __name__ == "__main__":
    # Upload audio file
    print("1. Uploading audio file...")
    upload_result = upload_audio("consultation.mp3")
    print(f"Audio ID: {upload_result['audio_id']}")
    
    # Start consultation
    print("\n2. Starting consultation...")
    chat_result = start_consultation(
        "I'm struggling with time management in my business. Can you help?"
    )
    session_id = chat_result["session_id"]
    print(f"AI Response: {chat_result['response']}")
    
    # Continue conversation
    print("\n3. Continuing conversation...")
    follow_up = continue_consultation(
        "What specific techniques would you recommend?",
        session_id
    )
    print(f"AI Response: {follow_up['response']}")
    
    # Check if relevant audio was provided
    if follow_up["audio_provided"]:
        print(f"Relevant audio provided: {follow_up['audio_files']}")
    
    # Get conversation history
    print("\n4. Getting conversation history...")
    history = get_chat_history(session_id)
    print(f"Total messages: {history['message_count']}")
    for msg in history['history']:
        print(f"{msg['role']}: {msg['content'][:100]}...")
```

#### Advanced Session Management
```python
import requests

class DaissyAIClient:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session_id = None
    
    def chat(self, message):
        """Send a chat message and get response"""
        payload = {"query": message}
        if self.session_id:
            payload["session_id"] = self.session_id
        
        response = requests.post(f"{self.base_url}/chat", json=payload)
        result = response.json()
        
        # Store session ID for future messages
        self.session_id = result["session_id"]
        return result
    
    def get_status(self):
        """Get current session status"""
        params = {"session_id": self.session_id} if self.session_id else {}
        response = requests.get(f"{self.base_url}/chat/status", params=params)
        return response.json()
    
    def reset_session(self):
        """Reset current session"""
        params = {"session_id": self.session_id} if self.session_id else {}
        response = requests.post(f"{self.base_url}/chat/reset", params=params)
        result = response.json()
        self.session_id = None
        return result
    
    def get_history(self):
        """Get conversation history"""
        if not self.session_id:
            return {"error": "No active session"}
        
        response = requests.get(f"{self.base_url}/chat/history/{self.session_id}")
        return response.json()

# Usage example
client = DaissyAIClient()

# Start conversation
response1 = client.chat("I need help with project planning")
print(f"AI: {response1['response']}")

# Continue conversation
response2 = client.chat("Can you provide a step-by-step approach?")
print(f"AI: {response2['response']}")

# Get session info
status = client.get_status()
print(f"Session has {status['conversation_length']} messages")

# Get full history
history = client.get_history()
for msg in history['history']:
    print(f"{msg['role'].title()}: {msg['content']}")
```

### 🌐 JavaScript/Node.js Example

```javascript
const axios = require('axios');

class DaissyAIClient {
    constructor(baseUrl = 'http://localhost:8000/api/v1') {
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }

    async chat(message) {
        const payload = { query: message };
        if (this.sessionId) {
            payload.session_id = this.sessionId;
        }

        try {
            const response = await axios.post(`${this.baseUrl}/chat`, payload);
            this.sessionId = response.data.session_id;
            return response.data;
        } catch (error) {
            console.error('Chat error:', error.response?.data || error.message);
            throw error;
        }
    }

    async uploadAudio(filePath) {
        const FormData = require('form-data');
        const fs = require('fs');
        
        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));

        try {
            const response = await axios.post(`${this.baseUrl}/upload-audio`, form, {
                headers: form.getHeaders()
            });
            return response.data;
        } catch (error) {
            console.error('Upload error:', error.response?.data || error.message);
            throw error;
        }
    }

    async searchAudio(query, limit = 5) {
        try {
            const response = await axios.get(`${this.baseUrl}/search`, {
                params: { query, limit }
            });
            return response.data;
        } catch (error) {
            console.error('Search error:', error.response?.data || error.message);
            throw error;
        }
    }
}

// Usage
async function example() {
    const client = new DaissyAIClient();
    
    // Start consultation
    const response = await client.chat("I need business advice on scaling my startup");
    console.log("AI:", response.response);
    
    if (response.audio_provided) {
        console.log("Relevant audio resources:", response.audio_files);
    }
    
    // Continue conversation
    const followUp = await client.chat("What are the key metrics I should track?");
    console.log("AI:", followUp.response);
}

example().catch(console.error);
```

## 🗄️ Database Schema

### Chat Sessions Table (`chat_sessions`)
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `session_id` | VARCHAR(255) | Unique session identifier (UUID) |
| `created_at` | DATETIME | Session creation timestamp |
| `updated_at` | DATETIME | Last activity timestamp |
| `is_active` | BOOLEAN | Session status flag |

### Chat Messages Table (`chat_messages`)
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `session_id` | VARCHAR(255) | Foreign key to chat_sessions |
| `message_id` | VARCHAR(255) | Unique message identifier (UUID) |
| `role` | VARCHAR(50) | Message role ('user' or 'assistant') |
| `content` | TEXT | Message content |
| `timestamp` | DATETIME | Message timestamp |
| `audio_files` | JSON | Audio file metadata (if any) |
| `function_calls` | JSON | AI function call data (if any) |
| `extra_metadata` | JSON | Additional metadata |

## 💾 File Storage Structure

```
daissy-ai/
├── uploads/                    # Audio files storage
│   ├── {uuid}.mp3             # Processed audio files
│   ├── {uuid}.wav
│   └── ...
├── chroma_db/                 # Vector database
│   ├── chroma.sqlite3         # ChromaDB metadata
│   └── collections/           # Vector embeddings
├── app/
│   ├── main.py               # FastAPI application
│   ├── api.py                # API endpoints
│   ├── chat.py               # Chat bot logic
│   ├── database.py           # PostgreSQL models
│   ├── chroma.py             # Vector database manager
│   └── transcribe.py         # Audio processing
└── .env                      # Environment configuration
```

## 🔧 Technologies Used

### Core Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **Pydantic**: Data validation and settings management

### AI & ML
- **OpenAI Whisper**: Speech recognition for audio transcription
- **OpenAI GPT Models**: Language models for summarization and chat
- **OpenAI Embeddings**: Text embedding models for vector similarity
- **ChromaDB**: Vector database for semantic search

### Database & Storage
- **PostgreSQL**: Relational database for chat history and sessions
- **SQLAlchemy**: SQL toolkit and ORM for Python
- **Alembic**: Database migration tool

### Audio Processing
- **FFmpeg**: Audio format conversion and processing
- **Python Audio Libraries**: Audio file handling and manipulation

## 🔒 Security Considerations

### Production Deployment
- **Environment Variables**: Store sensitive data (API keys, DB credentials) in environment variables
- **CORS Configuration**: Configure CORS properly for your domain (currently set to allow all origins)
- **Authentication**: Implement API authentication for production use
- **Rate Limiting**: Add rate limiting to prevent abuse
- **File Size Limits**: Implement file size restrictions for uploads
- **Input Validation**: Validate all inputs and sanitize file uploads

### Database Security
- **Connection Security**: Use SSL/TLS for database connections
- **User Permissions**: Create dedicated database user with minimum required permissions
- **Data Encryption**: Consider encrypting sensitive conversation data
- **Backup Strategy**: Implement regular database backups

### API Security
```python
# Example production CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],              # Specific methods only
    allow_headers=["Authorization", "Content-Type"],
)
```

## 🚀 Deployment

### Local Development
```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Deployment

#### Using Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Using Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Environment Variables for Production
```env
# Production environment
OPENAI_API_KEY=your_production_api_key
DATABASE_URL=postgresql://user:pass@prod-db:5432/daissy_ai
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
LOG_LEVEL=INFO
```

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Errors
```python
# Test database connection
from app.database import get_database_manager

try:
    db_manager = get_database_manager()
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
```

#### OpenAI API Issues
```bash
# Verify API key
curl -H "Authorization: Bearer your-api-key" \
     https://api.openai.com/v1/models
```

#### Audio Processing Issues
- Ensure FFmpeg is installed and accessible
- Check audio file format compatibility
- Verify file size limits

#### ChromaDB Issues
- Check if `chroma_db` directory has proper permissions
- Verify ChromaDB version compatibility

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with debug
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

## 📈 Performance Optimization

### Recommended Settings
- **Database Connection Pooling**: Configure SQLAlchemy pool settings
- **Async Processing**: Use background tasks for long-running operations
- **Caching**: Implement Redis caching for frequently accessed data
- **File Storage**: Consider cloud storage (AWS S3, Azure Blob) for audio files

### Monitoring
- **Health Checks**: Use `/api/v1/health` endpoint for monitoring
- **Metrics**: Implement Prometheus metrics for production monitoring
- **Logging**: Configure structured logging for better observability

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the interactive API documentation at `/docs`
3. Check the database setup guide in `DATABASE_SETUP.md`
4. Verify your environment configuration

## 📄 License

This project is licensed under the MIT License.

