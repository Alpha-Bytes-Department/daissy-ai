import json
import os
import uuid
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from chroma import ChromaDBManager
from database import get_database_manager

load_dotenv()

class RAGChatBot:
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
        
        # System prompt for the consultation AI
        self.system_prompt = """You are a professional consultant AI that helps users by providing guidance and determining when audio resources are necessary.

        Your capabilities:
        1. Provide professional consultation and advice
        2. Determine when audio files would be helpful for the user
        3. Search for and recommend relevant consultation audio when appropriate

        Guidelines:
        - Provide empathetic, professional advice as a consultant would
        - Only recommend audio files when they would genuinely add value to the consultation
        - Ask follow-up questions to better understand the user's situation
        - Maintain a warm, professional consultant tone
        - Use the search_audio_resources function only when audio would enhance your consultation
        """
    
    def _load_conversation_history(self) -> List[Dict[str, str]]:
        """Load conversation history from database"""
        try:
            # Load recent conversation history (last 10 messages for context)
            return self.db_manager.get_session_history(self.session_id, limit=10)
        except Exception as e:
            print(f"Warning: Could not load conversation history: {e}")
            return []
    
    def _save_message_to_db(self, role: str, content: str, audio_files: Optional[List[Dict]] = None, 
                           function_calls: Optional[List[Dict]] = None) -> None:
        """Queue a message for batch saving to the database"""
        message_id = str(uuid.uuid4())
        self._pending_messages.append({
            "session_id": self.session_id,
            "message_id": message_id,
            "role": role,
            "content": content,
            "audio_files": audio_files,
            "function_calls": function_calls
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
    
    def search_audio_resources(self, query: str, context: str = "") -> Dict[str, Any]:
        """Tool function to search for relevant audio resources"""
        try:
            search_results = self.chroma_manager.search_similar(query, n_results=3)
            
            context_items = []
            for i, (doc, metadata, distance, doc_id) in enumerate(zip(
                search_results["documents"],
                search_results["metadatas"], 
                search_results["distances"],
                search_results["ids"]
            )):
                # Only include highly relevant results (distance < 0.7)
                if distance < 0.7:
                    context_items.append({
                        "audio_id": metadata.get("audio_id", doc_id),
                        "summary": doc,
                        "metadata": metadata,
                        "relevance_score": 1 - distance,
                        "rank": i + 1
                    })
            
            # Find actual audio files
            audio_files = []
            uploads_dir = "uploads"
            
            if context_items and os.path.exists(uploads_dir):
                # Only get the most relevant audio file
                item = context_items[0]
                audio_id = item["audio_id"]
                
                for filename in os.listdir(uploads_dir):
                    if filename.startswith(audio_id):
                        audio_files.append({
                            "audio_id": audio_id,
                            "filename": filename,
                            "file_path": os.path.join(uploads_dir, filename),
                            "relevance_score": item["relevance_score"],
                            "summary": item["summary"]
                        })
                        break
            
            return {
                "found_relevant_audio": len(audio_files) > 0,
                "audio_files": audio_files,
                "context_items": context_items,
                "search_query": query
            }
        except Exception as e:
            return {
                "found_relevant_audio": False,
                "audio_files": [],
                "context_items": [],
                "error": str(e)
            }

    def call_function(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool functions"""
        if name == "search_audio_resources":
            return self.search_audio_resources(**args)
        raise ValueError(f"Unknown function: {name}")

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Define available tools for the AI agent"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_audio_resources",
                    "description": "Search for relevant consultation audio files when they would enhance the user's consultation experience. Only use this when audio resources would genuinely add value to your consultation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find relevant audio consultation content"
                            },
                            "context": {
                                "type": "string", 
                                "description": "Additional context about why audio would be helpful for this consultation"
                            }
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                }
            }
        ]
    
    def generate_response_with_tools(self, user_query: str) -> Dict[str, Any]:
        """Generate response using the agent tool call system"""
        try:
            # Build messages with conversation history
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add recent conversation history (last 6 messages to maintain context)
            recent_history = self.conversation_history[-6:] if len(self.conversation_history) > 6 else self.conversation_history
            messages.extend(recent_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_query})
            
            # Get tools definition
            tools = self.get_tools_definition()
            
            # Step 1: Call model with tools
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=400
            )
            
            assistant_message = response.choices[0].message
            messages.append(assistant_message)
            
            # Step 2: Handle function calls if any
            audio_files = []
            function_results = []
            
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    # Step 3: Execute function
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    function_result = self.call_function(function_name, function_args)
                    function_results.append(function_result)
                    
                    # Extract audio files if found
                    if function_result.get("found_relevant_audio"):
                        audio_files.extend(function_result.get("audio_files", []))
                    
                    # Step 4: Append function result to messages
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_result)
                    })
                
                # Step 5: Get final response with function results
                final_response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    tools=tools,
                    temperature=0.7,
                    max_tokens=400
                )
                
                ai_response = final_response.choices[0].message.content
            else:
                ai_response = assistant_message.content
            
            # Store this interaction in conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Queue messages for batch database save
            self._save_message_to_db("user", user_query)
            self._save_message_to_db("assistant", ai_response, audio_files=audio_files, function_calls=function_results)
            
            # Flush pending messages to database
            self._flush_pending_messages()
            
            return {
                "response": ai_response,
                "audio_files": audio_files,
                "function_calls_made": len(function_results),
                "function_results": function_results
            }
            
        except Exception as e:
            raise Exception(f"Error generating response with tools: {str(e)}")
    
    def chat(self, user_query: str) -> Dict[str, Any]:
        """Main chat function that acts as a consultant and intelligently provides audio when necessary"""
        try:
            # Use the agent-based approach to generate response and determine if audio is needed
            result = self.generate_response_with_tools(user_query)
            
            return {
                "response": result["response"],
                "query": user_query,
                "audio_files": result["audio_files"],  # Only contains audio when AI determined it was necessary
                "audio_provided": len(result["audio_files"]) > 0,
                "function_calls_made": result["function_calls_made"],
                "conversation_length": len(self.conversation_history),
                "session_id": self.session_id
            }
            
        except Exception as e:
            raise Exception(f"Chat error: {str(e)}")
    
    def get_audio_file_path(self, audio_id: str) -> Optional[str]:
        """Get the file path for a specific audio ID"""
        uploads_dir = "uploads"
        
        if not os.path.exists(uploads_dir):
            return None
        
        for filename in os.listdir(uploads_dir):
            if filename.startswith(audio_id):
                return os.path.join(uploads_dir, filename)
        
        return None
    
    def reset_conversation(self):
        """Reset the conversation history for a new consultation session"""
        # Flush any pending messages before resetting
        self._flush_pending_messages()
        
        # Clear in-memory history
        self.conversation_history = []
        
        # End current session in database
        self.db_manager.end_session(self.session_id)
        
        # Create new session
        self.session_id = str(uuid.uuid4())
        self.db_manager.create_chat_session_if_not_exists(self.session_id)
        
        return {
            "message": "Conversation history cleared. Ready for new consultation session.",
            "new_session_id": self.session_id
        }
    
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
            return self.db_manager.get_session_history(self.session_id)
        except Exception as e:
            return []
