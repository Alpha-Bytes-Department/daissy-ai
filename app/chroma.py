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
         
    def store_summary(self, audio_id: str, summary: str, transcription: str = None) -> str:
        """Store summary with embeddings in ChromaDB"""
        try:
            # Generate embeddings for the summary
            embeddings = self.get_embeddings(summary)
            
            # Prepare metadata
            metadata = {
                "audio_id": audio_id,
                "summary_length": len(summary),
                "has_transcription": transcription is not None
            }
            
            if transcription:
                metadata["transcription_length"] = len(transcription)
            
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
    
    def get_by_audio_id(self, audio_id: str) -> Dict[str, Any]:
        """Retrieve summary by audio ID"""
        try:
            result = self.collection.get(
                ids=[audio_id],
                include=["documents", "metadatas"]
            )
            
            if not result["ids"]:
                return None
            
            return {
                "id": result["ids"][0],
                "document": result["documents"][0],
                "metadata": result["metadatas"][0]
            }
        except Exception as e:
            raise Exception(f"Error retrieving summary: {str(e)}")