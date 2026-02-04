# services/config/email_config.py
import os
from dotenv import load_dotenv

load_dotenv()

class EmailConfig:
    """Central configuration for ALL email services"""
    
    @staticmethod
    def get_email_config():
        """Get email configuration for SMTP"""
        return {
            'sender_email': os.getenv('EMAIL_USER', ''),
            'password': os.getenv('EMAIL_PASSWORD', ''),
            'smtp_server': "smtp.gmail.com",
            'smtp_port': 587,
            'to_emails': [email.strip() for email in os.getenv('TO_EMAILS', '').split(',') if email.strip()],
            'cc_emails': [email.strip() for email in os.getenv('CC_EMAILS', '').split(',') if email.strip()],
            'bcc_emails': [email.strip() for email in os.getenv('BCC_EMAILS', '').split(',') if email.strip()]
        }
    
    @staticmethod
    def get_vms_email_config():
        """VMS-specific email config (keeps original structure)"""
        return {
            'sender_email': os.getenv('EMAIL_USER'),
            'password': os.getenv('EMAIL_PASSWORD'),
            'smtp_server': "smtp.gmail.com",
            'smtp_port': 587,
            'to_emails': ["jobdescriptions1@gmail.com"],   # "support@innosoul.com"
            'cc_emails': [],
            'bcc_emails': []
        }
    
    @staticmethod
    def get_gmail_scopes():
        """Gmail API scopes"""
        return ['https://www.googleapis.com/auth/gmail.readonly']
    
    @staticmethod
    def get_gmail_credentials_path():
        """Path to Gmail credentials"""
        return {
            'token_path': 'token.json',
            'client_secrets': 'client.json'
        }