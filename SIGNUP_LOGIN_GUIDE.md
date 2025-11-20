# Employee Attendance & Task Tracker - Signup & Login Guide

## Overview
The system now includes a complete signup and login flow with credential validation. Employees can either create a new account or use demo credentials to log in.

## Getting Started

### 1. Running the Main Application
```bash
streamlit run main.py
```

### 2. Demo Credentials (Pre-seeded)
New users can log in with the following demo credentials:

| Office ID | Password | Name | Department | Role |
|-----------|----------|------|-----------|------|
| EMP001 | pass123 | John Doe | Engineering | Developer |
| EMP002 | pass123 | Jane Smith | Marketing | Manager |
| EMP003 | pass123 | Bob Johnson | Sales | Executive |
| EMP004 | pass123 | Alice Williams | HR | Specialist |
| EMP005 | pass123 | Charlie Brown | Engineering | Senior Developer |

### 3. Creating a New Account
1. On the login page, click **"Create Account"** button
2. Fill in the following fields:
   - **Office ID**: Unique identifier (required) - e.g., `EMP006`
   - **Full Name**: Your name (required) - e.g., `Sarah Johnson`
   - **Email**: Your email (optional) - e.g., `sarah@company.com`
   - **Department**: Your department (optional) - e.g., `Finance`
   - **Role**: Your role (optional) - e.g., `Analyst`
   - **Password**: Strong password (required, min 6 characters)
   - **Confirm Password**: Repeat your password (must match)
3. Click **"Create Account"**
4. Once successful, you'll be redirected to login page
5. Log in with your new Office ID and password

### 4. After Successful Login
Once logged in, you'll see the sidebar with your name and Employee ID. You can access:

- **Daily Check-in**: Mark your attendance for the day
  - Options: Work from Home, Work in Office, On Leave
  - Add optional notes
  
- **Submit Report**: File your daily task report
  - Pre-filled with your logged-in employee info
  
- **Dashboard**: View overall productivity insights
  
- **Settings**: Configure system settings
  
- **Reminders**: Set up email reminders for missing reports

### 5. Daily Check-in Workflow
1. Navigate to **"Daily Check-in"** tab
2. Select your work status for the day:
   - 🏢 Work in Office
   - 🏠 Work from Home
   - 📋 On Leave
3. Add optional notes (e.g., WFH due to weather)
4. Click **"Check In"**
5. ✅ Confirmation message will appear

### 6. Attendance Records
- All attendance records are saved to `attendance_records.csv`
- Records are synced across the main app and Attendance.py dashboard
- Each record includes: emp_id, status, timestamp, check_in_time, notes

## Error Messages & Solutions

### "Invalid Office ID or Password"
- **Cause**: Incorrect Office ID or password
- **Solution**: Double-check both fields and try again. Remember passwords are case-sensitive.

### "Office ID already exists"
- **Cause**: Trying to create an account with an existing Office ID
- **Solution**: Use a different Office ID or log in if you already have an account.

### "Passwords do not match"
- **Cause**: Password confirmation doesn't match the password field
- **Solution**: Re-enter passwords carefully and ensure they match.

### "Password must be at least 6 characters long"
- **Cause**: Password is too short
- **Solution**: Create a password with at least 6 characters.

## Data Storage

### employees.json
- Location: `/home/pinku/PTF Track/employees.json`
- Contains: Employee accounts with hashed passwords
- Auto-created on first run with demo credentials

### attendance_records.csv
- Location: `/home/pinku/PTF Track/attendance_records.csv`
- Contains: Daily check-in records for all employees
- Columns: emp_id, status, timestamp, check_in_time, notes

## Features Implemented

✅ **User Authentication**
- Secure password hashing (SHA-256)
- Login with Office ID and Password

✅ **Account Management**
- Create new employee accounts
- Validate unique Office IDs
- Password confirmation & minimum length validation

✅ **Session Management**
- Track logged-in user state
- Display user info in sidebar
- Logout functionality

✅ **Daily Check-in**
- Mark work status (WFO, WFH, On Leave)
- Optional notes field
- Real-time attendance recording

✅ **Attendance Dashboard** (Attendance.py)
- View all employees by status
- Real-time synchronization with check-ins

✅ **Cross-app Integration**
- Both main.py and Attendance.py share employee/attendance data
- Persistent storage via CSV and JSON

## Troubleshooting

**Issue**: Demo credentials don't work
- **Solution**: Check if `employees.json` exists. If deleted, run the app once to regenerate it.

**Issue**: Check-in not showing in Attendance.py dashboard
- **Solution**: Refresh the Attendance.py app to load latest records from CSV.

**Issue**: Password authentication failing for existing accounts
- **Solution**: Passwords are hashed. If you need to reset, delete `employees.json` to regenerate with demo accounts.

## Security Notes

- Passwords are hashed using SHA-256 before storage
- Never stored or transmitted in plain text
- For production use, consider:
  - Using bcrypt or argon2 instead of SHA-256
  - Adding 2FA (Two-Factor Authentication)
  - Using HTTPS/TLS for data transmission
  - Regular security audits

---

For more information, see the main README.md and documentation.md files.
