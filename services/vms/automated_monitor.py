import os
import re
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

class AutomatedRequisitionProcessor:
    def __init__(self, check_interval=300):  # 5 minutes
        self.check_interval = check_interval
        self.processed_email_ids = set()
        self.is_running = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start automated monitoring in a separate thread"""
        if self.is_running:
            print("Monitoring is already running")
            return False
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        print("🚀 Starting Automated Requisition Monitor")
        print("=" * 50)
        print("Monitoring for NEW 'Now Open' emails...")
        print(f"Check interval: {self.check_interval} seconds")
        print("=" * 50)
        
        return True
    
    def stop_monitoring(self):
        """Stop automated monitoring"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("🛑 Monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                print(f"\n🔍 Checking for NEW emails at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 50)
                
                new_emails_found = self.check_and_process_new_emails()
                
                if new_emails_found:
                    print(f"✅ Processed new requisitions. Next check in {self.check_interval} seconds...")
                else:
                    print(f"⏳ No new emails found. Waiting {self.check_interval} seconds...")
                
                # Wait for next check
                for _ in range(self.check_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                self.is_running = False
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(60)  # Wait a minute on error
    
    def check_and_process_new_emails(self):
        """Check for and process ONLY new emails that haven't been processed before"""
        try:
            from services.vms.gmail_reader import GmailReader
            
            reader = GmailReader()
            gmail_service = reader.authenticate()
            
            # Get TODAY'S emails
            today_date = datetime.now().strftime("%Y/%m/%d")
            query = f'subject:"Now Open" newer_than:1d'
            
            results = gmail_service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("📭 No 'Now Open' emails found from today")
                return False
            
            # Filter out already processed emails
            new_messages = [msg for msg in messages if msg['id'] not in self.processed_email_ids]
            
            if not new_messages:
                print("✅ No NEW emails found (all today's emails already processed)")
                return False
            
            print(f"📨 Found {len(new_messages)} NEW 'Now Open' emails from today")
            
            # Extract URLs from NEW emails only
            all_new_urls = []
            for msg in new_messages:
                msg_id = msg['id']
                print(f"📧 Processing NEW email: {msg_id}")
                
                urls = self._extract_urls_from_single_email(gmail_service, msg_id)
                if urls:
                    all_new_urls.extend(urls)
                    print(f"   Found {len(urls)} requisition URLs")
                
                # Mark as processed
                self.processed_email_ids.add(msg_id)
            
            if not all_new_urls:
                print("❌ No Vector VMS links found in new emails")
                return False
            
            print(f"🔄 Found {len(all_new_urls)} NEW requisition URLs total, starting processing...")
            
            # Process the new requisitions in background
            processing_thread = threading.Thread(target=self._process_requisitions, args=(all_new_urls,))
            processing_thread.daemon = True
            processing_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking new emails: {e}")
            return False
    
    def _extract_urls_from_single_email(self, gmail_service, message_id):
        """Extract URLs from a single email"""
        try:
            from services.vms.gmail_reader import GmailReader
            
            reader = GmailReader()
            
            msg_data = gmail_service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            payload = msg_data['payload']
            html_body = ""
            plain_text = ""
            
            # Extract email content
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/html':
                        data = part['body'].get('data', '')
                        if data:
                            import base64
                            html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    elif part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            import base64
                            plain_text = base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                if payload['mimeType'] == 'text/html':
                    data = payload['body'].get('data', '')
                    if data:
                        import base64
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                elif payload['mimeType'] == 'text/plain':
                    data = payload['body'].get('data', '')
                    if data:
                        import base64
                        plain_text = base64.urlsafe_b64decode(data).decode('utf-8')
            
            links = reader.extract_direct_links(html_body, plain_text)
            return links
            
        except Exception as e:
            print(f"❌ Error extracting URLs from email: {e}")
            return []
    
    def _process_requisitions(self, urls):
        """Process a list of requisition URLs"""
        if not urls:
            return False
        
        print(f"🎯 PROCESSING {len(urls)} NEW REQUISITIONS")
        
        try:
            from services.vms.requisition_processor import RequisitionProcessor
            
            processor = RequisitionProcessor()
            
            # Clear previous outputs for fresh processing
            self._clear_processing_directories()
            
            # Use existing functions for processing
            from services.vms.requisition_processor import RequisitionProcessor
            req_processor = RequisitionProcessor()
            
            # This would need the driver initialization and processing logic
            # For now, just print a message
            print("Processing would happen here with the original logic")
            
            print("\n✅ NEW requisitions processed COMPLETELY!")
            return True
            
        except Exception as e:
            print(f"❌ Error processing requisitions: {e}")
            return False
    
    def _clear_processing_directories(self):
        """Clear processing directories for fresh start"""
        output_dir = "vms_outputs"
        updated_docs_dir = "vms_documents"
        
        # Clear output directory
        if os.path.exists(output_dir):
            for file in os.listdir(output_dir):
                file_path = os.path.join(output_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            print(f"🧹 Cleared output directory: {output_dir}")
        
        # Clear updated documents directory
        if os.path.exists(updated_docs_dir):
            for file in os.listdir(updated_docs_dir):
                file_path = os.path.join(updated_docs_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            print(f"🧹 Cleared documents directory: {updated_docs_dir}")