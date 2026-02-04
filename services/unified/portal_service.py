"""
Main portal orchestrator - runs individual portal systems
"""
import os
import pandas as pd
import time
from datetime import datetime, timedelta
import shutil
import sys

# Import from unified portal modules
from utils.state_manager import (
    load_processed_emails, load_processed_files,
    mark_email_processed, is_email_processed,
    mark_file_processed, is_file_processed,
    save_processed_emails, processed_emails_state,
    processed_files_state
)
from utils.scheduler import get_est_time
from utils.config import EMAIL_RECIPIENTS

# ===== IMPORT REAL FUNCTIONS FROM YOUR PROJECT =====

# For HHSC/DIR system (texas1.py equivalent)
try:
    from services.dir.hhsc_processor import (
        main as hhsc_main,
        auto_authenticate_primary_gmail,
        search_specific_hhsc_email,
        get_email_full_content,
        extract_portal_link,
        initialize_driver,
        login_to_hhsc_portal,
        process_portal_without_login,
        logout_from_portal,
        process_all_downloaded_documents as hhsc_process_docs,
        process_files_with_llm,
        DEPARTMENT_CREDENTIALS,
        SolicitationAutomation
    )
    from services.dir.email_sender import HHSCOutlookEmailSender
    HHSC_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ HHSC/DIR services not available: {e}")
    HHSC_AVAILABLE = False

# For VMS system (vms1.py equivalent)
try:
    from services.vms.requisition_processor import RequisitionProcessor
    from services.vms.email_sender import EmailSender as VMSEmailSender
    from services.vms.file_manager import FileManager
    VMS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ VMS services not available: {e}")
    VMS_AVAILABLE = False

# For Dual Table system (ram1.py equivalent)
try:
    from services.dual_table.dual_table_service import run_dual_table_processing
    DUAL_TABLE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Dual Table services not available: {e}")
    DUAL_TABLE_AVAILABLE = False

# ===== ODOO INTEGRATION - FIXED SECTION ONLY =====
# CHANGED ONLY THIS SECTION - NOTHING ELSE
try:
    # FIXED: Import from the correct location
    from services.odoo.file_processor import process_oddo_job_postings
    ODOO_AVAILABLE = True
    
    # Create a wrapper function that matches the expected signature
    def process_job_files_from_folders():
        print("🔄 Running Odoo job posting via file_processor...")
        result = process_oddo_job_postings()
        return {"status": "success", "posted": result} if result else {"status": "no_jobs", "portal": "odoo"}
    
except ImportError as e:
    print(f"⚠️ Odoo integration not available: {e}")
    ODOO_AVAILABLE = False
    # Create placeholder
    def process_job_files_from_folders():
        print("ℹ️ Odoo integration placeholder - no actual posting")
        return {"status": "not_available", "portal": "odoo"}

# ===== FUNCTIONS FROM UNIFIED CODE =====

