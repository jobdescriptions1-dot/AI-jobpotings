from flask import Blueprint, jsonify, request
from services.vms.email_sender import EmailSender
from services.vms.file_manager import FileManager

email_bp = Blueprint('vms_email', __name__)

@email_bp.route('/send/requisition', methods=['POST'])
def send_requisition_email():
    """Send requisition email with documents"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        req_id = data.get('req_id')
        title = data.get('title')
        state_abbr = data.get('state_abbr')
        content = data.get('content')
        to_emails = data.get('to_emails')
        cc_emails = data.get('cc_emails')
        bcc_emails = data.get('bcc_emails')
        
        # FIX: Better email list handling
        if to_emails and isinstance(to_emails, str):
            to_emails = [email.strip() for email in to_emails.split(',') if email.strip()]
        elif not isinstance(to_emails, list):
            to_emails = []
            
        if cc_emails and isinstance(cc_emails, str):
            cc_emails = [email.strip() for email in cc_emails.split(',') if email.strip()]
        elif not isinstance(cc_emails, list):
            cc_emails = []
            
        if bcc_emails and isinstance(bcc_emails, str):
            bcc_emails = [email.strip() for email in bcc_emails.split(',') if email.strip()]
        elif not isinstance(bcc_emails, list):
            bcc_emails = []
        
        if not all([req_id, title, state_abbr, content]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # FIX: Validate at least one recipient exists
        if not any([to_emails, cc_emails, bcc_emails]):
            return jsonify({"error": "No valid email recipients specified"}), 400
        
        sender = EmailSender()
        file_manager = FileManager()
        
        # Find documents
        sm_files, rtr_files = file_manager.find_requisition_files(req_id, state_abbr)
        
        if not sm_files or not rtr_files:
            return jsonify({"error": "Documents not found"}), 404
        
        sm_path = sm_files[0]
        rtr_path = rtr_files[0]
        
        success = sender.send_requisition_email(
            req_id=req_id,
            title=title,
            state_abbr=state_abbr,
            body_content=content,
            sm_path=sm_path,
            rtr_path=rtr_path,
            to_emails=to_emails,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails
        )
        
        if success:
            return jsonify({"message": "Email sent successfully", "status": "success"})
        else:
            return jsonify({"error": "Failed to send email"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@email_bp.route('/send/report', methods=['POST'])
def send_excel_report():
    """Send Excel report via email"""
    try:
        sender = EmailSender()
        success = sender.send_excel_report_email()
        
        if success:
            return jsonify({"message": "Excel report email sent", "status": "success"})
        else:
            return jsonify({"error": "Failed to send report email"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@email_bp.route('/config', methods=['GET'])
def get_email_config():
    """Get current email configuration"""
    try:
        sender = EmailSender()
        config = sender.get_email_config()
        return jsonify({"config": config, "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500