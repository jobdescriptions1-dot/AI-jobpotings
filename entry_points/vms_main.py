from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import routes
from api.vms_gmail_routes import vms_gmail_bp
from api.vms_email_routes import email_bp
from api.vms_llm_routes import llm_bp
from api.dir_hhsc_routes import hhsc_bp

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# Register blueprints
app.register_blueprint(vms_gmail_bp, url_prefix='/api/gmail')
app.register_blueprint(email_bp, url_prefix='/api/email')
app.register_blueprint(llm_bp, url_prefix='/api/llm')
app.register_blueprint(hhsc_bp, url_prefix='/api/hhsc')

@app.route('/')
def root():
    """Root endpoint"""
    return jsonify({
        "message": "Requisition Processing System API (Flask)",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/process/now', methods=['POST'])
def process_requisitions_now():
    """Process requisitions immediately"""
    try:
        from services.vms.requisition_processor import RequisitionProcessor
        processor = RequisitionProcessor()
        
        # Run in background thread
        import threading
        thread = threading.Thread(target=processor.run_manual_processing)
        thread.start()
        
        return jsonify({
            "message": "Requisition processing started in background",
            "status": "started"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/monitor/start', methods=['POST'])
def start_monitoring():
    """Start automated monitoring"""
    try:
        from services.vms.automated_monitor import AutomatedRequisitionProcessor
        processor = AutomatedRequisitionProcessor()
        
        # In a real implementation, this would be managed differently
        return jsonify({
            "message": "Monitoring would start (not implemented in this example)",
            "status": "info"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Requisition Processing System (Flask)...")
    print("=" * 50)
    print("API available at: http://localhost:5000")
    print("Endpoints:")
    print("  GET  /              - API status")
    print("  GET  /health        - Health check")
    print("  POST /process/now   - Process requisitions")
    print("  POST /monitor/start - Start monitoring")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)