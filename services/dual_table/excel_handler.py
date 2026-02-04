import os
import pandas as pd
import xlsxwriter
from datetime import datetime
import pytz

# ADD THIS IMPORT AT TOP:
from services.dual_table.gmail_authenticator import get_est_time
from services.dual_table.date_processor import format_due_dates_column, format_past_due_dates_column
from services.dual_table.date_processor import is_today_due_date, filter_past_due_dates

def append_to_excel(new_df, excel_path):
    """Append new data to existing Excel file with posting dates - MODIFIED FOR CUMULATIVE COUNTING"""
    try:
        # Add posting date to new jobs (current date when discovered)
        current_est = get_est_time() # Format for Gmail search
        new_df['Posting_Date'] = current_est
        
        print(f"📅 Added posting date {current_est} to {len(new_df)} new jobs")
        
        # Check if Excel file exists and read existing data
        if os.path.exists(excel_path):
            existing_active = pd.read_excel(excel_path, sheet_name='Active Jobs')
            existing_past_due = pd.read_excel(excel_path, sheet_name='Past Due Jobs')
            
            print(f"📁 Existing data loaded:")
            print(f"   - Active Jobs: {len(existing_active)} rows")
            print(f"   - Past Due Jobs: {len(existing_past_due)} rows")
            print(f"   - New jobs to add: {len(new_df)} rows")
            
            # Combine ALL existing data with new data
            all_existing = pd.concat([existing_active, existing_past_due], ignore_index=True)
            combined_df = pd.concat([all_existing, new_df], ignore_index=True)
            
            print(f"📊 Before duplicate removal: {len(combined_df)} total rows")
            
        else:
            # If file doesn't exist, just use new data
            print("📁 No existing Excel file found - creating new one")
            combined_df = new_df
            print(f"📊 New data: {len(combined_df)} rows")
        
        # Remove duplicates based on Job_ID (keep first occurrence - oldest)
        initial_combined_count = len(combined_df)
        combined_deduped = combined_df.drop_duplicates(subset=['Job_ID'], keep='first')
        final_combined_count = len(combined_deduped)
        
        print(f"🔄 Duplicate removal: {initial_combined_count} → {final_combined_count} rows")
        
        if os.path.exists(excel_path):
            net_new_jobs = final_combined_count - (len(existing_active) + len(existing_past_due))
            print(f"📈 Net new jobs added: {net_new_jobs}")
        
        # Re-separate into active and past due using FIXED logic
        updated_active, updated_past_due = filter_past_due_dates(combined_deduped)
        
        # Format dates
        updated_active = format_due_dates_column(updated_active)
        updated_past_due = format_past_due_dates_column(updated_past_due)
        
        # Add Status column (blank values)
        updated_active = add_status_column(updated_active)
        updated_past_due = add_status_column(updated_past_due)
        
        # Add No_of_submissions column if missing
        if 'No_of_submissions' not in updated_active.columns:
            updated_active['No_of_submissions'] = 0
        if 'No_of_submissions' not in updated_past_due.columns:
            updated_past_due['No_of_submissions'] = 0
            
        # Ensure Posting_Date column exists for all rows
        if 'Posting_Date' not in updated_active.columns:
            updated_active['Posting_Date'] = current_est
        if 'Posting_Date' not in updated_past_due.columns:
            updated_past_due['Posting_Date'] = current_est
        
        # Save back to Excel
        save_both_tables_to_excel(updated_active, updated_past_due, excel_path)
        
        print(f"✅ Successfully updated Excel:")
        print(f"   - Updated Active Jobs: {len(updated_active)} rows")
        print(f"   - Updated Past Due Jobs: {len(updated_past_due)} rows")
        print(f"   - Added Posting_Date column for cumulative counting")
        
        return updated_active, updated_past_due
        
    except Exception as e:
        print(f"❌ Error in append_to_excel: {e}")
        import traceback
        traceback.print_exc()
        # Return empty dataframes as fallback
        return pd.DataFrame(), pd.DataFrame()


