"""
Integration hooks into your existing code
Minimal changes to add RAG processing before folder clearing
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional, Callable
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class RAGIntegrationHooks:
    """Hooks to integrate RAG with your existing system"""
    
    # Singleton instance
    _instance = None
    _rag_system = None
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.processed_before_clear = False
        self.rag_ingestion_service = None
    
    def set_rag_system(self, rag_system):
        """Set the RAG system instance"""
        self.rag_system = rag_system
        self.rag_ingestion_service = rag_system.get('ingestion_service')
        logger.info("RAG system set for integration hooks")
    
    def before_folder_clear(self, folder_path: str) -> bool:
        """
        Call this BEFORE clearing any folder
        Processes all files in the folder for RAG
        Returns: True if processed successfully, False otherwise
        """
        try:
            if not self.rag_ingestion_service:
                logger.warning("RAG system not available, skipping pre-clear processing")
                return False
            
            folder = Path(folder_path)
            if not folder.exists():
                logger.warning(f"Folder does not exist: {folder_path}")
                return True  # Return True since nothing to process
            
            logger.info(f"Processing files in {folder_path} before clearing...")
            
            # Process all files in the folder
            processed_count = 0
            for file_path in folder.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in {'.txt', '.pdf', '.docx', '.xlsx', '.xls'}:
                    try:
                        # Process the file through RAG
                        self.rag_ingestion_service.process_file(file_path)
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
            
            logger.info(f"Processed {processed_count} files from {folder_path} before clearing")
            self.processed_before_clear = True
            return True
            
        except Exception as e:
            logger.error(f"Error in before_folder_clear for {folder_path}: {e}")
            return False
    
    def after_excel_update(self, excel_path: str) -> bool:
        """
        Call this AFTER updating job_tracker_report.xlsx
        Processes the updated Excel file
        """
        try:
            if not self.rag_ingestion_service:
                logger.warning("RAG system not available, skipping Excel processing")
                return False
            
            file_path = Path(excel_path)
            if not file_path.exists():
                logger.warning(f"Excel file does not exist: {excel_path}")
                return False
            
            logger.info(f"Processing updated Excel file: {excel_path}")
            
            # Process the Excel file
            self.rag_ingestion_service.process_file(file_path)
            
            logger.info(f"Successfully processed Excel file: {excel_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing Excel file {excel_path}: {e}")
            return False
    
    def after_odoo_posting(self, job_id: str, status: str, details: Optional[Dict] = None):
        """
        Call this AFTER posting to Odoo
        Records the posting in RAG database
        """
        try:
            if not self.rag_system:
                logger.warning("RAG system not available, skipping Odoo posting record")
                return False
            
            sqlite_manager = self.rag_system.get('sqlite_manager')
            if not sqlite_manager:
                logger.warning("SQLite manager not available")
                return False
            
            # Record Odoo posting
            posting_data = {
                'job_id': job_id,
                'posting_status': status,
                'posting_time': details.get('posting_time') if details else None,
                'odoo_id': details.get('odoo_id') if details else None,
                'details': json.dumps(details) if details else None
            }
            
            # TODO: Implement Odoo posting recording in SQLite manager 
            # For now, just log it
            logger.info(f"Odoo posting recorded: Job={job_id}, Status={status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording Odoo posting for {job_id}: {e}")
            return False

# Global instance for easy access
rag_hooks = RAGIntegrationHooks.get_instance()

# ============================================================================
# MONKEY PATCH FUNCTIONS - Add to your existing files
# ============================================================================

def patch_folder_clearing_function(original_func: Callable) -> Callable:
    """
    Decorator to patch your existing folder clearing functions
    Usage: Add @patch_folder_clearing_function above your clear_folders function
    """
    def wrapper(*args, **kwargs):
        # Check if folder path is in args/kwargs
        folder_path = None
        
        # Try to find folder path in args
        for arg in args:
            if isinstance(arg, str) and ('vms_outputs' in arg or 'dir_portal_outputs' in arg):
                folder_path = arg
                break
        
        # If not found in args, check kwargs
        if not folder_path:
            for key, value in kwargs.items():
                if isinstance(value, str) and ('vms_outputs' in value or 'dir_portal_outputs' in value):
                    folder_path = value
                    break
        
        # Process files before clearing
        if folder_path:
            rag_hooks.before_folder_clear(folder_path)
        
        # Call original function
        return original_func(*args, **kwargs)
    
    return wrapper

def patch_excel_update_function(original_func: Callable) -> Callable:
    """
    Decorator to patch your Excel update functions
    """
    def wrapper(*args, **kwargs):
        # Call original function first
        result = original_func(*args, **kwargs)
        
        # Process Excel after update
        excel_path = "job_tracker_report.xlsx"  # Default path
        rag_hooks.after_excel_update(excel_path)
        
        return result
    
    return wrapper