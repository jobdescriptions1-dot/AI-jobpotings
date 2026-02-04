from .odoo_service import OdooService

def process_oddo_job_postings():
    """Simple function to process jobs to Odoo"""
    print("🚀 Processing job postings to Odoo...")
    
    service = OdooService()
    created = service.process_files()
    
    print(f"✅ Created {created} job postings in Odoo")
    return created > 0