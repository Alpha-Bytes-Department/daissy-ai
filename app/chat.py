import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

try:
    from .chroma import ChromaDBManager
except ImportError:
    from chroma import ChromaDBManager

load_dotenv()

class RAGChatBot:
    def __init__(self):
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize ChromaDB manager
        self.chroma_manager = ChromaDBManager()
        
        # Store conversation history for continuity
        self.conversation_history = []
        
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
                "conversation_length": len(self.conversation_history)
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
        self.conversation_history = []
        return {"message": "Conversation history cleared. Ready for new consultation session."}
    
    def get_conversation_length(self) -> int:
        """Get the current conversation length"""
        return len(self.conversation_history)
