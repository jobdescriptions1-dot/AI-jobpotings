from flask import Blueprint, jsonify, request
from services.dir.gmail_reader import GmailReader
from services.vms.requisition_processor import RequisitionProcessor
import threading

dir_gmail_bp = Blueprint('gmail', __name__)

@dir_gmail_bp.route('/authenticate', methods=['GET'])
def authenticate_gmail():
    """Authenticate with Gmail"""
    try:
        reader = GmailReader()
        service = reader.authenticate()
        return jsonify({
            "message": "Gmail authenticated successfully",
            "status": "success"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dir_gmail_bp.route('/urls/today', methods=['GET'])
def get_todays_requisition_urls():
    """Get today's requisition URLs from Gmail"""
    try:
        reader = GmailReader()
        urls = reader.extract_todays_requisition_urls()
        return jsonify({
            "count": len(urls),
            "urls": urls,
            "status": "success"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dir_gmail_bp.route('/process/today', methods=['POST'])
def process_todays_requisitions():
    """Process today's requisitions from Gmail"""
    try:
        def run_processing():
            processor = RequisitionProcessor()
            processor.run_manual_processing()
        
        thread = threading.Thread(target=run_processing)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": "Today's requisitions processing started",
            "status": "started"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dir_gmail_bp.route('/emails/recent', methods=['GET'])
def get_recent_emails():
    """Get recent 'Now Open' emails"""
    try:
        reader = GmailReader()
        emails = reader.get_recent_now_open_emails()
        return jsonify({
            "count": len(emails),
            "emails": emails,
            "status": "success"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500