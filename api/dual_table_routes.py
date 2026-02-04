# NEW FILE - CREATE THIS
from flask import Blueprint, jsonify, request
from services.dual_table.dual_table_service import run_dual_table_processing
import threading

dual_table_bp = Blueprint('dual_table', __name__)

@dual_table_bp.route('/process', methods=['POST'])
def process_dual_table():
    """Process dual table from folder files"""
    try:
        thread = threading.Thread(target=run_dual_table_processing)
        thread.start()
        
        return jsonify({
            "message": "Dual table processing started",
            "status": "started"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dual_table_bp.route('/status', methods=['GET'])
def get_dual_table_status():
    """Get dual table processing status"""
    return jsonify({
        "status": "ready",
        "description": "Dual table processing system"
    })