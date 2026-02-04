import os
import re
from typing import List, Tuple

class FileManager:
    def __init__(self):
        self.output_dir = "vms_outputs"
        self.updated_docs_dir = "vms_documents"
        self.documents_dir = "Documents"
        
        # Create directories if they don't exist
        self.create_directories()
    
    def create_directories(self):
        """Create necessary directories"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.updated_docs_dir, exist_ok=True)
        os.makedirs(self.documents_dir, exist_ok=True)
    
    def clear_updated_documents(self):
        """Clear the updated_documents directory before processing"""
        if not os.path.exists(self.updated_docs_dir):
            os.makedirs(self.updated_docs_dir)
            print(f"Created directory: {self.updated_docs_dir}")
        else:
            # Remove all files in the directory
            for file in os.listdir(self.updated_docs_dir):
                file_path = os.path.join(self.updated_docs_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f"Removed previous file: {file}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            print(f"Cleared output directory: {self.updated_docs_dir}")
    
    def find_requisition_files(self, req_id, state_abbr):
        """Find SM and RTR files for a given requisition ID - enhanced for combined documents"""
        sm_files = []
        rtr_files = []
        
        if not os.path.exists(self.updated_docs_dir):
            print(f"  ❌ Directory not found: {self.updated_docs_dir}")
            return sm_files, rtr_files
        
        print(f"  🔍 Searching for files for requisition {req_id} (State: {state_abbr})")
        
        # FIRST: Check for combined document (like RTR_SM_Idaho_776597.docx)
        combined_patterns = [
            f"RTR_SM_{state_abbr}_{req_id}.docx",
            f"SM_RTR_{state_abbr}_{req_id}.docx", 
            f"Combined_{state_abbr}_{req_id}.docx"
        ]
        
        for pattern in combined_patterns:
            combined_path = os.path.join(self.updated_docs_dir, pattern)
            if os.path.exists(combined_path):
                print(f"  ✅ Found combined document: {pattern}")
                # For combined documents, return the same file for both SM and RTR
                return [pattern], [pattern]
        
        # SECOND: Look for separate files with exact state matching
        for file in os.listdir(self.updated_docs_dir):
            if req_id in file and file.endswith('.docx'):
                # Exact match for state abbreviation
                if file.startswith(f'SM_{state_abbr}_'):
                    sm_files.append(file)
                    print(f"  ✅ Found SM file: {file}")
                elif file.startswith(f'RTR_{state_abbr}_'):
                    rtr_files.append(file)
                    print(f"  ✅ Found RTR file: {file}")
        
        # THIRD: If no exact matches, look for files with state abbreviation anywhere in filename
        if not sm_files or not rtr_files:
            for file in os.listdir(self.updated_docs_dir):
                if req_id in file and file.endswith('.docx') and state_abbr in file.upper():
                    if 'SM' in file.upper() and file not in sm_files:
                        sm_files.append(file)
                        print(f"  ✅ Found SM file (loose match): {file}")
                    elif 'RTR' in file.upper() and file not in rtr_files:
                        rtr_files.append(file)
                        print(f"  ✅ Found RTR file (loose match): {file}")
        
        # FOURTH: If still no files, look for any files with this req_id (as fallback)
        if not sm_files or not rtr_files:
            for file in os.listdir(self.updated_docs_dir):
                if req_id in file and file.endswith('.docx'):
                    if 'SM' in file.upper() and file not in sm_files:
                        sm_files.append(file)
                        print(f"  ⚠️ Found SM file (req_id only): {file}")
                    elif 'RTR' in file.upper() and file not in rtr_files:
                        rtr_files.append(file)
                        print(f"  ⚠️ Found RTR file (req_id only): {file}")
        
        print(f"  📊 Search results: {len(sm_files)} SM files, {len(rtr_files)} RTR files")
        return sm_files, rtr_files
    
    def get_all_requisition_files(self):
        """Get all requisition files from output directory"""
        requisition_files = []
        if os.path.exists(self.output_dir):
            for file_name in os.listdir(self.output_dir):
                if file_name.endswith('.txt') and file_name.startswith('requisition_'):
                    requisition_files.append(os.path.join(self.output_dir, file_name))
        return requisition_files
    
    def check_documents_folder(self):
        """
        Check what documents are available in the Documents folder
        """
        print("\n=== CHECKING DOCUMENTS FOLDER ===")
        if not os.path.exists(self.documents_dir):
            print(f"ERROR: Documents folder '{self.documents_dir}' does not exist!")
            return
        
        files = os.listdir(self.documents_dir)
        sm_files = [f for f in files if f.startswith('SM_') and f.endswith('.docx')]
        rtr_files = [f for f in files if f.startswith('RTR_') and f.endswith('.docx')]
        
        print("Available SM files:")
        for sm_file in sm_files:
            print(f"  - {sm_file}")
        
        print("Available RTR files:")
        for rtr_file in rtr_files:
            print(f"  - {rtr_file}")
        
        # Check if we have templates for all states
        from utils.vms_helpers import STATE_MAPPING
        for state_abbr, state_info in STATE_MAPPING.items():
            if state_abbr == 'DEFAULT':
                continue
                
            sm_found = any(state_abbr in f.upper() for f in sm_files)
            rtr_found = any(state_abbr in f.upper() for f in rtr_files)
            
            status = "✓" if sm_found and rtr_found else "✗"
            print(f"{status} {state_abbr}: SM={sm_found}, RTR={rtr_found}")
    
    def clear_processing_directories(self):
        """Clear processing directories for fresh start"""
        # Clear output directory
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            print(f"🧹 Cleared output directory: {self.output_dir}")
        
        # Clear updated documents directory
        if os.path.exists(self.updated_docs_dir):
            for file in os.listdir(self.updated_docs_dir):
                file_path = os.path.join(self.updated_docs_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            print(f"🧹 Cleared documents directory: {self.updated_docs_dir}")
    
    def get_file_content(self, file_path):
        """Read file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def save_file_content(self, file_path, content):
        """Save content to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error saving file {file_path}: {e}")
            return False