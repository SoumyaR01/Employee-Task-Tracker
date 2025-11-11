import schedule
import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
from pathlib import Path
import pandas as pd
import os
import requests


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reminder_service.log'),
        logging.StreamHandler()
    ]
)

# Constants
CONFIG_FILE = 'config.json'
EMAIL_CONFIG_FILE = 'email_config.json'
WHATSAPP_CONFIG_FILE = 'whatsapp_config.json'
TELEGRAM_CONFIG_FILE = 'telegram_config.json'
EXCEL_FILE_PATH = r'D:\Employee Track Report\task_tracker.xlsx'

# ==================== Configuration Management ====================

def load_config():
    """Load main configuration"""
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'excel_file_path': EXCEL_FILE_PATH,
        'reminder_time': '18:00',
        'reminder_days': [0, 1, 2, 3, 4, 5],  # Mon-Sat
        'admin_email': '',
        'employee_emails': [],
        # Optional: list of E.164 phone numbers aligned by index to employee_emails
        # Example: ["+9198XXXXXXXX", "+9199XXXXXXXX"]
        'employee_phones': [],
        # Optional: Telegram chat IDs aligned by index to employee_emails
        # Example: [123456789, 987654321]
        'employee_telegram_chat_ids': []
    }

def load_email_config():
    """Load email configuration"""
    if Path(EMAIL_CONFIG_FILE).exists():
        with open(EMAIL_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': '',
        'sender_password': '',
        'use_tls': True
    }

