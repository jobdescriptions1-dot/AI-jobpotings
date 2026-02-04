import os
import pandas as pd
import logging
import re

# ADD THESE IMPORTS AT TOP:
from services.dual_table.gmail_authenticator import auto_authenticate_secondary_gmail, get_est_time
# from services.dual_table.job_extractor import extract_job_details, extract_job_details_from_file
from services.dual_table.excel_handler import append_to_excel, save_both_tables_to_excel, reorder_columns
from services.dual_table.email_counter import count_emails_for_job_id, process_job_ids_for_specific_jobs
from services.dual_table.date_processor import filter_past_due_dates, format_due_dates_column, sort_by_due_date, sort_past_due_by_date
from services.dual_table.file_processor import process_folder_files_simple, clear_folders_after_processing
from services.dual_table.email_scheduler import send_results_email, should_send_email

def display_dataframe(df, title):
    """Display DataFrame in formatted table"""
    if df.empty:
        print(f"\n{title}: No data available")
        return
        
    print(f"\n{title}")
    print("=" * 120)
    
    pd.set_option('display.max_colwidth', 40)
    pd.set_option('display.width', 120)
    pd.set_option('display.colheader_justify', 'center')
    
    table = df.to_markdown(
        tablefmt="grid",
        stralign="left",
        numalign="left",
        index=False
    )
    
    margined_table = [f"    {line}" for line in table.split('\n')]
    print('\n'.join(margined_table))
    print("=" * 120)

