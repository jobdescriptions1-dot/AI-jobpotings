# services/email/universal_email_sender.py
import os
import re
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

from utils.email_config import EmailConfig

class UniversalEmailSender:
    def __init__(self, config_type='default'):
        """
        Initialize with specific config type
        config_type: 'default' or 'vms'
        """
        if config_type == 'vms':
            self.config = EmailConfig.get_vms_email_config()
        else:
            self.config = EmailConfig.get_email_config()
        
        # Import helpers as needed
        from utils.vms_helpers import validate_email_addresses, STATE_MAPPING
        self.validate_email_addresses = validate_email_addresses
        self.STATE_MAPPING = STATE_MAPPING
    
    def validate_email_list(self, email_list):
        """Validate email addresses before sending"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        valid_emails = []
        
        for email in email_list if email_list else []:
            if isinstance(email, str) and re.match(email_regex, email):
                valid_emails.append(email)
            else:
                print(f"Invalid email address: {email}")
        
        return valid_emails
    
    def attach_file(self, msg, file_path, filename):
        """Helper function to attach files with error handling"""
        # FIX: Check if file_path is just a filename without path
        if not os.path.isabs(file_path) and not os.path.exists(file_path):
            # Try common directories
            common_dirs = ["vms_documents", "dir_documents", "Documents"]
            for dir_name in common_dirs:
                potential_path = os.path.join(dir_name, file_path)
                if os.path.exists(potential_path):
                    file_path = potential_path
                    break
                # Try with just the filename
                potential_path = os.path.join(dir_name, filename)
                if os.path.exists(potential_path):
                    file_path = potential_path
                    break
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as file:
                    part = MIMEApplication(file.read(), Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)
                print(f"    ✅ Attached: {filename} from {file_path}")
                return True
            except Exception as e:
                logging.error(f"Failed to attach {filename}: {str(e)}")
                return False
        else:
            logging.warning(f"File not found for attachment: {file_path}")
            return False
    
    def extract_title_from_content(self, content):
        """Extract job title from LLM-processed content (for HHSC/DIR)"""
        lines = content.split('\n')
        
        # Look for the title line (after Job ID line)
        for i, line in enumerate(lines):
            if line.startswith('Job ID:'):
                # The title should be 2 lines after Job ID
                if i + 2 < len(lines):
                    title_line = lines[i + 2].strip()
                    if title_line and not title_line.startswith(('Location:', 'Duration:', 'Positions:', 'Skills:', 'Description:')):
                        return title_line
        
        return "Solicitation Response"
    
    def send_generic_email(self, subject, body, attachments=None, 
                          to_emails=None, cc_emails=None, bcc_emails=None):
        """Send a generic email with attachments"""
        try:
            # Use provided emails or config defaults
            to_emails = self.validate_email_list(to_emails or self.config.get('to_emails', []))
            cc_emails = self.validate_email_list(cc_emails or self.config.get('cc_emails', []))
            bcc_emails = self.validate_email_list(bcc_emails or self.config.get('bcc_emails', []))
            
            if not any([to_emails, cc_emails, bcc_emails]):
                logging.error("No valid email recipients found")
                return False
            
            sender_email = self.config['sender_email']
            password = self.config['password']
            smtp_server = self.config['smtp_server']
            smtp_port = self.config['smtp_port']
            
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = sender_email
            
            # Set recipients
            if to_emails:
                msg['To'] = ', '.join(to_emails)
            
            # Add CC if specified
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Subject
            msg['Subject'] = subject
            
            # Body
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach files
            attachments = attachments or []
            attachments_successful = 0
            for attachment in attachments:
                if isinstance(attachment, tuple):
                    file_path, filename = attachment
                else:
                    file_path = attachment
                    filename = os.path.basename(attachment)
                
                if self.attach_file(msg, file_path, filename):
                    attachments_successful += 1
            
            # Prepare all recipients
            all_recipients = []
            if to_emails:
                all_recipients.extend(to_emails)
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            # Remove duplicates
            all_recipients = list(set(all_recipients))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.sendmail(sender_email, all_recipients, msg.as_string())
            
            logging.info(f"✅ Email sent: {subject}")
            logging.info(f"   Recipients: {len(all_recipients)}")
            logging.info(f"   Attachments: {attachments_successful}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to send email: {str(e)}")
            return False
    
    # ===== PORTAL-SPECIFIC METHODS (keeping original signatures) =====
    
    def send_solicitation_email(self, req_number, title, body_content, document_paths):
        """HHSC/DIR Portal email sending (original signature)"""
        return self.send_generic_email(
            subject=title,
            body=body_content,
            attachments=[(doc, os.path.basename(doc)) for doc in document_paths]
        )
    
    def send_requisition_email(self, req_id, title, state_abbr, body_content, sm_path, rtr_path, 
                              to_emails=None, cc_emails=None, bcc_emails=None):
        """VMS Portal email sending (original signature)"""
        # Use VMS-specific email validation
        to_emails = self.validate_email_addresses(to_emails or self.config.get('to_emails', []))
        cc_emails = self.validate_email_addresses(cc_emails or self.config.get('cc_emails', []))
        bcc_emails = self.validate_email_addresses(bcc_emails or self.config.get('bcc_emails', []))
        
        # Determine filenames
        sm_filename = f"SM_{state_abbr}_{req_id}.docx"
        rtr_filename = f"RTR_{state_abbr}_{req_id}.docx"
        
        # Prepare attachments
        attachments = []
        if sm_path == rtr_path:
            # Combined document
            attachments.append((sm_path, sm_filename))
            attachments.append((rtr_path, rtr_filename))
        else:
            # Separate documents
            attachments.append((sm_path, sm_filename))
            attachments.append((rtr_path, rtr_filename))
        
        # Add state info to body
        state_name = self.STATE_MAPPING.get(state_abbr, self.STATE_MAPPING['DEFAULT'])['full_name']
        enhanced_body = f"""{body_content}

