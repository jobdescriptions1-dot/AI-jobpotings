from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys
import threading
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import ONLY unified blueprint
from api.unified_routes import unified_bp

app = Flask(__name__)
CORS(app)

# ============================================================================
# RAG SYSTEM INITIALIZATION (NEW - Add at top)
# ============================================================================
try:
    from rag import init_rag_system
    from rag.chatbot_api import create_rag_blueprint
    
    # Initialize RAG system
    RAG_SYSTEM = init_rag_system()
    
    if RAG_SYSTEM:
        # Create RAG blueprint
        rag_bp = create_rag_blueprint(RAG_SYSTEM)
        app.register_blueprint(rag_bp, url_prefix='/rag')
        RAG_AVAILABLE = True
        print("✅ RAG Chatbot System: INITIALIZED")
    else:
        RAG_AVAILABLE = False
        print("⚠️ RAG Chatbot System: DISABLED (Initialization failed)")
        
except ImportError as e:
    print(f"⚠️ RAG system not available: {e}")
    RAG_AVAILABLE = False
    RAG_SYSTEM = None
except Exception as e:
    print(f"⚠️ Error initializing RAG system: {e}")
    RAG_AVAILABLE = False
    RAG_SYSTEM = None

# ============================================================================
# YOUR EXISTING CODE BELOW - NO CHANGES TO LOGIC
# ============================================================================

# Register ONLY unified blueprint
app.register_blueprint(unified_bp, url_prefix='/api')

@app.route('/')
def root():
    endpoints = {
        "system": "Unified Government Procurement Automation System",
        "version": "1.0.0",
        "status": "running",
        "automation": "auto-started",
        "monitoring": "active",
        "endpoints": {
            "GET /": "This information",
            "GET /api/status": "Get system status",
            "POST /api/start": "Start unified processing",
            "POST /api/monitor/start": "Start continuous monitoring",
            "POST /api/monitor/stop": "Stop monitoring",
            "POST /api/email/send": "Send due list email",
            "GET /api/stats": "Get processing statistics",
            "POST /api/run/portal/<portal_name>": "Run specific portal"
        }
    }
    
    # Add RAG endpoints if available
    if RAG_AVAILABLE:
        endpoints["rag_chatbot"] = {
            "GET /rag/stats": "RAG system statistics",
            "POST /rag/query": "Ask questions about jobs",
            "GET /rag/sample-queries": "Example questions",
            "GET /rag/odoo-postings": "Odoo posting statistics"
        }
    
    return jsonify(endpoints)

def auto_start_monitoring():
    """Automatically start monitoring when server starts"""
    time.sleep(5)  # Wait 5 seconds for Flask to fully initialize
    
    print("\n" + "="*70)
    print("🤖 STARTING CONTINUOUS MONITORING WITH DUAL TABLE PROCESSING")
    print("="*70)
    
    try:
        # Import here to avoid circular imports
        from services.unified.combined_monitor import start_combined_monitoring
        
        print("📧 Monitoring both HHSC and VMS portals for NEW emails only")
        print("⏰ Checking every 15 seconds for NEW emails")
        print("📊 Processing due list using dual table (job_tracker_report.xlsx)")
        print("📧 Sending daily email to 1 recipients daily")
        print("👥 Recipients: jobdescriptions1@gmail.com")
        
        # Add RAG information
        if RAG_AVAILABLE:
            print("🤖 RAG Chatbot: ENABLED (http://localhost:5000/rag)")
            print("   • Auto-processes files before clearing")
            print("   • Query jobs via: POST /rag/query")
        else:
            print("🤖 RAG Chatbot: DISABLED")
            
        print("⏹️  Press Ctrl+C to stop automation")
        print("="*70)
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(
            target=start_combined_monitoring,
            daemon=True,
            name="Automation-Monitor"
        )
        monitor_thread.start()
        
        # Give it a moment to start
        time.sleep(2)
        
        if monitor_thread.is_alive():
            print("✅ AUTOMATION MONITORING STARTED SUCCESSFULLY!")
            print("   System is now actively watching for emails")
            print("   Press Ctrl+C to stop both Flask and automation")
            print("="*70)
        else:
            print("⚠️  Monitoring thread started but may have issues")
            print("   Check logs for details")
            print("="*70)
            
    except ImportError as e:
        print(f"❌ Cannot import monitoring modules: {e}")
        print("   Make sure services/unified/ directory exists")
        print("="*70)
    except Exception as e:
        print(f"❌ Failed to auto-start monitoring: {e}")
        print("   You can still start manually via: POST /api/monitor/start")
        print("="*70)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Create output directories
    os.makedirs('dir_documents', exist_ok=True)
    os.makedirs('vms_documents', exist_ok=True)
    
    print("🚀 UNIFIED BACKEND SYSTEM STARTING")
    print("="*70)
    print("🌐 Web Server: Flask API")
    print("🤖 Automation: Auto-start enabled")
    print("🔄 Monitoring: Will start in 5 seconds")
    
    # Add RAG status
    if RAG_AVAILABLE:
        print("🤖 RAG Chatbot: ENABLED")
    else:
        print("🤖 RAG Chatbot: DISABLED (check requirements)")
    
    print("\n📋 AVAILABLE ENDPOINTS:")
    print("  GET  /                    - System information")
    print("  GET  /api/status          - System status")
    print("  POST /api/start           - Run all portals once")
    print("  POST /api/monitor/start   - Start continuous monitoring")
    print("  POST /api/monitor/stop    - Stop monitoring")
    print("  POST /api/email/send      - Send due list email")
    print("  GET  /api/stats           - Processing statistics")
    print("  POST /api/run/portal/<name> - Run specific portal")
    
    # Add RAG endpoints if available
    if RAG_AVAILABLE:
        print("\n🤖 RAG CHATBOT ENDPOINTS:")
        print("  GET  /rag/stats           - RAG system statistics")
        print("  POST /rag/query           - Ask questions about jobs")
        print("  GET  /rag/sample-queries  - Example questions")
        print("  GET  /rag/odoo-postings   - Odoo posting statistics")
    
    print("="*70)
    print("⏳ Starting Flask server on http://0.0.0.0:5000")
    print("⏳ Automation will auto-start in 5 seconds...")
    
    # Start automation monitoring in background thread
    automation_thread = threading.Thread(
        target=auto_start_monitoring,
        daemon=True,
        name="Auto-Start-Monitoring"
    )
    automation_thread.start()
    
    # Start Flask server
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n" + "="*70)
        print("🛑 SYSTEM SHUTDOWN REQUESTED")
        print("="*70)
        print("Stopping Flask server and automation...")
        
        # Stop RAG ingestion if running
        if RAG_AVAILABLE and RAG_SYSTEM:
            try:
                RAG_SYSTEM['ingestion_service'].stop_watching()
                print("✅ RAG ingestion stopped")
            except:
                pass
        
        print("Goodbye!")
        print("="*70)