"""
Unified portal API routes for Flask application
"""
from flask import Blueprint, jsonify, request
import threading
import os
from datetime import datetime

# Import from unified services
from services.unified.portal_service import (
    run_texas1_initial,
    run_vms1_initial,
    run_suresh1_processing,
    run_odoo_integration
)
from services.unified.combined_monitor import start_combined_monitoring
from services.unified.email_service import send_due_list_email
from services.unified.runner import main as unified_main

# Import state manager
from utils.state_manager import (
    load_processed_emails,
    load_processed_files,
    save_processed_emails,
    processed_emails_state,
    processed_files_state
)

# Create blueprint
unified_bp = Blueprint('unified', __name__)

# Global monitoring thread
monitoring_thread = None
is_monitoring = False

@unified_bp.route('/')
def index():
    """Root endpoint for unified portal API"""
    return jsonify({
        "message": "Unified Portal API",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/unified/": "This information",
            "GET /api/unified/status": "Get system status",
            "POST /api/unified/start": "Start unified processing",
            "POST /api/unified/monitor/start": "Start continuous monitoring",
            "POST /api/unified/monitor/stop": "Stop continuous monitoring",
            "POST /api/unified/email/send": "Send due list email manually",
            "GET /api/unified/stats": "Get processing statistics"
        }
    })

@unified_bp.route('/status', methods=['GET'])
def get_unified_status():
    """Get current unified portal status"""
    global is_monitoring, monitoring_thread
    
    # Load current state
    load_processed_emails()
    load_processed_files()
    
    excel_exists = os.path.exists("job_tracker_report.xlsx")
    excel_size = os.path.getsize("job_tracker_report.xlsx") if excel_exists else 0
    
    status = {
        "monitoring_active": is_monitoring,
        "monitoring_thread_alive": monitoring_thread.is_alive() if monitoring_thread else False,
        "last_email_sent": processed_emails_state.get('last_email_sent_date', 'Never'),
        "processed_hhsc_emails": len(processed_emails_state.get('hhsc_emails', [])),
        "processed_vms_emails": len(processed_emails_state.get('vms_emails', [])),
        "processed_files": len(processed_files_state.get('processed_files', [])),
        "due_list_file": {
            "exists": excel_exists,
            "size_bytes": excel_size
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return jsonify(status)

@unified_bp.route('/start', methods=['POST'])
def start_unified_processing():
    """Start unified processing (run all portals once)"""
    try:
        # Run in background thread
        def run_processing():
            try:
                unified_main()
            except Exception as e:
                print(f"❌ Error in unified processing: {e}")
        
        thread = threading.Thread(target=run_processing)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": "Unified processing started in background",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@unified_bp.route('/monitor/start', methods=['POST'])
def start_unified_monitoring():
    """Start continuous monitoring"""
    global monitoring_thread, is_monitoring
    
    try:
        if is_monitoring:
            return jsonify({
                "message": "Monitoring is already active",
                "status": "already_running"
            })
        
        # Start monitoring in background thread
        monitoring_thread = threading.Thread(target=start_combined_monitoring)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        is_monitoring = True
        
        return jsonify({
            "message": "Continuous monitoring started",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@unified_bp.route('/monitor/stop', methods=['POST'])
def stop_unified_monitoring():
    """Stop continuous monitoring"""
    global is_monitoring
    
    try:
        if not is_monitoring:
            return jsonify({
                "message": "Monitoring is not active",
                "status": "not_running"
            })
        
        # Note: Monitoring runs in infinite loop, needs KeyboardInterrupt
        # For Flask API, we can only set the flag
        is_monitoring = False
        
        return jsonify({
            "message": "Monitoring stop requested (may take a moment)",
            "status": "stopping",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@unified_bp.route('/email/send', methods=['POST'])
def trigger_daily_email():
    """Manually trigger due list email send"""
    try:
        excel_file = "job_tracker_report.xlsx"
        
        if not os.path.exists(excel_file):
            return jsonify({
                "error": "Due list file not found",
                "file": excel_file
            }), 404
        
        # Send email
        success = send_due_list_email(excel_file)
        
        if success:
            # Update last sent date
            processed_emails_state['last_email_sent_date'] = datetime.now().strftime("%Y-%m-%d")
            save_processed_emails()
            
            return jsonify({
                "message": "Due list email sent successfully",
                "status": "sent",
                "timestamp": datetime.now().isoformat(),
                "file": excel_file
            })
        else:
            return jsonify({
                "error": "Failed to send email",
                "status": "failed"
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@unified_bp.route('/stats', methods=['GET'])
def get_processed_stats():
    """Get processing statistics"""
    try:
        # Load current state
        load_processed_emails()
        load_processed_files()
        
        stats = {
            "hhsc_emails_processed": len(processed_emails_state.get('hhsc_emails', [])),
            "vms_emails_processed": len(processed_emails_state.get('vms_emails', [])),
            "total_emails_processed": (
                len(processed_emails_state.get('hhsc_emails', [])) +
                len(processed_emails_state.get('vms_emails', []))
            ),
            "files_processed": len(processed_files_state.get('processed_files', [])),
            "last_email_sent": processed_emails_state.get('last_email_sent_date', 'Never'),
            "last_processing": processed_files_state.get('last_processing_time', 'Never'),
            "state_files": {
                "processed_emails": os.path.exists("processed_emails.json"),
                "processed_files": os.path.exists("processed_files.json"),
                "due_list": os.path.exists("job_tracker_report.xlsx")
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@unified_bp.route('/run/portal/<portal_name>', methods=['POST'])
def run_single_portal(portal_name):
    """Run a single portal processing"""
    try:
        result = None
        
        if portal_name.lower() == 'hhsc':
            result = run_texas1_initial()
        elif portal_name.lower() == 'vms':
            result = run_vms1_initial()
        elif portal_name.lower() == 'dual_table' or portal_name.lower() == 'due_list':
            result = run_suresh1_processing()
        elif portal_name.lower() == 'odoo':
            result = run_odoo_integration()
        else:
            return jsonify({
                "error": f"Unknown portal: {portal_name}",
                "available_portals": ["hhsc", "vms", "dual_table", "odoo"]
            }), 400
        
        return jsonify({
            "portal": portal_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500