from flask import Blueprint, jsonify, request
import threading
import time
from services.dir.hhsc_processor import SolicitationAutomation

hhsc_bp = Blueprint('hhsc', __name__)

def run_processing():
    """Run HHSC solicitation processing in background thread"""
    try:
        print("\n=== STARTING HHSC SOLICITATION PROCESSING ===")
        print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ==== FIX NEEDED HERE: Use the class instead of main() ====
        # ORIGINAL (causing error):
        # main()
        
        # CORRECTED VERSION:
        automation = SolicitationAutomation()
        
        # Since we need to process new emails, we should call the appropriate method
        # The run_single_automation_cycle expects a list of messages
        # For now, let's start the automation which will monitor for emails
        automation.start_automation()
        # ============================================================
        
        print("✅ HHSC processing started successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in HHSC processing: {e}")
        import traceback
        traceback.print_exc()
        return False

@hhsc_bp.route('/process/now', methods=['POST'])
def process_hhsc_now():
    """Process HHSC solicitations immediately"""
    try:
        '''def run_processing():
            from services.dir.hhsc_processor import SolicitationAutomation

            automation = SolicitationAutomation()'''
        
        thread = threading.Thread(target=run_processing)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": "HHSC solicitation processing started",
            "status": "started"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@hhsc_bp.route('/solicitations', methods=['GET'])
def get_solicitations():
    """Get processed solicitations"""
    try:
        import os
        import json
        
        output_dir = "hhsc_portal_outputs"
        if not os.path.exists(output_dir):
            return jsonify({"count": 0, "solicitations": []})
        
        solicitation_files = []
        for filename in os.listdir(output_dir):
            if filename.startswith("Solicitation_Response_Number_") and filename.endswith(".txt"):
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                solicitation_files.append({
                    "filename": filename,
                    "content": content[:500] + "..." if len(content) > 500 else content
                })
        
        return jsonify({
            "count": len(solicitation_files),
            "solicitations": solicitation_files
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500