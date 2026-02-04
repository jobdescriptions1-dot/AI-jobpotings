import os
import json
from datetime import datetime
from utils.config import *

def load_processed_emails():
    """Load the state of processed emails from file"""
    global processed_emails_state
    try:
        if os.path.exists(PROCESSED_EMAILS_FILE):
            with open(PROCESSED_EMAILS_FILE, 'r') as f:
                processed_emails_state = json.load(f)
        else:
            processed_emails_state = {
                'hhsc_emails': [],
                'vms_emails': [],
                'last_initial_run': None,
                'last_email_sent_date': None
            }
    except Exception as e:
        print(f"❌ Error loading processed emails state: {e}")
        processed_emails_state = {
            'hhsc_emails': [],
            'vms_emails': [],
            'last_initial_run': None,
            'last_email_sent_date': None
        }

def save_processed_emails():
    """Save the state of processed emails to file"""
    try:
        with open(PROCESSED_EMAILS_FILE, 'w') as f:
            json.dump(processed_emails_state, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving processed emails state: {e}")

def mark_email_processed(portal_type, email_id):
    """Mark an email as processed"""
    if portal_type not in processed_emails_state:
        processed_emails_state[portal_type] = []
    
    if email_id not in processed_emails_state[portal_type]:
        processed_emails_state[portal_type].append(email_id)
        save_processed_emails()

def is_email_processed(portal_type, email_id):
    """Check if an email has been processed"""
    return email_id in processed_emails_state.get(portal_type, [])

def clear_old_processed_emails():
    """Clear processed emails older than 7 days to prevent state file from growing too large"""
    try:
        # Keep only emails from last 7 days in memory
        # In a real implementation, you'd track timestamps
        max_emails_to_keep = 1000
        for portal_type in ['hhsc_emails', 'vms_emails']:
            if portal_type in processed_emails_state and len(processed_emails_state[portal_type]) > max_emails_to_keep:
                # Keep only the most recent emails
                processed_emails_state[portal_type] = processed_emails_state[portal_type][-max_emails_to_keep:]
        
        save_processed_emails()
    except Exception as e:
        print(f"⚠️ Error clearing old processed emails: {e}")

# ==================== NEW 24-HOUR FUNCTIONS ====================

def load_processed_files():
    """Load processed files state"""
    global processed_files_state
    try:
        if os.path.exists(PROCESSED_FILES_FILE):
            with open(PROCESSED_FILES_FILE, 'r') as f:
                processed_files_state = json.load(f)
        else:
            processed_files_state = {
                'processed_files': [],
                'last_email_date': None,
                'last_processing_time': None
            }
    except Exception as e:
        print(f"❌ Error loading processed files: {e}")
        processed_files_state = {
            'processed_files': [],
            'last_email_date': None,
            'last_processing_time': None
        }

def save_processed_files():
    """Save processed files state"""
    try:
        with open(PROCESSED_FILES_FILE, 'w') as f:
            json.dump(processed_files_state, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving processed files: {e}")

def mark_file_processed(filename):
    """Mark a file as processed"""
    if filename not in processed_files_state.get('processed_files', []):
        processed_files_state['processed_files'].append(filename)
        processed_files_state['last_processing_time'] = datetime.now().isoformat()
        save_processed_files()

def is_file_processed(filename):
    """Check if file is already processed"""
    return filename in processed_files_state.get('processed_files', [])
