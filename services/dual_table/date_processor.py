import pandas as pd
import pytz
from datetime import datetime

# ADD THIS IMPORT AT TOP:
from services.dual_table.gmail_authenticator import get_est_time

def format_due_date(due_date_str):
    """Convert MM/DD format to 'Day, Month Day, Year' format using EST timezone - FIXED YEAR LOGIC"""
    if pd.isna(due_date_str) or due_date_str is None:
        return None
    
    try:
        # Parse MM/DD format
        month, day = due_date_str.split('/')
        month = int(month)
        day = int(day)
        
        # Use EST timezone for date calculations
        est = pytz.timezone('US/Eastern')
        
        # Get current year from EST time string
        est_time_str = get_est_time()  # "2026-01-17 07:46:48 EST"
        try:
            # Parse the year from the string
            year_part = est_time_str[:4]  # First 4 chars are year
            current_year = int(year_part)
        except:
            # Fallback to datetime.now()
            current_year = datetime.now().year
        
        # Create due date in CURRENT YEAR only (don't add +1 year)
        due_date_est = est.localize(datetime(current_year, month, day))
        
        # Format as "Monday, January 1, 2025" in EST
        formatted_date = due_date_est.strftime("%A, %B %d, %Y")
        return formatted_date
    except (ValueError, AttributeError):
        # If date parsing fails, return original string
        return due_date_str


def format_past_due_date(due_date_str):
    """Convert MM/DD format to 'Day, Month Day, Year' format for PAST DUE dates using EST timezone - FIXED YEAR LOGIC"""
    if pd.isna(due_date_str) or due_date_str is None:
        return None
    
    try:
        # Parse MM/DD format
        month, day = due_date_str.split('/')
        month = int(month)
        day = int(day)
        
        # Use EST timezone for date calculations
        est = pytz.timezone('US/Eastern')
        
        # Get current year from EST time string
        est_time_str = get_est_time()  # "2026-01-17 07:46:48 EST"
        try:
            year_part = est_time_str[:4]  # First 4 chars are year
            current_year = int(year_part)
        except:
            current_year = datetime.now().year
        
        # For past due dates, use the CURRENT YEAR (not previous year)
        due_date_est = est.localize(datetime(current_year, month, day))
        
        # Format as "Monday, January 1, 2025" in EST
        formatted_date = due_date_est.strftime("%A, %B %d, %Y")
        return formatted_date
    except (ValueError, AttributeError):
        # If date parsing fails, return original string
        return due_date_str

def format_due_dates_column(df):
    """Format the Due_date column to display as 'Day, Month Day, Year' using EST"""
    if 'Due_date' not in df.columns:
        return df
    
    print("\n=== Formatting Due Dates (EST) ===")
    # FIX: Use .copy() and .loc to avoid SettingWithCopyWarning
    df_formatted = df.copy()
    df_formatted.loc[:, 'Due_date'] = df_formatted['Due_date'].apply(format_due_date)
    return df_formatted

def format_past_due_dates_column(df):
    """Format the Due_date column for PAST DUE dates to show correct years"""
    if 'Due_date' not in df.columns:
        return df
    
    print("\n=== Formatting Past Due Dates (EST) ===")
    # FIX: Use .copy() and .loc to avoid SettingWithCopyWarning
    df_formatted = df.copy()
    df_formatted.loc[:, 'Due_date'] = df_formatted['Due_date'].apply(format_past_due_date)
    return df_formatted


