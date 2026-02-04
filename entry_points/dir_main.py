import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config
from services.dir.hhsc_processor import SolicitationAutomation
from api.dir_hhsc_routes import hhsc_bp
from api.dir_email_routes import dir_email_bp
from api.vms_llm_routes import llm_bp
from api.dir_hhsc_routes import hhsc_bp

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app)

# Register blueprints
app.register_blueprint(hhsc_bp, url_prefix='/api/hhsc')
app.register_blueprint(dir_email_bp, url_prefix='/api/email')
app.register_blueprint(llm_bp, url_prefix='/api/llm')

# Global automation instance
automation = None

@app.route('/')
def root():
    return jsonify({
        "message": "Texas HHSC Solicitation Processing System",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/process/now', methods=['POST'])
def process_hhsc_now():
    """Process HHSC solicitations immediately"""
    global automation
    
    try:
        # Run initial processing in background thread
        def run_processing():
            from services.dir.hhsc_processor import main
            main()
        
        thread = threading.Thread(target=run_processing)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": "HHSC solicitation processing started in background",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error starting processing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/monitor/start', methods=['POST'])
def start_monitoring():
    """Start automated monitoring"""
    global automation
    
    try:
        if automation and automation.is_running:
            return jsonify({
                "message": "Monitoring is already active",
                "status": "already_running"
            })
        
        automation = SolicitationAutomation()
        automation.start_automation()
        
        return jsonify({
            "message": "HHSC monitoring started",
            "status": "started",
            "interval_seconds": app.config['CHECK_INTERVAL'],
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error starting monitoring: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/monitor/stop', methods=['POST'])
def stop_monitoring():
    """Stop automated monitoring"""
    global automation
    
    try:
        if not automation or not automation.is_running:
            return jsonify({
                "message": "Monitoring is not active",
                "status": "not_running"
            })
        
        automation.stop_automation()
        
        return jsonify({
            "message": "HHSC monitoring stopped",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error stopping monitoring: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def get_status():
    """Get current system status"""
    global automation
    
    if automation:
        status = automation.get_status()
        return jsonify(status)
    else:
        return jsonify({
            "monitoring_active": False,
            "status": "Not monitoring",
            "timestamp": datetime.now().isoformat()
        })

if __name__ == '__main__':
    print("🚀 Starting Texas HHSC Solicitation Processing System (Flask)...")
    print("=" * 60)
    print(f"API available at: http://localhost:5000")
    print("Endpoints:")
    print("  GET  /                  - API status")
    print("  GET  /health            - Health check")
    print("  POST /process/now       - Process solicitations")
    print("  POST /monitor/start     - Start monitoring")
    print("  POST /monitor/stop      - Stop monitoring")
    print("  GET  /status            - Get monitoring status")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=app.config['FLASK_DEBUG'])