Please find attached the SM and RTR documents for this {state_name} requisition.
"""
        
        return self.send_generic_email(
            subject=title,
            body=enhanced_body,
            attachments=attachments,
            to_emails=to_emails,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails
        )
    
    def send_excel_report_email(self, excel_file_path="combined_due_list.xlsx", subject_prefix="Requisition Due List Report"):
        """Send Excel report email"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        subject = f"{subject_prefix} - {current_date}"
        
        body = f"""
        Hello Team,
        
        Please find attached the Combined Requisition Due List Report for {current_date}.
        
        This report contains:
        - All processed requisitions from Vector VMS
        - All solicitation responses from HHSC Portal
        - Due date categorization (Active vs Past Due)
        - Job titles and IDs from both sources
        
        The report is automatically generated and includes all requisitions processed today.
        
        Report Features:
        • Active Due: Jobs with future due dates
        • Past Due: Jobs with due dates that have passed
        • Combined data from multiple sources
        
        Best regards,
        Automated Requisition System
        """
        
        attachments = [(excel_file_path, "combined_due_list.xlsx")]
        
        return self.send_generic_email(
            subject=subject,
            body=body,
            attachments=attachments
        )
    
    def get_email_config(self, hide_password=True):
        """Get current email configuration"""
        config = self.config.copy()
        if hide_password and 'password' in config:
            config['password'] = '********'
        return config
    
    def send_emails_for_all_solicitations(self):
        """HHSC/DIR specific batch email sending"""
        print("\n=== SENDING SOLICITATION EMAILS ===")
        email_count = 0
        
        # Get all processed solicitation files
        output_dir = "dir_portal_outputs"
        documents_dir = "dir_documents"
        
        if not os.path.exists(output_dir):
            print("No output directory found")
            return 0
        
        import re
        
        solicitation_files = []
        for filename in os.listdir(output_dir):
            if filename.startswith("Solicitation_Response_Number_") and filename.endswith(".txt"):
                solicitation_files.append(filename)
        
        if not solicitation_files:
            print("No solicitation files found")
            return 0
        
        import time
        
        for filename in solicitation_files:
            try:
                # Extract requisition number from filename
                req_match = re.search(r'Solicitation_Response_Number_([^_\.]+)', filename)
                if not req_match:
                    continue
                    
                req_number = req_match.group(1)
                
                # Read the processed content
                file_path = os.path.join(output_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract title from content
                title = self.extract_title_from_content(content)
                
                # Find corresponding document files
                document_files = []
                for doc_file in os.listdir(documents_dir):
                    if req_number in doc_file and doc_file.lower().endswith(('.docx', '.doc', '.pdf')):
                        document_files.append(os.path.join(documents_dir, doc_file))
                
                if not document_files:
                    print(f"⚠️ No documents found for {req_number}, skipping email")
                    continue
                
                # Send email
                success = self.send_solicitation_email(
                    req_number=req_number,
                    title=title,
                    body_content=content,
                    document_paths=document_files
                )
                
                if success:
                    email_count += 1
                
                # Small delay between emails
                time.sleep(2)
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
        
        return email_count