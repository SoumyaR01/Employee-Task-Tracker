import csv
import json
import os
from datetime import datetime
import hashlib

BASE_DIR = os.path.dirname(__file__)
EMP_FILE = os.path.join(BASE_DIR, "employees.json")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance_records.csv")

DEMO_IDS = {"EMP001", "EMP002", "EMP003", "EMP004", "EMP005"}

def ensure_files():
    # Ensure attendance CSV exists with header
    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["emp_id", "status", "timestamp", "check_in_time", "notes"]) 
    # Ensure employees json exists (start empty)
    if not os.path.exists(EMP_FILE):
        with open(EMP_FILE, "w", encoding='utf-8') as f:
            json.dump({}, f, indent=2)

def append_attendance(emp_id, status, notes="", client_time=None):
    """
    Append an attendance record.
    - `timestamp` is always the server-side ISO timestamp (for audit).
    - `check_in_time` stores the actual check-in time in ISO format for accurate display.
    """
    ensure_files()
    now = datetime.now()
    timestamp = now.isoformat()
    
    # Store check_in_time in ISO format so it can be parsed correctly later
    if client_time:
        check_in_time = client_time
    else:
        check_in_time = now.isoformat()  # Changed from strftime to isoformat
    
    with open(ATTENDANCE_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([emp_id, status, timestamp, check_in_time, notes])

def load_attendance():
    ensure_files()
    records = []
    with open(ATTENDANCE_FILE, "r", encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Keep timestamp as ISO string; consumers can parse when needed
            records.append({
                "emp_id": row.get("emp_id"),
                "status": row.get("status"),
                "timestamp": row.get("timestamp"),
                "check_in_time": row.get("check_in_time") or None,
                "notes": row.get("notes") or "",
            })
    return records

def save_employees(employees_dict):
    # employees_dict expected to be a mapping emp_id -> info (including hashed password)
    ensure_files()
    with open(EMP_FILE, "w", encoding='utf-8') as f:
        json.dump(employees_dict, f, default=str, indent=2)

def load_employees():
    ensure_files()
    try:
        with open(EMP_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            # Remove any pre-seeded demo IDs if present
            if not isinstance(data, dict):
                data = {}
            removed = False
            for did in list(DEMO_IDS):
                if did in data:
                    data.pop(did, None)
                    removed = True
            if removed:
                # persist cleaned file
                try:
                    with open(EMP_FILE, "w", encoding='utf-8') as wf:
                        json.dump(data, wf, indent=2)
                except Exception:
                    pass
            return data
    except Exception:
        return {}

def verify_login(emp_id, password):
    """
    Verify employee login credentials.
    Returns (success: bool, name: str or None, role: str or None)
    """
    employees = load_employees()
    emp = employees.get(emp_id.upper())
    if emp:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        if emp.get("password") == hashed_pw:
            return True, emp.get("name"), emp.get("role")
    return False, None, None

def check_employee_exists(emp_id):
    """Check if employee with given ID already exists"""
    employees = load_employees()
    return emp_id.upper() in employees

def check_already_checked_in_today(emp_id):
    """
    Check if an employee has already checked in today (same calendar day).
    Returns True if already checked in, False otherwise.
    """
    records = load_attendance()
    today = datetime.now().date()
    
    for record in records:
        if record.get("emp_id") == emp_id:
            # Parse the timestamp to get the date
            try:
                record_timestamp = record.get("timestamp")
                if record_timestamp:
                    # Handle both ISO format and other formats
                    record_date = datetime.fromisoformat(record_timestamp.replace('Z', '+00:00')).date()
                    if record_date == today:
                        return True
            except Exception:
                pass
    
    return False

def create_employee(emp_id, password, name="", email="", department="", role=""):
    """
    Create a new employee account.
    Returns (success: bool, message: str)
    """
    employees = load_employees()
    emp_id_upper = emp_id.upper()
    
    if emp_id_upper in employees:
        return False, "Employee ID already exists"
    
    if not emp_id or not password or not name:
        return False, "Office ID, Password, and Name are required"
    
    employees[emp_id_upper] = {
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "name": name,
        "email": email,
        "department": department,
        "role": role
    }
    
    try:
        save_employees(employees)
        return True, "Account created successfully"
    except Exception as e:
        return False, f"Failed to create account: {str(e)}"
