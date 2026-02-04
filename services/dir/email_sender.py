# services/dir/email_sender.py
from services.email.universal_email_sender import UniversalEmailSender

class HHSCOutlookEmailSender(UniversalEmailSender):
    """HHSC/DIR Email Sender - Now inherits from UniversalEmailSender"""
    def __init__(self, config: dict = None):
        super().__init__(config_type='default')
        # Keep original config parameter for backward compatibility
        if config:
            self.config = config
    
    # All methods are inherited from UniversalEmailSender
    # Original methods: validate_email_addresses, attach_file, extract_title_from_content,
    # send_solicitation_email, send_emails_for_all_solicitations, get_email_config
    # ALL work exactly the same way!