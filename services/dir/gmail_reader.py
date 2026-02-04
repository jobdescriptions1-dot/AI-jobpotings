# services/dir/gmail_reader.py
from services.email.universal_gmail_reader import UniversalGmailReader

class GmailReader(UniversalGmailReader):
    """DIR/HHSC Gmail Reader - Now inherits from UniversalGmailReader"""
    def __init__(self):
        super().__init__()
    
    # All methods are inherited from UniversalGmailReader
    # Can add HHSC-specific methods if needed
    def search_specific_hhsc_email(self, days_back=1):
        """HHSC-specific email search method"""
        query = f'hhsc newer_than:{days_back}d'
        return self.get_recent_emails(query=query)