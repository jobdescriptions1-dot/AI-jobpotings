# services/vms/email_sender.py
from services.email.universal_email_sender import UniversalEmailSender

class EmailSender(UniversalEmailSender):
    """VMS Email Sender - Now inherits from UniversalEmailSender"""
    def __init__(self):
        super().__init__(config_type='vms')
    
    def send_requisition_email_for_id(self, req_id, state_abbr, title, content):
        """Send email for a specific requisition ID"""
        from services.vms.file_manager import FileManager
        
        file_manager = FileManager()
        
        # Find documents
        sm_files, rtr_files = file_manager.find_requisition_files(req_id, state_abbr)
        
        if not sm_files or not rtr_files:
            print(f"❌ Documents not found for requisition {req_id}")
            return False
        
        sm_file = sm_files[0]
        rtr_file = rtr_files[0]
        
        # Send email
        success = self.send_requisition_email(
            req_id=req_id,
            title=title,
            state_abbr=state_abbr,
            body_content=content,
            sm_path=sm_file,
            rtr_path=rtr_file,
            to_emails=self.config.get('to_emails'),
            cc_emails=self.config.get('cc_emails'),
            bcc_emails=self.config.get('bcc_emails')
        )
        
        return success