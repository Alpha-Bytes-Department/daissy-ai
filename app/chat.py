import openai
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

try:
    from .chroma import ChromaDBManager
except ImportError:
    from chroma import ChromaDBManager

load_dotenv()

class RAGChatBot:
    def __init__(self):
        # Initialize OpenAI client
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize ChromaDB manager
        self.chroma_manager = ChromaDBManager()
        
        # Store conversation history for continuity
        self.conversation_history = []
        
        # System prompt for the consultation AI
        self.system_prompt = """You are a professional consultant AI that helps users by:
        1. Finding relevant consultation audio files that match their needs
        2. Acting as a consultant yourself to continue the conversation and provide guidance

        When responding:
        - If you find a relevant consultation audio, mention it and provide the user with additional consultant guidance
        - Provide professional, empathetic, and helpful advice as a consultant would
        - Ask follow-up questions when appropriate to better understand the user's situation
        - Offer practical suggestions and guidance beyond just directing to audio files
        - Maintain a warm, professional consultant tone throughout the conversation
        - You can reference the consultation audio as supplementary material while also providing your own consultation

        Your role is to be both a resource finder AND an active consultant in the conversation.
        Provide comprehensive help that includes both the audio resource and your own professional guidance.
        """
    
    def retrieve_relevant_context(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant consultation audio summaries based on the user query"""
        try:
            search_results = self.chroma_manager.search_similar(query, n_results)
            
            context_items = []
            for i, (doc, metadata, distance, doc_id) in enumerate(zip(
                search_results["documents"],
                search_results["metadatas"], 
                search_results["distances"],
                search_results["ids"]
            )):
                context_items.append({
                    "audio_id": metadata.get("audio_id", doc_id),
                    "summary": doc,
                    "metadata": metadata,
                    "relevance_score": 1 - distance,  # Convert distance to similarity score
                    "rank": i + 1
                })
            
            return context_items
        except Exception as e:
            raise Exception(f"Error retrieving context: {str(e)}")
    
    def format_context_for_llm(self, context_items: List[Dict[str, Any]]) -> str:
        """Format retrieved context for the LLM"""
        if not context_items:
            return "No relevant audio content found for this query."
        
        formatted_context = []
        for item in context_items:
            formatted_context.append(f"""Audio ID: {item['audio_id']}
Summary: {item['summary']}
Relevance Score: {item['relevance_score']:.3f}
---""")
        
        return "\n".join(formatted_context)
    
    def generate_response(self, user_query: str, context_available: bool = False, context_summary: str = "") -> str:
        """Generate response as a consultant, optionally referencing available consultation audio"""
        try:
            if context_available and context_summary:
                user_content = f"""A user is asking: "{user_query}"

I have found a relevant consultation audio that covers: {context_summary}

Please act as a professional consultant and:
1. Mention the relevant consultation audio I found for them
2. Provide your own consultant guidance and advice on their question
3. Continue the conversation as their consultant, offering practical help
4. Ask follow-up questions if appropriate to better understand their needs

Provide a comprehensive consultant response that includes both the audio resource and your own professional guidance."""
            else:
                user_content = f"""A user is asking: "{user_query}"

I did not find any specific consultation audio for this query.

Please act as a professional consultant and:
1. Acknowledge that while I don't have a specific consultation audio for this topic, you can still help as their consultant
2. Provide professional guidance and advice on their question
3. Continue the conversation as their consultant, offering practical help
4. Ask follow-up questions if appropriate to better understand their needs

Provide a comprehensive consultant response focused on helping them with their inquiry."""

            # Build messages with conversation history
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add recent conversation history (last 6 messages to maintain context)
            recent_history = self.conversation_history[-6:] if len(self.conversation_history) > 6 else self.conversation_history
            messages.extend(recent_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_content})
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=400  # Increased for more comprehensive consultant responses
            )
            
            ai_response = response.choices[0].message.content
            
            # Store this interaction in conversation history
            self.conversation_history.append({"role": "user", "content": user_query})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            return ai_response
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")
    
    def chat(self, user_query: str, n_results: int = 3) -> Dict[str, Any]:
        """Main chat function that acts as a consultant and provides relevant consultation audio"""
        try:
            # Retrieve relevant context
            context_items = self.retrieve_relevant_context(user_query, n_results)
            
            # Prepare context summary for the AI consultant
            context_summary = ""
            has_relevant_audio = len(context_items) > 0
            
            if has_relevant_audio:
                # Use the most relevant item's summary for context
                context_summary = context_items[0]["summary"][:300] + "..." if len(context_items[0]["summary"]) > 300 else context_items[0]["summary"]
            
            # Generate response as a consultant
            response = self.generate_response(user_query, has_relevant_audio, context_summary)
            
            # Prepare audio file paths for relevant sources - limit to 1 most relevant
            audio_files = []
            uploads_dir = "uploads"
            
            # Only get the most relevant audio file (first in the sorted list)
            if context_items:
                item = context_items[0]  # Most relevant item
                audio_id = item["audio_id"]
                
                # Look for audio file with this ID in uploads folder
                if os.path.exists(uploads_dir):
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
                "response": response,
                "query": user_query,
                "context_used": context_items,
                "audio_files": audio_files,  # Now contains at most 1 audio file
                "sources_count": len(context_items)
            }
            
        except Exception as e:
            raise Exception(f"Chat error: {str(e)}")
    
    def get_audio_file_path(self, audio_id: str) -> Optional[str]:
        """Get the file path for a specific audio ID"""
        uploads_dir = "uploads"
        
        if not os.path.exists(uploads_dir):
            return None
    
    def reset_conversation(self):
        """Reset the conversation history for a new consultation session"""
        self.conversation_history = []
        return {"message": "Conversation history cleared. Ready for new consultation session."}
    
    def get_conversation_length(self) -> int:
        """Get the current conversation length"""
        return len(self.conversation_history)
        
        for filename in os.listdir(uploads_dir):
            if filename.startswith(audio_id):
                return os.path.join(uploads_dir, filename)
        
        return None
