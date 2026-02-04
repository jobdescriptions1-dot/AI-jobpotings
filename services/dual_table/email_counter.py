import csv
import time
import logging
import pandas as pd

# ADD THESE IMPORTS AT TOP:
from services.dual_table.gmail_authenticator import get_est_time

def count_emails_for_job_id(service, job_id, posting_date_str, due_date_str):
    """Count emails from posting date to due date (FIXED range) - CUMULATIVE counting"""
    try:
        print(f"🔍 Searching for Job ID: {job_id}")
        print(f"📅 FIXED date range: {posting_date_str} to {due_date_str}")
        
        # Use FIXED date range: posting_date to due_date
        date_range_query = f"after:{posting_date_str} before:{due_date_str}"
        
        # Try multiple search strategies with FIXED date range
        search_strategies = [
            f'{job_id} {date_range_query}',                              # Basic search with fixed date
            f'"{job_id}" {date_range_query}',                           # Exact phrase with fixed date
            f'subject:{job_id} {date_range_query}',                     # In subject with fixed date
            f'"{job_id}"',                                              # Exact phrase fallback
            job_id,                                                     # Basic fallback
        ]
        
        total_count = 0
        emails_found = set()
        
        for i, search_query in enumerate(search_strategies):
            try:
                print(f"  Trying search #{i+1}: {search_query}")
                
                results = service.users().messages().list(
                    userId="me",
                    q=search_query,
                    labelIds=['INBOX']
                ).execute()
                
                messages = results.get('messages', [])
                count = len(messages)
                
                if count > 0:
                    print(f"  ✅ Found {count} emails with strategy #{i+1}")
                    total_count += count
                    
                    # Get message details to avoid duplicates
                    for message in messages:
                        emails_found.add(message['id'])
                
            except Exception as e:
                print(f"  ❌ Search strategy #{i+1} failed: {e}")
                continue
        
        # Use unique count to avoid duplicates
        unique_count = len(emails_found)
        print(f"📧 CUMULATIVE count for {job_id}: {unique_count} emails (from {posting_date_str} to {due_date_str})")
        
        return unique_count
        
    except Exception as e:
        print(f"❌ Error counting emails for {job_id}: {e}")
        return 0
    
def process_job_ids_for_specific_jobs(csv_path, service, specific_job_ids, job_data_dict):
    """Process only specific job IDs using FIXED posting date to due date ranges."""
    try:
        with open(csv_path, 'r') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            fieldnames = reader.fieldnames
        
        # Ensure No_of_submissions column exists
        if 'No_of_submissions' not in fieldnames:
            if 'No_of_emails' in fieldnames:
                fieldnames.remove('No_of_emails')
            fieldnames.append('No_of_submissions')
            for row in rows:
                if 'No_of_emails' in row:
                    del row['No_of_emails']
                row['No_of_submissions'] = '0'
    
        # Only process rows with specific job IDs
        processed_count = 0
        for row in rows:
            job_id = row.get('Job ID', '').strip() or row.get('Job_ID', '').strip()
            if job_id and job_id in specific_job_ids:
                # Get posting date and due date for this job
                if job_id in job_data_dict:
                    posting_date = job_data_dict[job_id]['posting_date']
                    due_date = job_data_dict[job_id]['due_date']
                    
                    logging.info(f"Searching for emails with job ID: {job_id}")
                    logging.info(f"FIXED date range: {posting_date} to {due_date}")
                    
                    email_count = count_emails_for_job_id(service, job_id, posting_date, due_date)
                    row['No_of_submissions'] = str(email_count)
                    logging.info(f"Found {email_count} CUMULATIVE submissions for {job_id}")
                    processed_count += 1
                    time.sleep(0.5)  # Rate limiting
                else:
                    print(f"⚠️  No date data found for {job_id}, using fallback counting")
                    # Fallback to basic counting
                    email_count = count_emails_for_job_id(service, job_id, None, None)
                    row['No_of_submissions'] = str(email_count)
                    processed_count += 1
                    time.sleep(0.5)
            else:
                # Keep existing count for non-new jobs
                if 'No_of_submissions' not in row:
                    row['No_of_submissions'] = '0'
    
        print(f"✅ Processed {processed_count} NEW jobs with CUMULATIVE counting")
        
        with open(csv_path, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
        logging.info(f"Successfully updated CSV with CUMULATIVE counts")
        
    except Exception as e:
        logging.error(f"Error processing CSV file: {e}")
        raise
