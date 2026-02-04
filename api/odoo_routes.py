from flask import Blueprint, jsonify, request
from services.odoo.odoo_service import OdooService
import threading

oddo_bp = Blueprint('oddo', __name__)

@oddo_bp.route('/process', methods=['POST'])
def process_oddo():
    """Process all job files to Odoo"""
    try:
        def run_processing():
            service = OdooService()
            created = service.process_files()
            if created:
                print(f"✅ Created {created} job postings in Odoo")
            else:
                print("❌ No jobs created in Odoo")
        
        thread = threading.Thread(target=run_processing)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": "Odoo processing started in background",
            "status": "started"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@oddo_bp.route('/status', methods=['GET'])
def oddo_status():
    """Check Odoo connection status"""
    try:
        service = OdooService()
        connected = service.authenticate()
        
        return jsonify({
            "connected": connected,
            "status": "ready" if connected else "disconnected",
            "message": "Odoo connection successful" if connected else "Odoo connection failed"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500