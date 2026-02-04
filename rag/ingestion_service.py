"""
Real-time ingestion service for RAG chatbot
Watches output folders and automatically processes new files
"""
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

from .chroma_manager import ChromaManager
from .sqlite_manager import SQLiteManager
from .file_parser import FileParser
from services.odoo.odoo_service import OdooService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OutputFileHandler(FileSystemEventHandler):
    """Watchdog handler for monitoring output folders"""
    
    def __init__(self, ingestion_service):
        self.ingestion_service = ingestion_service
        self.recently_processed = set()
        self.processing_extensions = {'.txt', '.xlsx', '.xls'}
        
    def on_created(self, event):
        """Handle new file creation"""
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def on_modified(self, event):
        """Handle file modifications"""
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, file_path: str):
        """Handle file creation or modification"""
        file_path_obj = Path(file_path)
        
        if file_path_obj.suffix.lower() in self.processing_extensions:
            # Avoid duplicate processing
            file_key = f"{file_path}_{file_path_obj.stat().st_mtime}"
            
            if file_key not in self.recently_processed:
                self.recently_processed.add(file_key)
                
                # Delay processing to ensure file is fully written
                threading.Timer(2, lambda: self._process_file(file_path_obj)).start()
    
    def _process_file(self, file_path: Path):
        """Process a single file"""
        try:
            self.ingestion_service.process_file(file_path)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