def run_dual_table_processing():
    """Main function that processes folder files and properly appends to Excel"""
    try:
        # List of recipient email addresses
        recipient_emails = [
            "support@innosoul.com" ,
            "jobdescriptions1@gmail.com"     # Updated email recipient
        ]
        
        # Check if email is configured
        if not recipient_emails or recipient_emails[0] == "":
            print("❌ No recipient email specified. Please update recipient_emails in main() function.")
            send_email = False
        else:
            send_email = True
            print(f"✅ Email recipient configured: {recipient_emails[0]}")
        
        # Display current EST time
        current_est = get_est_time()
        print(f"Current EST Time: {current_est}")
        print("🎯 MODE: Processing Folder Files + Append to Existing Excel")
        
        # Step 1: Process folder files
        '''folder_results = process_folder_files_simple(
            hhsc_folder="dir_portal_outputs",  
            vms_folder="vms_outputs"
        )
        '''

        folder_results = process_folder_files_simple()
        

        if folder_results.empty:
            print("❌ No valid job files found in folders")
            return
        
        # Use folder_results directly
        df = folder_results

        if df.empty:
            print("\nNo valid job details found in files")
            return

        # Remove rows with missing or invalid data
        initial_count = len(df)
        df = df.dropna(subset=['Title', 'Job_ID'])
        
        # Clean up titles
        email_markers = ['URL :', 'Posted :', 'Author :', 'Categories :', 'Blog Job ID:']
        for marker in email_markers:
            mask = df['Title'].str.contains(marker, na=False)
            if mask.any():
                print(f"🔄 Removing {mask.sum()} rows with full email content markers")
                df = df[~mask]
        
        df = df[df['Title'].str.len() <= 200]
        final_count = len(df)
        
        if initial_count != final_count:
            print(f"🔄 Removed {initial_count - final_count} invalid rows")

        if df.empty:
            print("\nNo valid job details found after filtering")
            return
            
        # Step 2: Append to Excel (this should ADD to existing data, not replace)
        excel_path = 'job_tracker_report.xlsx'
        print(f"\n=== Appending {len(df)} New Jobs to Excel ===")
        
        # This function should COMBINE existing data with new data
        appended_active_df, appended_past_due_df = append_to_excel(df, excel_path)
        
        if appended_active_df.empty and appended_past_due_df.empty:
            print("❌ No data available after appending")
            return
        
        print(f"📊 Data ready for counting:")
        print(f"   - Active Jobs: {len(appended_active_df)} rows")
        print(f"   - Past Due Jobs: {len(appended_past_due_df)} rows")
        
                # Step 3: Count submissions ONLY for NEW jobs using FIXED DATE RANGES (CUMULATIVE)
        print(f"\n=== Counting Submissions for NEW Jobs Using FIXED Date Ranges ===")
        
        # Track NEW job IDs from the folder processing
        new_job_ids = set(df['Job_ID'].dropna().tolist())
        
        # Create a dictionary of job_id -> {posting_date, due_date} for new jobs
        job_data_dict = {}
        for _, row in df.iterrows():
            if pd.notna(row['Job_ID']):
                # Get posting date (today for new jobs)
                posting_date = get_est_time()
                # Get due date
                due_date = row['Due_date'] if pd.notna(row['Due_date']) else None
                
                job_data_dict[row['Job_ID']] = {
                    'posting_date': posting_date,
                    'due_date': due_date
                }
        
        print(f"🎯 NEW JOBS TO COUNT: {len(new_job_ids)} jobs with FIXED date ranges")
        for job_id, dates in job_data_dict.items():
            print(f"   - {job_id}: Posting {dates['posting_date']} to Due {dates['due_date']}")
        
        try:
            secondary_service = auto_authenticate_secondary_gmail()
            
            # Initialize final dataframes
            final_active_df = appended_active_df.copy()
            final_past_due_df = appended_past_due_df.copy()
            
            # Only process if there are new jobs
            if new_job_ids:
                # Create temporary dataframes with ONLY new jobs for counting
                new_active_for_counting = appended_active_df[appended_active_df['Job_ID'].isin(new_job_ids)].copy()
                new_past_due_for_counting = appended_past_due_df[appended_past_due_df['Job_ID'].isin(new_job_ids)].copy()
                
                temp_active_csv = 'temp_active_new_jobs.csv'
                temp_past_due_csv = 'temp_past_due_new_jobs.csv'
                
                # Process NEW active jobs with FIXED date ranges
                if not new_active_for_counting.empty:
                    print(f"📊 Counting submissions for {len(new_active_for_counting)} NEW active jobs using FIXED date ranges...")
                    new_active_for_counting.to_csv(temp_active_csv, index=False)
                    process_job_ids_for_specific_jobs(temp_active_csv, secondary_service, new_job_ids, job_data_dict)
                    counted_active_df = pd.read_csv(temp_active_csv)
                    
                    # Update counts in final dataframe
                    for _, row in counted_active_df.iterrows():
                        job_id = row['Job_ID']
                        count = row['No_of_submissions']
                        final_active_df.loc[final_active_df['Job_ID'] == job_id, 'No_of_submissions'] = count
                    
                    os.remove(temp_active_csv)
                    print(f"✅ NEW active jobs counting completed with FIXED date ranges")
                else:
                    print("⚠️  No NEW active jobs to count")
                
                # Process NEW past due jobs with FIXED date ranges
                if not new_past_due_for_counting.empty:
                    print(f"📊 Counting submissions for {len(new_past_due_for_counting)} NEW past due jobs using FIXED date ranges...")
                    new_past_due_for_counting.to_csv(temp_past_due_csv, index=False)
                    process_job_ids_for_specific_jobs(temp_past_due_csv, secondary_service, new_job_ids, job_data_dict)
                    counted_past_due_df = pd.read_csv(temp_past_due_csv)
                    
                    # Update counts in final dataframe
                    for _, row in counted_past_due_df.iterrows():
                        job_id = row['Job_ID']
                        count = row['No_of_submissions']
                        final_past_due_df.loc[final_past_due_df['Job_ID'] == job_id, 'No_of_submissions'] = count
                    
                    os.remove(temp_past_due_csv)
                    print(f"✅ NEW past due jobs counting completed with FIXED date ranges")
                else:
                    print("⚠️  No NEW past due jobs to count")
            else:
                print("ℹ️  No new jobs to count - keeping existing submission counts")
                
        except Exception as e:
            print(f"❌ Error during NEW jobs email counting: {e}")
            print("📊 Continuing without submission counts for new jobs...")
            # Keep the original dataframes if counting fails
            final_active_df = appended_active_df
            final_past_due_df = appended_past_due_df
        
        # Step 4: Final processing
        final_active_df = reorder_columns(final_active_df)
        final_past_due_df = reorder_columns(final_past_due_df)
        final_active_df = sort_by_due_date(final_active_df)
        final_past_due_df = sort_past_due_by_date(final_past_due_df)
        
        # Step 5: Save and display
        save_both_tables_to_excel(final_active_df, final_past_due_df, excel_path)
        
        current_est_final = get_est_time()
        
        # Display Active Jobs
        if not final_active_df.empty:
            display_dataframe(final_active_df, f"ACTIVE JOBS\nReport Time (EST): {current_est_final}")
        else:
            print(f"\nACTIVE JOBS: No data available")
        
        # Display Past Due Jobs
        if not final_past_due_df.empty:
            display_dataframe(final_past_due_df, f"PAST DUE JOBS\nReport Time (EST): {current_est_final}")
        else:
            print(f"\nPAST DUE JOBS: No data available")
        
        # Step 6: Send scheduled email (will only send at 6:00 PM EST and only once per day)
        if send_email:
            # Choose sending mode:
            use_bcc = True  # Set to True for BCC (recipients hidden), False for regular (all visible)
            
            if use_bcc:
                print("🔒 Using BCC mode - recipients will not see each other's addresses")
            else:
                print("👁️  Using regular mode - all recipients can see each other's addresses")
            
            has_new_jobs = len(new_job_ids) > 0
            success = send_results_email(excel_path, recipient_emails, use_bcc=use_bcc, has_new_jobs=has_new_jobs)
            
            if success:
                print("✅ Scheduled email sent successfully")
            else:
                print("ℹ️  Email not sent - either already sent today or not yet 6:00 PM EST")
        else:
            print("📧 Email not sent - no valid recipients configured")
        
        print(f"\n✅ PROCESSING COMPLETE!")
        print(f"📊 New jobs processed: {len(df)}")
        print(f"📊 Total active jobs: {len(final_active_df)}")
        print(f"📊 Total past due jobs: {len(final_past_due_df)}")
        print(f"📁 Excel file updated: {excel_path}")
        print(f"🗑️  Folders cleared and ready for new files")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_dual_table_processing()


    
    # TO:
    # excel_path = 'outputs/excel_reports/job_tracker_report.xlsx' 
