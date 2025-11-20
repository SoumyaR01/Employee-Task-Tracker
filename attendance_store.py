import csv
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
EMP_FILE = os.path.join(BASE_DIR, "employees.json")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance_records.csv")

def ensure_files():
    # Ensure attendance CSV exists with header
    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["emp_id", "status", "timestamp", "check_in_time", "notes"]) 
    # Ensure employees json exists (may be created by Attendance module)
    if not os.path.exists(EMP_FILE):
        with open(EMP_FILE, "w", encoding='utf-8') as f:
            json.dump({}, f)

def append_attendance(emp_id, status, notes=""):
    ensure_files()
    timestamp = datetime.now().isoformat()
    check_in_time = datetime.now().strftime('%H:%M:%S') if status in ["WFO", "WFH"] else ""
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
            return json.load(f)
    except Exception:
        return {}
