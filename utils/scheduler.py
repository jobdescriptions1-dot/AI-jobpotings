import pytz
from datetime import datetime
from utils.config import *

# REAL FUNCTION TO USE:
from services.dual_table.gmail_authenticator import get_est_time


def should_send_daily_email():
    """Check if it's time to send the daily email using EST timezone - SIMPLIFIED"""
    try:
        # Get current time in EST
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        
        current_time = now_est.strftime("%H:%M:%S")
        current_hour = now_est.hour
        current_minute = now_est.minute
        today = now_est.strftime("%Y-%m-%d")
        
        last_sent_date = processed_emails_state.get('last_email_sent_date')
        
        # Parse the scheduled time
        scheduled_hour = int(DAILY_EMAIL_START_TIME.split(':')[0])
        scheduled_minute = int(DAILY_EMAIL_START_TIME.split(':')[1])
        
        # Check if we're within the email time window
        window_start_hour = scheduled_hour
        window_start_minute = scheduled_minute
        window_end_hour = int(DAILY_EMAIL_END_TIME.split(':')[0])
        window_end_minute = int(DAILY_EMAIL_END_TIME.split(':')[1])
        
        is_in_email_window = (
            (current_hour == window_start_hour and current_minute >= window_start_minute) or
            (current_hour == window_end_hour and current_minute < window_end_minute)
        )
        
        # Send email if we're in the time window AND we haven't sent today
        if is_in_email_window and last_sent_date != today:
            print(f"⏰ Email time check: {current_time} EST → WITHIN {DAILY_EMAIL_START_TIME}-{DAILY_EMAIL_END_TIME} WINDOW = READY TO SEND")
            print(f"📅 Last sent: {last_sent_date}, Today: {today} = EMAIL NOT SENT TODAY")
            return True
        else:
            if last_sent_date == today:
                print(f"📭 Email already sent today (at {DAILY_EMAIL_START_TIME}-{DAILY_EMAIL_END_TIME} window)")
            elif not is_in_email_window:
                # Show how much time until next email window
                if current_hour < window_start_hour or (current_hour == window_start_hour and current_minute < window_start_minute):
                    hours_left = window_start_hour - current_hour
                    minutes_left = window_start_minute - current_minute
                    
                    if minutes_left < 0:
                        hours_left -= 1
                        minutes_left += 60
                    
                    if hours_left > 0:
                        print(f"⏰ Next email window: {hours_left}h {minutes_left}m from now ({DAILY_EMAIL_START_TIME}-{DAILY_EMAIL_END_TIME} EST)")
                    else:
                        print(f"⏰ Next email window: {minutes_left}m from now ({DAILY_EMAIL_START_TIME}-{DAILY_EMAIL_END_TIME} EST)")
                else:
                    print(f"⏰ Email window closed for today ({DAILY_EMAIL_START_TIME}-{DAILY_EMAIL_END_TIME} EST)")
            return False
            
    except Exception as e:
        print(f"❌ Error checking email time: {e}")
        return False
