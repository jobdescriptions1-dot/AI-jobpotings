import sqlite3
import re
from datetime import datetime

def normalize_pretty_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    if not date_str or date_str.lower() in ['n/a', 'none', 'null']:
        return None
        
    # Already ISO check (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return date_str[:10]
        
    # Standard Odoo Pretty format: Monday, February 02, 2026
    # Also handles February 02, 2026 or 02/02/2026
    formats = [
        "%A, %B %d, %Y", 
        "%B %d, %Y", 
        "%m/%d/%Y", 
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%A, %d %B %Y"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    # Try Regex for (Month Day, Year) if strptime fails
    try:
        match = re.search(r'([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})', date_str)
        if match:
            mon_str, day_str, year_str = match.groups()
            dt = datetime.strptime(f"{mon_str} {day_str} {year_str}", "%B %d %Y")
            return dt.strftime("%Y-%m-%d")
    except:
        pass
        
    return date_str

def migrate():
    conn = sqlite3.connect("sqlite_db/jobs_metadata.db")
    cursor = conn.cursor()
    
    tables = ['jobs', 'job_tracking']
    total_updated = 0
    
    for table in tables:
        cursor.execute(f"SELECT id, due_date FROM {table}")
        rows = cursor.fetchall()
        print(f"Checking {len(rows)} records in {table}...")
        
        for row_id, due_date in rows:
            if not due_date: continue
            normalized = normalize_pretty_date(due_date)
            if normalized != due_date:
                cursor.execute(f"UPDATE {table} SET due_date = ? WHERE id = ?", (normalized, row_id))
                total_updated += 1
            
    conn.commit()
    conn.close()
    print(f"Done! Updated {total_updated} total records.")

if __name__ == "__main__":
    migrate()