def filter_past_due_dates(df):
    """Separate rows into active and past due dates, using EST timezone - FIXED YEAR LOGIC"""
    if 'Due_date' not in df.columns or df.empty:
        return df, pd.DataFrame()
    
    est = pytz.timezone('US/Eastern')
    from datetime import datetime
    
    est_time_str = get_est_time()  # Get string like "2026-01-17 07:46:48 EST"
    
    # Parse the string correctly
    try:
        # Try parsing with space before timezone
        today_est = datetime.strptime(est_time_str, "%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        try:
            # If that fails, remove the timezone part and parse just the datetime
            # String is "2026-01-17 07:46:48 EST" - remove last 4 chars for timezone
            time_part = est_time_str[:-4].strip()  # Remove " EST"
            today_est = datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S")
        except:
            # Last resort: extract just the date part
            try:
                date_part = est_time_str.split(' ')[0]  # Get "2026-01-17"
                today_est = datetime.strptime(date_part, "%Y-%m-%d")
            except:
                # Final fallback: use current time
                today_est = datetime.now()
    
    # Set time to midnight
    today_est = today_est.replace(hour=0, minute=0, second=0, microsecond=0)
        
    print(f"🔍 DATE DEBUG: Today (EST): {today_est.strftime('%Y-%m-%d')}")
    
    def is_active_row(due_date_str):
        if pd.isna(due_date_str) or due_date_str is None:
            return False
        
        try:
            # Handle MM/DD format (like "11/14")
            if '/' in due_date_str and len(due_date_str) <= 5:
                month, day = due_date_str.split('/')
                month = int(month)
                day = int(day)
                
                # Create due date in CURRENT YEAR only
                due_date_est = est.localize(datetime(today_est.year, month, day))
                
                # Active if due date is today or in the future (within current year)
                is_active = due_date_est.date() >= today_est.date()
                print(f"   MM/DD: {due_date_str} -> {due_date_est.date()} -> {'ACTIVE' if is_active else 'PAST DUE'}")
                return is_active
            
            # Handle formatted date like "Friday, November 14, 2025"
            elif ',' in due_date_str:
                # Parse the formatted date
                date_obj = datetime.strptime(due_date_str, "%A, %B %d, %Y")
                due_date_est = est.localize(date_obj)
                
                is_active = due_date_est.date() >= today_est.date()
                print(f"   Formatted: {due_date_str} -> {due_date_est.date()} -> {'ACTIVE' if is_active else 'PAST DUE'}")
                return is_active
            
            else:
                print(f"   Unknown format: {due_date_str}")
                return False
                
        except (ValueError, AttributeError, Exception) as e:
            print(f"   Error parsing '{due_date_str}': {e}")
            return False
    
    # Separate active and past due rows
    active_mask = df['Due_date'].apply(is_active_row)
    active_df = df[active_mask].copy()  # FIX: Use .copy()
    past_due_df = df[~active_mask].copy()  # FIX: Use .copy()
    
    print(f"📊 DATE SEPARATION RESULT:")
    print(f"   Active Jobs: {len(active_df)} rows")
    print(f"   Past Due Jobs: {len(past_due_df)} rows")
    
    return active_df, past_due_df


def sort_by_due_date(df):
    """Sort DataFrame by due date in ascending order - FIXED YEAR LOGIC"""
    if 'Due_date' not in df.columns:
        return df
    
    # Create a temporary column for sorting
    df_sorted = df.copy()
    
    # Convert due dates to sortable format
    def create_sortable_date(due_date_str):
        if pd.isna(due_date_str) or due_date_str is None:
            return datetime.max  # Put missing dates at the end
        
        try:
            # Parse formatted date like "Monday, October 20, 2025"
            date_obj = datetime.strptime(due_date_str, "%A, %B %d, %Y")
            return date_obj
        except (ValueError, AttributeError):
            # If parsing fails, try MM/DD format
            try:
                month, day = due_date_str.split('/')
                # Get current year from EST time string
                est_time_str = get_est_time()  # "2026-01-17 07:46:48 EST"
                try:
                    year_part = est_time_str[:4]
                    current_year = int(year_part)
                except:
                    current_year = datetime.now().year
                # Use CURRENT YEAR only (don't add +1 year)
                date_obj = datetime(current_year, int(month), int(day))
                return date_obj
            except:
                return datetime.max  # Put invalid dates at the end
    
    df_sorted['_sort_date'] = df_sorted['Due_date'].apply(create_sortable_date)
    df_sorted = df_sorted.sort_values('_sort_date')
    df_sorted = df_sorted.drop('_sort_date', axis=1)
    
    return df_sorted.reset_index(drop=True)

def sort_past_due_by_date(df):
    """Sort Past Due DataFrame by due date in ascending order (oldest first)"""
    if 'Due_date' not in df.columns:
        return df
    
    # Create a temporary column for sorting
    df_sorted = df.copy()
    
    # Convert due dates to sortable format
    def create_sortable_date(due_date_str):
        if pd.isna(due_date_str) or due_date_str is None:
            return datetime.min  # Put missing dates at the beginning
        
        try:
            # Parse formatted date like "Monday, October 20, 2025"
            date_obj = datetime.strptime(due_date_str, "%A, %B %d, %Y")
            return date_obj
        except (ValueError, AttributeError):
            # If parsing fails, try MM/DD format
            try:
                month, day = due_date_str.split('/')
                # Get current year from EST time string
                est_time_str = get_est_time()  # "2026-01-17 07:46:48 EST"
                try:
                    year_part = est_time_str[:4]
                    current_year = int(year_part)
                except:
                    current_year = datetime.now().year
                date_obj = datetime(current_year, int(month), int(day))
                return date_obj
            except:
                return datetime.min  # Put invalid dates at the beginning
    
    df_sorted['_sort_date'] = df_sorted['Due_date'].apply(create_sortable_date)
    df_sorted = df_sorted.sort_values('_sort_date')  # Ascending order (oldest first)
    df_sorted = df_sorted.drop('_sort_date', axis=1)
    
    return df_sorted.reset_index(drop=True)

def is_today_due_date(due_date_str):
    """Check if due date is today in EST timezone"""
    if pd.isna(due_date_str) or due_date_str is None:
        return False
    
    try:
        # Parse formatted date like "Monday, October 20, 2025"
        due_date = datetime.strptime(due_date_str, "%A, %B %d, %Y")
        
        # Get today's date from EST string
        est_time_str = get_est_time()  # "2026-01-17 07:46:48 EST"
        try:
            # Extract date part
            date_part = est_time_str.split(' ')[0]  # "2026-01-17"
            today_est = datetime.strptime(date_part, "%Y-%m-%d")
        except:
            today_est = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
        return due_date.date() == today_est.date()
    except (ValueError, AttributeError):
        return False
    
def debug_date_logic(df):
    """Debug function to check why dates are being classified incorrectly"""
    if 'Due_date' not in df.columns:
        return
    
    est = pytz.timezone('US/Eastern')
    
    # Get today's date from EST string
    est_time_str = get_est_time()  # "2026-01-17 07:46:48 EST"
    try:
        date_part = est_time_str.split(' ')[0]  # "2026-01-17"
        today_est = datetime.strptime(date_part, "%Y-%m-%d")
        today_est = today_est.replace(hour=0, minute=0, second=0, microsecond=0)
    except:
        today_est = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    print(f"\n🔍 DEBUG DATE LOGIC:")
    print(f"   Today (EST): {today_est.strftime('%A, %B %d, %Y')}")
    
    for i, due_date in enumerate(df['Due_date'].head(5)):  # Check first 5 dates
        if pd.isna(due_date) or due_date is None:
            continue
            
        try:
            # Try to parse as formatted date first
            if ',' in due_date:
                parsed_date = datetime.strptime(due_date, "%A, %B %d, %Y")
                due_date_est = est.localize(parsed_date)
                status = "ACTIVE" if due_date_est.date() >= today_est.date() else "PAST DUE"
                print(f"   {due_date} -> {status} (parsed as: {due_date_est.date()})")
            # Try to parse as MM/DD
            elif '/' in due_date and len(due_date) <= 5:
                month, day = due_date.split('/')
                due_date_est = est.localize(datetime(today_est.year, int(month), int(day)))
                status = "ACTIVE" if due_date_est.date() >= today_est.date() else "PAST DUE"
                print(f"   {due_date} -> {status} (parsed as: {due_date_est.date()})")
                
        except Exception as e:
            print(f"   {due_date} -> ERROR: {e}")