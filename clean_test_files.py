"""
Script to remove test files created earlier
Run this once to clean up
"""
import os
import shutil
from pathlib import Path

def clean_test_files():
    """Remove all test files created earlier"""
    print("Cleaning up test files...")
    
    files_to_remove = [
        "vms_outputs/GA_Business_Analyst_98765.json",
        "vms_outputs/test",
        "dir_portal_outputs/TX_Developer_54321.txt",
    ]
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
                print(f"Removed directory: {file_path}")
            else:
                os.remove(file_path)
                print(f"Removed file: {file_path}")
    
    # Check for job_tracker_report.xlsx and warn
    if os.path.exists("job_tracker_report.xlsx"):
        # Don't remove this - it might be your real file
        print("Note: job_tracker_report.xlsx exists - keeping it (might be your real file)")
    
    print("Cleanup complete!")

if __name__ == "__main__":
    clean_test_files()