def save_email_config(config):
    """Save email configuration"""
    with open(EMAIL_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# ==================== WhatsApp Config (Twilio or WhatsApp Cloud API) ====================

def load_whatsapp_config():
    """Load WhatsApp configuration"""
    if Path(WHATSAPP_CONFIG_FILE).exists():
        with open(WHATSAPP_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        # Choose provider: 'twilio' or 'cloud_api'
        'provider': 'twilio',
        'enabled': False,
        # Twilio settings
        'twilio_account_sid': '',
        'twilio_auth_token': '',
        # Must be in the format 'whatsapp:+14155238886' or your approved sender
        'twilio_from': 'whatsapp:+14155238886',
        # WhatsApp Cloud API settings
        'cloud_api_token': '',
        'cloud_api_phone_number_id': '',
        # Message template
        'message_prefix': '⏰ Reminder:'
    }

def save_whatsapp_config(config):
    """Save WhatsApp configuration"""
    with open(WHATSAPP_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# ==================== Telegram Config ====================

def load_telegram_config():
    """Load Telegram configuration"""
    if Path(TELEGRAM_CONFIG_FILE).exists():
        with open(TELEGRAM_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'enabled': False,
        'bot_token': '',
        'message_prefix': '⏰ Reminder:'
    }

def save_telegram_config(config):
    """Save Telegram configuration"""
    with open(TELEGRAM_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# ==================== Excel File Functions ====================

def read_excel_data(excel_path=None):
    """Read data from local Excel file"""
    if excel_path is None:
        config = load_config()
        excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)
    
    try:
        if not os.path.exists(excel_path):
            logging.warning(f"Excel file not found at {excel_path}")
            return pd.DataFrame()
        
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Handle empty file
        if df.empty:
            return pd.DataFrame()
        
        return df
    
    except Exception as error:
        logging.error(f"Error reading Excel file: {error}")
        return None

def get_missing_reporters(df, today):
    """Get list of employees who haven't reported today"""
    if df is None or df.empty:
        logging.warning("No data available")
        return []

    today_str = today.strftime('%Y-%m-%d')

    # Filter today's submissions (create a copy to avoid modifying original)
    if 'Date' in df.columns:
        # Convert Date column to string for comparison
        df_copy = df.copy()
        df_copy['Date'] = pd.to_datetime(df_copy['Date']).dt.strftime('%Y-%m-%d')
        today_submissions = df_copy[df_copy['Date'] == today_str]
        submitted_employees = today_submissions['Name'].unique().tolist() if 'Name' in today_submissions.columns else []
    else:
        logging.warning("Date column not found in data")
        submitted_employees = []

    # Get all employees from config
    config = load_config()
    all_employees = config.get('employee_emails', [])

    # Find missing reporters
    # Compare employee emails/names with submitted employees
    missing = []
    for emp_email in all_employees:
        # Try to match by email or by name extracted from email
        emp_name = emp_email.split('@')[0] if '@' in emp_email else emp_email
        # Check if employee name or email is in submitted list
        if emp_name not in submitted_employees and emp_email not in submitted_employees:
            # Also check if any part of the email matches
            found = False
            for submitted_name in submitted_employees:
                if isinstance(submitted_name, str):
                    if emp_name.lower() in submitted_name.lower() or submitted_name.lower() in emp_name.lower():
                        found = True
                        break
            if not found:
                missing.append(emp_email)

    return missing

# ==================== Email Functions ====================

def send_email(to_email, subject, body, email_config):
    """Send email reminder"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_config['sender_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Create HTML version
        html_body = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f9f9f9;
                        border-radius: 10px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 10px 10px 0 0;
                        text-align: center;
                    }}
                    .content {{
                        background: white;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 12px 30px;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 20px;
                        color: #666;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 Daily Progress Report Reminder</h1>
                    </div>
                    <div class="content">
                        {body}
                    </div>
                    <div class="footer">
                        <p>This is an automated reminder from Employee Progress Tracker</p>
                        <p>© {datetime.now().year} Your Organization</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Attach HTML
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            if email_config.get('use_tls', True):
                server.starttls()
            
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
        
        logging.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return False

def send_reminder_emails(missing_reporters, email_config):
    """Send reminder emails to all missing reporters"""
    config = load_config()
    
    subject = "⏰ Daily Progress Report Reminder"
    
    for email in missing_reporters:
        body = f"""
        <p>Hello,</p>
        
        <p>This is a friendly reminder that you haven't submitted your daily progress report yet.</p>
        
        <p><strong>Please submit your report before end of day.</strong></p>
        
        <p>Your daily report helps the team stay informed about project progress and ensures smooth coordination.</p>
        
        <a href="{config.get('form_url', '#')}" class="button">Submit Report Now</a>
        
        <p>If you've already submitted your report, please disregard this message.</p>
        
        <p>Thank you for your cooperation!</p>
        
        <p>Best regards,<br>HR Team</p>
        """
        
        send_email(email, subject, body, email_config)
        time.sleep(2)  # Avoid rate limiting

def send_admin_summary(missing_reporters, email_config, total_employees):
    """Send summary to admin"""
    config = load_config()
    admin_email = config.get('admin_email')
    
    if not admin_email:
        logging.warning("No admin email configured")
        return
    
    subject = f"📊 Daily Report Summary - {datetime.now().strftime('%Y-%m-%d')}"
    
    submitted_count = total_employees - len(missing_reporters)
    submission_rate = (submitted_count / total_employees * 100) if total_employees > 0 else 0
    
    missing_list = "<ul>"
    for email in missing_reporters:
        missing_list += f"<li>{email}</li>"
    missing_list += "</ul>"
    
    body = f"""
    <h2>Daily Report Summary</h2>
    
    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
    
    <h3>Statistics</h3>
    <ul>
        <li><strong>Total Employees:</strong> {total_employees}</li>
        <li><strong>Reports Submitted:</strong> {submitted_count}</li>
        <li><strong>Reports Pending:</strong> {len(missing_reporters)}</li>
        <li><strong>Submission Rate:</strong> {submission_rate:.1f}%</li>
    </ul>
    
    <h3>Employees Who Haven't Reported:</h3>
    {missing_list if missing_reporters else "<p>All employees have submitted their reports! 🎉</p>"}
    
    <p>Reminder emails have been sent to employees who haven't submitted their reports.</p>
    """
    
    send_email(admin_email, subject, body, email_config)

# ==================== Reminder Scheduler ====================

def check_and_send_reminders():
    """Main reminder function"""
    logging.info("=" * 50)
    logging.info("Starting reminder check...")
    
    # Load configurations
    config = load_config()
    email_config = load_email_config()
    wa_config = load_whatsapp_config()
    tg_config = load_telegram_config()
    
    # Validate configuration
    excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)
    if not excel_path:
        logging.error("Excel file path not configured")
        return
    
    if not email_config.get('sender_email') or not email_config.get('sender_password'):
        logging.error("Email credentials not configured")
        return
    
    # Check if today is a reminder day
    today = datetime.now()
    reminder_days = config.get('reminder_days', [0, 1, 2, 3, 4, 5])
    
    if today.weekday() not in reminder_days:
        logging.info(f"Today ({today.strftime('%A')}) is not a reminder day. Skipping...")
        return
    
    # Read data from Excel file
    logging.info(f"Reading Excel data from {excel_path}...")
    df = read_excel_data(excel_path)
    
    if df is None:
        logging.error("Failed to read Excel data")
        return
    
    # Get missing reporters
    missing_reporters = get_missing_reporters(df, today)
    total_employees = len(config.get('employee_emails', []))
    
    logging.info(f"Total employees: {total_employees}")
    logging.info(f"Missing reporters: {len(missing_reporters)}")
    
    if missing_reporters:
        if email_config.get('sender_email') and email_config.get('sender_password'):
            logging.info("Sending reminder emails...")
            send_reminder_emails(missing_reporters, email_config)
            logging.info(f"Sent {len(missing_reporters)} reminder emails")
        else:
            logging.warning("Email not configured; skipping email reminders")

        if wa_config.get('enabled', False):
            logging.info("Sending WhatsApp reminders...")
            send_reminder_whatsapp(missing_reporters)

        if tg_config.get('enabled', False):
            logging.info("Sending Telegram reminders...")
            send_reminder_telegram(missing_reporters)
    else:
        logging.info("All employees have submitted their reports!")
    
    # Send admin summary
    logging.info("Sending admin summary...")
    send_admin_summary(missing_reporters, email_config, total_employees)
    
    logging.info("Reminder check completed")
    logging.info("=" * 50)

# ==================== WhatsApp Sending ====================

def send_whatsapp_twilio(to_phone, message, wa_config):
    """Send WhatsApp message via Twilio API"""
    try:
        from requests.auth import HTTPBasicAuth
        account_sid = wa_config.get('twilio_account_sid', '')
        auth_token = wa_config.get('twilio_auth_token', '')
        from_id = wa_config.get('twilio_from', '')
        if not account_sid or not auth_token or not from_id:
            logging.error("Twilio WhatsApp is not configured properly")
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        data = {
            'From': from_id,
            'To': f"whatsapp:{to_phone}" if not str(to_phone).strip().startswith("whatsapp:") else str(to_phone).strip(),
            'Body': message
        }
        resp = requests.post(url, data=data, auth=HTTPBasicAuth(account_sid, auth_token), timeout=20)
        if 200 <= resp.status_code < 300:
            logging.info(f"WhatsApp (Twilio) sent to {to_phone}")
            return True
        logging.error(f"Twilio send failed to {to_phone}: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logging.error(f"Twilio WhatsApp error for {to_phone}: {e}")
        return False

def send_whatsapp_cloud_api(to_phone, message, wa_config):
    """Send WhatsApp message via Meta WhatsApp Cloud API"""
    try:
        token = wa_config.get('cloud_api_token', '')
        phone_number_id = wa_config.get('cloud_api_phone_number_id', '')
        if not token or not phone_number_id:
            logging.error("WhatsApp Cloud API is not configured properly")
            return False

        url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone.replace("whatsapp:", "").replace(" ", ""),
            "type": "text",
            "text": {"body": message}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if 200 <= resp.status_code < 300:
            logging.info(f"WhatsApp (Cloud API) sent to {to_phone}")
            return True
        logging.error(f"Cloud API send failed to {to_phone}: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logging.error(f"Cloud API WhatsApp error for {to_phone}: {e}")
        return False

def send_whatsapp_message(to_phone, message, wa_config):
    """Dispatch WhatsApp message using selected provider"""
    provider = (wa_config.get('provider') or 'twilio').lower()
    if provider == 'cloud_api':
        return send_whatsapp_cloud_api(to_phone, message, wa_config)
    return send_whatsapp_twilio(to_phone, message, wa_config)

def send_reminder_whatsapp(missing_reporters):
    """Send WhatsApp reminders to missing reporters if enabled and phone numbers present"""
    wa_config = load_whatsapp_config()
    if not wa_config.get('enabled', False):
        logging.info("WhatsApp reminders are disabled.")
        return

    config = load_config()
    emails = config.get('employee_emails', []) or []
    phones = config.get('employee_phones', []) or []

    if not phones:
        logging.warning("No employee phone numbers configured (config.json -> employee_phones). Skipping WhatsApp.")
        return

    # Create mapping by email index if lengths match; otherwise best-effort by position
    if len(phones) != len(emails):
        logging.warning("employee_phones length does not match employee_emails; mapping by position may be incorrect.")

    prefix = wa_config.get('message_prefix', '⏰ Reminder:')
    today_str = datetime.now().strftime('%Y-%m-%d')
    base_message = (
        f"{prefix} You haven't submitted your Daily Progress Report for {today_str}."
        "\nPlease submit it before EOD.\n\nThank you."
    )

    sent = 0
    for idx, emp in enumerate(emails):
        if emp in missing_reporters:
            # Find phone by index
            if idx < len(phones):
                to_phone = str(phones[idx]).strip()
                if to_phone:
                    if send_whatsapp_message(to_phone, base_message, wa_config):
                        sent += 1
                        time.sleep(1.5)  # mild pacing
                else:
                    logging.warning(f"No phone number for {emp}")
            else:
                logging.warning(f"No phone mapping for {emp} at index {idx}")

    logging.info(f"WhatsApp reminders sent: {sent}")

# ==================== Telegram Sending ====================

def send_telegram_message(chat_id, message, tg_config):
    """Send a Telegram message via Bot API"""
    try:
        token = tg_config.get('bot_token', '')
        if not token:
            logging.error("Telegram bot token not configured")
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        resp = requests.post(url, json=payload, timeout=20)
        if 200 <= resp.status_code < 300 and resp.json().get("ok"):
            logging.info(f"Telegram message sent to chat_id {chat_id}")
            return True
        logging.error(f"Telegram send failed to {chat_id}: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logging.error(f"Telegram error for chat_id {chat_id}: {e}")
        return False

def send_reminder_telegram(missing_reporters):
    """Send Telegram reminders to missing reporters if enabled and chat IDs present"""
    tg_config = load_telegram_config()
    if not tg_config.get('enabled', False):
        logging.info("Telegram reminders are disabled.")
        return

    config = load_config()
    emails = config.get('employee_emails', []) or []
    chat_ids = config.get('employee_telegram_chat_ids', []) or []

    if not chat_ids:
        logging.warning("No Telegram chat IDs configured (config.json -> employee_telegram_chat_ids). Skipping Telegram.")
        return

    if len(chat_ids) != len(emails):
        logging.warning("employee_telegram_chat_ids length does not match employee_emails; mapping by position may be incorrect.")

    prefix = tg_config.get('message_prefix', '⏰ Reminder:')
    today_str = datetime.now().strftime('%Y-%m-%d')
    base_message = (
        f"{prefix} You haven't submitted your Daily Progress Report for {today_str}."
        "\nPlease submit it before EOD.\n\nThank you."
    )

    sent = 0
    for idx, emp in enumerate(emails):
        if emp in missing_reporters:
            if idx < len(chat_ids):
                chat_id = chat_ids[idx]
                if send_telegram_message(chat_id, base_message, tg_config):
                    sent += 1
                    time.sleep(1.0)
            else:
                logging.warning(f"No Telegram chat ID mapping for {emp} at index {idx}")

    logging.info(f"Telegram reminders sent: {sent}")

def schedule_reminders():
    """Schedule daily reminders"""
    config = load_config()
    reminder_time = config.get('reminder_time', '18:00')
    
    logging.info(f"Scheduling daily reminders at {reminder_time}")
    
    schedule.every().day.at(reminder_time).do(check_and_send_reminders)
    
    logging.info("Reminder service started successfully")
    logging.info(f"Next reminder check: {schedule.next_run()}")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# ==================== Setup Functions ====================

def setup_email_config():
    """Interactive email configuration setup"""
    print("\n" + "=" * 50)
    print("Email Configuration Setup")
    print("=" * 50 + "\n")
    
    email_config = load_email_config()
    
    print("For Gmail, you need to use an App Password:")
    print("1. Go to https://myaccount.google.com/apppasswords")
    print("2. Generate a new app password")
    print("3. Use that password here\n")
    
    email_config['sender_email'] = input(f"Sender Email [{email_config.get('sender_email', '')}]: ") or email_config.get('sender_email', '')
    email_config['sender_password'] = input("Sender Password (App Password): ") or email_config.get('sender_password', '')
    
    smtp_server = input(f"SMTP Server [{email_config.get('smtp_server', 'smtp.gmail.com')}]: ") or email_config.get('smtp_server', 'smtp.gmail.com')
    email_config['smtp_server'] = smtp_server
    
    smtp_port = input(f"SMTP Port [{email_config.get('smtp_port', 587)}]: ") or email_config.get('smtp_port', 587)
    email_config['smtp_port'] = int(smtp_port)
    
    save_email_config(email_config)
    
    print("\n✅ Email configuration saved!")
    print("\nTesting email connection...")
    
    # Test email
    try:
        test_body = "<p>This is a test email from Employee Progress Tracker.</p><p>Email configuration is working correctly!</p>"
        if send_email(email_config['sender_email'], "Test Email", test_body, email_config):
            print("✅ Test email sent successfully!")
        else:
            print("❌ Failed to send test email")
    except Exception as e:
        print(f"❌ Error: {e}")

def setup_whatsapp_config():
    """Interactive WhatsApp configuration setup"""
    print("\n" + "=" * 50)
    print("WhatsApp Configuration Setup")
    print("=" * 50 + "\n")

    wa_config = load_whatsapp_config()

    provider = input(f"Provider [twilio/cloud_api] [{wa_config.get('provider','twilio')}]: ") or wa_config.get('provider','twilio')
    wa_config['provider'] = provider.lower()
    enabled = input(f"Enable WhatsApp reminders? [y/N]: ").strip().lower() == 'y'
    wa_config['enabled'] = enabled

    if wa_config['provider'] == 'twilio':
        wa_config['twilio_account_sid'] = input(f"Twilio Account SID [{wa_config.get('twilio_account_sid','')}]: ") or wa_config.get('twilio_account_sid','')
        wa_config['twilio_auth_token'] = input(f"Twilio Auth Token [{wa_config.get('twilio_auth_token','')}]: ") or wa_config.get('twilio_auth_token','')
        wa_config['twilio_from'] = input(f"Twilio From (e.g., whatsapp:+14155238886) [{wa_config.get('twilio_from','whatsapp:+14155238886')}]: ") or wa_config.get('twilio_from','whatsapp:+14155238886')
    else:
        wa_config['cloud_api_token'] = input(f"Cloud API Token [{wa_config.get('cloud_api_token','')}]: ") or wa_config.get('cloud_api_token','')
        wa_config['cloud_api_phone_number_id'] = input(f"Cloud API Phone Number ID [{wa_config.get('cloud_api_phone_number_id','')}]: ") or wa_config.get('cloud_api_phone_number_id','')

    wa_config['message_prefix'] = input(f"Message Prefix [{wa_config.get('message_prefix','⏰ Reminder:')}]: ") or wa_config.get('message_prefix','⏰ Reminder:')

    save_whatsapp_config(wa_config)
    print("\n✅ WhatsApp configuration saved!")

def setup_telegram_config():
    """Interactive Telegram configuration setup"""
    print("\n" + "=" * 50)
    print("Telegram Configuration Setup")
    print("=" * 50 + "\n")

    tg_config = load_telegram_config()

    enabled = input(f"Enable Telegram reminders? [y/N]: ").strip().lower() == 'y'
    tg_config['enabled'] = enabled
    tg_config['bot_token'] = input(f"Bot Token [{tg_config.get('bot_token','')}]: ") or tg_config.get('bot_token','')
    tg_config['message_prefix'] = input(f"Message Prefix [{tg_config.get('message_prefix','⏰ Reminder:')}]: ") or tg_config.get('message_prefix','⏰ Reminder:')

    save_telegram_config(tg_config)
    print("\n✅ Telegram configuration saved!")
    print("\nTip: Add employee Telegram chat IDs in config.json -> employee_telegram_chat_ids (aligned to employee_emails).")

def test_reminder_now():
    """Test reminder functionality immediately"""
    print("\n" + "=" * 50)
    print("Testing Reminder Functionality")
    print("=" * 50 + "\n")
    
    check_and_send_reminders()
    
    print("\n✅ Test completed! Check the logs for details.")

# ==================== Main Entry Point ====================

def main():
    """Main entry point"""
    import sys
    
    # Check if required libraries are installed
    try:
        import pandas as pd
        import schedule
    except ImportError as e:
        print(f"❌ Required library not installed: {e}")
        print("\nPlease install:")
        print("pip install pandas schedule openpyxl")
        return
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            setup_email_config()
        elif command == "setup_whatsapp":
            setup_whatsapp_config()
        elif command == "setup_telegram":
            setup_telegram_config()
        elif command == "test":
            test_reminder_now()
        elif command == "run":
            schedule_reminders()
        else:
            print("Unknown command. Use: setup, test, or run")
    else:
        print("\nEmployee Progress Tracker - Reminder Service")
        print("=" * 50)
        print("\nCommands:")
        print("  python reminder_service.py setup  - Configure email settings")
        print("  python reminder_service.py setup_whatsapp - Configure WhatsApp settings")
        print("  python reminder_service.py setup_telegram - Configure Telegram settings")
        print("  python reminder_service.py test   - Test reminder functionality now")
        print("  python reminder_service.py run    - Start reminder service")
        print("\n")

if __name__ == "__main__":
    main()