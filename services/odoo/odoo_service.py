import xmlrpc.client
import os
import re
from datetime import datetime
from utils.config import Config  # ADD THIS IMPORT

class OdooService:
    def __init__(self):
        # Get Odoo config from Config class
        odoo_config = Config.get_odoo_config()
        self.url = odoo_config['url']
        self.db = odoo_config['db']
        self.username = odoo_config['username']
        self.password = odoo_config['password']
        
        # Original values as fallback
        if not self.url:
            self.url = "http://84.247.136.24:8069"
        if not self.db:
            self.db = 'mydb'
        if not self.username:
            self.username = 'admin'
        if not self.password:
            self.password = "79NM46eRqDv)w^q^"
        
        # **FIXED: Use correct folder paths based on your logs**
        # From your logs, files are saved in 'vms_outputs' folder
        # DIR portal files should be in 'dir_portal_outputs'
        self.vms_folder = 'vms_outputs'  # This is where VMS saves files
        self.dir_folder = 'dir_portal_outputs'  # This is where DIR portal saves files
        
        # Debug: Show folder paths
        print(f"🔍 Odoo Service initialized:")
        print(f"   URL: {self.url}")
        print(f"   VMS Folder: {self.vms_folder}")
        print(f"   DIR Folder: {self.dir_folder}")
        
        # Check if folders exist
        self.check_folders()
    
    def check_folders(self):
        """Check and create necessary folders"""
        print(f"📁 Checking folder structure...")
        
        if not os.path.exists(self.vms_folder):
            print(f"⚠️  VMS folder doesn't exist: {self.vms_folder}")
            try:
                os.makedirs(self.vms_folder, exist_ok=True)
                print(f"✅ Created VMS folder: {self.vms_folder}")
            except Exception as e:
                print(f"❌ Failed to create VMS folder: {e}")
        
        if not os.path.exists(self.dir_folder):
            print(f"⚠️  DIR folder doesn't exist: {self.dir_folder}")
            try:
                os.makedirs(self.dir_folder, exist_ok=True)
                print(f"✅ Created DIR folder: {self.dir_folder}")
            except Exception as e:
                print(f"❌ Failed to create DIR folder: {e}")
    
    def authenticate(self):
        """Check if Odoo connection works"""
        try:
            print(f"🔗 Testing Odoo connection to: {self.url}")
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            uid = common.authenticate(self.db, self.username, self.password, {})
            
            if uid:
                print(f"✅ Odoo authentication successful (UID: {uid})")
                return True
            else:
                print("❌ Odoo authentication failed - check credentials")
                return False
                
        except Exception as e:
            print(f"❌ Odoo connection error: {e}")
            print(f"\n🔧 Please check:")
            print(f"   1. Is Odoo server running at {self.url}?")
            print(f"   2. Can you access it in browser?")
            print(f"   3. Check firewall/network connectivity")
            return False
    
    def parse_due_date_from_job_id(self, job_id):
        """Extract due date from Job ID format like (98091204)"""
        try:
            # Extract the number in parentheses
            match = re.search(r'\((\d+)\)', job_id)
            if match:
                number_str = match.group(1)
                
                # Take last 4 digits
                if len(number_str) >= 4:
                    date_code = number_str[-4:]  # Get last 4 digits
                    
                    # Parse month and day from MMDD format
                    month = int(date_code[:2])
                    day = int(date_code[2:])
                    
                    # Validate month and day
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        # Use current year or next year if date has passed
                        current_year = datetime.now().year
                        
                        # Try to create date
                        try:
                            due_date = datetime(current_year, month, day)
                            
                            # If date is in the past, use next year
                            if due_date < datetime.now():
                                due_date = datetime(current_year + 1, month, day)
                            
                            # Format as "2025-12-04" (ISO) for database logic
                            return due_date.strftime("%Y-%m-%d")
                        except ValueError as ve:
                            # Invalid date (e.g., Feb 30)
                            print(f"   - Invalid date error: {ve}")
                            return ""
            
            return ""
        except Exception as e:
            print(f"   - Error parsing due date: {e}")
            return ""
    
    def normalize_pretty_date(self, date_str):
        """Convert 'Monday, February 02, 2026' to '2026-02-02'"""
        if not date_str or not isinstance(date_str, str):
            return ""
        
        # Already ISO check
        import re
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
            
        try:
            from datetime import datetime
            # Try popular formats
            for fmt in ["%A, %B %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            
            return date_str # Return as is if NO format matched
        except Exception:
            return date_str

    def extract_job_data_from_file(self, file_path):
        """Extract job posting data from text files"""
        job_data = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            print(f"   - File: {os.path.basename(file_path)}")
            print(f"   - Content length: {len(content)} chars")
                
            # Extract Job ID
            job_id_match = re.search(r'Job ID:\s*([^\n]+)', content)
            if job_id_match:
                job_id_full = job_id_match.group(1).strip()
                job_data['x_job_id'] = job_id_full
                
                # Extract and parse due date from Job ID
                due_date = self.parse_due_date_from_job_id(job_id_full)
                if due_date:
                    job_data['x_due_date'] = due_date
                else:
                    job_data['x_due_date'] = ""
                    
                print(f"   - Job ID: {job_data['x_job_id']}")
                print(f"   - Due Date: {job_data['x_due_date']}")
            
            # Extract Title (look for the first line that's not Job ID:)
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Job ID:'):
                    job_data['name'] = line
                    print(f"   - Title: {line}")
                    break
            
            # Extract Description (everything after Description:)
            desc_match = re.search(r'Description:\s*(.*?)(?=Skills:|$)', content, re.DOTALL | re.IGNORECASE)
            if desc_match:
                job_data['x_description'] = desc_match.group(1).strip()
            else:
                # If no specific description section, use the entire content
                job_data['x_description'] = content[:500] + "..." if len(content) > 500 else content
            
            # Extract Location
            location_match = re.search(r'Location:\s*([^\n\(]+)', content)
            if location_match:
                job_data['x_location'] = location_match.group(1).strip()
                print(f"   - Location: {job_data['x_location']}")
            
            # Extract Duration
            duration_match = re.search(r'Duration:\s*([^\n]+)', content)
            if duration_match:
                job_data['x_duration'] = duration_match.group(1).strip()
                print(f"   - Duration: {job_data['x_duration']}")
                
        except Exception as e:
            print(f"   ❌ Error reading file {file_path}: {e}")
            return None
        
        return job_data
    
    def create_job_posting(self, job_data):
        """Create job posting in Odoo"""
        try:
            print(f"   📤 Creating job in Odoo...")
            
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            uid = common.authenticate(self.db, self.username, self.password, {})
            
            if not uid:
                print("   ❌ Authentication failed")
                return False
            
            models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
            
            # Prepare job data for Odoo
            odoo_job_data = {
                "name": job_data.get('name', 'Job Posting'),
                "x_job_id": job_data.get('x_job_id', ''),
                "x_location": job_data.get('x_location', ''),
                "x_duration": job_data.get('x_duration', ''),
                "x_description": job_data.get('x_description', ''),
                "x_due_date": job_data.get('x_due_date', ''),
                "website_published": True,
                "company_id": 1,
                "address_id": 1,
                "no_of_recruitment": 1  # Default to 1 position
            }
            
            # Create job in Odoo
            job_id = models.execute_kw(
                self.db, uid, self.password,
                "hr.job", "create", [odoo_job_data]
            )
            
            print(f"   ✅ Created Odoo job ID: {job_id}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error creating Odoo job: {e}")
            return False
    
    def process_files(self):
        """Process all job files to Odoo"""
        print("="*60)
        print("🚀 ODOO JOB POSTING - STARTING")
        print("="*60)
        
        # First authenticate with Odoo
        if not self.authenticate():
            print("❌ Cannot connect to Odoo")
            return 0
        
        # **FIXED: Use correct folder paths**
        folders = [self.vms_folder, self.dir_folder]
        created = 0
        
        for folder in folders:
            print(f"\n📁 Processing folder: {folder}")
            
            if not os.path.exists(folder):
                print(f"   ⚠️  Folder not found: {folder}")
                continue
            
            txt_files = [f for f in os.listdir(folder) if f.endswith('.txt')]
            print(f"   📄 Found {len(txt_files)} .txt files")
            
            for filename in txt_files:
                file_path = os.path.join(folder, filename)
                print(f"\n   Processing: {filename}")
                
                # Extract job data from file
                job_data = self.extract_job_data_from_file(file_path)
                
                if job_data:
                    # Create job posting in Odoo
                    if self.create_job_posting(job_data):
                        created += 1
                else:
                    print(f"   ❌ Failed to extract data from {filename}")
        
        print(f"\n📊 Odoo posting complete: {created} jobs posted")
        return created

    def fetch_jobs(self, limit=100, domain=[], offset=0):
        """
        Fetch jobs from Odoo to sync with RAG system
        """
        try:
            print(f"   📥 Fetching jobs from Odoo (Limit: {limit}, Offset: {offset})...")
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            uid = common.authenticate(self.db, self.username, self.password, {})
            
            if not uid:
                print("   ❌ Authentication failed")
                return []
            
            models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
            
            # Search for jobs
            # Fetch ALL jobs for now to ensure we get data
            search_domain = domain
            
            print(f"   🔍 Search domain: {search_domain}")
            
            job_ids = models.execute_kw(
                self.db, uid, self.password,
                'hr.job', 'search',
                [search_domain],
                {'limit': limit, 'offset': offset}
            )
            
            if not job_ids:
                return []
                
            # Read job details
            fields = [
                'name', 'x_job_id', 'x_location', 'x_duration', 
                'x_description', 'x_due_date', 'write_date', 'description'
            ]
            
            jobs = models.execute_kw(
                self.db, uid, self.password,
                'hr.job', 'read',
                [job_ids],
                {'fields': fields}
            )
            
            print(f"   ✅ Fetched {len(jobs)} jobs from Odoo")
            return jobs
            
        except Exception as e:
            print(f"   ❌ Error fetching Odoo jobs: {e}")
            return []