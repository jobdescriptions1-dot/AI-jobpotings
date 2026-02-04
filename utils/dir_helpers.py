import os
import re
from datetime import datetime

def create_directories():
    """Create necessary directories"""
    directories = ["dir_portal_outputs", "dir_documents"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    return True

def clean_filename(filename):
    """Clean filename for safe use"""
    # Remove invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Replace multiple underscores with single
    cleaned = re.sub(r'_+', '_', cleaned)
    return cleaned

def get_timestamp():
    """Get current timestamp"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"