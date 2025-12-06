"""
Test and demonstrate the enhanced missing reporter detection logic
Run this to see how the improved detection works
"""

from missing_reporters import (
    load_all_employees,
    get_missing_reporters_detailed,
    print_missing_reporters_table
)
import pandas as pd
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_missing_reporters():
    """Test the improved missing reporter detection"""
    print("\n" + "="*80)
    print("🔍 TESTING ENHANCED MISSING REPORTER DETECTION")
    print("="*80 + "\n")
    
    try:
        # Load employee data
        print("📂 Loading employees from employees.json...")
        employees = load_all_employees()
        print(f"✅ Loaded {len(employees)} employees (excluding admins)\n")
        
        # Display all employees
        print("👥 ALL EMPLOYEES:")
        print("-"*80)
        print(f"{'Emp ID':<15} | {'Name':<30} | {'Email':<30}")
        print("-"*80)
        for email, emp in employees.items():
            print(f"{emp['emp_id']:<15} | {emp['name']:<30} | {emp['email']:<30}")
        print("-"*80 + "\n")
        
        # Load Excel data
        print("📊 Loading reports from task_tracker.xlsx...")
        df = pd.read_excel('task_tracker.xlsx')
        print(f"✅ Loaded {len(df)} total report entries\n")
        
        # Get today's date
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        print(f"📅 Checking reports for: {today_str}\n")
        
        # Check for today's submissions
        df_copy = df.copy()
        df_copy['Date'] = pd.to_datetime(df_copy['Date'], errors='coerce')
        df_copy['Date_str'] = df_copy['Date'].dt.strftime('%Y-%m-%d')
        today_submissions = df_copy[df_copy['Date_str'] == today_str]
        
        if not today_submissions.empty:
            print(f"📋 TODAY'S SUBMISSIONS ({len(today_submissions)} entries):")
            print("-"*80)
            # Show columns that exist
            cols_to_show = []
            for possible_col in ['Employee ID', 'Emp ID', 'Name', 'Employee Name', 'Date']:
                if possible_col in today_submissions.columns:
                    cols_to_show.append(possible_col)
            
            if cols_to_show:
                print(today_submissions[cols_to_show].to_string(index=False))
            else:
                print(today_submissions.head().to_string())
            print("-"*80 + "\n")
        else:
            print("⚠️  No submissions found for today\n")
        
        # Find missing reporters
        print("🔍 Identifying missing reporters...\n")
        missing = get_missing_reporters_detailed(df, today)
        
        # Display results
        print_missing_reporters_table(missing)
        
        # Summary
        print("\n" + "="*80)
        print("📊 SUMMARY")
        print("="*80)
        print(f"Total employees: {len(employees)}")
        print(f"Submitted today: {len(employees) - len(missing)}")
        print(f"Missing reports: {len(missing)}")
        print(f"Submission rate: {((len(employees) - len(missing)) / len(employees) * 100):.1f}%")
        print("="*80 + "\n")
        
        # Return results for potential use
        return missing
        
    except FileNotFoundError as e:
        print(f"❌ Error: Required file not found - {e}")
        print("\nMake sure you have:")
        print("  - employees.json")
        print("  - task_tracker.xlsx")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    missing_reporters = test_missing_reporters()
    
    if missing_reporters:
        print("\n💡 TIP: These employees will receive reminder notifications")
        print("    Run: python reminder_service.py test")
        print("    to send test reminders now.\n")
