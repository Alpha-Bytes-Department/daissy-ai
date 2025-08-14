#!/usr/bin/env python3
"""
Test script for the RAG-based chat API
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_chat_api():
    """Test the chat API functionality"""
    
    print("=== Testing RAG Chat API ===\n")
    
    # Test 1: Simple chat query with consultation
    print("1. Testing AI consultant with initial query...")
    chat_data = {
        "query": "I've been feeling overwhelmed with work stress lately"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        if response.status_code == 200:
            result = response.json()
            print("✓ Chat endpoint successful!")
            print(f"Response: {result['response'][:200]}...")
            print(f"Sources found: {result['sources_count']}")
            print(f"Audio files referenced: {len(result['audio_files'])} (max 1)")
            
            # Show audio file that was referenced (should be at most 1)
            if result['audio_files']:
                audio = result['audio_files'][0]  # Only one audio file expected
                print(f"\nReferenced audio file:")
                print(f"  - {audio['filename']} (ID: {audio['audio_id']}, Score: {audio['relevance_score']:.3f})")
            else:
                print("\nNo audio files referenced")
        else:
            print(f"✗ Chat endpoint failed: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"✗ Chat test failed: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Follow-up consultation question
    print("2. Testing follow-up consultation...")
    try:
        followup_data = {
            "query": "That's helpful. Can you give me some specific techniques I can try today?"
        }
        response = requests.post(f"{BASE_URL}/chat", json=followup_data)
        if response.status_code == 200:
            result = response.json()
            print("✓ Follow-up consultation successful!")
            print(f"AI Response: {result['response'][:200]}...")
        else:
            print(f"✗ Follow-up consultation failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Follow-up test failed: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Check conversation status
    print("3. Testing conversation status...")
    try:
        response = requests.get(f"{BASE_URL}/chat/status")
        if response.status_code == 200:
            result = response.json()
            print("✓ Conversation status check successful!")
            print(f"Conversation length: {result['conversation_length']}")
            print(f"Status: {result['status']}")
        else:
            print(f"✗ Conversation status failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Status check failed: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Reset conversation
    print("4. Testing conversation reset...")
    try:
        response = requests.post(f"{BASE_URL}/chat/reset")
        if response.status_code == 200:
            result = response.json()
            print("✓ Conversation reset successful!")
            print(f"Message: {result['message']}")
        else:
            print(f"✗ Conversation reset failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Reset test failed: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 5: Test GET chat endpoint
    print("5. Testing GET consultation endpoint...")
    try:
        params = {
            "query": "I need advice on managing difficult conversations with my team"
        }
        response = requests.get(f"{BASE_URL}/chat", params=params)
        if response.status_code == 200:
            result = response.json()
            print("✓ GET Consultation endpoint successful!")
            print(f"Response: {result['response'][:200]}...")
            print(f"Sources found: {result['sources_count']}")
        else:
            print(f"✗ GET Consultation endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"✗ GET Chat test failed: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Search for audio files
    print("3. Testing search endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/search", params={"query": "certification", "limit": 3})
        if response.status_code == 200:
            result = response.json()
            print("✓ Search endpoint successful!")
            print(f"Found {len(result['results']['documents'])} results")
            
            # Test audio file info for first result if available
            if result['results']['ids']:
                audio_id = result['results']['ids'][0]
                print(f"\n4. Testing audio file info for ID: {audio_id}")
                
                info_response = requests.get(f"{BASE_URL}/audio-file-info/{audio_id}")
                if info_response.status_code == 200:
                    info_result = info_response.json()
                    print("✓ Audio file info successful!")
                    print(f"  File: {info_result['filename']}")
                    print(f"  Size: {info_result['file_size']} bytes")
                else:
                    print(f"✗ Audio file info failed: {info_response.status_code}")
        else:
            print(f"✗ Search endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Search test failed: {str(e)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Health check
    print("5. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            result = response.json()
            print("✓ Health check successful!")
            print(f"Status: {result['status']}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Health check failed: {str(e)}")

def test_api_documentation():
    """Test the API documentation endpoints"""
    print("\n=== API Documentation ===")
    
    try:
        response = requests.get("http://127.0.0.1:8000/")
        if response.status_code == 200:
            result = response.json()
            print("✓ Root endpoint successful!")
            print("Available endpoints:")
            for key, value in result.get('endpoints', {}).items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"✗ Documentation test failed: {str(e)}")

if __name__ == "__main__":
    print("Starting API tests...\n")
    print("Make sure the FastAPI server is running on http://127.0.0.1:8000")
    print("You can start it with: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload\n")
    
    test_api_documentation()
    test_chat_api()
    
    print("\n=== Test Complete ===")
    print("You can also test the API interactively at: http://127.0.0.1:8000/docs")