class IngestionService:
    """Main ingestion service for real-time file processing"""
    
    def __init__(self, watch_dirs: List[str], chroma_manager: ChromaManager, 
                 sqlite_manager: SQLiteManager, check_interval: int = 60):
        """
        Initialize ingestion service
        
        Args:
            watch_dirs: List of directories to watch
            chroma_manager: ChromaDB manager instance
            sqlite_manager: SQLite manager instance
            check_interval: How often to check for updates (seconds)
        """
        self.watch_dirs = [Path(dir) for dir in watch_dirs]
        self.chroma_manager = chroma_manager
        self.sqlite_manager = sqlite_manager
        self.file_parser = FileParser()
        self.check_interval = check_interval
        self.observer = None
        self.running = False
        self.thread = None
        
        # Ensure directories exist
        for dir_path in self.watch_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Track processed files to avoid duplicates
        self.processed_files = set()
        
        # Initial scan of existing files
        self.initial_scan()
    
    def initial_scan(self):
        """Scan existing files in watched directories"""
        logger.info("Performing initial scan of existing files...")
        
        all_files = []
        
        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                for file_path in watch_dir.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in {'.txt', '.xlsx', '.xls'}:
                        all_files.append(file_path)
        
        # Also check for job_tracker_report.xlsx in current directory
        excel_path = Path("job_tracker_report.xlsx")
        if excel_path.exists():
            all_files.append(excel_path)
        
        # Process files
        processed_count = 0
        for file_path in all_files:
            try:
                success = self.process_file(file_path)
                if success:
                    processed_count += 1
            except Exception as e:
                logger.error(f"Error processing existing file {file_path}: {e}")
        
        logger.info(f"Initial scan complete. Processed {processed_count} files.")
    
    def process_file(self, file_path: Path) -> bool:
        """
        Process a single file
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: Success status
        """
        try:
            file_key = str(file_path)
            
            # Skip if recently processed
            if file_key in self.processed_files:
                logger.debug(f"Skipping already processed file: {file_path}")
                return False
            
            logger.info(f"Processing file: {file_path}")
            
            # Process based on file type
            if file_path.suffix.lower() == '.txt':
                success = self._process_txt_file(file_path)
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                success = self._process_excel_file(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return False
            
            if success:
                self.processed_files.add(file_key)
                logger.info(f"Successfully processed: {file_path.name}")
            else:
                logger.warning(f"Failed to process: {file_path.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return False
    
    def _process_txt_file(self, file_path: Path) -> bool:
        """Process a .txt file"""
        try:
            # Parse the .txt file
            job_data = self.file_parser.parse_txt_file(str(file_path))
            
            if not job_data or not job_data.get('job_id'):
                logger.warning(f"No job data extracted from {file_path}")
                return False
            
            # Store in SQLite
            success_sqlite, row_id = self.sqlite_manager.upsert_job_from_txt(job_data)
            
            if not success_sqlite:
                logger.warning(f"Failed to store in SQLite: {job_data.get('job_id')}")
                return False
            
            # Store in ChromaDB (vector search)
            success_chroma = self.chroma_manager.add_job_document(job_data)
            
            if not success_chroma:
                logger.warning(f"Failed to store in ChromaDB: {job_data.get('job_id')}")
            
            return success_sqlite  # SQLite success is more critical
            
        except Exception as e:
            logger.error(f"Error processing txt file {file_path}: {e}")
            return False
    
    def _process_excel_file(self, file_path: Path) -> bool:
        """Process an Excel file"""
        try:
            # Parse the Excel file
            tracking_data_list = self.file_parser.parse_excel_file(str(file_path))
            
            if not tracking_data_list:
                logger.warning(f"No tracking data extracted from {file_path}")
                return False
            
            success_count = 0
            
            for tracking_data in tracking_data_list:
                if tracking_data.get('job_id'):
                    # Store in SQLite
                    success = self.sqlite_manager.upsert_job_tracking(tracking_data)
                    
                    if success:
                        success_count += 1
                    else:
                        logger.warning(f"Failed to store tracking for {tracking_data.get('job_id')}")
            
            logger.info(f"Processed {success_count}/{len(tracking_data_list)} records from {file_path.name}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error processing Excel file {file_path}: {e}")
            return False
    
    def start_watching(self):
        """Start the file system watcher"""
        if self.running:
            logger.warning("Ingestion service is already running")
            return
        
        self.running = True
        
        try:
            self.observer = Observer()
            event_handler = OutputFileHandler(self)
            
            for watch_dir in self.watch_dirs:
                if watch_dir.exists():
                    self.observer.schedule(event_handler, str(watch_dir), recursive=True)
                    logger.info(f"Started watching: {watch_dir}")
                else:
                    logger.warning(f"Watch directory does not exist: {watch_dir}")
            
            self.observer.start()
            
            # Start periodic manual scan as backup
            self.thread = threading.Thread(target=self._periodic_scan, daemon=True)
            self.thread.start()
            
            logger.info("Ingestion service started successfully")
            
        except Exception as e:
            logger.error(f"Error starting file watcher: {e}")
            self.running = False
    
    def _periodic_scan(self):
        """Periodic scan as backup to file watcher"""
        last_scan_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            if current_time - last_scan_time >= self.check_interval:
                try:
                    self.scan_for_new_files()
                    last_scan_time = current_time
                except Exception as e:
                    logger.error(f"Error in periodic scan: {e}")

            # Every hour (roughly), sync with Odoo
            # We use a simple counter or timestamp check
            if current_time - getattr(self, 'last_odoo_sync', 0) >= 3600:
                try:
                    self.process_odoo_jobs()
                    self.last_odoo_sync = current_time
                except Exception as e:
                    logger.error(f"Error in Odoo sync: {e}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def scan_for_new_files(self):
        """Manual scan for new files (backup method)"""
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
                
            for file_path in watch_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in {'.txt', '.xlsx', '.xls'}:
                    # Check if file modified in last 5 minutes
                    try:
                        mtime = file_path.stat().st_mtime
                        if time.time() - mtime < 300:  # 5 minutes
                            self.process_file(file_path)
                    except Exception as e:
                        logger.error(f"Error scanning file {file_path}: {e}")
        
        # Also check for updated Excel file
        excel_path = Path("job_tracker_report.xlsx")
        if excel_path.exists():
            try:
                mtime = excel_path.stat().st_mtime
                if time.time() - mtime < 300:  # 5 minutes
                    self.process_file(excel_path)
            except Exception as e:
                logger.error(f"Error scanning Excel file: {e}")
    
    def stop_watching(self):
        """Stop the file system watcher"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("Stopped ingestion service")

    def process_odoo_jobs(self, days_back: int = 7) -> int:
        """
        Fetch and process recent jobs from Odoo
        Returns number of new/updated jobs processed
        """
        try:
            from datetime import datetime, timedelta
            last_week = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Starting Odoo job sync (Last {days_back} days)...")
            odoo_service = OdooService()
            
            # Domain to fetch only recent jobs
            domain = [('write_date', '>=', last_week)]
            
            total_processed = 0
            offset = 0
            limit = 100
            
            while True:
                # Fetch batch of jobs
                jobs = odoo_service.fetch_jobs(limit=limit, offset=offset, domain=domain)
                
                if not jobs:
                    break
                    
                batch_count = 0
                for job in jobs:
                    try:
                        # Robust ID extraction
                        # Odoo returns False for empty fields, so .get(key, default) doesn't work as expected if key exists but is False
                        raw_job_id = job.get('x_job_id')
                        odoo_id = job.get('id')
                        
                        if raw_job_id and isinstance(raw_job_id, str):
                            final_job_id = raw_job_id
                        elif odoo_id:
                            final_job_id = f"ODOO-{odoo_id}"
                        else:
                            logger.warning(f"Skipping Odoo job with no ID: {job.get('name')}")
                            continue

                        # Normalize data
                        title = job.get('name') or "Untitled Job"
                        desc = job.get('description', '') or job.get('x_description', '') or ""
                        loc = job.get('x_location') or ""
                        
                        if isinstance(desc, bool): desc = ""
                        if isinstance(loc, bool): loc = ""

                        # Extract state from location
                        state = ""
                        if loc:
                            import re
                            # Look for 2-letter state code like ", GA" or "GA " or just "GA"
                            state_match = re.search(r'\b([A-Z]{2})\b', loc)
                            if state_match:
                                state = state_match.group(1)

                        job_data = {
                            'job_id': final_job_id,
                            'title': title,
                            'description': desc,
                            'location': loc,
                            'state': state,
                            'posted_date': job.get('write_date') if isinstance(job.get('write_date'), str) else "",
                            'due_date': odoo_service.normalize_pretty_date(job.get('x_due_date')) if job.get('x_due_date') else "",
                            'duration': job.get('x_duration') if isinstance(job.get('x_duration'), str) else "",
                            'experience_certs': '', 
                            'work_mode': 'Onsite', 
                            'source_file': f"odoo_{odoo_id}",
                            'parsed_time': datetime.now().isoformat()
                        }
                        
                        # Store in SQLite
                        success_sqlite, _ = self.sqlite_manager.upsert_job_from_odoo(job_data)
                        
                        if success_sqlite:
                            # Store in ChromaDB
                            self.chroma_manager.add_job_document(job_data)
                            batch_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing Odoo job {job.get('name')}: {e}")
            
                total_processed += batch_count
                offset += limit
                
                # Safety break to prevent infinite loops if something is wrong
                if offset > 5000:
                    logger.warning("Reached safety limit of 5000 jobs, stopping sync")
                    break
            
            logger.info(f"Odoo sync complete: Processed {total_processed} total jobs")
            return total_processed
            
        except Exception as e:
            logger.error(f"Error in process_odoo_jobs: {e}")
            return 0
    
    def process_folder_before_clear(self, folder_path: str) -> Dict:
        """
        Process all files in a folder before it's cleared
        
        Args:
            folder_path: Path to folder to process
            
        Returns:
            Dict with processing results
        """
        result = {
            'folder': folder_path,
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'details': []
        }
        
        folder = Path(folder_path)
        if not folder.exists():
            result['error'] = f"Folder does not exist: {folder_path}"
            return result
        
        # Process all .txt files in the folder
        for file_path in folder.rglob('*.txt'):
            if file_path.is_file():
                result['total_files'] += 1
                
                try:
                    success = self.process_file(file_path)
                    
                    if success:
                        result['processed'] += 1
                        result['details'].append({
                            'file': str(file_path),
                            'status': 'success'
                        })
                    else:
                        result['failed'] += 1
                        result['details'].append({
                            'file': str(file_path),
                            'status': 'failed'
                        })
                        
                except Exception as e:
                    result['failed'] += 1
                    result['details'].append({
                        'file': str(file_path),
                        'status': 'error',
                        'error': str(e)
                    })
        
        logger.info(f"Processed {result['processed']}/{result['total_files']} files from {folder_path}")
        return result