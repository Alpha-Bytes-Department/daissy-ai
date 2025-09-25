import os
import uuid
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from chroma import ChromaDBManager
from database import get_database_manager

load_dotenv()

class SimpleChatBot:
    def __init__(self, user_id: str):
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
    
        # Store user_id for conversation management
        self.user_id = user_id
        
        # Initialize database manager for persistent storage
        self.db_manager = get_database_manager()
         
        # Store conversation history for continuity (loaded from database)
        self.conversation_history = self._load_conversation_history()
        
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
            return self.db_manager.get_user_history(self.user_id, limit=10)
        except Exception as e:
            print(f"Warning: Could not load conversation history: {e}")
            return []
    
    def _save_message_to_db(self, role: str, content: str) -> None:
        """Save a single message to database immediately"""
        try:
            message_id = str(uuid.uuid4())
            self.db_manager.save_message(
                user_id=self.user_id,
                message_id=message_id,
                role=role,
                content=content
            )
        except Exception as e:
            print(f"Warning: Could not save message to database: {e}")
    
    def get_user_id(self) -> str:
        """Get the current user ID"""
        return self.user_id
    
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
                model="gpt-4.1-nano",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            
            # Save user message to database immediately
            self._save_message_to_db("user", user_query)
            
            # Store user message in conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            
            # Save assistant response to database immediately
            self._save_message_to_db("assistant", ai_response)
            
            # Store assistant response in conversation history
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            return {
                "response": ai_response,
                "query": user_query,
                "conversation_length": len(self.conversation_history),
                "user_id": self.user_id
            }
            
        except Exception as e:
            raise Exception(f"Chat error: {str(e)}")
    
    def get_conversation_length(self) -> int:
        """Get the current conversation length"""
        return len(self.conversation_history)
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get detailed user statistics (optimized version)"""
        try:
            return self.db_manager.get_user_stats(self.user_id)
        except Exception as e:
            return {"error": f"Could not retrieve user stats: {e}"}
    
    def get_full_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the complete conversation history for the current user"""
        try:
            return self.db_manager.get_full_user_messages(self.user_id)
        except Exception as e:
            print(f"Warning: Could not retrieve full conversation history: {e}")
            return []

class AudioProvider:
    def __init__(self):
        # Initialize ChromaDB manager for audio search
        self.chroma_manager = ChromaDBManager()
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
    def _generate_suggestion(self, user_query: str, summary: str) -> str:
        try:
            self.system_prompt_suggestions = "You are a helpful assistant. " \
            "Provide very short compassionate answer based on the context below:" \
            f"{summary}" 
            # Build messages with conversation history
            messages = [{"role": "system", "content": self.system_prompt_suggestions}]
            
            # Add current user message
            messages.append({"role": "user", "content": user_query})
            
            # Generate response without tools
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            return ai_response
            
        except Exception as e:
            raise Exception(f"Chat error: {str(e)}")
    
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
            
            return best_audio, doc # best audio and summary 
            
        except Exception as e:
            print(f"Warning: Could not search for audio: {e}")
            return None

    def get_audio_and_suggestion(self, user_query: str) -> Dict[str, Any]:
        """Get the best matching audio file for a user message"""
        try:
            # Search for relevant audio
            audio_file, summary = self._search_best_audio(user_query)
            suggestion = self._generate_suggestion(user_query, summary)
            return {
                "suggestion": suggestion,
                "audio_file": audio_file
            }
            
        except Exception as e:
            raise Exception(f"Audio provider error: {str(e)}")
    
