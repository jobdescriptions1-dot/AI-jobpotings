# services/vms/gmail_reader.py
from services.email.universal_gmail_reader import UniversalGmailReader

class GmailReader(UniversalGmailReader):
    """VMS Gmail Reader - Now inherits from UniversalGmailReader"""
    def __init__(self):
        super().__init__()
    
    # All methods are inherited from UniversalGmailReader
    # Original methods: authenticate, extract_direct_links, extract_todays_requisition_urls,
    # get_recent_now_open_emails
    # ALL work exactly the same way!