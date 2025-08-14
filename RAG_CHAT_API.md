# AI Consultant API Documentation

## Overview

This API provides an AI consultant that:

1. **Finds** relevant consultation audio files based on user queries
2. **Acts as a consultant** itself, providing professional guidance and advice
3. **Continues conversations** with memory of previous interactions
4. **Combines resources** with active consultation in a seamless experience

The AI works in dual mode:
- **Resource Provider**: Finds and provides relevant consultation audio files
- **Active Consultant**: Continues conversations, asks follow-up questions, and provides professional guidance

## Chat Endpoints

### POST `/api/v1/chat`
Chat with the AI consultant that finds resources and provides professional guidance.

**Request Body:**
```json
{
  "query": "I've been feeling really anxious lately and it's affecting my work"
}
```

**Response:**
```json
{
  "response": "I understand you're experiencing anxiety that's impacting your work, and I want to help you with this. I've found a consultation audio specifically about managing workplace anxiety that includes practical techniques and coping strategies. \n\nIn addition to that resource, let me offer some immediate guidance: anxiety often feels overwhelming, but there are effective ways to manage it. Can you tell me more about when the anxiety feels strongest - is it during specific work situations, or more throughout the day? Understanding the patterns can help us develop the best approach for you.\n\nThe consultation audio I found will give you a comprehensive framework, and I'm here to work through this with you as well.",
  "query": "I've been feeling really anxious lately and it's affecting my work",
  "sources_count": 1,
  "audio_files": [
    {
      "audio_id": "8dab72e3-3f04-4ce9-90d2-4d3e231489bf",
      "filename": "workplace-anxiety-consultation.mp3",
      "file_path": "uploads/8dab72e3-3f04-4ce9-90d2-4d3e231489bf.mp3",
      "relevance_score": 0.892,
      "summary": "Consultation covering workplace anxiety management..."
    }
  ]
}
```

### POST `/api/v1/chat/reset`
Reset the conversation history to start a new consultation session.

**Response:**
```json
{
  "success": true,
  "message": "Conversation history cleared. Ready for new consultation session."
}
```

### GET `/api/v1/chat/status`
Get current conversation status and length.

**Response:**
```json
{
  "success": true,
  "conversation_length": 4,
  "status": "active"
}
```

### GET `/api/v1/chat`
Alternative consultant endpoint using query parameters.

**Query Parameters:**
- `query` (string, required): The user's question or concern

**Example:**
```
GET /api/v1/chat?query=I'm having trouble sleeping and it's affecting my daily life
```

### GET `/api/v1/download-audio/{audio_id}`
Download the original audio file by audio ID.

**Example:**
```
GET /api/v1/download-audio/8dab72e3-3f04-4ce9-90d2-4d3e231489bf
```

**Response:** Binary audio file download

### GET `/api/v1/audio-file-info/{audio_id}`
Get information about an audio file without downloading it.

**Response:**
```json
{
  "success": true,
  "audio_id": "8dab72e3-3f04-4ce9-90d2-4d3e231489bf",
  "filename": "8dab72e3-3f04-4ce9-90d2-4d3e231489bf.mp3",
  "file_size": 1234567,
  "file_path": "uploads/8dab72e3-3f04-4ce9-90d2-4d3e231489bf.mp3",
  "exists": true
}
```

## How It Works

1. **Upload Audio**: Use `/api/v1/upload-audio` to upload audio files
2. **Ask Questions**: Use `/api/v1/chat` to ask questions about the audio content
3. **Get Responses**: Receive AI-generated responses with reference to the most relevant audio file
4. **Access Audio**: Download or get info about the referenced audio file

## Example Usage

### 1. Upload an Audio File
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/upload-audio" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_audio.mp3"
```

### 2. Chat About the Audio
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main topics discussed?"
  }'
```

### 3. Download Referenced Audio
```bash
curl -O "http://127.0.0.1:8000/api/v1/download-audio/{audio_id}"
```

## Python Example

```python
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

# Chat with the system
response = requests.post(f"{BASE_URL}/chat", json={
    "query": "What certifications were mentioned?"
})

if response.status_code == 200:
    result = response.json()
    print(f"AI Response: {result['response']}")
    
    # Download the referenced audio file (at most 1)
    if result['audio_files']:
        audio = result['audio_files'][0]  # Only 1 audio file returned
        audio_id = audio['audio_id']
        download_response = requests.get(f"{BASE_URL}/download-audio/{audio_id}")
        
        if download_response.status_code == 200:
            with open(f"downloaded_{audio['filename']}", "wb") as f:
                f.write(download_response.content)
            print(f"Downloaded: {audio['filename']}")
    else:
        print("No audio file referenced in the response")
```

## Features

- **Semantic Search**: Finds relevant audio content based on meaning, not just keywords
- **Contextual Responses**: AI responses are grounded in actual audio content
- **Single Audio Reference**: Returns the most relevant audio file (max 1) to keep responses focused
- **Relevance Scoring**: See how relevant the audio source is to your query
- **Multiple Context Sources**: Combines information from multiple audio summaries in responses while returning only the most relevant audio file

## Testing

Run the test script to verify the API is working:

```bash
python test_chat_api.py
```

Or visit the interactive API documentation at: http://127.0.0.1:8000/docs

## Error Handling

The API includes comprehensive error handling:
- Empty queries return 400 Bad Request
- Invalid audio IDs return 404 Not Found  
- Processing errors return 500 Internal Server Error
- All responses include detailed error messages

## Environment Setup

Make sure you have:
1. `OPENAI_API_KEY` environment variable set
2. Required dependencies installed (see `requirements.txt`)
3. ChromaDB initialized (happens automatically on first run)
4. Uploads directory (created automatically)
