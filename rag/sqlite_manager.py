"""
SQLite database for structured job metadata
"""
import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SQLiteManager:
    """Manage SQLite database for job metadata"""
    
    def __init__(self, db_path: str = "sqlite_db/jobs_metadata.db"):
        """
        Initialize SQLite manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create jobs table (from .txt files)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                title TEXT,
                work_mode TEXT,
                experience_certs TEXT,
                location TEXT,
                state TEXT,
                duration TEXT,
                state TEXT,
                duration TEXT,
                description TEXT,
                posted_date DATE,
                due_date DATE,
                source_file TEXT,
                source_system TEXT,
                parsed_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create job_skills table (detailed skills)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                skill_full TEXT,
                skill_clean TEXT,
                is_required BOOLEAN DEFAULT 1,
                experience_years INTEGER,
                FOREIGN KEY (job_id) REFERENCES jobs (job_id),
                UNIQUE(job_id, skill_clean)
            )
        ''')
        
        # Create job_tracking table (from Excel)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                title TEXT,
                state TEXT,
                due_date DATE,
                skills_summary TEXT,
                submission_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP,
                source_sheet TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (job_id),
                UNIQUE(job_id, source_sheet)
            )
        ''')
        
        # Create odoo_postings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS odoo_postings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                posting_time TIMESTAMP,
                odoo_status TEXT,
                odoo_id TEXT,
                details_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (job_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_work_mode ON jobs(work_mode)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_tracking_due_date ON job_tracking(due_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_tracking_state ON job_tracking(state)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_odoo_postings_time ON odoo_postings(posting_time)')
        
        # Schema Migration: Add missing columns if they don't exist
        try:
            # Check for posted_date
            cursor.execute("PRAGMA table_info(jobs)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'posted_date' not in columns:
                logger.info("Migrating schema: Adding posted_date column")
                cursor.execute('ALTER TABLE jobs ADD COLUMN posted_date DATE')
                
            if 'due_date' not in columns:
                logger.info("Migrating schema: Adding due_date column")
                cursor.execute('ALTER TABLE jobs ADD COLUMN due_date DATE')
                
        except Exception as e:
            logger.error(f"Schema migration error: {e}")
        
        conn.commit()
        conn.close()
        logger.info("SQLite database initialized")
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(str(self.db_path))
    
    def upsert_job_from_txt(self, job_data: Dict) -> Tuple[bool, int]:
        """
        Insert or update job from .txt file parsing
        
        Args:
            job_data: Dictionary with job information from .txt file
            
        Returns:
            Tuple of (success, row_id)
        """
        if not job_data.get('job_id'):
            logger.warning("No job_id in job_data, skipping")
            return False, -1
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if job exists
            cursor.execute('SELECT id FROM jobs WHERE job_id = ?', (job_data['job_id'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing job
                cursor.execute('''
                    UPDATE jobs 
                    SET title = ?, work_mode = ?, experience_certs = ?, location = ?,
                        state = ?, duration = ?, description = ?, source_file = ?,
                        source_system = ?, parsed_time = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                ''', (
                    job_data.get('title'),
                    job_data.get('work_mode'),
                    job_data.get('experience_certs'),
                    job_data.get('location'),
                    job_data.get('state'),
                    job_data.get('duration'),
                    job_data.get('description'),
                    job_data.get('source_file'),
                    self._detect_source_system(job_data.get('source_file', '')),
                    job_data.get('parsed_time'),
                    job_data['job_id']
                ))
                row_id = existing[0]
            else:
                # Insert new job
                cursor.execute('''
                    INSERT INTO jobs 
                    (job_id, title, work_mode, experience_certs, location, state,
                     duration, description, source_file, source_system, parsed_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_data['job_id'],
                    job_data.get('title'),
                    job_data.get('work_mode'),
                    job_data.get('experience_certs'),
                    job_data.get('location'),
                    job_data.get('state'),
                    job_data.get('duration'),
                    job_data.get('description'),
                    job_data.get('source_file'),
                    self._detect_source_system(job_data.get('source_file', '')),
                    job_data.get('parsed_time')
                ))
                row_id = cursor.lastrowid
            
            # Update skills
            self._update_job_skills(job_data['job_id'], job_data.get('skills_full', []), 
                                   job_data.get('skills_clean', []), cursor)
            
            conn.commit()
            logger.debug(f"Upserted job: {job_data['job_id']}")
            return True, row_id
            
        except Exception as e:
            logger.error(f"Error upserting job {job_data['job_id']}: {e}")
            conn.rollback()
            return False, -1
        finally:
            conn.close()
    
    def _detect_source_system(self, file_path: str) -> str:
        """Detect source system from file path"""
        if 'vms_outputs' in file_path:
            return 'VMS'
        elif 'dir_portal_outputs' in file_path:
            return 'HHSC'
        else:
            return 'UNKNOWN'
    
    def _update_job_skills(self, job_id: str, skills_full: List[str], 
                          skills_clean: List[str], cursor):
        """Update job skills in database"""
        # Clear existing skills
        cursor.execute('DELETE FROM job_skills WHERE job_id = ?', (job_id,))
        
        # Insert new skills
        for i, (full_skill, clean_skill) in enumerate(zip(skills_full, skills_clean)):
            # Parse experience years from full skill
            years_match = None
            if full_skill:
                import re
                years_match = re.search(r'(\d+)\s+Years?', full_skill)
            
            experience_years = int(years_match.group(1)) if years_match else None
            
            # Check if required or desired
            is_required = 'Required' in full_skill if full_skill else True
            
            cursor.execute('''
                INSERT INTO job_skills (job_id, skill_full, skill_clean, 
                                      is_required, experience_years)
                VALUES (?, ?, ?, ?, ?)
            ''', (job_id, full_skill, clean_skill, is_required, experience_years))
    
    def get_state_stats(self) -> List[Tuple[str, int]]:
        """
        Get job counts by state
        source_system='ODOO' or any
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Group by state, ignore empty
            cursor.execute('''
                SELECT state, COUNT(*) as count 
                FROM jobs 
                WHERE state IS NOT NULL AND state != '' 
                GROUP BY state 
                ORDER BY count DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting state stats: {e}")
            return []

    def upsert_job_from_odoo(self, job_data: Dict) -> Tuple[bool, int]:
        """
        Insert or update job from Odoo fetch
        
        Args:
            job_data: Dictionary with job information from Odoo
            
        Returns:
            Tuple of (success, row_id)
        """
        if not job_data.get('job_id'):
            logger.warning("No job_id in Odoo data, skipping")
            return False, -1
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if job exists
            cursor.execute('SELECT id FROM jobs WHERE job_id = ?', (job_data['job_id'],))
            existing = cursor.fetchone()
            
            # Use provided location or default
            location = job_data.get('location', '')
            if 'x_location' in job_data and job_data['x_location']:
                location = job_data['x_location']
                
            # Parse state from location if possible
            state = job_data.get('state', '')
            if not state and location:
                # Simple extraction of 2-letter state code
                import re
                state_match = re.search(r'\b([A-Z]{2})\b', location)
                if state_match:
                    state = state_match.group(1)
            
            if existing:
                # Update existing job
                cursor.execute('''
                    UPDATE jobs 
                    SET title = ?, duration = ?, description = ?, 
                        location = ?, state = ?, source_system = 'ODOO',
                        posted_date = ?, due_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                ''', (
                    job_data.get('title'),
                    job_data.get('duration'),
                    job_data.get('description'),
                    location,
                    state,
                    job_data.get('posted_date'),
                    job_data.get('due_date'),
                    job_data['job_id']
                ))
                row_id = existing[0]
            else:
                # Insert new job
                cursor.execute('''
                    INSERT INTO jobs 
                    (job_id, title, duration, description, location, state, source_system, source_file, posted_date, due_date)
                    VALUES (?, ?, ?, ?, ?, ?, 'ODOO', 'odoo_api', ?, ?)
                ''', (
                    job_data['job_id'],
                    job_data.get('title'),
                    job_data.get('duration'),
                    job_data.get('description'),
                    location,
                    state,
                    job_data.get('posted_date'),
                    job_data.get('due_date')
                ))
                row_id = cursor.lastrowid
            
            conn.commit()
            return True, row_id
            
        except Exception as e:
            logger.error(f"Error upserting Odoo job {job_data.get('job_id')}: {e}")
            conn.rollback()
            return False, -1
        finally:
            conn.close()
    
    def upsert_job_tracking(self, tracking_data: Dict) -> bool:
        """
        Insert or update job tracking data from Excel
        
        Args:
            tracking_data: Dictionary with tracking information
            
        Returns:
            bool: Success status
        """
        if not tracking_data.get('job_id'):
            logger.warning("No job_id in tracking_data, skipping")
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if tracking exists for this sheet
            cursor.execute('''
                SELECT id FROM job_tracking 
                WHERE job_id = ? AND source_sheet = ?
            ''', (tracking_data['job_id'], tracking_data.get('sheet_name', 'Sheet1')))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing tracking
                cursor.execute('''
                    UPDATE job_tracking 
                    SET title = ?, state = ?, due_date = ?, skills_summary = ?,
                        submission_count = ?, last_updated = ?
                    WHERE job_id = ? AND source_sheet = ?
                ''', (
                    tracking_data.get('title'),
                    tracking_data.get('state'),
                    tracking_data.get('due_date'),
                    tracking_data.get('skills'),
                    tracking_data.get('submission_count', 0),
                    tracking_data.get('parsed_time'),
                    tracking_data['job_id'],
                    tracking_data.get('sheet_name', 'Sheet1')
                ))
            else:
                # Insert new tracking
                cursor.execute('''
                    INSERT INTO job_tracking 
                    (job_id, title, state, due_date, skills_summary, 
                     submission_count, last_updated, source_sheet)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tracking_data['job_id'],
                    tracking_data.get('title'),
                    tracking_data.get('state'),
                    tracking_data.get('due_date'),
                    tracking_data.get('skills'),
                    tracking_data.get('submission_count', 0),
                    tracking_data.get('parsed_time'),
                    tracking_data.get('sheet_name', 'Sheet1')
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error upserting tracking for {tracking_data['job_id']}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def record_odoo_posting(self, posting_data: Dict) -> bool:
        """
        Record an Odoo posting
        
        Args:
            posting_data: Dictionary with posting information
            
        Returns:
            bool: Success status
        """
        if not posting_data.get('job_id'):
            logger.warning("No job_id in posting_data, skipping")
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO odoo_postings 
                (job_id, posting_time, odoo_status, odoo_id, details_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                posting_data['job_id'],
                posting_data.get('posting_time', datetime.now().isoformat()),
                posting_data.get('odoo_status', 'posted'),
                posting_data.get('odoo_id'),
                json.dumps(posting_data.get('details', {}))
            ))
            
            conn.commit()
            logger.info(f"Recorded Odoo posting: {posting_data['job_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording Odoo posting: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def search_jobs(self, filters: Optional[Dict] = None, 
                   limit: int = 100) -> List[Dict]:
        """
        Search jobs with filters
        
        Args:
            filters: Dictionary of filter conditions
            limit: Maximum results to return
            
        Returns:
            List of job dictionaries
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Base query with joins
        query = '''
            SELECT j.*, 
                   GROUP_CONCAT(js.skill_clean, '|') as skills,
                   GROUP_CONCAT(js.skill_full, '||') as skills_full,
                   jt.due_date as tracking_due_date,
                   jt.submission_count,
                   MAX(op.posting_time) as last_posting_time
            FROM jobs j
            LEFT JOIN job_skills js ON j.job_id = js.job_id
            LEFT JOIN job_tracking jt ON j.job_id = jt.job_id
            LEFT JOIN odoo_postings op ON j.job_id = op.job_id
            WHERE 1=1
        '''
        
        params = []
        group_by = " GROUP BY j.id"
        
        if filters:
            # 1. Location filter (matches city or state) - Case Insensitive
            if filters.get('location'):
                term = f'%{str(filters["location"]).lower()}%'
                query += " AND (LOWER(COALESCE(j.location, '')) LIKE ? OR LOWER(COALESCE(j.state, '')) LIKE ? OR LOWER(COALESCE(jt.state, '')) LIKE ?)"
                params.extend([term, term, term])
                
            # 2. Job ID filter - Case Insensitive
            if filters.get('job_id'):
                term = f'%{str(filters["job_id"]).lower()}%'
                query += " AND (LOWER(COALESCE(j.job_id, '')) LIKE ? OR LOWER(COALESCE(jt.job_id, '')) LIKE ?)"
                params.extend([term, term])
            
            # 3. Title filter - Case Insensitive
            if filters.get('title'):
                term = f'%{str(filters["title"]).lower()}%'
                query += " AND (LOWER(COALESCE(j.title, '')) LIKE ? OR LOWER(COALESCE(jt.title, '')) LIKE ?)"
                params.extend([term, term])
            
            # 4. Work mode filter
            if filters.get('work_mode'):
                query += " AND LOWER(COALESCE(j.work_mode, '')) LIKE ?"
                params.append(f'%{str(filters["work_mode"]).lower()}%')
            
            # 5. Skill filter
            if filters.get('skill'):
                query += " AND js.skill_clean LIKE ?"
                params.append(f'%{filters["skill"]}%')
            
            # 6. Date filters
            if filters.get('due_date_after'):
                query += " AND jt.due_date >= ?"
                params.append(filters['due_date_after'])
            
            if filters.get('due_date_before'):
                query += " AND jt.due_date <= ?"
                params.append(filters['due_date_before'])
            
            # 7. Odoo posting date filter
            if filters.get('posted_after'):
                query += " AND op.posting_time >= ?"
                params.append(filters['posted_after'])
            
            # 8. Submission count filter
            if filters.get('min_submissions'):
                query += " AND jt.submission_count >= ?"
                params.append(filters['min_submissions'])
                
            # 9. Status filter (Custom for dashboard)
            if filters.get('status'):
                curr = date.today().isoformat()
                # Standardize date expr
                date_expr = "NULLIF(NULLIF(TRIM(COALESCE(jt.due_date, j.due_date)), ''), 'N/A')"
                if filters['status'] == 'active':
                    query += f" AND ({date_expr} >= ? OR {date_expr} IS NULL)"
                    params.append(curr)
                elif filters['status'] == 'expired' or filters['status'] == 'closed':
                    query += f" AND {date_expr} < ?"
                    params.append(curr)
        
        # Add filtering for location, job_id, and title specifically if they are in filters
        # The frontend calls with these, so we ensure they are handled if not already
        if filters:
            if filters.get('state'):
                query += " AND (j.state = ? OR jt.state = ?)"
                params.extend([filters['state'], filters['state']])
        
        query += group_by + " ORDER BY jt.due_date ASC, jt.submission_count DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dictionaries
        results = []
        for row in rows:
            job = dict(row)
            
            # Parse skills
            if job.get('skills'):
                job['skills_list'] = job['skills'].split('|') if job['skills'] else []
            
            if job.get('skills_full'):
                job['skills_full_list'] = job['skills_full'].split('||') if job['skills_full'] else []
            
            # Calculate status
            curr = date.today().isoformat()
            due = job.get('tracking_due_date') or job.get('due_date')
            
            # Normalize due date for calculation
            if not due or not str(due).strip() or str(due).strip().upper() == 'N/A':
                job['status'] = 'Active'
            else:
                due_str = str(due).strip()
                job['status'] = 'Active' if due_str >= curr else 'Closed'
                
            results.append(job)
        
        conn.close()
        return results
    
    def get_job_stats(self) -> Dict:
        """Get job statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM jobs")
        stats['total_jobs'] = cursor.fetchone()[0]
        
        # Jobs by state
        cursor.execute("SELECT state, COUNT(*) FROM jobs WHERE state IS NOT NULL GROUP BY state")
        stats['jobs_by_state'] = dict(cursor.fetchall())
        
        # Jobs by work mode
        cursor.execute("SELECT work_mode, COUNT(*) FROM jobs WHERE work_mode IS NOT NULL GROUP BY work_mode")
        stats['jobs_by_work_mode'] = dict(cursor.fetchall())
        
        # Jobs by source system
        cursor.execute("SELECT source_system, COUNT(*) FROM jobs GROUP BY source_system")
        stats['jobs_by_system'] = dict(cursor.fetchall())
        
        # Skills statistics
        cursor.execute("SELECT COUNT(DISTINCT skill_clean) FROM job_skills")
        stats['unique_skills'] = cursor.fetchone()[0]
        
        # Top skills
        cursor.execute("""
            SELECT skill_clean, COUNT(*) as count 
            FROM job_skills 
            WHERE skill_clean IS NOT NULL AND skill_clean != ''
            GROUP BY skill_clean 
            ORDER BY count DESC 
            LIMIT 20
        """)
        stats['top_skills'] = dict(cursor.fetchall())
        
        # Odoo postings
        cursor.execute("SELECT COUNT(*) FROM odoo_postings")
        stats['total_odoo_postings'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT job_id) FROM odoo_postings")
        stats['unique_jobs_posted'] = cursor.fetchone()[0]
        
        # Recent postings (Jobs synced from Odoo or posted to Odoo today)
        cursor.execute("""
            SELECT COUNT(*) FROM jobs 
            WHERE source_system = 'ODOO' 
            AND (date(posted_date) = date('now') OR date(updated_at) = date('now'))
        """)
        stats['postings_today'] = cursor.fetchone()[0]
        
        # Active vs Expired jobs
        curr = date.today().isoformat()
        # Robust date expression: prioritize tracking, fallback to job, treat empty/NA as NULL
        date_expr = "NULLIF(NULLIF(TRIM(COALESCE(jt.due_date, j.due_date)), ''), 'N/A')"
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM jobs j
            LEFT JOIN job_tracking jt ON j.job_id = jt.job_id
            WHERE {date_expr} >= ? OR {date_expr} IS NULL
        """, (curr,))
        stats['active_jobs'] = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM jobs j
            LEFT JOIN job_tracking jt ON j.job_id = jt.job_id
            WHERE {date_expr} < ?
        """, (curr,))
        stats['expired_jobs'] = cursor.fetchone()[0]
        
        conn.close()
        return stats