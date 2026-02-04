"""
VMS continuous monitoring service
"""
import time
import os
import re
from datetime import datetime as dt  # RENAMED: datetime to dt to avoid conflict
from datetime import timedelta
# Import from unified portal modules
from utils.state_manager import (
    mark_email_processed, 
    is_email_processed,
    processed_emails_state
)
from utils.global_lock import global_lock

def start_vms_monitoring():
    """Start VMS continuous monitoring - PROCESS ONLY NEW EMAILS"""
    print("💼 Starting VMS monitoring (NEW emails only)...")
    
    # Check if VMS services are available
    try:
        from services.vms.requisition_processor import RequisitionProcessor
        from services.vms.gmail_reader import GmailReader
        VMS_AVAILABLE = True
    except ImportError as e:
        print(f"❌ VMS services not available: {e}")
        VMS_AVAILABLE = False
        return
    
    while True:
        print(f"\n🔍 VMS Monitoring Check at {dt.now().strftime('%Y-%m-%d %H:%M:%S')}")  # CHANGED: dt.now()
        
        # Check if DIR is processing - WAIT if it is
        if not global_lock.wait_if_processing('vms', max_wait=30):
            print("⚠️  Still waiting for DIR to finish, continuing VMS check anyway")
        
        try:
            # Use texas1 authentication as it's working
            from services.dir.hhsc_processor import auto_authenticate_primary_gmail
            
            # Authenticate with Gmail
            gmail_service = auto_authenticate_primary_gmail()
            
            # Simple search for VMS emails from LAST 1 HOUR (not whole day)
            current_time = int(time.time())
            one_hour_ago = current_time - 3600
            
            # Convert to Gmail query format
            one_hour_dt = dt.now() - timedelta(hours=1)  # CHANGED: dt.now()
            gmail_date = one_hour_dt.strftime("%Y/%m/%d")
            
            # Query for emails from last 1 hour only
            query = f'subject:"Now Open" after:{gmail_date}'
            print(f"🔍 Searching for VMS emails from last 1 hour (after: {gmail_date})")
            
            result = gmail_service.users().messages().list(
                userId='me',
                q=query
            ).execute()
            
            messages = result.get('messages', [])
            
            if messages:
                new_emails = []
                for message in messages:
                    if not is_email_processed('vms_emails', message['id']):
                        new_emails.append(message)
                        print(f"📧 NEW VMS email found: {message['id']}")
                
                if new_emails:
                    print(f"🎯 Found {len(new_emails)} new VMS emails - Running VMS processing...")
                    
                    # Extract email IDs from new emails
                    new_email_ids = [msg['id'] for msg in new_emails]
                    
                    # Try to acquire lock for VMS processing
                    if global_lock.acquire('vms'):
                        try:
                            # Mark emails as processed immediately (BEFORE actual processing)
                            for message in new_emails:
                                mark_email_processed('vms_emails', message['id'])
                                print(f"✅ MARKED as processed: {message['id']}")
                            
                            # Run the VMS processing with ONLY NEW email IDs
                            print("🚀 Starting VMS processing for NEW emails only...")
                            
                            # Initialize the VMS processor
                            processor = RequisitionProcessor()
                            
                            # Get the GmailReader to extract URLs from specific emails
                            gmail_reader = GmailReader()
                            gmail_reader.service = gmail_service  # Reuse the authenticated service
                            
                            # Extract URLs ONLY from new emails
                            print(f"🔗 Extracting URLs from {len(new_email_ids)} new emails...")
                            new_urls = gmail_reader.extract_todays_requisition_urls(specific_email_ids=new_email_ids)
                            
                            if new_urls:
                                print(f"✅ Found {len(new_urls)} new URLs to process")
                                
                                # Initialize driver and process these specific URLs
                                driver = processor.initialize_driver()
                                try:
                                    # Clear folders first
                                    processor.clear_vms_folders()
                                    
                                    # Open all TODAY'S requisitions in new tabs
                                    print(f"📋 Opening {len(new_urls)} new requisitions in new tabs...")
                                    processor.open_all_requisitions_in_new_tabs(driver, new_urls)
                                    
                                    # Import regex extraction functions
                                    from utils.vms_helpers import extract_all_scraped_files
                                    
                                    # IMMEDIATE REGEX EXTRACTION
                                    print("\n" + "="*60)
                                    print("IMMEDIATE REGEX EXTRACTION")
                                    print("="*60)
                                    
                                    extraction_count = extract_all_scraped_files(output_dir='vms_outputs')
                                    print(f"✅ Raw data extracted and saved: {extraction_count} files")
                                    
                                    # Process the extracted data to create documents
                                    print("\n=== Creating Today's Documents ===")
                                    processor.process_requisition_files()
                                    
                                    # LLM Enhancement Process
                                    print("\n" + "="*60)
                                    print("ENHANCING WITH LLM")
                                    print("="*60)
                                    
                                    try:
                                        processor.process_files_with_llm() 
                                    except Exception as llm_error:
                                        print(f"LLM processing skipped or failed: {llm_error}")
                                    
                                    # EMAIL SENDING SECTION
                                    print("\n" + "="*60)
                                    print("SENDING EMAILS")
                                    print("="*60)
                                    
                                    # Send emails for all processed requisitions
                                    from services.vms.email_sender import EmailSender
                                    from utils.vms_helpers import extract_state_from_job_id
                                    
                                    email_sender = EmailSender()
                                    email_count = 0
                                    
                                    output_dir = "vms_outputs"
                                    for filename in os.listdir(output_dir):
                                        if filename.startswith("requisition_") and filename.endswith("_complete.txt"):
                                            # Extract requisition ID
                                            match = re.search(r'requisition_(\d+)_complete\.txt', filename)
                                            if not match:
                                                continue
                                                
                                            req_id = match.group(1)
                                            
                                            # Read the file content to extract state and title
                                            req_file = os.path.join(output_dir, filename)
                                            with open(req_file, 'r', encoding='utf-8') as f:
                                                content = f.read()
                                            
                                            # Extract state abbreviation from content
                                            state_abbr = extract_state_from_job_id(content)
                                            if not state_abbr:
                                                state_abbr = 'DEFAULT'
                                            
                                            # Extract title from content
                                            title = "Position"
                                            if "Job ID:" in content:
                                                lines = content.split('\n')
                                                for i, line in enumerate(lines):
                                                    if line.startswith('Job ID:'):
                                                        # Look for title in subsequent lines
                                                        for j in range(i+1, min(i+10, len(lines))):
                                                            if lines[j].strip() and not lines[j].startswith(('Location:', 'Duration:', 'Position:')):
                                                                title = lines[j].strip()
                                                                break
                                                        break
                                            
                                            # Send email
                                            success = email_sender.send_requisition_email_for_id(req_id, state_abbr, title, content)
                                            
                                            if success:
                                                print(f"✅ Email sent for requisition {req_id} (State: {state_abbr})")
                                                email_count += 1
                                            else:
                                                print(f"❌ Failed to send email for requisition {req_id} (State: {state_abbr})")
                                    
                                    # FINAL SUMMARY
                                    print("\n=== Today's Processing Complete ===")
                                    print(f"Processed {len(new_urls)} requisitions from NEW emails successfully!")
                                    print(f"Sent {email_count} emails successfully!")
                                    print("All NEW requisitions have been processed, documents created, and emails sent!")
                                    
                                    # Trigger dual table processing
                                    print("\n📊 TRIGGERING DUAL TABLE FOR VMS FILES")
                                    processor.trigger_dual_table_for_vms()
                                    
                                finally:
                                    try:
                                        driver.quit()
                                    except:
                                        pass
                                    
                            else:
                                print("⚠️  No URLs found in new emails")
                                
                        finally:
                            # Always release lock
                            global_lock.release('vms')
                    else:
                        print("❌ Could not acquire lock for VMS processing - will retry next cycle")
                else:
                    print("📭 VMS: No new emails found")
            else:
                print("📭 VMS: No emails found at all")
            
        except Exception as e:
            print(f"❌ VMS Monitoring error: {e}")
            # Make sure lock is released on error
            global_lock.release('vms')
            import traceback
            traceback.print_exc()
        
        # Wait 15 seconds before next check
        print("⏳ VMS: Waiting 15 seconds for next check...")
        time.sleep(15)