import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
import os
import logging
import re
from openpyxl import load_workbook

# Constants
EXCEL_FILE_PATH = r'D:\Employee Track Report\task_tracker.xlsx'
CONFIG_FILE = 'config.json'
DATA_COLUMNS = [
    'Date',
    'Work Mode',
    'Emp Id',
    'Name',
    'Project Name',
    'Task Title',
    'Task Assigned By',
    'Task Priority',
    'Task Status',
    'Plan for next day',
    'Comments',
    'Employee Performance (%)'
]
SUMMARY_SHEET_NAME = '📈 Employee Progress Dashboard'
PERFORMANCE_SHEET_NAME = 'Employee Performance'
EMPLOYEE_SHEET_SUFFIX = ' Dashboard'


def sanitize_sheet_name(name: str) -> str:
    """Return a workbook-safe base sheet name (<=31 chars, invalid chars removed)."""
    safe = re.sub(r'[\\/*?:\[\]]', '_', str(name)).strip()
    if not safe:
        safe = 'Unnamed'
    return safe[:31]


def build_employee_sheet_name(base_name: str, used_names: set[str]) -> str:
    """Construct a unique sheet name for an employee while respecting Excel limits."""
    suffix = EMPLOYEE_SHEET_SUFFIX
    max_base_len = max(0, 31 - len(suffix))
    trimmed_base = base_name[:max_base_len] if max_base_len else base_name[:31]
    candidate = f"{trimmed_base}{suffix}"
    counter = 2
    while candidate in used_names:
        extra = f" {counter}"
        counter += 1
        allowed_len = max(0, 31 - len(suffix) - len(extra))
        trimmed_base = base_name[:allowed_len] if allowed_len else ''
        fallback = trimmed_base if trimmed_base else 'Employee'
        candidate = f"{fallback}{extra}{suffix}"
    used_names.add(candidate)
    return candidate