def save_both_tables_to_excel(active_df, past_due_df, excel_path):
    """Save both active and past due tables to Excel with separate sheets"""
    try:
        import xlsxwriter
        writer = pd.ExcelWriter(excel_path, engine='xlsxwriter')
        
        # Save active jobs as Sheet1
        active_df.to_excel(writer, index=False, sheet_name='Active Jobs')
        
        # Save past due jobs as Sheet2  
        past_due_df.to_excel(writer, index=False, sheet_name='Past Due Jobs')
        
        workbook = writer.book
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True, 
            'text_wrap': True, 
            'valign': 'top', 
            'align': 'center', 
            'border': 1,
            'bg_color': '#D3D3D3'  # Light gray background for headers
        })
        
        cell_format = workbook.add_format({
            'text_wrap': True, 
            'valign': 'top', 
            'align': 'left', 
            'border': 1
        })
        
        # Bold format for today's due dates
        today_bold_format = workbook.add_format({
            'text_wrap': True, 
            'valign': 'top', 
            'align': 'left', 
            'border': 1,
            'bold': True
        })
        
        # Format both sheets with same styling
        for sheet_name in ['Active Jobs', 'Past Due Jobs']:
            worksheet = writer.sheets[sheet_name]
            current_df = active_df if sheet_name == 'Active Jobs' else past_due_df
            
            # Apply header formatting
            for col_num, value in enumerate(current_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Apply cell formatting to data rows
            for row in range(1, len(current_df) + 1):
                is_today_row = False
                
                # Check if this row has today's due date (only for Active Jobs sheet)
                if sheet_name == 'Active Jobs':
                    due_date_value = current_df.iloc[row-1]['Due_date']
                    is_today_row = is_today_due_date(due_date_value)
                
                for col in range(len(current_df.columns)):
                    cell_value = str(current_df.iloc[row-1, col])
                    
                    # Handle Status column - replace 'nan' with empty string
                    if current_df.columns[col] == 'Status' and cell_value == 'nan':
                        cell_value = ''
                    
                    # Use bold format for today's due dates in Active Jobs, otherwise normal format
                    if is_today_row:
                        worksheet.write(row, col, cell_value, today_bold_format)
                    else:
                        worksheet.write(row, col, cell_value, cell_format)
            
            # Set optimal column widths
            col_widths = calculate_column_widths(current_df)
            for i, col in enumerate(current_df.columns):
                worksheet.set_column(i, i, col_widths[col])
            
            # Freeze the header row for easy scrolling
            worksheet.freeze_panes(1, 0)  # Freeze first row
        
        writer.close()
        print(f"\n✅ Excel file '{excel_path}' created with:")
        print(f"   - Sheet1: 'Active Jobs' ({len(active_df)} rows)")
        print(f"   - Sheet2: 'Past Due Jobs' ({len(past_due_df)} rows)")
        
        # Count and display today's due dates
        today_count = active_df['Due_date'].apply(is_today_due_date).sum()
        if today_count > 0:
            print(f"   - Today's due dates highlighted in bold: {today_count} row(s)")
        
    except ImportError:
        print("\n❌ Error: xlsxwriter not installed - cannot create Excel file")
        print("💡 Install with: pip install xlsxwriter")
        # Fallback to separate CSV files
        active_df.to_csv('active_jobs.csv', index=False)
        past_due_df.to_csv('past_due_jobs.csv', index=False)
        print("📁 Results saved to 'active_jobs.csv' and 'past_due_jobs.csv'")

def calculate_column_widths(df):
    """Calculate optimal column widths based on content"""
    col_widths = {}
    
    for col in df.columns:
        # Get the maximum length in the column
        max_content_len = df[col].astype(str).apply(len).max()
        max_header_len = len(col)
        max_len = max(max_content_len, max_header_len)
        
        # Add some padding but keep it tight
        col_widths[col] = min(max_len + 2, 50)  # Cap at 50 to prevent overly wide columns
    
    return col_widths

def reorder_columns(df):
    """Reorder columns to: Job_ID, Title, No_of_submissions, Status, Due_date"""
    desired_order = ['Job_ID', 'Title', 'No_of_submissions', 'Status', 'Due_date']
    
    # Only include columns that actually exist in the DataFrame
    existing_columns = [col for col in desired_order if col in df.columns]
    
    # Add any remaining columns that weren't in the desired order
    remaining_columns = [col for col in df.columns if col not in existing_columns]
    
    final_order = existing_columns + remaining_columns
    return df[final_order]

def add_status_column(df):
    """Add Status column with blank values"""
    df_with_status = df.copy()
    df_with_status['Status'] = ""  # Empty string instead of "Active" or "Past Due"
    return df_with_status

def remove_duplicates(df):
    """Remove duplicate rows based on Job_ID, keeping the first occurrence"""
    if df.empty:
        return df
    
    initial_count = len(df)
    df_deduplicated = df.drop_duplicates(subset=['Job_ID'], keep='first')
    final_count = len(df_deduplicated)
    
    if initial_count != final_count:
        print(f"🔄 Removed {initial_count - final_count} duplicate rows based on Job_ID")
    
    return df_deduplicated