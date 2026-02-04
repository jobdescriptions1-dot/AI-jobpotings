"""
Parser for YOUR specific file formats
Extracts data from your .txt files and Excel
"""
import re
import json
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FileParser:
    """Parser for your specific file formats"""
    
    @staticmethod
    def parse_txt_file(file_path: str) -> Dict:
        """
        Parse your .txt files like requisition_791950_complete.txt
        
        Format:
        Job ID: NC-791950 (99090129)
        Hybrid/Local Java Developer (12+ Cúram V6/7/8 Certified Developer)...
        Location: Research Triangle Park, NC (NCDHHS-NCFAST)
        Duration: 12 Months
        skills:
        Cúram V6/7/8 Certified Developer. V8 preferred. Required 5 Years
        Description:
        NC FAST requires the services of a senior Java developer...
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            result = {
                'source_file': file_path,
                'raw_content': content,
                'job_id': None,
                'title': None,
                'work_mode': None,
                'experience_certs': None,
                'location': None,
                'duration': None,
                'skills_full': [],  # Full skill lines with experience
                'skills_clean': [], # Just skill names
                'description': None,
                'state': None,
                'parsed_time': datetime.now().isoformat()
            }
            
            # Extract Job ID
            job_id_match = re.search(r'Job ID:\s*(.+)', content)
            if job_id_match:
                result['job_id'] = job_id_match.group(1).strip()
            
            # Extract Title Line and parse it
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Job ID:') and not line.startswith('Location:'):
                    # This is likely the title line
                    result = FileParser._parse_title_line(line, result)
                    break
            
            # Extract Location
            location_match = re.search(r'Location:\s*(.+)', content)
            if location_match:
                location = location_match.group(1).strip()
                result['location'] = location
                # Try to extract state from location
                state_match = re.search(r',\s*([A-Z]{2})\b', location)
                if state_match:
                    result['state'] = state_match.group(1)
            
            # Extract Duration
            duration_match = re.search(r'Duration:\s*(.+)', content)
            if duration_match:
                result['duration'] = duration_match.group(1).strip()
            
            # Extract Skills section
            skills_section = FileParser._extract_section(content, 'skills:', 'Description:')
            if skills_section:
                skills_data = FileParser._parse_skills_section(skills_section)
                result['skills_full'] = skills_data['full_lines']
                result['skills_clean'] = skills_data['clean_skills']
            
            # Extract Description section
            desc_section = FileParser._extract_section(content, 'Description:', None)
            if desc_section:
                result['description'] = desc_section.strip()
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing txt file {file_path}: {e}")
            return {}
    
    @staticmethod
    def _parse_title_line(title_line: str, result: Dict) -> Dict:
        """Parse title line like: Hybrid/Local Java Developer (12+ Cúram V6/7/8 Certified Developer)..."""
        
        # Extract work mode (Hybrid/Local)
        work_mode_match = re.match(r'^([A-Za-z/]+)\s+', title_line)
        if work_mode_match:
            result['work_mode'] = work_mode_match.group(1).strip()
            # Remove work mode from title for cleaner title
            title_line = title_line[len(work_mode_match.group(0)):].strip()
        
        # Extract content in parentheses (experience/certs)
        paren_match = re.search(r'\(([^)]+)\)', title_line)
        if paren_match:
            result['experience_certs'] = paren_match.group(1).strip()
            # Remove parentheses content for title
            title_line = title_line.replace(f"({paren_match.group(1)})", "").strip()
        
        # The remaining part is the clean title
        result['title'] = title_line.strip()
        
        return result
    
    @staticmethod
    def _extract_section(content: str, start_marker: str, end_marker: Optional[str]) -> Optional[str]:
        """Extract a section between markers"""
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return None
        
        start_idx += len(start_marker)
        
        if end_marker:
            end_idx = content.find(end_marker, start_idx)
            if end_idx == -1:
                return content[start_idx:].strip()
            return content[start_idx:end_idx].strip()
        else:
            return content[start_idx:].strip()
    
    @staticmethod
    def _parse_skills_section(skills_content: str) -> Dict:
        """Parse skills section into full lines and clean skill names"""
        lines = [line.strip() for line in skills_content.split('\n') if line.strip()]
        
        full_lines = []
        clean_skills = []
        
        for line in lines:
            full_lines.append(line)
            
            # Extract clean skill name (remove experience years, required/desired)
            # Example: "Cúram V6/7/8 Certified Developer. V8 preferred. Required 5 Years"
            # Clean: "Cúram V6/7/8 Certified Developer"
            
            # Remove experience info
            clean_line = re.sub(r'\.?\s*(Required|Highly desired|Desired|Preferred).*$', '', line)
            clean_line = re.sub(r'\d+\s+Years?.*$', '', clean_line)
            clean_line = clean_line.strip()
            
            if clean_line and clean_line not in clean_skills:
                clean_skills.append(clean_line)
        
        return {
            'full_lines': full_lines,
            'clean_skills': clean_skills
        }
    
    @staticmethod
    def parse_excel_file(file_path: str) -> List[Dict]:
        """
        Parse your job_tracker_report.xlsx file
        
        Expected columns: Job ID, Title, State, Due Date, Skills, Submission Count
        Both Sheet1 and Sheet2 have same structure
        """
        try:
            results = []
            
            # Read both sheets
            for sheet_name in ['Sheet1', 'Sheet2']:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # Handle column name variations
                    column_mapping = {}
                    for col in df.columns:
                        col_lower = str(col).lower()
                        if 'job' in col_lower and 'id' in col_lower:
                            column_mapping['job_id'] = col
                        elif 'title' in col_lower:
                            column_mapping['title'] = col
                        elif 'state' in col_lower:
                            column_mapping['state'] = col
                        elif 'due' in col_lower and 'date' in col_lower:
                            column_mapping['due_date'] = col
                        elif 'skill' in col_lower:
                            column_mapping['skills'] = col
                        elif 'submission' in col_lower:
                            column_mapping['submission_count'] = col
                    
                    for _, row in df.iterrows():
                        job_data = {
                            'source_file': file_path,
                            'sheet_name': sheet_name,
                            'job_id': str(row.get(column_mapping.get('job_id', ''))) if column_mapping.get('job_id') else None,
                            'title': str(row.get(column_mapping.get('title', ''))) if column_mapping.get('title') else None,
                            'state': str(row.get(column_mapping.get('state', ''))) if column_mapping.get('state') else None,
                            'due_date': row.get(column_mapping.get('due_date', None)),
                            'skills': str(row.get(column_mapping.get('skills', ''))) if column_mapping.get('skills') else None,
                            'submission_count': row.get(column_mapping.get('submission_count', 0)),
                            'parsed_time': datetime.now().isoformat()
                        }
                        
                        # Convert due_date to string if it's a date
                        if hasattr(job_data['due_date'], 'isoformat'):
                            job_data['due_date'] = job_data['due_date'].isoformat()
                        
                        # Convert skills string to list
                        if job_data['skills']:
                            skills_list = [s.strip() for s in job_data['skills'].split(',') if s.strip()]
                            job_data['skills_list'] = skills_list
                        
                        if job_data['job_id'] and job_data['job_id'].lower() != 'nan':
                            results.append(job_data)
                            
                except Exception as e:
                    logger.warning(f"Error reading sheet {sheet_name} from {file_path}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing Excel file {file_path}: {e}")
            return []
    
    @staticmethod
    def extract_odoo_posting_info(file_path: str) -> Optional[Dict]:
        """
        Extract Odoo posting information from log files
        This needs to be customized based on your Odoo output format
        """
        # TODO: Customize based on your actual Odoo output format
        # For now, returns basic info
        return {
            'job_id': None,
            'posting_time': datetime.now().isoformat(),
            'status': 'unknown',
            'source_file': file_path
        }