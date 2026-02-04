"""
RAG Chatbot System for Government Procurement Automation
"""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Global RAG system instance
RAG_SYSTEM = None

def init_rag_system():
    """
    Initialize the RAG system
    Returns the RAG system instance
    """
    global RAG_SYSTEM
    
    if RAG_SYSTEM is not None:
        return RAG_SYSTEM
    
    try:
        # Import components
        from .chroma_manager import ChromaManager
        from .sqlite_manager import SQLiteManager
        from .ingestion_service import IngestionService
        
        # Initialize components
        chroma_manager = ChromaManager()
        sqlite_manager = SQLiteManager()
        
        # Define directories to watch
        watch_dirs = [
            "vms_outputs",
            "dir_portal_outputs",
        ]
        
        # Create ingestion service
        ingestion_service = IngestionService(
            watch_dirs=watch_dirs,
            chroma_manager=chroma_manager,
            sqlite_manager=sqlite_manager,
            check_interval=60
        )
        
        # Create system instance
        RAG_SYSTEM = {
            'chroma_manager': chroma_manager,
            'sqlite_manager': sqlite_manager,
            'ingestion_service': ingestion_service
        }
        
        # Setup integration hooks
        from .utils import setup_rag_integration
        setup_rag_integration()
        
        print("RAG System initialized successfully")
        return RAG_SYSTEM
        
    except Exception as e:
        print(f"Error initializing RAG system: {e}")
        return None

# Export components
__all__ = [
    'init_rag_system',
    'RAG_SYSTEM',
    'ChromaManager',
    'SQLiteManager',
    'IngestionService',
    'QueryEngine',
    'FileParser'
]