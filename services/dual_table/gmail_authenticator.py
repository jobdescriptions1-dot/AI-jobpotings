# services/dual_table/gmail_authenticator.py
from services.email.universal_gmail_reader import UniversalGmailReader

def get_est_time():
    """Get current Eastern Time"""
    from datetime import datetime
    import pytz
    
    est = pytz.timezone('US/Eastern')
    return datetime.now(est).strftime("%Y-%m-%d %H:%M:%S %Z")

def auto_authenticate_secondary_gmail():
    """Authenticate with secondary Gmail account"""
    try:
        # USE the universal reader with secondary credentials
        reader = UniversalGmailReader(
            token_path='token_secondary.json',
            client_secrets='client_secondary.json'
        )
        return reader.authenticate()
    except Exception as e:
        print(f"Secondary Gmail authentication failed: {e}")
        return None