"""
Enhanced Missing Reporter Detection Module
Provides improved logic for identifying employees who haven't submitted reports
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging


def load_all_employees():
    """Load all employees from employees.json with their complete information
    
    Returns:
        dict: Dictionary with email as key and employee details as value
              Format: {'email': {'emp_id': str, 'name': str, 'email': str, 'department': str, 'role': str}}
    """
    try:
        employees_file = Path('employees.json')
        if not employees_file.exists():
            logging.error("employees.json not found")
            return {}
        
        with open(employees_file, 'r') as f:
            employees_data = json.load(f)
        
        # Convert to dict with email as key for easier matching
        employees = {}
        for emp_id, emp_info in employees_data.items():
            # Exclude admin accounts from reminders
            if emp_info.get('role', '').lower() != 'admin':
                email = emp_info.get('email', '').lower()
                employees[email] = {
                    'emp_id': emp_id,
                    'name': emp_info.get('name', ''),
                    'email': emp_info.get('email', ''),
                    'department': emp_info.get('department', ''),
                    'role': emp_info.get('role', '')
                }
        
        return employees
    except Exception as e:
        logging.error(f"Error loading employees: {e}")
        return {}


def get_missing_reporters_detailed(df, today):
    """Get list of employees who haven't reported today with complete details
    
    Args:
        df (DataFrame): Report submission data from Excel
        today (datetime): Today's date
    
    Returns:
        list: List of dictionaries containing employee details:
              [{'emp_id': str, 'name': str, 'email': str, 'department': str, 'role': str}, ...]
    """
    if df is None or df.empty:
        logging.warning("No data available")
        return []

    today_str = today.strftime('%Y-%m-%d')
    
    # Load all employees from employees.json
    all_employees = load_all_employees()
    if not all_employees:
        logging.warning("No employees found in employees.json")
        return []
    
    # Get list of employees who submitted today
    submitted_emails = set()
    
    if 'Date' in df.columns:
        # Create a copy and filter for today's date
        df_copy = df.copy()
        df_copy['Date'] = pd.to_datetime(df_copy['Date'], errors='coerce')
        df_copy = df_copy.dropna(subset=['Date'])
        df_copy['Date_str'] = df_copy['Date'].dt.strftime('%Y-%m-%d')
        
        today_submissions = df_copy[df_copy['Date_str'] == today_str]
        
        if today_submissions.empty:
            logging.info(f"No submissions found for {today_str}")
        else:
            logging.info(f"Found {len(today_submissions)} submissions for {today_str}")
        
        # Try to extract emails from submissions
        # Check multiple possible column names for employee identification
        # Note: Excel uses 'Emp Id' (with space), not 'Employee ID'
        possible_id_columns = ['Emp Id', 'Employee ID', 'Emp ID', 'ID', 'EmpID', 'emp_id', 'EmployeeID']
        possible_name_columns = ['Name', 'Employee Name', 'Employee', 'Emp Name', 'EmployeeName']
        
        # Method 1: Match by Employee ID (most reliable)
        matched_by_id = False
        for col in possible_id_columns:
            if col in today_submissions.columns:
                submitted_ids = today_submissions[col].dropna().astype(str).unique()
                logging.info(f"Matching by column '{col}': found {len(submitted_ids)} IDs")
                for emp_email, emp_data in all_employees.items():
                    if str(emp_data['emp_id']).upper() in [str(sid).upper() for sid in submitted_ids]:
                        submitted_emails.add(emp_email)
                        logging.debug(f"Matched {emp_data['name']} by ID: {emp_data['emp_id']}")
                matched_by_id = True
                break
        
        # Method 2: Match by Name (if ID matching didn't work or found nothing)
        if not matched_by_id or not submitted_emails:
            for col in possible_name_columns:
                if col in today_submissions.columns:
                    submitted_names = today_submissions[col].dropna().unique()
                    logging.info(f"Matching by column '{col}': found {len(submitted_names)} names")
                    for emp_email, emp_data in all_employees.items():
                        emp_name = emp_data['name'].lower().strip()
                        for submitted_name in submitted_names:
                            if isinstance(submitted_name, str):
                                submitted_name_lower = submitted_name.lower().strip()
                                # Exact match or contains match
                                if (emp_name == submitted_name_lower or 
                                    emp_name in submitted_name_lower or 
                                    submitted_name_lower in emp_name):
                                    submitted_emails.add(emp_email)
                                    logging.debug(f"Matched {emp_data['name']} by name: {submitted_name}")
                                    break
                    if submitted_emails:
                        break
    else:
        logging.warning("Date column not found in data")
    
    # Find missing reporters - employees who didn't submit
    missing_reporters = []
    for emp_email, emp_data in all_employees.items():
        if emp_email not in submitted_emails:
            missing_reporters.append({
                'emp_id': emp_data['emp_id'],
                'name': emp_data['name'],
                'email': emp_data['email'],
                'department': emp_data['department'],
                'role': emp_data['role']
            })
    
    # Log the results
    logging.info(f"\n{'='*60}")
    logging.info(f"📊 MISSING REPORTERS SUMMARY")
    logging.info(f"{'='*60}")
    logging.info(f"Total employees (non-admin): {len(all_employees)}")
    logging.info(f"Submitted reports today: {len(submitted_emails)}")
    logging.info(f"Missing reporters: {len(missing_reporters)}")
    logging.info(f"{'='*60}")
    
    if missing_reporters:
        logging.info(f"\n📋 PENDING EMPLOYEES:")
        logging.info(f"{'-'*60}")
        logging.info(f"{'Emp ID':<12} | {'Name':<25} | {'Email'}")
        logging.info(f"{'-'*60}")
        for emp in missing_reporters:
            logging.info(f"{emp['emp_id']:<12} | {emp['name']:<25} | {emp['email']}")
        logging.info(f"{'-'*60}\n")
    else:
        logging.info("✅ All employees have submitted their reports!\n")
    
    return missing_reporters


def print_missing_reporters_table(missing_reporters):
    """Print a formatted table of missing reporters to console
    
    Args:
        missing_reporters (list): List of employee dictionaries
    """
    if not missing_reporters:
        print("\n✅ All employees have submitted their reports!")
        return
    
    print(f"\n📋 EMPLOYEES WHO HAVEN'T SUBMITTED REPORTS")
    print(f"{'='*80}")
    print(f"{'Emp ID':<15} | {'Name':<30} | {'Email':<30}")
    print(f"{'-'*80}")
    
    for emp in missing_reporters:
        print(f"{emp['emp_id']:<15} | {emp['name']:<30} | {emp['email']:<30}")
    
    print(f"{'='*80}")
    print(f"Total missing: {len(missing_reporters)}\n")


# For backward compatibility, create wrapper that returns old format
def get_missing_reporters_emails_only(df, today):
    """Legacy function that returns only emails (for compatibility)
    
    Args:
        df (DataFrame): Report data
        today (datetime): Today's date
    
    Returns:
        list: List of email addresses
    """
    detailed = get_missing_reporters_detailed(df, today)
    return [emp['email'] for emp in detailed]


if __name__ == "__main__":
    # Test the logic
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Missing Reporter Detection")
    print("="*80)
    
    # Load sample data
    try:
        df = pd.read_excel('task_tracker.xlsx')
        today = datetime.now()
        
        missing = get_missing_reporters_detailed(df, today)
        print_missing_reporters_table(missing)
        
    except Exception as e:
        print(f"Error: {e}")
