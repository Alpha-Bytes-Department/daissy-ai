import os
import uuid
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from chroma import ChromaDBManager
from database import get_database_manager

load_dotenv()

class SimpleChatBot:
    def __init__(self, session_id: Optional[str] = None):
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize ChromaDB manager
        self.chroma_manager = ChromaDBManager()
        
        # Initialize database manager for persistent storage
        self.db_manager = get_database_manager()
        
        # Session management
        self.session_id = session_id or str(uuid.uuid4())
        
        # Create session in database if it doesn't exist (optimized)
        self.db_manager.create_chat_session_if_not_exists(self.session_id)
        
        # Store conversation history for continuity (loaded from database)
        self.conversation_history = self._load_conversation_history()
        
        # Cache for pending messages to batch database writes
        self._pending_messages = []
        
        # System prompt for the simple chat AI
        self.system_prompt = """You are a helpful and professional AI assistant that provides guidance and support through text-based conversations.

        Your capabilities:
        1. Provide professional consultation and advice
        2. Answer questions and help with problem-solving
        3. Engage in meaningful conversations

        Guidelines:
        - Provide empathetic, professional advice
        - Ask follow-up questions to better understand the user's situation
        - Maintain a warm, helpful tone
        - Focus on text-based assistance only
        """
    
    def _load_conversation_history(self) -> List[Dict[str, str]]:
        """Load conversation history from database"""
        try:
            # Load recent conversation history (last 10 messages for context)
            return self.db_manager.get_session_history(self.session_id, limit=10)
        except Exception as e:
            print(f"Warning: Could not load conversation history: {e}")
            return []
    
    def _save_message_to_db(self, role: str, content: str) -> None:
        """Queue a message for batch saving to the database"""
        message_id = str(uuid.uuid4())
        self._pending_messages.append({
            "session_id": self.session_id,
            "message_id": message_id,
            "role": role,
            "content": content
        })
    
    def _flush_pending_messages(self) -> None:
        """Save all pending messages to database in a single batch operation"""
        if self._pending_messages:
            try:
                self.db_manager.save_messages_batch(self._pending_messages)
                self._pending_messages.clear()
            except Exception as e:
                print(f"Warning: Could not save messages to database: {e}")
                self._pending_messages.clear()  # Clear to prevent memory buildup
    
    def get_session_id(self) -> str:
        """Get the current session ID"""
        return self.session_id
    
    def chat(self, user_query: str) -> Dict[str, Any]:
        """Simple chat function for text-only conversations"""
        try:
            # Build messages with conversation history
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add recent conversation history (last 10 messages to maintain context)
            recent_history = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
            messages.extend(recent_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_query})
            
            # Generate response without tools
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            
            # Store this interaction in conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Queue messages for batch database save
            self._save_message_to_db("user", user_query)
            self._save_message_to_db("assistant", ai_response)
            
            # Flush pending messages to database
            self._flush_pending_messages()
            
            return {
                "response": ai_response,
                "query": user_query,
                "conversation_length": len(self.conversation_history),
                "session_id": self.session_id
            }
            
        except Exception as e:
            raise Exception(f"Chat error: {str(e)}")
    
    def get_conversation_length(self) -> int:
        """Get the current conversation length"""
        return len(self.conversation_history)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get detailed session statistics (optimized version)"""
        try:
            return self.db_manager.get_session_stats_optimized(self.session_id)
        except Exception as e:
            return {"error": f"Could not retrieve session stats: {e}"}
    
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load an existing session"""
        try:
            # Flush any pending messages from current session
            self._flush_pending_messages()
            
            self.session_id = session_id
            self.conversation_history = self._load_conversation_history()
            return {
                "success": True,
                "session_id": session_id,
                "conversation_length": len(self.conversation_history),
                "message": f"Loaded session {session_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not load session: {e}"
            }
    
    def get_full_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the complete conversation history for the current session"""
        try:
            return self.db_manager.get_full_session_messages(self.session_id)
        except Exception as e:
            print(f"Warning: Could not retrieve full conversation history: {e}")
            return []

class AudioProvider:
    def __init__(self):
        # Initialize ChromaDB manager for audio search
        self.chroma_manager = ChromaDBManager()
    
    def get_audio_for_message(self, user_query: str) -> Dict[str, Any]:
        """Get the best matching audio file for a user message"""
        try:
            # Search for relevant audio
            audio_file = self._search_best_audio(user_query)
            
            return {
                "query": user_query,
                "audio_file": audio_file
            }
            
        except Exception as e:
            raise Exception(f"Audio provider error: {str(e)}")
    
    def _search_best_audio(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Search for the most relevant audio file based on user query"""
        try:
            search_results = self.chroma_manager.search_similar(user_query)
            
            best_audio = None
            best_score = 0
            uploads_dir = "uploads"
            
            if not os.path.exists(uploads_dir):
                return None
            
            for doc, metadata, distance, doc_id in zip(
                search_results["documents"],
                search_results["metadatas"], 
                search_results["distances"],
                search_results["ids"]
            ):
                # Only consider highly relevant results (distance < 0.8)
                if distance < 0.8:
                    relevance_score = 1 - distance
                    audio_id = metadata.get("audio_id", doc_id)
                    
                    # Check if audio file exists
                    for filename in os.listdir(uploads_dir):
                        if filename.startswith(audio_id):
                            if relevance_score > best_score:
                                best_score = relevance_score
                                best_audio = {
                                    "audio_id": audio_id,
                                    "filename": filename,
                                    "file_path": os.path.join(uploads_dir, filename),
                                    "relevance_score": relevance_score,
                                    "summary": doc
                                }
                            break
            
            return best_audio
            
        except Exception as e:
            print(f"Warning: Could not search for audio: {e}")
            return None
