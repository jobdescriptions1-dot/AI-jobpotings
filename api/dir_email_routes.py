from flask import Blueprint, jsonify, request
from services.dir.email_sender import HHSCOutlookEmailSender
import threading

dir_email_bp = Blueprint('dir_email', __name__)

@dir_email_bp.route('/send/all', methods=['POST'])
def send_all_emails():
    """Send emails for all processed solicitations"""
    try:
        sender = HHSCOutlookEmailSender()
        
        def run_sending():
            sender.send_emails_for_all_solicitations()
        
        thread = threading.Thread(target=run_sending)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": "Email sending started in background",
            "status": "started"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dir_email_bp.route('/config', methods=['GET'])
def get_email_config():
    """Get email configuration"""
    try:
        sender = HHSCOutlookEmailSender()
        config = sender.get_email_config()
        return jsonify({"config": config, "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500