def ensure_performance_column(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee the performance column exists and is numeric."""
    df = df.copy()
    if 'Employee Performance (%)' not in df.columns:
        df['Employee Performance (%)'] = 0.0
    df['Employee Performance (%)'] = (
        pd.to_numeric(df['Employee Performance (%)'], errors='coerce')
        .fillna(0.0)
        .astype(float)
    )
    return df


def update_dashboard_sheets(excel_path: str, full_df: pd.DataFrame) -> None:
    """Regenerate the summary and individual employee dashboard sheets."""
    if full_df is None or full_df.empty:
        logging.info("Skipping dashboard sheet update because there is no data.")
        return

    if 'Name' not in full_df.columns:
        logging.warning("Cannot build dashboard sheets because 'Name' column is missing.")
        return

    try:
        full_df = ensure_performance_column(full_df)
        if 'Date' in full_df.columns:
            full_df['Date'] = pd.to_datetime(full_df['Date'], errors='coerce')
    except Exception as parse_error:
        logging.error(f"Failed to normalise data for dashboard sheets: {parse_error}")
        return

    try:
        book = load_workbook(excel_path)
    except Exception as workbook_error:
        logging.error(f"Unable to open workbook '{excel_path}' to update dashboard sheets: {workbook_error}")
        return

    # Clean up existing dashboard-related sheets
    all_sheetnames = list(book.sheetnames)
    for sheet_name in all_sheetnames:
        if sheet_name == SUMMARY_SHEET_NAME:
            del book[sheet_name]
        elif sheet_name == PERFORMANCE_SHEET_NAME:
            del book[sheet_name]
        elif sheet_name.endswith(EMPLOYEE_SHEET_SUFFIX) and sheet_name != SUMMARY_SHEET_NAME:
            del book[sheet_name]

    # Prepare data for summary
    summary_records = []
    unique_names = (
        full_df['Name']
        .dropna()
        .astype(str)
        .str.strip()
    )
    unique_names = [name for name in unique_names.unique() if name]

    for name in unique_names:
        emp_mask = full_df['Name'].astype(str).str.strip() == name
        emp_data = full_df[emp_mask]
        total_tasks = len(emp_data)
        if 'Task Status' in emp_data.columns:
            completed_tasks = int((emp_data['Task Status'] == 'Completed').sum())
        else:
            completed_tasks = 0
        pending_tasks = max(total_tasks - completed_tasks, 0)
        completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks else 0.0, 2)
        avg_perf = round(emp_data['Employee Performance (%)'].mean(), 2)
        last_update = None
        if 'Date' in emp_data.columns and not emp_data['Date'].dropna().empty:
            last_update = emp_data['Date'].dropna().max()

        summary_records.append({
            'name': name,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'completion_rate': completion_rate,
            'avg_performance': avg_perf,
            'last_update': last_update
        })

    # Sort by average performance descending, then by completion rate
    summary_records.sort(key=lambda record: (record['avg_performance'], record['completion_rate']), reverse=True)

    ws_summary = book.create_sheet(SUMMARY_SHEET_NAME)
    summary_headers = [
        'Employee Name',
        'Total Tasks',
        'Completed Tasks',
        'Pending Tasks',
        'Completion Rate (%)',
        'Employee Performance (%)',
        'Last Update',
        'Individual Dashboard'
    ]
    for col_idx, header in enumerate(summary_headers, start=1):
        ws_summary.cell(row=1, column=col_idx, value=header)

    ws_summary.freeze_panes = "A2"
    col_widths = [28, 14, 16, 14, 20, 20, 16, 24]
    for idx, width in enumerate(col_widths, start=1):
        column_letter = ws_summary.cell(row=1, column=idx).column_letter
        ws_summary.column_dimensions[column_letter].width = width

    used_sheet_names: set[str] = set(book.sheetnames)
    data_start_row = 2

    for offset, record in enumerate(summary_records):
        row_idx = data_start_row + offset
        ws_summary.cell(row=row_idx, column=1, value=record['name'])
        ws_summary.cell(row=row_idx, column=2, value=record['total_tasks'])
        ws_summary.cell(row=row_idx, column=3, value=record['completed_tasks'])
        ws_summary.cell(row=row_idx, column=4, value=record['pending_tasks'])
        ws_summary.cell(row=row_idx, column=5, value=record['completion_rate'])
        ws_summary.cell(row=row_idx, column=6, value=record['avg_performance'])
        last_update_value = ""
        if record['last_update'] is not None and not pd.isna(record['last_update']):
            if isinstance(record['last_update'], pd.Timestamp):
                last_update_value = record['last_update'].date().isoformat()
            else:
                last_update_value = str(record['last_update'])
        ws_summary.cell(row=row_idx, column=7, value=last_update_value)

        base_name = sanitize_sheet_name(record['name'])
        employee_sheet_name = build_employee_sheet_name(base_name, used_sheet_names)
        hyperlink_formula = f'=HYPERLINK("#\'{employee_sheet_name}\'!A1", "View Dashboard")'
        ws_summary.cell(row=row_idx, column=8).value = hyperlink_formula

        # Build individual employee sheet
        ws_emp = book.create_sheet(employee_sheet_name)
        ws_emp.freeze_panes = "A8"

        ws_emp.cell(row=1, column=1, value=f"Employee Dashboard")
        ws_emp.cell(row=2, column=1, value="Employee Name")
        ws_emp.cell(row=2, column=2, value=record['name'])
        ws_emp.cell(row=3, column=1, value="Total Tasks")
        ws_emp.cell(row=3, column=2, value=record['total_tasks'])
        ws_emp.cell(row=4, column=1, value="Completed Tasks")
        ws_emp.cell(row=4, column=2, value=record['completed_tasks'])
        ws_emp.cell(row=5, column=1, value="Pending Tasks")
        ws_emp.cell(row=5, column=2, value=record['pending_tasks'])
        ws_emp.cell(row=6, column=1, value="Completion Rate (%)")
        ws_emp.cell(row=6, column=2, value=record['completion_rate'])
        ws_emp.cell(row=7, column=1, value="Avg Performance (%)")
        ws_emp.cell(row=7, column=2, value=record['avg_performance'])
        ws_emp.cell(row=2, column=4, value="Last Update")
        ws_emp.cell(row=2, column=5, value=last_update_value)
        ws_emp.cell(row=3, column=4, value="Back to Dashboard")
        ws_emp.cell(row=3, column=5).value = f'=HYPERLINK("#\'{SUMMARY_SHEET_NAME}\'!A1", "View All Employees")'

        ws_emp.cell(row=9, column=1, value="Task Details")
        header_row = 10
        detail_start_row = header_row + 1

        emp_details = full_df[emp_mask].copy()
        emp_details = emp_details.sort_values(by='Date') if 'Date' in emp_details.columns else emp_details
        for col_idx, col_name in enumerate(DATA_COLUMNS, start=1):
            ws_emp.cell(row=header_row, column=col_idx, value=col_name)

        for row_offset, (_, detail_row) in enumerate(emp_details.iterrows()):
            excel_row_idx = detail_start_row + row_offset
            for col_idx, col_name in enumerate(DATA_COLUMNS, start=1):
                cell_value = detail_row.get(col_name)
                if pd.isna(cell_value):
                    cell_value = ""
                elif isinstance(cell_value, pd.Timestamp):
                    cell_value = cell_value.date()
                ws_emp.cell(row=excel_row_idx, column=col_idx, value=cell_value)

        for col_idx in range(1, len(DATA_COLUMNS) + 1):
            column_letter = ws_emp.cell(row=header_row, column=col_idx).column_letter
            ws_emp.column_dimensions[column_letter].width = 18

    if summary_records:
        ws_summary.auto_filter.ref = f"A1:H{data_start_row + len(summary_records) - 1}"
        ws_perf = book.create_sheet(PERFORMANCE_SHEET_NAME)
        perf_headers = [
            'Rank',
            'Employee Name',
            'Total Tasks',
            'Completed Tasks',
            'Completion Rate (%)',
            'Employee Performance (%)',
            'Last Update',
            'Dashboard Link'
        ]
        perf_col_widths = [8, 28, 14, 16, 20, 20, 16, 24]
        for col_idx, header in enumerate(perf_headers, start=1):
            ws_perf.cell(row=1, column=col_idx, value=header)
            column_letter = ws_perf.cell(row=1, column=col_idx).column_letter
            width = perf_col_widths[col_idx - 1] if col_idx - 1 < len(perf_col_widths) else 18
            ws_perf.column_dimensions[column_letter].width = width
        ws_perf.freeze_panes = "A2"

        for rank, record in enumerate(summary_records, start=1):
            row_idx = rank + 1
            ws_perf.cell(row=row_idx, column=1, value=rank)
            ws_perf.cell(row=row_idx, column=2, value=record['name'])
            ws_perf.cell(row=row_idx, column=3, value=record['total_tasks'])
            ws_perf.cell(row=row_idx, column=4, value=record['completed_tasks'])
            ws_perf.cell(row=row_idx, column=5, value=record['completion_rate'])
            ws_perf.cell(row=row_idx, column=6, value=record['avg_performance'])
            last_update_value = ws_summary.cell(data_start_row + rank - 1, column=7).value
            ws_perf.cell(row=row_idx, column=7, value=last_update_value)
            ws_perf.cell(row=row_idx, column=8).value = f'=HYPERLINK("#\'{SUMMARY_SHEET_NAME}\'!A{data_start_row + rank - 1}", "Open Dashboard")'

        ws_perf.auto_filter.ref = f"A1:H{len(summary_records) + 1}"

    try:
        book.save(excel_path)
    except Exception as save_error:
        logging.error(f"Failed to save workbook with updated dashboard sheets: {save_error}")


def load_config():
    """Load configuration from file"""
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'excel_file_path': EXCEL_FILE_PATH,
        'logo_path': '/home/pinku/PTF Track/logo/PTF1.png',
        'reminder_time': '18:00',
        'reminder_days': [0, 1, 2, 3, 4, 5],  # Mon-Sat
        'admin_email': '',
        'employee_emails': []
    }


def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def read_excel_data(excel_path=None):
    """Read data from local Excel file"""
    if excel_path is None:
        excel_path = EXCEL_FILE_PATH
    
    try:
        if not os.path.exists(excel_path):
            # Create empty Excel file with headers if it doesn't exist
            df = pd.DataFrame(columns=DATA_COLUMNS)
            df.to_excel(excel_path, index=False, engine='openpyxl')
            return df
        
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Handle empty file
        if df.empty:
            return pd.DataFrame()
        
        # Ensure 'Employee Performance (%)' column exists
        return ensure_performance_column(df)
    
    except Exception as error:
        logging.error(f"Error reading Excel file: {error}")
        return None


def append_to_excel(data_list, excel_path=None):
    """Append data to local Excel file with retry logic for concurrent access
    Args:
        data_list: List of dictionaries, each representing a row to append
    """
    if excel_path is None:
        excel_path = EXCEL_FILE_PATH
    
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # Check if file exists and is accessible
            if os.path.exists(excel_path):
                # Try to check if file is locked by attempting to open it
                try:
                    # Try to read the file first to check if it's locked
                    existing_df = pd.read_excel(excel_path, engine='openpyxl')
                    # Remove any completely empty rows
                    existing_df = existing_df.dropna(how='all')
                except PermissionError as pe:
                    if attempt < max_retries - 1:
                        logging.warning(f"Permission error on attempt {attempt + 1}, retrying...")
                        import time
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logging.error(f"Permission Error: Excel file is locked or inaccessible: {pe}")
                        return False
                except Exception as e:
                    # If file is corrupted or empty, start fresh
                    logging.warning(f"Error reading file, starting fresh: {e}")
                    existing_df = pd.DataFrame()
            else:
                existing_df = pd.DataFrame()
            
            # Create new rows DataFrame
            new_rows = pd.DataFrame(data_list)
            
            # Define column order
            columns = DATA_COLUMNS
            
            # Combine with existing data
            if existing_df.empty:
                for col in columns:
                    if col not in new_rows.columns:
                        new_rows[col] = 0.0 if col == 'Employee Performance (%)' else ''
                combined_df = new_rows[columns]
            else:
                # Ensure column order matches
                # Add missing columns if any
                for col in columns:
                    if col not in existing_df.columns:
                        existing_df[col] = 0.0 if col == 'Employee Performance (%)' else ''
                    if col not in new_rows.columns:
                        new_rows[col] = 0.0 if col == 'Employee Performance (%)' else ''
                
                # Reorder columns
                existing_df = existing_df[columns]
                new_rows = new_rows[columns]
                
                combined_df = pd.concat([existing_df, new_rows], ignore_index=True)
            
            # Ensure all columns are in the right order
            if not existing_df.empty:
                combined_df = combined_df[columns]
            combined_df = ensure_performance_column(combined_df)
            
            # Write to Excel
            try:
                with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                    combined_df.to_excel(writer, index=False, sheet_name='Sheet1')
            except PermissionError as pe:
                if attempt < max_retries - 1:
                    logging.warning(f"Permission error writing file on attempt {attempt + 1}, retrying...")
                    import time
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logging.error(f"Permission Error: Cannot write to Excel file: {pe}")
                    return False
            except Exception as write_error:
                if attempt < max_retries - 1:
                    logging.warning(f"Write error on attempt {attempt + 1}, retrying...")
                    import time
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logging.error(f"Error writing to Excel file: {write_error}")
                    return False

            # Update dashboard sheets after successful main sheet write
            try:
                update_dashboard_sheets(excel_path, combined_df)
            except Exception as dash_error:
                logging.error(f"Failed to update dashboard sheets: {dash_error}")
                # Continue without failing the main append
            
            return True
        
        except PermissionError as pe:
            # File might be locked by another process
            if attempt < max_retries - 1:
                logging.warning(f"Permission error on attempt {attempt + 1}, retrying...")
                import time
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                logging.error(f"Permission Error: Excel file is locked or inaccessible: {pe}")
                return False
        
        except Exception as error:
            if attempt < max_retries - 1:
                logging.warning(f"Error on attempt {attempt + 1}, retrying... Error: {str(error)}")
                import time
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                logging.error(f"Error appending to Excel file: {error}")
                return False
    
    return False


def get_missing_reporters(df, today):
    """Get list of employees who haven't reported today"""
    if df is None or df.empty:
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
        submitted_employees = []

    # Get all employees from config
    config = load_config()
    all_employees = config.get('employee_emails', [])

    # Find missing reporters
    missing = [emp for emp in all_employees if emp not in submitted_employees]

    return missing


# Streamlit entry point wrapper - redirects to app.py
# Note: Best practice is to set main file to app.py in Streamlit Community Cloud settings
# This wrapper allows main.py to work as an entry point by importing and running app.py

# Import and run the Streamlit app from app.py when this file is executed
try:
    from app import main as app_main
    # Execute the app - Streamlit will run this when main.py is the entry point
    app_main()
except ImportError as e:
    # Show error in Streamlit if available
    try:
        import streamlit as st
        st.error(f"❌ Error importing app.py: {e}")
        st.info("💡 Please ensure app.py exists in the same directory as main.py")
        st.info("💡 Alternatively, change the main file to app.py in Streamlit Community Cloud settings")
    except ImportError:
        # Streamlit not available, just print error (for local testing)
        print(f"Error importing app.py: {e}")
        print("Please ensure app.py exists in the same directory as main.py")