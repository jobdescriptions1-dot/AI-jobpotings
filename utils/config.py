import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # VMS Configuration
    VMS_GMAIL_USER = os.getenv('VMS_GMAIL_USER', '')
    VMS_GMAIL_PASSWORD = os.getenv('VMS_GMAIL_PASSWORD', '')
    
    # DIR Configuration
    DIR_USERNAME = os.getenv('DIR_USERNAME', '')
    DIR_PASSWORD = os.getenv('DIR_PASSWORD', '')
    
    # LLM Configuration
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    
    # Dual Table Configuration
    DUAL_TABLE_RECIPIENTS = os.getenv('DUAL_TABLE_RECIPIENTS', 'jobdescriptions1@gmail.com').split(',')
    
    # ===== ODOO CONFIGURATION - NEW =====
    ODOO_URL = os.getenv('ODOO_URL', 'http://84.247.136.24:8069')
    ODOO_DB = os.getenv('ODOO_DB', 'mydb')
    ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'admin')
    ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', '79NM46eRqDv)w^q^')
    
    @classmethod
    def get_odoo_config(cls):
        """Get Odoo configuration as a dictionary"""
        return {
            'url': cls.ODOO_URL,
            'db': cls.ODOO_DB,
            'username': cls.ODOO_USERNAME,
            'password': cls.ODOO_PASSWORD
        }
    
# UNIFIED PORTAL CONFIG ONLY
PROCESSED_EMAILS_FILE = "processed_emails.json"
PROCESSED_FILES_FILE = "processed_files.json"
DAILY_EMAIL_TIME = "09:25"
DAILY_EMAIL_START_TIME = "09:25"
DAILY_EMAIL_END_TIME = "09:40"
EMAIL_RECIPIENTS = ["jobdescriptions1@gmail.com"]
processed_emails_state = {}
processed_files_state = {}