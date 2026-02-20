# Fix for older SQLite versions on production servers
# ChromaDB requires sqlite3 >= 3.35.0
import sys
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass  # pysqlite3 not installed, use system sqlite3

import chromadb
from chromadb.config import Settings
import openai
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
from database import get_database_manager
load_dotenv()

# Resolve chroma_db path relative to this file's location (project root)
# Using an absolute path avoids PermissionError when gunicorn changes the CWD
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHROMA_DB_PATH = os.path.join(_PROJECT_ROOT, "chroma_db")

class ChromaDBManager:
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=_CHROMA_DB_PATH)
        
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
         
    def store_summary(self, audio_id: str, summary: str) -> str:
        """Store summary with embeddings in ChromaDB with minimal metadata"""
        try:
            # Generate embeddings for the summary
            embeddings = self.get_embeddings(summary)
            
            # Only store audio_id and summary_length as metadata
            # All other metadata will be stored in SQL database
            metadata = {
                "audio_id": audio_id,
                "summary_length": len(summary)
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
            # Use SQL database for metadata search instead of ChromaDB
            db_manager = get_database_manager()
            audio_records = db_manager.search_audio_data(query)
            
            # Convert to expected format
            filtered_audios = []
            for record in audio_records:
                filtered_audios.append({"metadata": record})
            
            return filtered_audios
        except Exception as e:
            raise Exception(f"Error filtering audios: {str(e)}")
    
    def get_all_audios(self) -> List[Dict[str, Any]]:
        """Retrieve all audio summaries with their metadata from SQL database"""
        try:
            # Use SQL database for metadata retrieval instead of ChromaDB
            db_manager = get_database_manager()
            audio_records = db_manager.get_all_audio_data()
            
            # Convert to expected format
            audios = []
            for record in audio_records:
                audios.append({"metadata": record})
            
            return audios
        except Exception as e:
            raise Exception(f"Error retrieving all audios: {str(e)}")
    
    def delete_audio(self, audio_id: str) -> bool:
        """Delete audio record from ChromaDB and SQL database"""
        try:
            # Check if audio exists in ChromaDB first
            result = self.collection.get(
                ids=[audio_id],
                include=["metadatas"]
            )
            
            if not result["ids"]:
                return False
            
            # Delete from ChromaDB
            self.collection.delete(ids=[audio_id])
            
            # Permanently delete from SQL database
            db_manager = get_database_manager()
            db_manager.delete_audio_data(audio_id)
            
            return True
        except Exception as e:
            raise Exception(f"Error deleting audio from ChromaDB: {str(e)}")