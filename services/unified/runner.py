"""
Main unified portal runner - orchestrates all systems
FIXED VERSION: No duplicate emails, no duplicate Odoo posts
"""
import os
import time
import glob
import hashlib
from datetime import datetime
import pytz

# Import from unified portal modules
from utils.state_manager import (
    load_processed_emails, 
    load_processed_files, 
    save_processed_emails, 
    save_processed_files,
    processed_emails_state,
    processed_files_state
)
from utils.scheduler import get_est_time

# Import from unified services
from .portal_service import (
    run_texas1_initial,
    run_vms1_initial,
    run_suresh1_processing
)
from .combined_monitor import start_combined_monitoring

# Import configuration
from utils.config import EMAIL_RECIPIENTS, DAILY_EMAIL_START_TIME

def main():
    """
    Run initial processing ONLY. Do NOT send email here.
    Email will ONLY be sent by continuous monitoring.
    """
    print("🚀 UNIFIED PORTAL RUNNER - INITIAL PROCESSING ONLY")
    print("=" * 70)
    print("📋 Running initial portal processing")
    print("📊 Creating due list Excel file")
    print(f"📧 Email will be sent by MONITORING at {DAILY_EMAIL_START_TIME} EST")
    print(f"👥 Recipients: {', '.join(EMAIL_RECIPIENTS)}")
    print("=" * 70)
    
    # Load states
    load_processed_emails()
    load_processed_files()
    
    # Get today's date in EST
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    today_date = now_est.strftime("%Y-%m-%d")
    current_time = now_est.strftime("%H:%M:%S EST")
    
    print(f"📅 Today's date (EST): {today_date}")
    print(f"⏰ Current time (EST): {current_time}")
    
    # ========== CHECK EMAIL STATUS ==========
    last_sent_date = processed_emails_state.get('last_email_sent_date')
    
    if last_sent_date == today_date:
        print(f"📧 Email already sent today ({last_sent_date}) - monitoring WON'T send again")
    else:
        print(f"📧 Email not sent yet - monitoring will send at {DAILY_EMAIL_START_TIME} EST")
    
    # ========== RUN INITIAL PROCESSING ==========
    print("\n" + "=" * 70)
    print("STEP 1: RUNNING HHSC PORTAL")
    print("=" * 70)
    hhsc_result = run_texas1_initial()
    time.sleep(2)
    
    print("\n" + "=" * 70)
    print("STEP 2: RUNNING VMS PORTAL")
    print("=" * 70)
    vms_result = run_vms1_initial()
    time.sleep(2)
    
    print("\n" + "=" * 70)
    print("STEP 3: CREATING DUE LIST EXCEL")
    print("=" * 70)
    due_list_result = run_suresh1_processing()
    
    # ========== DO NOT RUN ODOO HERE ==========
    # Let monitoring handle Odoo with proper duplicate prevention
    print("\n" + "=" * 70)
    print("STEP 4: MARKING INITIAL FILES AS PROCESSED")
    print("=" * 70)
    
    # Check for files in both directories
    vms_files = glob.glob("vms_outputs/*.txt")
    dir_files = glob.glob("dir_portal_outputs/*.txt")
    all_files = vms_files + dir_files
    
    if all_files:
        print(f"📁 Found {len(all_files)} initial file(s)")
        print("🔒 Marking them as processed to prevent duplicates...")
        
        current_processed = processed_files_state.get('processed_files', [])
        files_marked = 0
        
        for file_path in all_files:
            try:
                # Create hash of file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                if len(file_content) == 0:
                    continue
                
                file_hash = hashlib.md5(file_content).hexdigest()
                file_id = f"{file_path}:{file_hash}"
                
                if file_id not in current_processed:
                    current_processed.append(file_id)
                    files_marked += 1
                    print(f"   ✓ Marked: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"   ⚠️ Could not hash {os.path.basename(file_path)}: {e}")
                # Mark with filename only as fallback
                if file_path not in current_processed:
                    current_processed.append(file_path)
                    files_marked += 1
        
        # Save the updated state
        processed_files_state['processed_files'] = current_processed
        save_processed_files()
        
        if files_marked > 0:
            print(f"✅ Marked {files_marked} file(s) as processed in state")
        else:
            print("📝 All files were already marked as processed")
    else:
        print("📭 No initial files found to mark as processed")
    
    # ========== DO NOT SEND EMAIL HERE ==========
    # Email will ONLY be sent by monitoring at the scheduled time
    print("\n" + "=" * 70)
    print("📧 EMAIL RULES:")
    print("=" * 70)
    print(f"❌ NO email sent by runner.py")
    print(f"✅ Email will be sent by monitoring at {DAILY_EMAIL_START_TIME} EST")
    print(f"📎 Attachment: job_tracker_report.xlsx")
    print(f"👥 To: {len(EMAIL_RECIPIENTS)} recipients")
    print("=" * 70)
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 70)
    print("🎯 INITIAL PROCESSING COMPLETE")
    print("=" * 70)
    
    # Show results
    if due_list_result.get('status') == 'success':
        excel_file = due_list_result.get('excel_file', 'job_tracker_report.xlsx')
        file_size = os.path.getsize(excel_file) if os.path.exists(excel_file) else 0
        print(f"📊 Due List: ✅ Excel file created")
        print(f"   📄 File: {excel_file} ({file_size} bytes)")
    else:
        print(f"📊 Due List: ❌ Failed")
    
    if hhsc_result.get('status') == 'success':
        processed = hhsc_result.get('processed', 0)
        print(f"🏥 HHSC Portal: ✅ {processed} portals processed")
    else:
        print(f"🏥 HHSC Portal: ❌ Failed")
    
    if vms_result.get('status') == 'success':
        print(f"💼 VMS Portal: ✅ Success")
    else:
        print(f"💼 VMS Portal: ❌ Failed")
    
    print(f"📁 Processed files: {len(all_files)} marked in state")
    print("=" * 70)
    
    # ========== START MONITORING ==========
    print("\n" + "=" * 70)
    print("🔄 STARTING CONTINUOUS MONITORING")
    print("=" * 70)
    print("⚠️  IMPORTANT:")
    print(f"    • Email sends ONCE at {DAILY_EMAIL_START_TIME} EST")
    print(f"    • Initial files already marked as processed")
    print(f"    • Only NEW files will be sent to Odoo")
    print("=" * 70)
    
    time.sleep(3)
    
    # Start monitoring - EMAIL WILL BE SENT BY MONITORING ONLY
    start_combined_monitoring()


if __name__ == "__main__":
    main()