import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.odoo_routes import oddo_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app)

# Register blueprint
app.register_blueprint(oddo_bp, url_prefix='/api/oddo')

@app.route('/')
def root():
    return jsonify({
        "message": "Odoo Integration API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /api/oddo/authenticate": "Authenticate with Odoo",
            "POST /api/oddo/process/jobs": "Process jobs to Odoo",
            "GET /api/oddo/status": "Get Odoo status and file counts",
            "GET /api/oddo/config": "Get Odoo configuration",
            "POST /api/oddo/test/connection": "Test Odoo connection"
        }
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Odoo Integration API...")
    print("=" * 60)
    print(f"API available at: http://localhost:5050")
    print("Endpoints:")
    print("  GET  /                  - API status")
    print("  GET  /health            - Health check")
    print("  POST /api/oddo/authenticate - Authenticate with Odoo")
    print("  POST /api/oddo/process/jobs - Process jobs to Odoo")
    print("  GET  /api/oddo/status   - Get Odoo status")
    print("  GET  /api/oddo/config   - Get Odoo config")
    print("  POST /api/oddo/test/connection - Test Odoo connection")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5050, debug=True)