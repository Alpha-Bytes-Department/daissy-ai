#!/usr/bin/env python
"""
Django development server runner.
This file helps run Django using a familiar FastAPI-like interface.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_django_server():
    """Run Django development server"""
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set")
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Change to project root directory
    os.chdir(project_root)
    
    # Run Django development server
    execute_from_command_line([
        'manage.py', 
        'runserver', 
        '127.0.0.1:8000'
    ])

if __name__ == "__main__":
    run_django_server()