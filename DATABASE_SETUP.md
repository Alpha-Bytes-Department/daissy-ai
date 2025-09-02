# Chat History Database Setup

This document explains how to set up PostgreSQL database integration for storing chat history in DAISSY AI.

## Features Added

- **Persistent Chat History**: All conversations are now saved to PostgreSQL database
- **Session Management**: Each chat session gets a unique ID for tracking
- **Message Storage**: Individual messages with metadata (audio files, function calls) are stored
- **Session Statistics**: Track session duration, message count, etc.
- **API Enhancements**: New endpoints for session management and history retrieval

## Database Schema

### Tables Created

1. **chat_sessions**
   - `id`: Primary key
   - `session_id`: Unique session identifier (UUID)
   - `created_at`: Session creation timestamp
   - `updated_at`: Last activity timestamp
   - `is_active`: Session status flag

2. **chat_messages**
   - `id`: Primary key
   - `session_id`: Foreign key to chat_sessions
   - `message_id`: Unique message identifier (UUID)
   - `role`: Message role ('user' or 'assistant')
   - `content`: Message content
   - `timestamp`: Message timestamp
   - `audio_files`: JSON field for audio file metadata
   - `function_calls`: JSON field for AI function call data
   - `metadata`: JSON field for additional data

## Setup Instructions

### 1. Install Dependencies

Run the setup script:
```bash
setup_postgres.bat
```

Or manually install:
```bash
pip install psycopg2-binary sqlalchemy alembic
```

### 2. Configure Database Connection

Copy the example environment file:
```bash
copy .env.example .env
```

Edit `.env` and set your PostgreSQL connection string:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/daissy_ai
```

### Example Connection Strings

- **Local PostgreSQL**: `postgresql://postgres:password@localhost:5432/daissy_ai`
- **Heroku**: `postgres://user:password@host:port/database`
- **AWS RDS**: `postgresql://username:password@endpoint:5432/database_name`
- **Azure**: `postgresql://username:password@server.postgres.database.azure.com:5432/database_name`

### 3. Run Database Migration

Create the tables:
```bash
python migrate_db.py
```

### 4. Start Your Application

```bash
python -m app.main
```

## API Changes

### New Chat Request Format

```json
{
  "query": "Your message here",
  "session_id": "optional-session-id"
}
```

### New Chat Response Format

```json
{
  "response": "AI response",
  "query": "User query",
  "audio_files": [],
  "audio_provided": false,
  "conversation_length": 5,
  "session_id": "uuid-here"
}
```

### New Endpoints

1. **GET /chat/history/{session_id}** - Get complete chat history
2. **POST /chat/load-session?session_id=xxx** - Load existing session
3. **GET /chat/status?session_id=xxx** - Get session statistics
4. **POST /chat/reset?session_id=xxx** - Reset specific session

## Usage Examples

### Starting a New Chat Session

```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "query": "Hello, I need consultation advice"
})

session_id = response.json()["session_id"]
```

### Continuing an Existing Session

```python
response = requests.post("http://localhost:8000/chat", json={
    "query": "Can you elaborate on that?",
    "session_id": session_id
})
```

### Getting Chat History

```python
response = requests.get(f"http://localhost:8000/chat/history/{session_id}")
history = response.json()["history"]
```

## Benefits

1. **Persistence**: Chat history survives server restarts
2. **Analytics**: Track user engagement and conversation patterns  
3. **Multi-user**: Support multiple concurrent users with separate sessions
4. **Audit Trail**: Complete record of all interactions
5. **Recovery**: Ability to resume conversations from any point

## Troubleshooting

### Common Issues

1. **Connection Error**: Check your DATABASE_URL format and credentials
2. **Table Not Found**: Run `python migrate_db.py` to create tables
3. **Permission Error**: Ensure database user has CREATE/INSERT/SELECT permissions

### Testing Database Connection

```python
from app.database import get_database_manager

try:
    db_manager = get_database_manager()
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` file to version control
2. **Connection String**: Use strong passwords and secure connections (SSL)
3. **Access Control**: Limit database user permissions to minimum required
4. **Data Privacy**: Consider encrypting sensitive conversation data
