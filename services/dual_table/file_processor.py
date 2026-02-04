import os
import glob
import pandas as pd
import re


from services.dual_table.job_extractor import extract_job_id_directly, extract_job_details
def read_files_from_folders():
    """Read all text files from requisition_outputs and hhsc_portal_outputs folders"""
    folders = ['vms_outputs', 'dir_portal_outputs']
    all_files = []
    
    for folder in folders:
        if os.path.exists(folder):
            # Get all .txt files from the folder
            txt_files = glob.glob(os.path.join(folder, '*.txt'))
            print(f"📁 Found {len(txt_files)} files in {folder}")
            all_files.extend(txt_files)
        else:
            print(f"⚠️  Folder not found: {folder}")
    
    return all_files

def extract_job_details_from_file(file_path):
    """Extract job details from a text file with IMPROVED Job ID extraction"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        print(f"🔍 Checking file: {os.path.basename(file_path)}")
        
        # Try direct Job ID extraction first (more aggressive pattern)
        job_id = extract_job_id_directly(content)
        if job_id:
            print(f"✅ Direct Job ID found: {job_id}")
            # Use your existing function for title and due date
            job_details = extract_job_details(content)
            job_details['Job_ID'] = job_id  # Override with directly found ID
            return job_details
        else:
            # Fall back to original function
            job_details = extract_job_details(content)
            if not job_details['Job_ID']:
                print(f"❌ No Job ID found in file")
            return job_details
        
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return {'Job_ID': None, 'Title': None, 'Due_date': None}

def process_folder_files_simple():
    """Process all files from folders - WITH BETTER DEBUGGING"""
    print("\n=== Processing Files from Folders ===")
    
    files = read_files_from_folders()
    if not files:
        print("❌ No files found in folders")
        return pd.DataFrame()
    
    results = []
    valid_count = 0
    invalid_count = 0
    
    for file_path in files:
        print(f"\n📄 Processing: {os.path.basename(file_path)}")
        job_details = extract_job_details_from_file(file_path)
        
        if job_details['Job_ID']:  # Only add if we have a valid Job_ID
            results.append(job_details)
            valid_count += 1
            print(f"   ✅ VALID - Job_ID: {job_details['Job_ID']}")
            print(f"   Title: {job_details['Title']}")
            print(f"   Due_date: {job_details['Due_date']}")
        else:
            invalid_count += 1
            print(f"   ❌ INVALID - No Job ID found")
    
    print(f"\n📊 PROCESSING SUMMARY:")
    print(f"   Total files: {len(files)}")
    print(f"   Valid jobs: {valid_count}")
    print(f"   Invalid files: {invalid_count}")
    
    # Clear folders after processing
    # clear_folders_after_processing()
    
    return pd.DataFrame(results)

def get_already_processed_jobs(excel_path):
    """Get Job IDs that are already in Excel to avoid duplicates"""
    try:
        if os.path.exists(excel_path):
            existing_active = pd.read_excel(excel_path, sheet_name='Active Jobs')
            existing_past_due = pd.read_excel(excel_path, sheet_name='Past Due Jobs')
            
            all_existing_jobs = set(existing_active['Job_ID'].tolist() + existing_past_due['Job_ID'].tolist())
            print(f"📊 Found {len(all_existing_jobs)} existing jobs in Excel")
            return all_existing_jobs
        else:
            print("📊 No existing Excel file found - starting fresh")
            return set()
    except Exception as e:
        print(f"⚠️  Error reading existing jobs: {e}")
        return set()
    
def clear_folders_after_processing():
    """Clear folders after processing files"""
    folders = ['vms_outputs', 'dir_portal_outputs', 'dir_documents', 'vms_documents']
    files_cleared = 0
    
    for folder in folders:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.endswith(('.txt', '.doc', '.docx', '.pdf')):
                    file_path = os.path.join(folder, file)
                    os.remove(file_path)
                    files_cleared += 1
                    print(f"🗑️  Cleared: {file}")
    
    if files_cleared > 0:
        print(f"✅ Cleared {files_cleared} files from folders")
    else:
        print("ℹ️  No files to clear - folders already empty")