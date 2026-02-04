import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pytz
from datetime import datetime

# ADD THIS IMPORT AT TOP:
from services.dual_table.gmail_authenticator import get_est_time

def get_last_email_sent_date():
    """Get the last date when email was sent from the tracking file"""
    tracking_file = 'email_tracking.json'
    
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r') as f:
                data = json.load(f)
                return data.get('last_sent_date')
        except:
            return None
    return None

def update_email_sent_date():
    """Update the tracking file with today's date"""
    tracking_file = 'email_tracking.json'
    today_date = get_est_time()
    
    data = {
        'last_sent_date': today_date,
        'last_sent_time': get_est_time()
    }
    
    try:
        with open(tracking_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Email sent date updated: {today_date}")
    except Exception as e:
        print(f"❌ Failed to update email tracking: {e}")

def should_send_email(has_new_jobs=False):
    """Check if email should be sent based on schedule and duplicate prevention"""
    # Get current EST time
    current_est = get_est_time()
    current_time = current_est
    current_date = current_est
    
    # Check if it's the scheduled time (6:00 PM EST)
    scheduled_time = "18:00"
    
    # FIX: If there are new jobs, we should send email regardless of previous sends
    if has_new_jobs:
        print(f"📧 New jobs detected - will send email even if one was sent earlier today")
        return True
    
    # Check if we already sent email today
    last_sent_date = get_last_email_sent_date()
    
    if last_sent_date == current_date:
        print(f"📧 Email already sent today ({current_date}) - skipping to avoid duplicates")
        return False
    
    # Check if it's exactly or past the scheduled time
    if current_time >= scheduled_time:
        print(f"✅ It's {current_time} EST - scheduled email time reached ({scheduled_time} EST)")
        return True
    else:
        print(f"⏰ It's {current_time} EST - waiting for scheduled time ({scheduled_time} EST)")
        return False

def send_results_email(excel_path, recipient_emails, use_bcc=False, has_new_jobs=False):
    """Send the results Excel file as an email attachment to multiple recipients
    with option to use BCC (Blind Carbon Copy) and scheduled sending
    
    Args:
        excel_path (str): Path to the Excel file to attach
        recipient_emails (list): List of email addresses to send to
        use_bcc (bool): If True, use BCC to hide recipients from each other
                       If False, all recipients will see each other's addresses
        has_new_jobs (bool): Whether new jobs were processed in this run
    """
    try:
        # First check if we should send email based on schedule and duplicate prevention
        if not should_send_email(has_new_jobs):
            print("📧 Email not sent - either already sent today or not yet scheduled time (6:00 PM EST)")
            return False
        
        # Email configuration
        sender_email = "kodigantisuresh3731@gmail.com"
        password = "ofoe kqij qrlt vgnh"
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Validate recipient emails
        valid_recipients = []
        for email in recipient_emails:
            if email and email.strip() and "@" in email and "." in email.split("@")[1]:
                valid_recipients.append(email.strip())
        
        if not valid_recipients:
            print("❌ No valid recipient email addresses found")
            return False
        
        current_est = get_est_time()
        print(f"📧 Preparing scheduled email at {current_est} to {len(valid_recipients)} recipients")
        
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['Subject'] = f"Daily Job Application Tracker Report - {current_est}"
        
        # Configure recipients based on BCC preference
        if use_bcc:
            msg['To'] = sender_email
            msg['Bcc'] = ", ".join(valid_recipients)
            print(f"   📨 Mode: BCC (recipients hidden)")
        else:
            msg['To'] = ", ".join(valid_recipients)
            print(f"   📨 Mode: Regular (recipients visible)")
        
        # Email body
        body = f"""Daily Job Application Tracker Report

Report generated on: {current_est}

This is your scheduled daily report containing the latest job application tracking results.

📋 **Sheet1: Active Jobs** 
   - Jobs with future due dates (today and beyond)
   - Sorted by due date (ascending)

📋 **Sheet2: Past Due Jobs**
   - Jobs with past due dates
   - Sorted by due date (ascending)

Both sheets contain:
• Job IDs • Job Titles • Number of Submissions • Status • Due Dates

Note: This is an automated daily report sent at 6:00 PM EST.
Data is cumulative - all historical jobs are maintained and updated.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach Excel file
        try:
            with open(excel_path, 'rb') as file:
                part = MIMEApplication(file.read(), Name="Daily_Job_Tracker_Report.xlsx")
            part['Content-Disposition'] = f'attachment; filename="Daily_Job_Report_{current_est}.xlsx"'
            msg.attach(part)
            print("✅ Excel file attached successfully")
        except Exception as e:
            print(f"❌ Failed to attach Excel file: {e}")
            return False
        
        # Send email
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)
            
            # Update tracking after successful send
            update_email_sent_date()
            print(f"✅ Scheduled email sent successfully to {len(valid_recipients)} recipients at {current_est}")
            return True
            
        except smtplib.SMTPRecipientsRefused as e:
            print(f"❌ SMTP Recipients Refused: {e}")
            return False
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ SMTP Authentication Failed: Check your email credentials")
            return False
        except smtplib.SMTPSenderRefused as e:
            print(f"❌ SMTP Sender Refused: {e}")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP Error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during email sending: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False