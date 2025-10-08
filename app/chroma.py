import chromadb
from chromadb.config import Settings
import openai
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

class ChromaDBManager:
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Initialize OpenAI client
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="audio_summaries",
            metadata={"description": "Collection for audio transcription summaries"}
        )
    
    def get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI's text-embedding-ada-002 model"""
        try:
            response = openai.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Error generating embeddings: {str(e)}")
         
    def store_summary(self, audio_id: str, summary: str, title: str, category: str, use_case: str, emotion: str, duration: str, status: str = "active") -> str:
        """Store summary with embeddings in ChromaDB"""
        try:
            # Generate embeddings for the summary
            embeddings = self.get_embeddings(summary)
            
            # Prepare metadata
            metadata = {
                "audio_id": audio_id,
                "summary_length": len(summary),
                "title": title,
                "category": category,
                "use_case": use_case,
                "emotion": emotion,
                "duration": duration,
                "status": status
            }
            
            
            # Store in ChromaDB
            self.collection.add(
                embeddings=[embeddings],
                documents=[summary],
                metadatas=[metadata],
                ids=[audio_id]
            )
            
            return audio_id
        except Exception as e:
            raise Exception(f"Error storing summary: {str(e)}")
        
    def search_similar(self, query: str, n_results: int = 1) -> List[Dict[str, Any]]:
        """Search for similar summaries"""
        try:
            query_embeddings = self.get_embeddings(query)
            
            results = self.collection.query(
                query_embeddings=[query_embeddings],
                n_results=n_results
            )
            
            return {
                "documents": results["documents"][0],
                "metadatas": results["metadatas"][0],
                "distances": results["distances"][0],
                "ids": results["ids"][0]
            }
        except Exception as e:
            raise Exception(f"Error searching: {str(e)}")
    
    def get_audio_by_query(self, query: str) -> List[Dict[str, Any]]:
        """Filter audios by query string matching title, category, use_case, or emotion"""
        try:
            # Get all audios first
            result = self.collection.get(
                include=["metadatas"]
            )
            
            if not result["ids"]:
                return []
            
            # Filter based on query string matching metadata fields
            filtered_audios = []
            query_lower = query.lower()
            
            for i in range(len(result["ids"])):
                metadata = result["metadatas"][i]
                
                # Check if query matches any of the metadata fields
                if (query_lower in metadata.get("title", "").lower() or
                    query_lower in metadata.get("category", "").lower() or
                    query_lower in metadata.get("use_case", "").lower() or
                    query_lower in metadata.get("emotion", "").lower()):
                    
                    filtered_audios.append({"metadata": metadata})
            
            return filtered_audios
        except Exception as e:
            raise Exception(f"Error filtering audios: {str(e)}")
    
    def get_all_audios(self) -> List[Dict[str, Any]]:
        """Retrieve all audio summaries with their metadata"""
        try:
            result = self.collection.get(
                include=["metadatas"]
            )
            
            if not result["ids"]:
                return []
            
            audios = []
            for i in range(len(result["ids"])):
                audios.append({"metadata": result["metadatas"][i]})
            
            return audios
        except Exception as e:
            raise Exception(f"Error retrieving all audios: {str(e)}")
    
    def delete_audio(self, audio_id: str) -> bool:
        """Delete audio record from ChromaDB"""
        try:
            # Check if audio exists first
            result = self.collection.get(
                ids=[audio_id],
                include=["metadatas"]
            )
            
            if not result["ids"]:
                return False
            
            # Delete from ChromaDB
            self.collection.delete(ids=[audio_id])
            return True
        except Exception as e:
            raise Exception(f"Error deleting audio from ChromaDB: {str(e)}")