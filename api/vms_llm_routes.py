from flask import Blueprint, jsonify, request
from services.vms.llm_processor import PureLLMRequisitionProcessor, RequisitionTitleGenerator
from services.vms.file_manager import FileManager
import os

llm_bp = Blueprint('llm', __name__)

@llm_bp.route('/process/content', methods=['POST'])
def process_content_with_llm():
    """Process content with LLM"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        file_content = data.get('file_content')
        filename = data.get('filename')
        title = data.get('title')
        
        if not all([file_content, filename, title]):
            return jsonify({"error": "Missing required fields"}), 400
        
        processor = PureLLMRequisitionProcessor()
        result = processor.process_extracted_data(file_content, filename, title)
        
        if result:
            return jsonify({"processed_content": result, "status": "success"})
        else:
            return jsonify({"error": "LLM processing failed"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@llm_bp.route('/generate/title', methods=['POST'])
def generate_title():
    """Generate title using LLM"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        requisition_content = data.get('requisition_content')
        if not requisition_content:
            return jsonify({"error": "Missing requisition_content"}), 400
        
        generator = RequisitionTitleGenerator()
        title = generator.generate_title(requisition_content)
        
        if title:
            return jsonify({"title": title, "status": "success"})
        else:
            return jsonify({"error": "Title generation failed"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@llm_bp.route('/process/all', methods=['POST'])
def process_all_files():
    """Process all extracted files with LLM"""
    try:
        file_manager = FileManager()
        processor = PureLLMRequisitionProcessor()
        generator = RequisitionTitleGenerator()
        
        files = file_manager.get_all_requisition_files()
        processed_count = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                if "Job ID:" in file_content and "title:" in file_content:
                    continue
                
                title = generator.generate_title(file_content)
                if not title:
                    title = "Position"
                
                formatted_content = processor.process_extracted_data(
                    file_content,
                    os.path.basename(file_path),
                    title
                )
                
                if formatted_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(formatted_content)
                    processed_count += 1
                    
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        return jsonify({
            "message": f"Processed {processed_count} files",
            "processed_count": processed_count,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500