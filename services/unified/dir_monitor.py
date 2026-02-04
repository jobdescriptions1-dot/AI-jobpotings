"""
HHSC continuous monitoring service
"""
import os
import time
from datetime import datetime

# Import from unified portal modules
from utils.state_manager import (
    mark_email_processed, 
    is_email_processed,
    processed_emails_state
)
from utils.config import processed_emails_state
from utils.global_lock import global_lock

def start_hhsc_monitoring():
    """Start HHSC continuous monitoring - ONLY PROCESS NEW EMAILS"""
    print("🏥 Starting HHSC monitoring (NEW emails only)...")
    
    # Check if HHSC services are available
    try:
        from services.dir.hhsc_processor import (
            auto_authenticate_primary_gmail,
            search_specific_hhsc_email,
            get_email_full_content,
            extract_portal_link,
            initialize_driver,
            login_to_hhsc_portal,
            process_portal_without_login,
            logout_from_portal,
            process_all_downloaded_documents,
            process_files_with_llm,
            HHSCOutlookEmailSender,
            DEPARTMENT_CREDENTIALS,
            SolicitationAutomation
        )
        HHSC_AVAILABLE = True
    except ImportError as e:
        print(f"❌ HHSC services not available: {e}")
        HHSC_AVAILABLE = False
        return
    
    while True:
        print(f"\n🔍 HHSC Monitoring Check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if VMS is processing - WAIT if it is
        if not global_lock.wait_if_processing('dir', max_wait=30):
            print("⚠️  Still waiting for VMS to finish, continuing DIR check anyway")
        
        # Try to acquire lock for DIR check (even if no emails to process)
        lock_acquired = False
        try:
            # ACQUIRE LOCK before any processing
            lock_acquired = global_lock.acquire('dir')
            
            if lock_acquired:
                # 🧹 CLEAR FOLDERS ON EVERY CHECK
                print("🧹 Clearing HHSC folders for fresh processing...")
                folders_to_clear = [
                    "hhsc_portal_outputs",
                    "downloaded_documents", 
                    "processed_documents",
                    "llm_processed"
                ]
                
                for folder in folders_to_clear:
                    if os.path.exists(folder):
                        try:
                            for file in os.listdir(folder):
                                file_path = os.path.join(folder, file)
                                try:
                                    if os.path.isfile(file_path):
                                        os.unlink(file_path)
                                    elif os.path.isdir(file_path):
                                        import shutil
                                        shutil.rmtree(file_path)
                                except Exception as e:
                                    print(f"⚠️ Could not delete {file_path}: {e}")
                            print(f"✅ Cleared folder: {folder}")
                        except Exception as e:
                            print(f"⚠️ Error clearing folder {folder}: {e}")
                    else:
                        print(f"📁 Folder doesn't exist: {folder}")
                
                gmail_service = auto_authenticate_primary_gmail()
                # CHANGED: days_back from 1 to 3 to catch emails with wrong dates
                messages = search_specific_hhsc_email(gmail_service, days_back=3)
                
                if messages:
                    new_emails = []
                    for message in messages:
                        if not is_email_processed('hhsc_emails', message['id']):
                            new_emails.append(message)
                            print(f"📧 NEW HHSC email found: {message['id']}")
                    
                    if new_emails:
                        print(f"🎯 Processing {len(new_emails)} NEW HHSC emails")
                        
                        driver = initialize_driver()
                        try:
                            # Process new emails
                            first_portal_link = None
                            for message in new_emails:
                                email_details = get_email_full_content(gmail_service, message['id'])
                                if email_details:
                                    portal_link = extract_portal_link(email_details['full_body'])
                                    if portal_link:
                                        first_portal_link = portal_link
                                        break
                            
                            if first_portal_link:
                                login_success = login_to_hhsc_portal(driver, first_portal_link, DEPARTMENT_CREDENTIALS)
                                if login_success:
                                    processed_count = 0
                                    for message in new_emails:
                                        email_details = get_email_full_content(gmail_service, message['id'])
                                        department = message.get('department', 'HHSC')
                                        
                                        if email_details:
                                            portal_link = extract_portal_link(email_details['full_body'])
                                            if portal_link:
                                                success = process_portal_without_login(driver, portal_link, department)
                                                if success:
                                                    processed_count += 1
                                                    # Mark as processed immediately after successful processing
                                                    mark_email_processed('hhsc_emails', message['id'])
                                                
                                                time.sleep(2)
                                    
                                    logout_from_portal(driver)
                                    process_all_downloaded_documents()
                                    process_files_with_llm()
                                    
                                    email_sender = HHSCOutlookEmailSender()
                                    emails_sent = email_sender.send_emails_for_all_solicitations()
                                    
                                    print(f"✅ HHSC Monitoring: Processed {processed_count} new emails, sent {emails_sent} responses")
                                else:
                                    print("❌ HHSC Monitoring: Login failed")
                            else:
                                print("❌ HHSC Monitoring: No portal links found in new emails")
                        finally:
                            if driver:
                                driver.quit()
                    else:
                        print("📭 HHSC: No new emails found")
                else:
                    print("📭 HHSC: No emails found at all")
            
            else:
                print("❌ Could not acquire lock for DIR check")
            
        except Exception as e:
            print(f"❌ HHSC Monitoring error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Always release lock if acquired
            if lock_acquired:
                global_lock.release('dir')
        
        # Wait 15 seconds before next check
        print("⏳ HHSC: Waiting 15 seconds for next check...")
        time.sleep(15)