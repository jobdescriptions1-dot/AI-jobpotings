"""
Utility functions for RAG system
"""
import os
import json
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_rag_system():
    """Get the RAG system instance (for use in other modules)"""
    try:
        from . import RAG_SYSTEM
        return RAG_SYSTEM
    except ImportError:
        return None

def notify_rag_new_file(file_path: str):
    """
    Notify RAG system of new file
    Can be called from your existing services
    """
    rag_system = get_rag_system()
    if rag_system and rag_system.get('ingestion_service'):
        try:
            rag_system['ingestion_service'].process_file(Path(file_path))
            logger.info(f"RAG notified of new file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error notifying RAG of file {file_path}: {e}")
    return False

def before_folder_clear_hook(folder_path: str):
    """
    Hook to call before clearing any folder
    Use this in your existing folder clearing functions
    """
    from .integration_hooks import rag_hooks
    return rag_hooks.before_folder_clear(folder_path)

def after_excel_update_hook():
    """
    Hook to call after updating job_tracker_report.xlsx
    """
    from .integration_hooks import rag_hooks
    return rag_hooks.after_excel_update("job_tracker_report.xlsx")

def record_odoo_posting_hook(job_id: str, status: str, details: dict = None):
    """
    Hook to record Odoo posting
    """
    from .integration_hooks import rag_hooks
    return rag_hooks.after_odoo_posting(job_id, status, details)

def setup_rag_integration():
    """
    Setup RAG integration with your existing system
    Call this once during system initialization
    """
    try:
        from .integration_hooks import rag_hooks
        from . import RAG_SYSTEM
        
        if RAG_SYSTEM:
            rag_hooks.set_rag_system(RAG_SYSTEM)
            logger.info("RAG integration hooks set up successfully")
            return True
        else:
            logger.warning("RAG system not available for integration")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up RAG integration: {e}")
        return False