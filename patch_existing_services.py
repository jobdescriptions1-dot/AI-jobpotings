"""
Script to add minimal hooks to your existing services
Add these lines to your existing files
"""
import sys
import os

# Add these imports to your existing services

# ============================================================================
# 1. In services/vms/file_manager.py (or wherever you clear folders)
# ============================================================================
"""
# Add at top of file:
try:
    from rag.utils import before_folder_clear_hook
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    before_folder_clear_hook = lambda x: False

# In your clear_processing_directories() or similar function:
def clear_processing_directories(self):
    # Process files with RAG BEFORE clearing
    if RAG_AVAILABLE:
        before_folder_clear_hook("vms_outputs")
        before_folder_clear_hook("dir_portal_outputs")
    
    # YOUR EXISTING CLEARING CODE HERE
    # ...
"""

# ============================================================================
# 2. In services/dual_table/dual_table_service.py (after Excel update)
# ============================================================================
"""
# Add at top of file:
try:
    from rag.utils import after_excel_update_hook
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    after_excel_update_hook = lambda: False

# After saving/updating job_tracker_report.xlsx:
def save_both_tables_to_excel(active_df, past_due_df, excel_path):
    # YOUR EXISTING EXCEL SAVING CODE HERE
    # ...
    
    # Notify RAG about updated Excel
    if RAG_AVAILABLE:
        after_excel_update_hook()
    
    return excel_path
"""

# ============================================================================
# 3. In services/odoo/odoo_service.py (after successful posting)
# ============================================================================
"""
# Add at top of file:
try:
    from rag.utils import record_odoo_posting_hook
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    record_odoo_posting_hook = lambda *args, **kwargs: False

# After successful Odoo posting:
def create_job_posting(self, job_data):
    # YOUR EXISTING ODOO POSTING CODE HERE
    # ...
    
    # Record posting in RAG
    if RAG_AVAILABLE and success:
        record_odoo_posting_hook(
            job_id=job_data.get('job_id'),
            status='posted',
            details={
                'odoo_id': odoo_response_id,
                'posting_time': datetime.now().isoformat()
            }
        )
    
    return success
"""

print("""
Copy the appropriate code blocks above into your existing files.
These are MINIMAL hooks that won't break your existing code.
""")