"""
Combined monitoring orchestrator - FIXED VERSION
Dual table email sends ONLY ONCE at 9:25 AM EST
Individual requirement emails send immediately
No duplicate Odoo postings
"""
import os
import time
import threading
import hashlib
import glob
import shutil
from datetime import datetime
import pytz

# Import from unified portal modules
from utils.config import EMAIL_RECIPIENTS, DAILY_EMAIL_START_TIME
from utils.state_manager import (
    load_processed_emails,
    load_processed_files,
    processed_emails_state,
    processed_files_state,
    save_processed_emails,
    save_processed_files
)

# Import from unified services
from .portal_service import run_suresh1_processing, run_odoo_integration
from .email_service import send_due_list_email
from .dir_monitor import start_hhsc_monitoring
from .vms_monitor import start_vms_monitoring

class MonitoringState:
    """Track monitoring state in memory"""
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.dual_table_email_sent_today = False  # Track dual table email
        self.processed_files_hashes = set()  # Track processed files
        self.last_check_date = None  # Track date for daily reset
        self.dual_table_attempted_today = False  # Prevent multiple attempts

def start_combined_monitoring():
    """Start continuous monitoring - Dual table email sends ONLY ONCE at 9:25 AM EST"""
    print("\n" + "=" * 70)
    print("🤖 CONTINUOUS MONITORING - FIXED VERSION")
    print("=" * 70)
    print("📊 Dual table email: ONLY ONCE at 9:25 AM EST")
    print("📧 Individual requirements: Send immediately")
    print("🏢 Odoo: Process each file only once")
    print("=" * 70)
    
    # Initialize monitoring state
    state = MonitoringState()
    
    # Load persistent state
    load_processed_emails()
    load_processed_files()
    
    # Get today's date
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    today_date = now_est.strftime("%Y-%m-%d")
    current_time = now_est.strftime("%H:%M:%S EST")
    
    print(f"📅 Today's date: {today_date}")
    print(f"⏰ Current time: {current_time}")
    
    # ========== CHECK DUAL TABLE EMAIL STATUS ==========
    # Use a separate key for dual table email tracking
    last_dual_table_date = processed_emails_state.get('last_dual_table_sent_date')
    
    if last_dual_table_date == today_date:
        state.dual_table_email_sent_today = True
        dual_table_time = processed_emails_state.get('last_dual_table_sent_time', 'unknown')
        print(f"📊 Dual table email already sent today at {dual_table_time}")
        print(f"   Won't send again until tomorrow")
    else:
        print(f"📊 Dual table email not sent today - will send at {DAILY_EMAIL_START_TIME} EST")
    
    # Load already processed files from state
    for file_record in processed_files_state.get('processed_files', []):
        if isinstance(file_record, str):
            state.processed_files_hashes.add(file_record)
    
    print(f"📁 Loaded {len(state.processed_files_hashes)} processed files from state")
    print("=" * 70)
    
    # Start monitoring threads
    print("\n▶️ Starting monitoring threads...")
    hhsc_thread = threading.Thread(target=start_hhsc_monitoring, daemon=True)
    hhsc_thread.start()
    
    vms_thread = threading.Thread(target=start_vms_monitoring, daemon=True)
    vms_thread.start()
    
    print("✅ HHSC monitoring started")
    print("✅ VMS monitoring started")
    print("\n🔄 Monitoring active. Press Ctrl+C to stop.")
    print("\n📝 RULES:")
    print(f"   • Dual table email: ONLY at {DAILY_EMAIL_START_TIME} EST")
    print(f"   • Individual requirements: Process immediately")
    print(f"   • Each file processed only once")
    print("=" * 70)
    
    try:
        check_count = 0
        
        while True:
            # Get current time
            now_est = datetime.now(est)
            current_hour = now_est.hour
            current_minute = now_est.minute
            today_date = now_est.strftime("%Y-%m-%d")
            
            # ========== DAILY RESET ==========
            if state.last_check_date != today_date:
                print(f"\n🔄 NEW DAY: {today_date}")
                
                # Reset daily flags
                state.dual_table_email_sent_today = False
                state.dual_table_attempted_today = False
                state.last_check_date = today_date
                
                # Check persistent state for dual table email
                load_processed_emails()
                last_dual_table_date = processed_emails_state.get('last_dual_table_sent_date')
                if last_dual_table_date == today_date:
                    state.dual_table_email_sent_today = True
                    print(f"📊 State shows dual table email already sent today")
            
            # ========== DUAL TABLE EMAIL (ONLY AT 9:25 AM) ==========
            # Parse email time
            email_hour = int(DAILY_EMAIL_START_TIME.split(':')[0])  # 9
            email_minute = int(DAILY_EMAIL_START_TIME.split(':')[1])  # 25
            
            # Check if it's dual table email time (9:25 AM exact)
            is_dual_table_time = (
                current_hour == email_hour and 
                current_minute == email_minute
            )
            
            # ========== CRITICAL: Send dual table ONLY at 9:25 AM ==========
            if is_dual_table_time and not state.dual_table_email_sent_today and not state.dual_table_attempted_today:
                print(f"\n" + "=" * 70)
                print(f"🎯 DUAL TABLE EMAIL TIME: {DAILY_EMAIL_START_TIME} EST")
                print("=" * 70)
                
                # Mark as attempted to prevent multiple attempts
                state.dual_table_attempted_today = True
                
                # Process due list for dual table
                print("📊 Processing due list for dual table email...")
                due_result = run_suresh1_processing()
                
                if due_result.get('status') == 'success':
                    excel_file = "job_tracker_report.xlsx"
                    
                    if os.path.exists(excel_file):
                        file_size = os.path.getsize(excel_file)
                        print(f"📎 Dual table Excel file: {excel_file} ({file_size} bytes)")
                        print(f"👥 Sending to {len(EMAIL_RECIPIENTS)} recipients...")
                        
                        # Send dual table email
                        email_success = send_due_list_email(excel_file)
                        
                        if email_success:
                            # Update state - dual table email sent
                            state.dual_table_email_sent_today = True
                            processed_emails_state['last_dual_table_sent_date'] = today_date
                            processed_emails_state['last_dual_table_sent_time'] = now_est.strftime('%H:%M:%S')
                            save_processed_emails()
                            
                            print(f"✅ Dual table email sent successfully at {now_est.strftime('%H:%M:%S EST')}")
                            print(f"📅 Marked as sent in state: {today_date}")
                            
                            # ========== CLEAR FOLDERS AFTER DUAL TABLE EMAIL ==========
                            print("\n🗑️ Clearing folders after dual table email...")
                            
                            # Clear vms_outputs folder
                            vms_folder = "vms_outputs"
                            if os.path.exists(vms_folder):
                                for filename in os.listdir(vms_folder):
                                    file_path = os.path.join(vms_folder, filename)
                                    try:
                                        if os.path.isfile(file_path) or os.path.islink(file_path):
                                            os.unlink(file_path)
                                        elif os.path.isdir(file_path):
                                            shutil.rmtree(file_path)
                                    except Exception as e:
                                        print(f"⚠️ Could not delete {file_path}: {e}")
                                print("✅ Cleared vms_outputs folder")
                            
                            # Clear dir_portal_outputs folder
                            dir_folder = "dir_portal_outputs"
                            if os.path.exists(dir_folder):
                                for filename in os.listdir(dir_folder):
                                    file_path = os.path.join(dir_folder, filename)
                                    try:
                                        if os.path.isfile(file_path) or os.path.islink(file_path):
                                            os.unlink(file_path)
                                        elif os.path.isdir(file_path):
                                            shutil.rmtree(file_path)
                                    except Exception as e:
                                        print(f"⚠️ Could not delete {file_path}: {e}")
                                print("✅ Cleared dir_portal_outputs folder")
                            
                            # Clear processed files state for new day
                            processed_files_state['processed_files'] = []
                            save_processed_files()
                            state.processed_files_hashes.clear()
                            print("🔄 Cleared processed files state for new daily cycle")
                        else:
                            print("❌ Failed to send dual table email")
                    else:
                        print(f"❌ Dual table Excel file not found: {excel_file}")
                else:
                    print("❌ Due list processing failed for dual table")
                
                print("=" * 70)
            
            # ========== PROCESS NEW FILES FOR ODOO (NO DUAL TABLE EMAIL) ==========
            # Check for new files in monitoring folders
            vms_files = glob.glob("vms_outputs/*.txt")
            dir_files = glob.glob("dir_portal_outputs/*.txt")
            all_files = vms_files + dir_files
            
            new_files = []
            
            for file_path in all_files:
                try:
                    # Read file and create hash
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    if len(file_content) == 0:
                        continue  # Skip empty files
                    
                    file_hash = hashlib.md5(file_content).hexdigest()
                    file_id = f"{file_path}:{file_hash}"
                    
                    # Check if this exact file content was already processed
                    if file_id not in state.processed_files_hashes:
                        new_files.append(file_path)
                        state.processed_files_hashes.add(file_id)
                        
                        # Update persistent state
                        current_processed = processed_files_state.get('processed_files', [])
                        if file_id not in current_processed:
                            current_processed.append(file_id)
                            processed_files_state['processed_files'] = current_processed
                except Exception as e:
                    print(f"⚠️ Error reading {file_path}: {e}")
                    continue
            
            # ========== IMPORTANT: Process files WITHOUT sending dual table email ==========
            if new_files:
                print(f"\n🔍 FOUND {len(new_files)} NEW REQUIREMENT(S)")
                print("   Processing for Odoo (NO dual table email)...")
                
                for file_path in new_files:
                    print(f"   📄 {os.path.basename(file_path)}")
                
                # Run Odoo integration
                odoo_result = run_odoo_integration()
                
                if odoo_result:
                    if isinstance(odoo_result, dict):
                        posted = odoo_result.get('posted', 0)
                        if posted > 0:
                            print(f"✅ Odoo: Posted {posted} job(s) to Odoo")
                        else:
                            print(f"ℹ️ Odoo: No new jobs to post")
                    elif isinstance(odoo_result, int) and odoo_result > 0:
                        print(f"✅ Odoo: Posted {odoo_result} job(s) to Odoo")
                    else:
                        print(f"ℹ️ Odoo: Processed files")
                else:
                    print(f"ℹ️ Odoo: No result returned")
                
                # Save processed files state
                save_processed_files()
                print(f"✅ Marked {len(new_files)} file(s) as processed")
                
                # ========== CRITICAL: DO NOT send dual table email here ==========
                print(f"⚠️  Dual table email will ONLY be sent at {DAILY_EMAIL_START_TIME} EST")
            
            # ========== SLEEP AND CONTINUE ==========
            # Sleep for 60 seconds
            time.sleep(60)
            check_count += 1
            
            # ========== STATUS DISPLAY ==========
            if check_count % 15 == 0:  # Every 15 minutes
                current_time = datetime.now(est).strftime("%H:%M:%S EST")
                
                print(f"\n📊 STATUS @ {current_time}")
                print(f"   Dual table today: {'✅ Sent' if state.dual_table_email_sent_today else '❌ Not sent'}")
                print(f"   Next dual table: {DAILY_EMAIL_START_TIME} EST")
                print(f"   Processed files: {len(state.processed_files_hashes)}")
                print(f"   HHSC Thread: {'✅ Alive' if hhsc_thread.is_alive() else '❌ Dead'}")
                print(f"   VMS Thread: {'✅ Alive' if vms_thread.is_alive() else '❌ Dead'}")
                
                # Show folder contents
                vms_count = len(glob.glob("vms_outputs/*.txt"))
                dir_count = len(glob.glob("dir_portal_outputs/*.txt"))
                print(f"   Files in vms_outputs: {vms_count}")
                print(f"   Files in dir_portal_outputs: {dir_count}")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitoring...")
        print("💾 Saving state...")
        save_processed_emails()
        save_processed_files()
        print("✅ State saved. Goodbye!")
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    start_combined_monitoring()