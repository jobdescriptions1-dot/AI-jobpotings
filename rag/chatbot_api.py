"""
RAG Chatbot API endpoints
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any
import logging
from .query_engine import QueryEngine

logger = logging.getLogger(__name__)

def create_rag_blueprint(rag_system: Dict[str, Any]) -> Blueprint:
    """
    Create Flask blueprint for RAG chatbot API
    
    Args:
        rag_system: Dictionary containing RAG system components
        
    Returns:
        Flask Blueprint
    """
    bp = Blueprint('rag', __name__)
    
    # Extract components
    ingestion_service = rag_system.get('ingestion_service')
    chroma_manager = rag_system.get('chroma_manager')
    sqlite_manager = rag_system.get('sqlite_manager')
    
    # Initialize query engine
    query_engine = QueryEngine(chroma_manager, sqlite_manager)
    
    @bp.route('/query', methods=['POST'])
    def query():
        """
        Query the RAG system
        
        Expected JSON:
        {
            "question": "Show Georgia jobs due next week",
            "detailed": false  # Optional: return detailed skill info
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'question' not in data:
                return jsonify({
                    'error': 'Missing question parameter',
                    'usage': 'Send JSON with {"question": "your question"}'
                }), 400
            
            question = data['question']
            detailed = data.get('detailed', False)
            
            logger.info(f"Processing query: {question}")
            
            # Process query
            results = query_engine.process_query(question)
            
            # Add detailed skill info if requested
            if detailed and 'results' in results:
                for result in results['results']:
                    if result.get('job_id'):
                        # You could add more detailed skill info here
                        pass
            
            return jsonify(results)
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return jsonify({
                'error': str(e),
                'query': data.get('question', 'unknown') if 'data' in locals() else 'unknown'
            }), 500
            
    @bp.route('/jobs', methods=['GET'])
    def get_jobs():
        """
        Get list of jobs with filtering and pagination
        Query Params:
            state: Filter by state
            work_mode: Filter by work mode
            limit: Number of results (default 50)
            offset: Skip results (default 0)
        """
        try:
            if not sqlite_manager:
                return jsonify({'error': 'SQLite manager not available'}), 500
                
            state_filter = request.args.get('state')
            mode_filter = request.args.get('work_mode')
            title_filter = request.args.get('title')
            job_id_filter = request.args.get('job_id')
            status_filter = request.args.get('status')
            location_filter = request.args.get('location')
            due_after_filter = request.args.get('due_date_after')
            
            print(f"🔍 DEBUG: /jobs called with filters: location={location_filter}, title={title_filter}, status={status_filter}")
            
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            filters = {}
            if state_filter: filters['state'] = state_filter
            if mode_filter: filters['work_mode'] = mode_filter
            if title_filter: filters['title'] = title_filter
            if job_id_filter: filters['job_id'] = job_id_filter
            if status_filter: filters['status'] = status_filter
            if location_filter: filters['location'] = location_filter
            if due_after_filter: filters['due_date_after'] = due_after_filter
            
            # Fetch jobs from SQLite manager
            jobs = sqlite_manager.search_jobs(filters=filters, limit=limit)
            
            # Get total count for pagination info
            stats = sqlite_manager.get_job_stats()
            total_count = stats.get('total_jobs', len(jobs))
            
            return jsonify({
                'jobs': jobs,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'filters': filters,
                'stats': {
                    'active': stats.get('active_jobs', 0),
                    'expired': stats.get('expired_jobs', 0)
                }
            })
            
        except Exception as e:
            logger.error(f"Jobs list error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/ingest-folder', methods=['POST'])
    def ingest_folder():
        """
        Process all files in a folder before clearing
        
        Expected JSON:
        {
            "folder_path": "vms_outputs"
        }
        """
        try:
            if not ingestion_service:
                return jsonify({'error': 'Ingestion service not available'}), 500
            
            data = request.get_json()
            
            if not data or 'folder_path' not in data:
                return jsonify({
                    'error': 'Missing folder_path parameter'
                }), 400
            
            folder_path = data['folder_path']
            
            # Process folder before clearing
            result = ingestion_service.process_folder_before_clear(folder_path)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Folder ingestion error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/process-file', methods=['POST'])
    def process_file():
        """
        Manually process a specific file
        
        Expected JSON:
        {
            "file_path": "path/to/file.txt"
        }
        """
        try:
            if not ingestion_service:
                return jsonify({'error': 'Ingestion service not available'}), 500
            
            data = request.get_json()
            
            if not data or 'file_path' not in data:
                return jsonify({
                    'error': 'Missing file_path parameter'
                }), 400
            
            from pathlib import Path
            file_path = Path(data['file_path'])
            
            if not file_path.exists():
                return jsonify({
                    'error': f'File not found: {file_path}'
                }), 404
            
            success = ingestion_service.process_file(file_path)
            
            return jsonify({
                'success': success,
                'file_path': str(file_path),
                'message': 'File processed successfully' if success else 'Failed to process file'
            })
            
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/stats', methods=['GET'])
    def stats():
        """Get RAG system statistics"""
        try:
            if not chroma_manager or not sqlite_manager:
                return jsonify({'error': 'RAG system not fully initialized'}), 500
            
            chroma_stats = chroma_manager.get_stats()
            sqlite_stats = sqlite_manager.get_job_stats()
            
            stats = {
                'chroma_db': chroma_stats,
                'sqlite_db': sqlite_stats,
                'ingestion_status': {
                    'running': ingestion_service.running if ingestion_service else False,
                    'watch_dirs': [str(d) for d in ingestion_service.watch_dirs] if ingestion_service else []
                }
            }
            
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/sample-queries', methods=['GET'])
    def sample_queries():
        """Get sample queries for testing"""
        samples = [
            {
                "question": "Show Georgia jobs due next week",
                "description": "Find jobs in Georgia with due dates in the next 7 days",
                "type": "structured"
            },
            {
                "question": "Find Hybrid Java Developer positions",
                "description": "Search for Hybrid work Java Developer jobs",
                "type": "hybrid"
            },
            {
                "question": "What skills are required for Business Analyst roles?",
                "description": "Extract skills from Business Analyst positions",
                "type": "semantic"
            },
            {
                "question": "How many submissions for job GA-12345?",
                "description": "Get submission count for specific job from Excel",
                "type": "tracking"
            },
            {
                "question": "Show jobs posted to Odoo today",
                "description": "Find jobs that were posted to Odoo ERP today",
                "type": "odoo"
            },
            {
                "question": "List Texas jobs with Python skill and 5+ submissions",
                "description": "Complex query with multiple filters",
                "type": "complex"
            }
        ]
        
        return jsonify({
            'sample_queries': samples,
            'total_samples': len(samples),
            'usage_note': 'POST to /rag/query with {"question": "your question", "detailed": true/false}'
        })
    
    @bp.route('/search-skills', methods=['POST'])
    def search_skills():
        """
        Search for jobs by specific skill with experience requirements
        
        Expected JSON:
        {
            "skill": "Python",
            "min_experience_years": 3,
            "required_only": true
        }
        """
        try:
            if not sqlite_manager:
                return jsonify({'error': 'SQLite manager not available'}), 500
            
            data = request.get_json()
            
            if not data or 'skill' not in data:
                return jsonify({'error': 'Missing skill parameter'}), 400
            
            skill = data['skill']
            min_experience = data.get('min_experience_years')
            required_only = data.get('required_only', False)
            
            # Build query to search skills
            conn = sqlite_manager.get_connection()
            conn.row_factory = sqlite_manager._dict_factory
            cursor = conn.cursor()
            
            query = '''
                SELECT j.*, js.skill_full, js.experience_years, js.is_required
                FROM jobs j
                JOIN job_skills js ON j.job_id = js.job_id
                WHERE js.skill_clean LIKE ?
            '''
            
            params = [f'%{skill}%']
            
            if required_only:
                query += " AND js.is_required = 1"
            
            if min_experience:
                query += " AND js.experience_years >= ?"
                params.append(min_experience)
            
            query += " ORDER BY js.experience_years DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            conn.close()
            
            # Group by job
            jobs_by_id = {}
            for row in results:
                job_id = row['job_id']
                if job_id not in jobs_by_id:
                    jobs_by_id[job_id] = {
                        'job_id': job_id,
                        'title': row['title'],
                        'state': row['state'],
                        'work_mode': row['work_mode'],
                        'skills': []
                    }
                
                jobs_by_id[job_id]['skills'].append({
                    'skill': row['skill_full'],
                    'experience_years': row['experience_years'],
                    'is_required': bool(row['is_required'])
                })
            
            return jsonify({
                'skill': skill,
                'min_experience_years': min_experience,
                'required_only': required_only,
                'total_jobs': len(jobs_by_id),
                'jobs': list(jobs_by_id.values())[:20]  # Limit to 20
            })
            
        except Exception as e:
            logger.error(f"Skill search error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/ingest-odoo', methods=['POST'])
    def ingest_odoo():
        """
        Manually trigger Odoo job sync
        """
        try:
            if not ingestion_service:
                return jsonify({'error': 'Ingestion service not available'}), 500
            
            # Trigger sync
            count = ingestion_service.process_odoo_jobs()
            
            return jsonify({
                'success': True,
                'count': count,
                'message': f"Successfully synced {count} jobs from Odoo"
            })
            
        except Exception as e:
            logger.error(f"Odoo sync error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/odoo-postings', methods=['GET'])
    def odoo_postings():
        """Get Odoo posting statistics"""
        try:
            if not sqlite_manager:
                return jsonify({'error': 'SQLite manager not available'}), 500
            
            conn = sqlite_manager.get_connection()
            cursor = conn.cursor()
            
            # Today's postings
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM odoo_postings 
                WHERE date(posting_time) = date('now')
            """)
            today_count = cursor.fetchone()[0]
            
            # This week's postings
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM odoo_postings 
                WHERE strftime('%Y-%W', posting_time) = strftime('%Y-%W', 'now')
            """)
            week_count = cursor.fetchone()[0]
            
            # This month's postings
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM odoo_postings 
                WHERE strftime('%Y-%m', posting_time) = strftime('%Y-%m', 'now')
            """)
            month_count = cursor.fetchone()[0]
            
            # Recent postings
            cursor.execute("""
                SELECT op.*, j.title, j.state
                FROM odoo_postings op
                LEFT JOIN jobs j ON op.job_id = j.job_id
                ORDER BY op.posting_time DESC
                LIMIT 10
            """)
            
            columns = [desc[0] for desc in cursor.description]
            recent_postings = []
            for row in cursor.fetchall():
                recent_postings.append(dict(zip(columns, row)))
            
            conn.close()
            
            return jsonify({
                'statistics': {
                    'today': today_count,
                    'this_week': week_count,
                    'this_month': month_count
                },
                'recent_postings': recent_postings
            })
            
        except Exception as e:
            logger.error(f"Odoo postings error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/health', methods=['GET'])
    def health():
        """RAG system health check"""
        return jsonify({
            'status': 'healthy',
            'components': {
                'chroma_db': 'active' if chroma_manager else 'inactive',
                'sqlite_db': 'active' if sqlite_manager else 'inactive',
                'ingestion_service': 'running' if ingestion_service and ingestion_service.running else 'stopped',
                'query_engine': 'active'
            }
        })
    
    return bp