def run_texas1_initial():
    """Run HHSC/DIR portal for initial processing only"""
    print("🏥 STARTING HHSC/DIR PORTAL (Initial Processing)")
    print("=" * 60)
    
    if not HHSC_AVAILABLE:
        print("❌ HHSC/DIR services not available")
        return {"status": "error", "error": "HHSC services not available", "portal": "hhsc"}
    
    driver = None
    try:
        driver = initialize_driver()
        gmail_service = auto_authenticate_primary_gmail()
        
        # Search for TODAY'S emails
        messages = search_specific_hhsc_email(gmail_service, days_back=1)
        
        if not messages:
            print("❌ No TODAY'S HHSC emails found")
            return {"status": "no_emails", "processed": 0}
        
        print(f"Found {len(messages)} HHSC emails from TODAY")
        
        # Mark all found emails as processed for initial run
        for message in messages:
            mark_email_processed('hhsc_emails', message['id'])
        
        processed_portals = 0
        first_portal_link = None
        
        for message in messages:
            email_details = get_email_full_content(gmail_service, message['id'])
            if email_details:
                portal_link = extract_portal_link(email_details['full_body'])
                if portal_link:
                    first_portal_link = portal_link
                    break
        
        if not first_portal_link:
            print("❌ No valid HHSC portal links found")
            return {"status": "no_links", "processed": 0}
        
        login_success = login_to_hhsc_portal(driver, first_portal_link, DEPARTMENT_CREDENTIALS)
        
        if not login_success:
            print("❌ Failed to login to HHSC portal")
            return {"status": "login_failed", "processed": 0}
        
        print("✅ Successfully logged into HHSC portal")
        
        for i, message in enumerate(messages, 1):
            email_details = get_email_full_content(gmail_service, message['id'])
            department = message.get('department', 'HHSC')
            
            if email_details:
                portal_link = extract_portal_link(email_details['full_body'])
                if portal_link:
                    success = process_portal_without_login(driver, portal_link, department)
                    if success:
                        processed_portals += 1
                    
                    if i < len(messages):
                        time.sleep(3)
        
        logout_from_portal(driver)
        hhsc_process_docs()
        
        print("\n=== STARTING LLM DATA PROCESSING ===")
        process_files_with_llm()
        
        print("\n=== SENDING SOLICITATION RESPONSE EMAILS ===")
        email_sender = HHSCOutlookEmailSender()
        emails_sent = email_sender.send_emails_for_all_solicitations()
        print(f"✅ Sent {emails_sent} HHSC emails")
        
        return {
            "status": "success", 
            "processed": processed_portals,
            "total_emails": len(messages),
            "emails_sent": emails_sent,
            "portal": "hhsc"
        }
        
    except Exception as e:
        print(f"❌ Error in HHSC processing: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e), "portal": "hhsc"}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def run_vms1_initial():
    """Run VMS portal for initial processing only"""
    print("💼 STARTING VMS PORTAL (vms1.py)")
    print("=" * 60)
    
    if not VMS_AVAILABLE:
        print("❌ VMS services not available")
        return {"status": "error", "error": "VMS services not available", "portal": "vms"}
    
    try:
        # Use the RequisitionProcessor from VMS services
        processor = RequisitionProcessor()
        processor.run_manual_processing()
        
        print("✅ VMS Portal completed successfully!")
        return {"status": "success", "portal": "vms"}
        
    except Exception as e:
        print(f"❌ VMS Portal failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e), "portal": "vms"}
 
 
 
def run_suresh1_processing(send_email=False):
    """Run Dual Table processing"""
    print("📊 STARTING COMBINED DUE LIST PROCESSING (Dual Table)")
    print("=" * 60)
    
    if not DUAL_TABLE_AVAILABLE:
        print("❌ Dual Table services not available")
        return {'status': 'error', 'error': 'Dual Table services not available', 'portal': 'due_list'}
    
    try:
        # Run dual table processing
        run_dual_table_processing()
        
        # ========== NO ODOO CALL HERE! ==========
        # KEEP THIS SECTION REMOVED/COMMENTED OUT
        # 🟢🟢🟢🟢 KEEP THESE LINES REMOVED 🟢🟢🟢🟢
        # print("\n" + "=" * 60)
        # print("🔄 RUNNING ODOO INTEGRATION AFTER DUAL TABLE")
        # print("=" * 60)
        # odoo_result = run_odoo_integration()
        # 🟢🟢🟢🟢 KEEP REMOVED 🟢🟢🟢🟢
        
        # Check if the Excel file was created
        excel_file = "job_tracker_report.xlsx"
        if os.path.exists(excel_file):
            file_size = os.path.getsize(excel_file)
            print(f"✅ Due list Excel created: {excel_file} ({file_size} bytes)")
            
            # Read the Excel to get job counts
            try:
                active_df = pd.read_excel(excel_file, sheet_name='Active Jobs')
                past_due_df = pd.read_excel(excel_file, sheet_name='Past Due Jobs')
                active_jobs = len(active_df)
                past_due_jobs = len(past_due_df)
                print(f"📊 Job counts - Active: {active_jobs}, Past Due: {past_due_jobs}")
            except Exception as e:
                print(f"⚠️ Could not read Excel for counts: {e}")
                active_jobs = 0
                past_due_jobs = 0
        else:
            print("❌ job_tracker_report.xlsx not found after dual table processing")
            excel_file = None
            active_jobs = 0
            past_due_jobs = 0
        
        print("✅ Due List processing completed successfully!")
        
        return {
            'status': 'success', 
            'portal': 'due_list',
            'excel_file': excel_file,
            'active_jobs': active_jobs,
            'past_due_jobs': past_due_jobs,
            'email_sent': False
        }
        
    except Exception as e:
        print(f"❌ Due List processing failed: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e), 'portal': 'due_list'}
 
 
 

def run_odoo_integration():
    """Run Odoo job posting integration"""
    print("\n" + "=" * 70)
    print("🏢 STARTING ODOO INTEGRATION")
    print("=" * 70)
    
    try:
        print("🚀 Running Odoo integration to post new job files...")
        result = process_job_files_from_folders()
        
        print("✅ Odoo integration completed successfully!")
        return {"status": "success", "portal": "odoo"}
        
    except Exception as e:
        print(f"❌ Odoo integration failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e), "portal": "odoo"}

def process_all_downloaded_documents_24hr():
    """Process all documents and APPEND to master Excel - UPDATED FOR 24HR"""
    processed_count = 0
    download_folder = "downloaded_documents"
    
    if not os.path.exists(download_folder):
        print(f"📁 Folder doesn't exist: {download_folder}")
        return 0
    
    for filename in os.listdir(download_folder):
        if filename.endswith('.pdf') and not is_file_processed(filename):
            file_path = os.path.join(download_folder, filename)
            
            try:
                # For demo - you would replace this with your actual data extraction
                extracted_data = {
                    'id': f"HHSC_{datetime.now().strftime('%H%M%S')}",
                    'department': 'Health Services',
                    'due_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                }
                
                # Append to master Excel
                success = append_to_master_excel(extracted_data, source="HHSC", filename=filename)
                
                if success:
                    mark_file_processed(filename)
                    processed_count += 1
                    print(f"✅ Processed and appended: {filename}")
                
            except Exception as e:
                print(f"❌ Failed to process {filename}: {e}")
    
    print(f"📊 Total documents processed this cycle: {processed_count}")
    return processed_count

def append_to_master_excel(data, source="HHSC", filename=""):
    """Append data to master Excel file without overwriting existing data"""
    master_file = "due_list_master.xlsx"
    
    # Create data frame from extracted data
    new_data_df = pd.DataFrame([{
        'Requisition_ID': data.get('id', 'Unknown'),
        'Department': data.get('department', 'Unknown'),
        'Due_Date': data.get('due_date', 'Unknown'),
        'Status': 'Active',
        'Source': source,
        'File_Name': filename,
        'Processed_At': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Processed_Date': datetime.now().strftime('%Y-%m-%d')
    }])
    
    try:
        # Try to read existing master file
        if os.path.exists(master_file):
            with pd.ExcelFile(master_file) as xls:
                if 'Active_Requisitions' in xls.sheet_names:
                    existing_data = pd.read_excel(master_file, sheet_name='Active_Requisitions')
                else:
                    existing_data = pd.DataFrame()
        else:
            existing_data = pd.DataFrame()
        
        # Combine existing + new data
        if not existing_data.empty:
            combined_data = pd.concat([existing_data, new_data_df], ignore_index=True)
            # Remove duplicates based on Requisition_ID
            combined_data = combined_data.drop_duplicates(subset=['Requisition_ID'], keep='last')
        else:
            combined_data = new_data_df
        
        # Write back to Excel
        with pd.ExcelWriter(master_file, engine='openpyxl') as writer:
            combined_data.to_excel(writer, sheet_name='Active_Requisitions', index=False)
            
            # Create processing log sheet
            log_entry = pd.DataFrame([{
                'File_Processed': filename,
                'Source': source,
                'Processing_Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Requisition_ID': data.get('id', 'Unknown')
            }])
            
            if os.path.exists(master_file):
                try:
                    existing_log = pd.read_excel(master_file, sheet_name='Processing_Log')
                    updated_log = pd.concat([existing_log, log_entry], ignore_index=True)
                except:
                    updated_log = log_entry
            else:
                updated_log = log_entry
                
            updated_log.to_excel(writer, sheet_name='Processing_Log', index=False)
        
        print(f"✅ Appended data to master Excel: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error appending to master Excel: {e}")
        return False

from utils.state_manager import save_processed_files
def archive_yesterdays_data():
    """Archive yesterday's data and start fresh"""
    try:
        master_file = "due_list_master.xlsx"
        if os.path.exists(master_file):
            archive_file = f"due_list_archive_{datetime.now().strftime('%Y%m%d')}.xlsx"
            shutil.copy2(master_file, archive_file)
            print(f"✅ Archived yesterday's data to: {archive_file}")
            
            # Clear processed files for new cycle
            processed_files_state['processed_files'] = []
            save_processed_files()
            
    except Exception as e:
        print(f"⚠️ Error archiving data: {e}")