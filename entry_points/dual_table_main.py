# NEW FILE - CREATE THIS
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dual_table.dual_table_service import run_dual_table_processing

if __name__ == "__main__":
    run_dual_table_processing()