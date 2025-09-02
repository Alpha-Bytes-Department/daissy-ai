#!/usr/bin/env python3
"""
Database migration script for DAISSY AI Chat History
This script creates the necessary tables for storing chat sessions and messages.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from database import DatabaseManager, Base
from dotenv import load_dotenv

def migrate_database():
    """Run database migrations"""
    # Load environment variables
    load_dotenv()
    
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set!")
        print("Please set your PostgreSQL connection string in the .env file")
        print("Example: DATABASE_URL=postgresql://username:password@localhost:5432/daissy_ai")
        return False
    
    try:
        print("🔄 Connecting to database...")
        db_manager = DatabaseManager()
        
        print("🔄 Creating tables...")
        Base.metadata.create_all(bind=db_manager.engine)
        
        print("✅ Database migration completed successfully!")
        print(f"📊 Tables created:")
        print("   - chat_sessions (stores chat session metadata)")
        print("   - chat_messages (stores individual messages)")
        
        # Test the connection
        print("\n🔄 Testing database connection...")
        db = db_manager.get_db()
        db.close()
        print("✅ Database connection test successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

if __name__ == "__main__":
    print("DAISSY AI - Database Migration")
    print("=" * 40)
    
    success = migrate_database()
    
    if success:
        print("\n🎉 Migration completed! Your database is ready for storing chat history.")
    else:
        print("\n💥 Migration failed! Please check your database configuration.")
        sys.exit(1)
