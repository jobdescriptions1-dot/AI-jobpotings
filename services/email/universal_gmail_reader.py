# services/email/universal_gmail_reader.py
import os
import json
import base64
import re
import time
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import pytz

from utils.email_config import EmailConfig

class UniversalGmailReader:
    def __init__(self, token_path=None, client_secrets=None):
        """Initialize Gmail reader with configurable paths"""
        self.service = None
        config = EmailConfig.get_gmail_credentials_path()
        
        # Allow custom token and client secrets
        self.token_path = token_path or config['token_path']
        self.client_secrets = client_secrets or config['client_secrets']
        self.SCOPES = EmailConfig.get_gmail_scopes()
    
    def authenticate(self):
        """Authenticate with Gmail account"""
        print("\n=== Authenticating Gmail Account ===")
        creds = None
        
        if os.path.exists(self.token_path):
            print("Found token file, loading credentials...")
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
                if creds.expired and creds.refresh_token:
                    print("Credentials expired, refreshing...")
                    creds.refresh(Request())
            except Exception as e:
                print(f"Error loading credentials: {e}")
                creds = None
        
        if not creds or not creds.valid:
            print("No valid credentials found, initiating OAuth flow...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets, self.SCOPES)
                creds = flow.run_local_server(port=8080)
                token_data = json.loads(creds.to_json())
                token_data['creation_time'] = datetime.now(pytz.UTC).isoformat()
                with open(self.token_path, 'w') as token:
                    json.dump(token_data, token)
                print("Authentication successful! Token saved.")
            except Exception as e:
                print(f"Authentication failed: {e}")
                raise
        
        try:
            print("Building Gmail service...")
            self.service = build('gmail', 'v1', credentials=creds)
            print("Gmail service ready!")
            return self.service
        except Exception as e:
            print(f"Failed to build Gmail service: {e}")
            raise
    
    def extract_direct_links(self, html_body, plain_text, link_patterns=None):
        """Extracts links based on patterns"""
        links = []
        
        # Default pattern for Vector VMS
        default_patterns = [
            r'https?://vms\.vectorvms\.com[^\s<>"]+',
            r'https?://[^\s<>"]*hhsc[^\s<>"]*',  # HHSC patterns
            r'https?://[^\s<>"]*portal[^\s<>"]*', # General portals
        ]
        
        patterns = link_patterns or default_patterns
        
        # Extract from HTML
        if html_body:
            soup = BeautifulSoup(html_body, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                for pattern in patterns:
                    if re.search(pattern, href):
                        links.append(href)
                        break
        
        # Extract from plain text
        if plain_text:
            for pattern in patterns:
                text_links = re.findall(pattern, plain_text)
                links.extend(text_links)
            
            # Also capture links after specific text patterns
            prompt_links = re.findall(
                r'(?:Click link|Click here|here|Access|Login):?\s*(https?://[^\s<>"]+)',
                plain_text,
                re.IGNORECASE
            )
            links.extend(prompt_links)
        
        return list(set(links))
    
    def extract_todays_requisition_urls(self, specific_email_ids=None, subject_filter=None):
        """Extracts URLs from TODAY'S Gmail emails"""
        print("\n=== Extracting TODAY'S URLs from Gmail ===")
        
        try:
            if not self.service:
                self.authenticate()
            
            # If specific email IDs are provided
            if specific_email_ids:
                print(f"🔍 Extracting URLs from {len(specific_email_ids)} SPECIFIC emails...")
                today_links = set()
                
                for i, email_id in enumerate(specific_email_ids, 1):
                    print(f"Scanning email {i}/{len(specific_email_ids)} (ID: {email_id[:8]}...)")
                    try:
                        msg_data = self.service.users().messages().get(
                            userId='me',
                            id=email_id,
                            format='full'
                        ).execute()
                        
                        links = self._extract_links_from_message(msg_data)
                        if links:
                            today_links.update(links)
                            print(f"  ✓ Found {len(links)} URLs in this email")
                        
                    except Exception as e:
                        print(f"  ❌ Error scanning email: {e}")
                        continue
                
                print(f"\n✅ Extracted {len(today_links)} URLs from {len(specific_email_ids)} specific emails")
                return list(today_links)
            
            # Build query
            if subject_filter:
                query = f'subject:"{subject_filter}" newer_than:1d'
            else:
                query = 'newer_than:1d'  # Get all today's emails
            
            print(f"Gmail query: {query}")
            
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query
            ).execute()
            messages = results.get('messages', [])
            
            if not messages:
                print("No emails found from the last day.")
                return []
            
            print(f"Found {len(messages)} emails from today. Scanning for links...")
            
            today_links = set()
            processed_count = 0
            
            for i, msg in enumerate(messages, 1):
                print(f"Scanning email {i}/{len(messages)}")
                try:
                    msg_data = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Check if email is from today
                    internal_date = int(msg_data['internalDate'])
                    email_date = datetime.fromtimestamp(internal_date / 1000)
                    is_today = email_date.date() == datetime.now().date()
                    
                    if not is_today:
                        print(f"  ⚠ Email from {email_date.date()} (not today) - SKIPPING")
                        continue
                    
                    links = self._extract_links_from_message(msg_data)
                    today_links.update(links)
                    
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Error scanning email: {e}")
                    continue
            
            print(f"\nProcessed {processed_count} emails from today")
            print(f"Found {len(today_links)} links from today's emails")
            
            return list(today_links)
            
        except Exception as e:
            print(f"Error extracting URLs from Gmail: {e}")
            return []
    
    def _extract_links_from_message(self, msg_data):
        """Extract links from a single email message"""
        payload = msg_data['payload']
        html_body = ""
        plain_text = ""
        
        # Extract email content
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body'].get('data', '')
                    if data:
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        plain_text = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            if payload['mimeType'] == 'text/html':
                data = payload['body'].get('data', '')
                if data:
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
            elif payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    plain_text = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return self.extract_direct_links(html_body, plain_text)
    
    def get_recent_emails(self, query='', limit=10):
        """Get recent emails with optional query filter"""
        try:
            if not self.service:
                self.authenticate()
            
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query,
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for msg in messages:
                try:
                    msg_data = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['Subject', 'Date', 'From']
                    ).execute()
                    
                    headers = msg_data['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
                    from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
                    
                    email_list.append({
                        'id': msg['id'],
                        'subject': subject,
                        'date': date,
                        'from': from_email,
                        'snippet': msg_data.get('snippet', '')
                    })
                except Exception as e:
                    print(f"Error getting email metadata: {e}")
                    continue
            
            return email_list
            
        except Exception as e:
            print(f"Error getting recent emails: {e}")
            return []
    
    # ===== PORTAL-SPECIFIC METHODS (keeping original signatures) =====
    
    def extract_todays_vms_urls(self, specific_email_ids=None):
        """VMS-specific method (original signature)"""
        return self.extract_todays_requisition_urls(
            specific_email_ids=specific_email_ids,
            subject_filter="Now Open"
        )
    
    def extract_todays_hhsc_urls(self, specific_email_ids=None):
        """HHSC-specific method (original signature)"""
        return self.extract_todays_requisition_urls(
            specific_email_ids=specific_email_ids,
            subject_filter=None  # HHSC might have different subject patterns
        )
    
    def get_recent_now_open_emails(self):
        """Get recent 'Now Open' emails (VMS-specific)"""
        return self.get_recent_emails(query='subject:"Now Open" newer_than:1d', limit=10)