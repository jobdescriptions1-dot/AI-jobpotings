import sqlite3
from datetime import date

def check():
    conn = sqlite3.connect('sqlite_db/jobs_metadata.db')
    cursor = conn.cursor()
    curr = date.today().isoformat()
    print(f"Current Date: {curr}")
    
    # Check total
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]
    
    # Check Active with robust logic
    date_expr = "NULLIF(NULLIF(TRIM(COALESCE(jt.due_date, j.due_date)), ''), 'N/A')"
    
    cursor.execute(f"SELECT COUNT(*) FROM jobs j LEFT JOIN job_tracking jt ON j.job_id = jt.job_id WHERE {date_expr} >= ? OR {date_expr} IS NULL", (curr,))
    active = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM jobs j LEFT JOIN job_tracking jt ON j.job_id = jt.job_id WHERE {date_expr} < ?", (curr,))
    expired = cursor.fetchone()[0]
    
    # Check sample dates with JOIN
    query = f"""
        SELECT j.job_id, j.due_date, jt.due_date as tracking_due, {date_expr} as normalized 
        FROM jobs j 
        LEFT JOIN job_tracking jt ON j.job_id = jt.job_id 
        LIMIT 10
    """
    cursor.execute(query)
    samples = cursor.fetchall()
    
    print(f"Summary: Total={total}, Active={active}, Expired={expired}")
    print("Samples:")
    for s in samples:
        print(f"  ID: {s[0]} | Due: {s[1]} | Normalized: {s[2]}")
        
    conn.close()

if __name__ == "__main__":
    check()
