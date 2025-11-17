import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path
import time
import os
import logging
import base64
import re
from openpyxl import load_workbook
import io
import zipfile
st.set_page_config(
    page_title="Employee Progress Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Helper function to convert image to base64
def get_base64_image(image_path):
    """Convert image to base64 for CSS background"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

# Custom CSS (dark/black background)
st.markdown("""
<style>
    /* Background styling */
    .stApp {
        background: #000000; /* black */
        background-attachment: fixed;
        color: #e6eef2; /* light default text color for readability */
    }

    /* Subtle pattern overlay (very light) */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
    }

    /* Main content area */
    .main > div {
        padding: 1rem;
        position: relative;
        z-index: 1;
    }

    /* Block container styling (dark) */
    .block-container {
        padding: 2rem 1rem;
        background: rgba(10, 10, 10, 0.75);
        border-radius: 15px;
        backdrop-filter: blur(6px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
        color: #e6eef2; /* ensure text inside blocks is light */
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white !important;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: transform 0.25s ease;
    }

    .metric-card:hover {
        transform: translateY(-4px);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
    }

    .metric-label {
        font-size: 1rem;
        opacity: 0.95;
    }

    /* Filter container (dark) */
    .filter-container {
        background: linear-gradient(180deg, rgba(20,20,20,0.6) 0%, rgba(30,30,30,0.6) 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.6);
        color: #e6eef2;
    }

    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 6px;
        height: 3rem;
        font-weight: 600;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(102, 126, 234, 0.18);
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #4c5bd4 0%, #6b4bb8 100%);
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Input fields (dark theme) */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.12);
        transition: border-color 0.3s ease;
        background: #0f1113;
        color: #e6eef2;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.06);
    }

    /* Logo container styling */
    .logo-container {
        background: transparent;
        padding: 20px;
        border-radius: 15px;
        box-shadow: none;
        margin-bottom: 20px;
        text-align: center;
    }

    /* Constrain logo image size so it doesn't take the entire viewport */
    .logo-container img {
        max-width: 480px;
        width: 100%;
        height: auto;
        display: inline-block;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #1e293b 0%, #111827 100%);
        border-radius: 8px;
        font-weight: 600;
        color: #e6eef2 !important;
    }

    @media (max-width: 768px) {
        .main > div {
            padding: 0.5rem;
        }
        .metric-value {
            font-size: 1.8rem;
        }
        .block-container {
            padding: 1rem 0.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

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
    'Support Request',
    'Availability',
    'Effort (in hours)',
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


def ensure_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee the performance and effort columns exist and are numeric."""
    df = df.copy()
    numeric_cols = ['Employee Performance (%)', 'Effort (in hours)']
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = (
            pd.to_numeric(df[col], errors='coerce')
            .fillna(0.0)
            .astype(float)
        )
    return df


# ==================== PERFORMANCE CALCULATION ====================
def calculate_performance(tasks_list):
    """
    Calculate employee performance using formula:
    Average % = (Sum of Task Priority / Total Effort in Hours) * 100
    
    Priority weights: Low=1, Medium=2, High=3, Critical=4
    """
    if not tasks_list:
        return 0.0
    
    priority_weights = {
        'Low': 1,
        'Medium': 2,
        'High': 3,
        'Critical': 4
    }
    
    total_priority_weight = 0
    total_effort = 0
    
    for task in tasks_list:
        priority = task.get('Task Priority', 'Low')
        try:
            effort = float(task.get('Effort (in hours)', 0))
        except Exception:
            effort = 0.0
        
        weight = priority_weights.get(priority, 1)
        total_priority_weight += weight
        total_effort += effort
    
    if total_effort == 0:
        return 0.0
    
    performance = (total_priority_weight / total_effort) * 100
    return min(round(performance, 2), 100.0)  # Cap at 100%


def update_dashboard_sheets(excel_path: str, full_df: pd.DataFrame) -> None:
    """Regenerate the summary and individual employee dashboard sheets."""
    if full_df is None or full_df.empty:
        logging.info("Skipping dashboard sheet update because there is no data.")
        return

    if 'Name' not in full_df.columns:
        logging.warning("Cannot build dashboard sheets because 'Name' column is missing.")
        return

    try:
        full_df = ensure_numeric_columns(full_df)
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

# Helper Functions

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
        return ensure_numeric_columns(df)
    
    except Exception as error:
        st.error(f"Error reading Excel file: {error}")
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
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        st.error(f"❌ Permission Error: Excel file is locked or inaccessible.")
                        st.error(f"📁 File path: {excel_path}")
                        st.error(f"💡 Please ensure:")
                        st.error(f"   1. The Excel file is not open in Excel or another program")
                        st.error(f"   2. You have write permissions to the file")
                        st.error(f"   3. No other process is using the file")
                        st.error(f"   Error details: {str(pe)}")
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
            combined_df = ensure_numeric_columns(combined_df)
            
            # Write to Excel
            try:
                with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                    combined_df.to_excel(writer, index=False, sheet_name='Sheet1')
            except PermissionError as pe:
                if attempt < max_retries - 1:
                    logging.warning(f"Permission error writing file on attempt {attempt + 1}, retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    st.error(f"❌ Permission Error: Cannot write to Excel file.")
                    st.error(f"📁 File path: {excel_path}")
                    st.error(f"💡 Please ensure:")
                    st.error(f"   1. The Excel file is not open in Excel or another program")
                    st.error(f"   2. You have write permissions to the file and directory")
                    st.error(f"   3. No other process is using the file")
                    st.error(f"   Error details: {str(pe)}")
                    return False
            except Exception as write_error:
                if attempt < max_retries - 1:
                    logging.warning(f"Write error on attempt {attempt + 1}, retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    st.error(f"❌ Error writing to Excel file: {str(write_error)}")
                    st.error(f"📁 File path: {excel_path}")
                    st.error(f"💡 Error type: {type(write_error).__name__}")
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
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                st.error(f"❌ Permission Error: Excel file is locked or inaccessible.")
                st.error(f"📁 File path: {excel_path}")
                st.error(f"💡 Please ensure:")
                st.error(f"   1. The Excel file is not open in Excel or another program")
                st.error(f"   2. You have write permissions to the file")
                st.error(f"   3. No other process is using the file")
                st.error(f"   Error details: {str(pe)}")
                return False
        
        except Exception as error:
            if attempt < max_retries - 1:
                logging.warning(f"Error on attempt {attempt + 1}, retrying... Error: {str(error)}")
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                st.error(f"❌ Error appending to Excel file")
                st.error(f"📁 File path: {excel_path}")
                st.error(f"🔍 Error type: {type(error).__name__}")
                st.error(f"📝 Error message: {str(error)}")
                st.error(f"💡 Please check the file path and permissions.")
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

#Dashboard Functions

def show_metrics(df):
    """Display key metrics"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_submissions = len(df) if df is not None and not df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_submissions}</div>
            <div class="metric-label">Total Submissions</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        today = datetime.now().date()
        today_count = 0
        if df is not None and not df.empty and 'Date' in df.columns:
            today_count = len(df[df['Date'] == str(today)])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{today_count}</div>
            <div class="metric-label">Today's Reports</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        unique_employees = 0
        if df is not None and not df.empty and 'Name' in df.columns:
            unique_employees = df['Name'].nunique()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{unique_employees}</div>
            <div class="metric-label">Active Employees</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        completed_tasks = 0
        if df is not None and not df.empty and 'Task Status' in df.columns:
            completed_tasks = len(df[df['Task Status'] == 'Completed'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{completed_tasks}</div>
            <div class="metric-label">Completed Tasks</div>
        </div>
        """, unsafe_allow_html=True)

def show_filters(df):
    """Display filter options"""
    if df is None or df.empty:
        return df

    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    st.subheader("🔍 Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if 'Name' in df.columns:
            unique_vals = [x for x in df['Name'].unique() if pd.notna(x)]
            employees = ['All'] + sorted(unique_vals, key=lambda x: (0, x) if isinstance(x, (int, float)) else (1, str(x)))
        else:
            employees = ['All']
        selected_employee = st.selectbox("Employee", employees)

    with col2:
        if 'Project Name' in df.columns:
            unique_vals = [x for x in df['Project Name'].unique() if pd.notna(x)]
            projects = ['All'] + sorted(unique_vals, key=lambda x: (0, x) if isinstance(x, (int, float)) else (1, str(x)))
        else:
            projects = ['All']
        selected_project = st.selectbox("Project", projects)

    with col3:
        if 'Task Status' in df.columns:
            unique_vals = [x for x in df['Task Status'].unique() if pd.notna(x)]
            statuses = ['All'] + sorted(unique_vals, key=lambda x: (0, x) if isinstance(x, (int, float)) else (1, str(x)))
        else:
            statuses = ['All']
        selected_status = st.selectbox("Status", statuses)

    with col4:
        if 'Task Priority' in df.columns:
            unique_vals = [x for x in df['Task Priority'].unique() if pd.notna(x)]
            priorities = ['All'] + sorted(unique_vals, key=lambda x: (0, x) if isinstance(x, (int, float)) else (1, str(x)))
        else:
            priorities = ['All']
        selected_priority = st.selectbox("Priority", priorities)

    # Date range
    col5, col6 = st.columns(2)
    with col5:
        start_date = st.date_input("Start Date", (datetime.now() - timedelta(days=7)).date())
    with col6:
        end_date = st.date_input("End Date", datetime.now().date())

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    filtered_df = df.copy()

    if 'Date' in filtered_df.columns:
        filtered_df['Date'] = pd.to_datetime(filtered_df['Date'])
        filtered_df = filtered_df[
            (filtered_df['Date'].dt.date >= start_date) &
            (filtered_df['Date'].dt.date <= end_date)
        ]

    if selected_employee != 'All' and 'Name' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Name'] == selected_employee]

    if selected_project != 'All' and 'Project Name' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Project Name'] == selected_project]

    if selected_status != 'All' and 'Task Status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Task Status'] == selected_status]

    if selected_priority != 'All' and 'Task Priority' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Task Priority'] == selected_priority]

    return filtered_df

def show_charts(df):
    """Display analytics charts"""
    if df is None or df.empty:
        st.info("No data available for charts")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Task Status Distribution")
        if 'Task Status' in df.columns:
            status_counts = df['Task Status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("⚡ Priority Distribution")
        if 'Task Priority' in df.columns:
            priority_counts = df['Task Priority'].value_counts()
            fig = px.bar(
                x=priority_counts.index,
                y=priority_counts.values,
                color=priority_counts.index,
                color_discrete_map={
                    'Low': '#90EE90',
                    'Medium': '#FFD700',
                    'High': '#FFA500',
                    'Critical': '#FF6347'
                }
            )
            fig.update_layout(showlegend=False, xaxis_title="Priority", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

    # Weekly trend
    st.subheader("📊 Weekly Submission Trend")
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        daily_counts = df.groupby(df['Date'].dt.date).size().reset_index(name='count')
        fig = px.line(
            daily_counts,
            x='Date',
            y='count',
            markers=True
        )
        fig.update_layout(xaxis_title="Date", yaxis_title="Submissions")
        st.plotly_chart(fig, use_container_width=True)


def get_status_color_and_label(availability):
    """Return status label and color based on availability status"""
    if availability == "Underutilized":
        return "🟢 Underutilized", "#10b981"
    elif availability == "Partially Busy":
        return "🟡 Partially Busy", "#f59e0b"
    elif availability == "Fully Busy":
        return "🔴 Fully Busy", "#ef4444"
    else:
        return "⚪ Unknown", "#6b7280"


def format_availability_for_csv(availability):
    """Format availability value to HTML for CSV exports."""
    try:
        if availability is None:
            return "<span style='background-color:#6b7280;color:black;'>⚪ Unknown</span>"
        a = str(availability).strip()
        if a == "Underutilized":
            return "<span style='background-color:#10b981;color:white;'>🟢 Underutilized</span>"
        if a == "Partially Busy":
            return "<span style='background-color:#f59e0b;color:black;'>🟡 Partially Busy</span>"
        if a == "Fully Busy":
            return "<span style='background-color:#ef4444;color:black;'>🔴 Fully Busy</span>"
        return "<span style='background-color:#6b7280;color:black;'>⚪ Unknown</span>"
    except Exception:
        return "<span style='background-color:#6b7280;color:black;'>⚪ Unknown</span>"


def show_employee_dashboard(df):
    """Interactive dashboard for selected employee using performance metrics."""
    if df is None or df.empty or 'Name' not in df.columns:
        st.info("No employee data available for detailed view.")
        return

    df = ensure_numeric_columns(df)
    df = df.copy()
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    employees = sorted([name for name in df['Name'].dropna().unique() if str(name).strip()])
    if not employees:
        st.info("No employees found in the dataset.")
        return

    st.subheader("👤 Employee Performance Explorer")
    st.caption("Analyze and track employee performance metrics")

    # Per-employee average performance chart
    try:
        perf_summary = (
            df.groupby('Name')['Employee Performance (%)']
            .mean()
            .reset_index(name='AvgPerformance')
        )
        # latest availability per employee
        latest_avails = {}
        for name in perf_summary['Name'].tolist():
            emp_rows = df[df['Name'] == name]
            if 'Availability' in emp_rows.columns and not emp_rows[emp_rows['Availability'].notna()].empty:
                latest_avails[name] = emp_rows[emp_rows['Availability'].notna()]['Availability'].iloc[-1]
            else:
                latest_avails[name] = 'Unknown'

        perf_summary['StatusCategory'] = perf_summary['Name'].map(latest_avails)
        color_map = {
            'Underutilized': '#10b981',
            'Partially Busy': '#f59e0b',
            'Fully Busy': '#ef4444',
            'Unknown': '#6b7280'
        }
        # Use StatusCategory for colors
        perf_summary = perf_summary.sort_values('AvgPerformance', ascending=False)
        if not perf_summary.empty:
            fig_perf = px.bar(
                perf_summary,
                x='Name',
                y='AvgPerformance',
                color='StatusCategory',
                color_discrete_map=color_map,
                labels={'Name': 'Employee', 'AvgPerformance': 'Avg Performance (%)'},
                title='Average Performance by Employee'
            )
            fig_perf.update_layout(yaxis_range=[0, 100], showlegend=True, height=320)
            st.plotly_chart(fig_perf, use_container_width=True)
    except Exception:
        # don't break dashboard if chart fails
        pass

    # Export All Employees (create ZIP of per-employee CSVs)
    exp_col1, exp_col2 = st.columns([5, 1])
    with exp_col2:
        if st.button("📥 Export All", use_container_width=True, key="export_all_btn"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for name in employees:
                    emp_rows = df[df['Name'] == name].copy()
                    if 'Date' in emp_rows.columns:
                        emp_rows['Date'] = emp_rows['Date'].astype(str)
                    # Ensure Availability is formatted in exported CSVs
                    if 'Availability' in emp_rows.columns:
                        emp_rows_export = emp_rows.copy()
                        emp_rows_export['Availability'] = emp_rows_export['Availability'].apply(format_availability_for_csv)
                    else:
                        emp_rows_export = emp_rows
                    csv_bytes = emp_rows_export.to_csv(index=False).encode('utf-8-sig')
                    safe_name = re.sub(r"[^A-Za-z0-9_\- ]+", "", str(name)).strip() or "employee"
                    zf.writestr(f"{safe_name}_report.csv", csv_bytes)
            buf.seek(0)
            st.download_button(
                label="Download All Employees (ZIP)",
                data=buf,
                file_name=f"all_employees_reports_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
                key="download_all_zip"
            )

    selected_employee = st.selectbox("Select an employee to view detailed performance", ["All"] + employees, key="employee_selector")

    if not selected_employee:
        st.info("Select an employee to view their dashboard.")
        return

    emp_df = df[df['Name'] == selected_employee].copy()
    if emp_df.empty:
        st.warning("No records found for the selected employee.")
        return

    total_tasks = len(emp_df)
    completed_tasks = int((emp_df.get('Task Status') == 'Completed').sum()) if 'Task Status' in emp_df.columns else 0
    pending_tasks = max(total_tasks - completed_tasks, 0)
    avg_performance = round(emp_df['Employee Performance (%)'].mean(), 2)
    latest_perf = round(emp_df.sort_values('Date')['Employee Performance (%)'].iloc[-1], 2) if not emp_df['Employee Performance (%)'].empty else 0
    last_update = emp_df['Date'].dropna().max().date().isoformat() if 'Date' in emp_df.columns and not emp_df['Date'].dropna().empty else "N/A"
    
    # Calculate additional metrics for professional display
    completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
    productivity_score = round(avg_performance, 1)
    quality_score = round(min(avg_performance * 1.1, 100), 1)
    efficiency_score = round(min(avg_performance * 0.95, 100), 1)
    
    # Get status based on most recent Availability field from CSV
    latest_availability = emp_df[emp_df['Availability'].notna()]['Availability'].iloc[-1] if 'Availability' in emp_df.columns and not emp_df[emp_df['Availability'].notna()].empty else "Unknown"
    status_label, status_color = get_status_color_and_label(latest_availability)
    
    # Get department/project
    project_name = emp_df['Project Name'].mode()[0] if 'Project Name' in emp_df.columns and not emp_df['Project Name'].empty else 'Multiple Projects'
    
    # Professional Employee Card Display
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 25px; border-radius: 15px; margin-bottom: 20px; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <h2 style="color: white; margin: 0; font-size: 28px;">{selected_employee}</h2>
                <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 16px;">
                    {project_name}
                </p>
            </div>
            <div style="text-align: right;">
                <span style="background: {status_color}; color: white; padding: 8px 16px; 
                             border-radius: 20px; font-weight: bold; font-size: 14px;">
                    {status_label}
                </span>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 15px;">
            <div style="text-align: center;">
                <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 13px;">Productivity</p>
                <p style="color: white; margin: 5px 0 0 0; font-size: 24px; font-weight: bold;">{productivity_score}%</p>
            </div>
            <div style="text-align: center;">
                <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 13px;">Quality</p>
                <p style="color: white; margin: 5px 0 0 0; font-size: 24px; font-weight: bold;">{quality_score}%</p>
            </div>
            <div style="text-align: center;">
                <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 13px;">Efficiency</p>
                <p style="color: white; margin: 5px 0 0 0; font-size: 24px; font-weight: bold;">{efficiency_score}%</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # # Export individual employee data
    # col_export_individual = st.columns([5, 1])
    # with col_export_individual[1]:
    #     # Prepare export data
    #     export_df = emp_df.copy()
    #     if 'Date' in export_df.columns:
    #         export_df['Date'] = export_df['Date'].astype(str)
    #     export_df = export_df.sort_values('Date', ascending=False) if 'Date' in export_df.columns else export_df
    #     # Format Availability for CSV export
    #     if 'Availability' in export_df.columns:
    #         export_df = export_df.copy()
    #         export_df['Availability'] = export_df['Availability'].apply(format_availability_for_csv)

    #     csv_bytes = export_df.to_csv(index=False).encode('utf-8-sig')
    #     st.download_button(
    #         label=f"📥 Export",
    #         data=csv_bytes,
    #         file_name=f"{selected_employee}_performance_report_{datetime.now().strftime('%Y%m%d')}.csv",
    #         mime="text/csv",
    #         use_container_width=True,
    #         key="export_individual_emp"
    #     )

    # Export individual employee data
    col_export_individual = st.columns([5, 1])
    with col_export_individual[1]:
        # Prepare export data
        export_df = emp_df.copy()
        if 'Date' in export_df.columns:
            export_df['Date'] = export_df['Date'].astype(str)
    export_df = export_df.sort_values('Date', ascending=False) if 'Date' in export_df.columns else export_df

    # Add a new column for styled availability
    export_df['Styled Availability'] = export_df['Availability'].apply(lambda x: f"<span style='background-color:#ef4444;color:black;'>🔴 {x}</span>" if x == 'Fully Busy' else
                                                                       f"<span style='background-color:#f59e0b;color:black;'>🟡 {x}</span>" if x == 'Partially Busy' else
                                                                       f"<span style='background-color:#10b981;color:white;'>🟢 {x}</span>" if x == 'Underutilized' else
                                                                       f"<span style='background-color:#6b7280;color:black;'>⚪ {x}</span>")

    csv_bytes = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label=f"📥 Export",
        data=csv_bytes,
        file_name=f"{selected_employee}_performance_report_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
        key="export_individual_emp"
    )

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        st.metric("Total Tasks", total_tasks)
    with metric_col2:
        st.metric("Completed Tasks", completed_tasks)
    with metric_col3:
        st.metric("Completion Rate", f"{completion_rate}%")
    with metric_col4:
        st.metric("Last Update", last_update)

    chart_col1, chart_col2 = st.columns([1, 1])

    with chart_col1:
        st.caption("Current Performance Gauge")
        gauge_fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=latest_perf,
                title={'text': "Latest Performance"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#764ba2"},
                    'steps': [
                        {'range': [0, 50], 'color': "#ff7675"},
                        {'range': [50, 80], 'color': "#ffeaa7"},
                        {'range': [80, 100], 'color': "#55efc4"},
                    ]
                }
            )
        )
        gauge_fig.update_layout(height=280, margin=dict(l=40, r=40, t=60, b=40))
        st.plotly_chart(gauge_fig, use_container_width=True)

    with chart_col2:
        st.caption("Performance Snapshot")
        trend_df = emp_df[['Date', 'Employee Performance (%)']].dropna()
        if not trend_df.empty and trend_df['Date'].notna().any():
            trend_fig = px.line(
                trend_df.sort_values('Date'),
                x='Date',
                y='Employee Performance (%)',
                markers=True
            )
            trend_fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Performance (%)",
                yaxis_range=[0, 100]
            )
            st.plotly_chart(trend_fig, use_container_width=True)
        else:
            st.info("No performance history available for this employee.")

    st.caption("Task Breakdown")
    breakdown_col1, breakdown_col2 = st.columns(2)
    with breakdown_col1:
        if 'Task Status' in emp_df.columns:
            status_counts = emp_df['Task Status'].value_counts()
            if not status_counts.empty:
                status_fig = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                st.plotly_chart(status_fig, use_container_width=True)
            else:
                st.info("No task status data available for this employee.")
        else:
            st.info("Task status column not available.")
    with breakdown_col2:
        if 'Task Priority' in emp_df.columns:
            priority_counts = emp_df['Task Priority'].value_counts()
            if not priority_counts.empty:
                priority_fig = px.bar(
                    x=priority_counts.index,
                    y=priority_counts.values,
                    text=priority_counts.values,
                    color=priority_counts.index,
                    color_discrete_sequence=px.colors.sequential.PuBu
                )
                priority_fig.update_layout(showlegend=False, xaxis_title="Priority", yaxis_title="Tasks")
                priority_fig.update_traces(textposition='outside')
                st.plotly_chart(priority_fig, use_container_width=True)
            else:
                st.info("No task priority data available for this employee.")
        else:
            st.info("Task priority column not available.")

    st.subheader("📈 Performance Trend")
    st.caption("Track performance metrics over time")
    
    trend_df = emp_df[['Date', 'Employee Performance (%)']].dropna()
    if not trend_df.empty and trend_df['Date'].notna().any():
        # Add productivity, quality, efficiency calculations for trend
        trend_df = trend_df.sort_values('Date')
        trend_df['Productivity'] = trend_df['Employee Performance (%)']
        trend_df['Quality'] = (trend_df['Employee Performance (%)'] * 1.1).clip(upper=100)
        trend_df['Efficiency'] = (trend_df['Employee Performance (%)'] * 0.95).clip(upper=100)
        
        # Create multi-line trend chart
        trend_fig_full = go.Figure()
        
        trend_fig_full.add_trace(go.Scatter(
            x=trend_df['Date'],
            y=trend_df['Productivity'],
            mode='lines+markers',
            name='Productivity',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8)
        ))
        
        trend_fig_full.add_trace(go.Scatter(
            x=trend_df['Date'],
            y=trend_df['Quality'],
            mode='lines+markers',
            name='Quality',
            line=dict(color='#10b981', width=3),
            marker=dict(size=8)
        ))
        
        trend_fig_full.add_trace(go.Scatter(
            x=trend_df['Date'],
            y=trend_df['Efficiency'],
            mode='lines+markers',
            name='Efficiency',
            line=dict(color='#f59e0b', width=3),
            marker=dict(size=8)
        ))
        
        trend_fig_full.update_layout(
            title=f"{selected_employee}'s Performance Trend",
            xaxis_title='Date',
            yaxis_title='Performance (%)',
            yaxis_range=[0, 100],
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(trend_fig_full, use_container_width=True)
        
        # Performance statistics table
        st.markdown('**Performance Statistics**')
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        with stats_col1:
            st.metric("Avg Productivity", f"{trend_df['Productivity'].mean():.1f}%")
        with stats_col2:
            st.metric("Avg Quality", f"{trend_df['Quality'].mean():.1f}%")
        with stats_col3:
            st.metric("Avg Efficiency", f"{trend_df['Efficiency'].mean():.1f}%")
        
        # Recent performance data with download option
        st.markdown('**Recent Performance Values**')
        recent_performance_df = trend_df[['Date', 'Productivity', 'Quality', 'Efficiency']].copy()
        recent_performance_df = recent_performance_df.sort_values('Date', ascending=False).head(20)
        recent_performance_df['Date'] = recent_performance_df['Date'].dt.strftime('%Y-%m-%d')
        st.dataframe(recent_performance_df, use_container_width=True)
        
        # Download trend data
        trend_csv_bytes = trend_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Performance Trend Data",
            data=trend_csv_bytes,
            file_name=f"{selected_employee}_performance_trend_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="download_trend_data"
        )
    else:
        st.info("No performance history available for this employee.")

    st.subheader("📋 Recent Tasks")
    display_columns = [col for col in DATA_COLUMNS if col in emp_df.columns]
    if display_columns:
        display_df = emp_df.sort_values('Date', ascending=False)[display_columns]
        
        def highlight_support(val):
            if pd.isna(val) or str(val).strip() == "":
                return ""
            return "background-color: #ffcccb; color: #000000; font-weight: bold; border-left: 3px solid #ff4444"
        
        styled_df = display_df.style.map(highlight_support, subset=['Support Request'])
        st.dataframe(styled_df, use_container_width=True, height=320)
    else:
        st.info("No detailed task records to display.")

def show_data_table(df):
    """Display data table"""
    st.subheader("📋 Recent Submissions")

    if df is None or df.empty:
        st.info("No submissions found")
        return

    # Display options
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔎 Search", placeholder="Search in any column...")
    with col2:
        rows_to_show = st.number_input("Rows", min_value=10, max_value=1000, value=50, step=10)

    # Apply search
    display_df = df.copy()
    if search:
        mask = display_df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)
        display_df = display_df[mask]

    # NEW: Helper function to highlight non-empty Support Request cells
    def highlight_support(val):
        if pd.isna(val) or str(val).strip() == "":
            return ""
        return "background-color: #ffcccb; color: #000000; font-weight: bold; border-left: 3px solid #ff4444"  # Light red for flagged support requests

    # NEW: Apply styling to the Support Request column only
    styled_df = display_df.style.map(highlight_support, subset=['Support Request'])

    # UPDATED: Use the styled dataframe
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=400
    )

    # Download button
    if not display_df.empty:
        df_export = display_df.copy()
        # Ensure Availability column exports with emoji labels
        if 'Availability' in df_export.columns:
            df_export['Availability'] = df_export['Availability'].apply(format_availability_for_csv)

        csv_bytes = df_export.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv_bytes,
            file_name=f"employee_progress_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

#Settings Page

def show_settings():
    """Display settings page"""
    st.title("⚙️ Settings")

    config = load_config()

    with st.form("settings_form"):
        st.subheader("Excel File Configuration")

        excel_file_path = st.text_input(
            "Excel File Path",
            value=config.get('excel_file_path', EXCEL_FILE_PATH),
            help="Path to the local Excel file"
        )

        st.markdown("---")
        st.subheader("Reminder Settings")

        col1, col2 = st.columns(2)
        with col1:
            reminder_time = st.time_input(
                "Reminder Time",
                value=datetime.strptime(config.get('reminder_time', '18:00'), '%H:%M').time()
            )

        with col2:
            st.write("Reminder Days (uncheck Sunday)")
            reminder_days = []
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            default_days = config.get('reminder_days', [0, 1, 2, 3, 4, 5])

            for i, day in enumerate(days):
                if st.checkbox(day, value=i in default_days, key=f"day_{i}"):
                    reminder_days.append(i)

        st.markdown("---")
        st.subheader("Email Configuration")

        admin_email = st.text_input(
            "Admin Email",
            value=config.get('admin_email', '')
        )

        employee_emails = st.text_area(
            "Employee Emails (one per line)",
            value='\n'.join(config.get('employee_emails', [])),
            height=150
        )

        st.caption("If you enabled Telegram reminders, add chat IDs in the same order as emails.")
        employee_telegram_chat_ids = st.text_area(
            "Employee Telegram Chat IDs (one per line, aligned with emails)",
            value='\n'.join([str(x) for x in config.get('employee_telegram_chat_ids', [])]),
            height=150
        )

        submitted = st.form_submit_button("💾 Save Settings")

        if submitted:
            # Update config
            config['excel_file_path'] = excel_file_path
            config['reminder_time'] = reminder_time.strftime('%H:%M')
            config['reminder_days'] = reminder_days
            config['admin_email'] = admin_email
            config['employee_emails'] = [
                email.strip()
                for email in employee_emails.split('\n')
                if email.strip()
            ]
            # Parse Telegram chat IDs line by line, keep as int if numeric, else string
            parsed_chat_ids = []
            for line in employee_telegram_chat_ids.split('\n'):
                raw = line.strip()
                if not raw:
                    continue
                # Try int conversion (supports negative IDs)
                try:
                    parsed_chat_ids.append(int(raw))
                except ValueError:
                    parsed_chat_ids.append(raw)
            config['employee_telegram_chat_ids'] = parsed_chat_ids

            save_config(config)
            st.success("✅ Settings saved successfully!")
            time.sleep(1)
            st.rerun()

    # Connection test
    st.markdown("---")
    st.subheader("🔌 Test Connection & Diagnostics")

    if st.button("🔍 Test Excel File Connection & Check for Issues"):
        excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)
        
        with st.spinner("Running diagnostics..."):
            # Check 1: File exists
            st.write("**1. Checking if file exists...**")
            if os.path.exists(excel_path):
                st.success(f"✅ File exists at: `{excel_path}`")
                
                # Check 2: File permissions
                st.write("**2. Checking file permissions...**")
                if os.access(excel_path, os.R_OK):
                    st.success("✅ File is readable")
                else:
                    st.error("❌ File is NOT readable. Check permissions.")
                
                if os.access(excel_path, os.W_OK):
                    st.success("✅ File is writable")
                else:
                    st.error("❌ File is NOT writable. Check permissions.")
                
                # Check 3: Try to read the file
                st.write("**3. Testing file read access...**")
                try:
                    df = read_excel_data(excel_path)
                    if df is not None:
                        st.success(f"✅ Successfully read file! Found {len(df)} records")
                        if not df.empty:
                            st.dataframe(df.head(), use_container_width=True)
                        else:
                            st.info("📋 Excel file is empty. Start submitting reports to add data.")
                    else:
                        st.error("❌ Failed to read file data.")
                except PermissionError as pe:
                    st.error(f"❌ **Permission Error**: Cannot read file")
                    st.error(f"   Error: {str(pe)}")
                    st.warning("💡 **Solution**: Close the Excel file if it's open in Excel or another program.")
                except Exception as e:
                    st.error(f"❌ **Error reading file**: {type(e).__name__}")
                    st.error(f"   Error: {str(e)}")
                
                # Check 4: Try to write to the file (test write)
                st.write("**4. Testing file write access...**")
                try:
                    # Save original data first
                    original_df = df.copy() if df is not None and not df.empty else None
                    
                    # Try to open the file in write mode to check if it's locked
                    # We'll write the original data back, so this is safe
                    if original_df is not None:
                        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                            original_df.to_excel(writer, index=False, sheet_name='Sheet1')
                        st.success("✅ File write test successful! (Original data preserved)")
                    else:
                        # If file is empty, create a test write
                        test_data = pd.DataFrame([{'Test': 'test'}])
                        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                            test_data.to_excel(writer, index=False, sheet_name='Sheet1')
                        # Remove test data
                        empty_df = pd.DataFrame()
                        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                            empty_df.to_excel(writer, index=False, sheet_name='Sheet1')
                        st.success("✅ File write test successful!")
                except PermissionError as pe:
                    st.error(f"❌ **Permission Error**: Cannot write to file")
                    st.error(f"   Error: {str(pe)}")
                    st.warning("💡 **Most Common Causes:**")
                    st.warning("   1. Excel file is open in Microsoft Excel")
                    st.warning("   2. Excel file is open in another program")
                    st.warning("   3. Another process is using the file")
                    st.warning("   4. Insufficient file permissions")
                except Exception as e:
                    st.error(f"❌ **Error writing to file**: {type(e).__name__}")
                    st.error(f"   Error: {str(e)}")
                
            else:
                st.error(f"❌ File does NOT exist at: `{excel_path}`")
                st.info("💡 The file will be created automatically when you submit your first report.")

#  Submit Report Page

def show_submit_report():
    """Display form for submitting work progress reports with multiple tasks"""
    config = load_config()
    
    # Logo Section - Centered at top
    # Try multiple path approaches for compatibility
    # logo_found = False
    # possible_paths = [
    #     "logo/PTF1.png",  # Simple relative path (usually works on Streamlit Cloud)
    #     Path("logo/PTF1.png"),  # Path object version
    #     Path(__file__).parent / "logo" / "PTF1.png",  # Relative to script
    # ]

    # --- Logo Section (Fixed for Streamlit Cloud) ---
    # Use a single HTML block to ensure the image is centered and constrained
    logo_url = "https://raw.githubusercontent.com/SoumyaR01/Employee-Task-Tracker/main/logo/ptf.png"

    # Render using an HTML <img> so CSS sizing/centering is reliable inside Streamlit's layout
    try:
        st.markdown(
            f'<div class="logo-container" style="text-align:center;">'
            f'  <img src="{logo_url}" alt="PTF Logo" '
            f'       style="max-width:360px; width:100%; height:auto; display:block; margin:0 auto; border-radius:8px;"/>'
            f'</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        # Fallback placeholder if remote image cannot be loaded
        st.markdown(
            """
        <div class="logo-container" style="text-align: center;">
            <div style="width: 100%; max-width:360px; height: auto; padding: 12px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        display: flex; align-items: center; justify-content: center; 
                        border-radius: 10px; border: 2px solid #667eea; margin:0 auto;">
                <p style="color: white; font-size: 18px; font-weight: bold; margin: 0;">PTF</p>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    
    # Title Section - Centered below logo
    st.markdown("<h1 style='text-align: center; margin-top: 10px; color: #2c3e50;'>Employee Performance Management</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7f8c8d; font-size: 1.1rem;'>Submit all your tasks for today in one report</p>", unsafe_allow_html=True)
    
    st.markdown("---")

    excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)

    # Initialize session state for task count if not exists
    if 'num_tasks' not in st.session_state:
        st.session_state.num_tasks = 1
    
    st.subheader("👤 Employee Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("Date*", value=datetime.now().date())
        work_mode = st.selectbox(
            "Work Mode*",
            ["", "PTF", "Remote"],
            help="Select your work mode"
        )
    
    with col2:
        emp_id = st.text_input(
            "Employee ID*",
            placeholder="Enter your employee ID",
            help="Required field"
        )
        name = st.text_input(
            "Name*",
            placeholder="Enter your full name",
            help="Required field"
        )
    
    st.markdown("---")
    st.subheader("📋 Today's Tasks")
    st.info("💡 Add all the tasks you worked on today. You can add multiple tasks before submitting.")
    
    # Handle add/remove task buttons
    col_add_remove = st.columns([1, 1, 4])
    with col_add_remove[0]:
        if st.button("➕ Add Task", use_container_width=True):
            st.session_state.num_tasks += 1
            st.rerun()
    with col_add_remove[1]:
        if st.button("➖ Remove Task", use_container_width=True) and st.session_state.num_tasks > 1:
            st.session_state.num_tasks -= 1
            st.rerun()
    
    st.caption(f"📋 You have {st.session_state.num_tasks} task(s) in this report")
    
    # Display task inputs
    for i in range(st.session_state.num_tasks):
        with st.expander(f"Task {i+1}", expanded=(i == 0)):
            col3, col4 = st.columns(2)
            
            with col3:
                project_name = st.text_input(
                    "Project Name*",
                    placeholder="Enter project name",
                    help="Required field",
                    key=f"project_{i}"
                )
                task_title = st.text_input(
                    "Task Title*",
                    placeholder="Describe the task...",
                    help="Brief description of the task",
                    key=f"title_{i}"
                )
                task_assigned_by = st.text_input(
                    "Task Assigned By*",
                    placeholder="Who assigned this task?",
                    help="Person who assigned the task",
                    key=f"assigned_{i}"
                )
            
            with col4:
                task_priority = st.selectbox(
                    "Task Priority*",
                    ["", "Low", "Medium", "High", "Critical"],
                    help="Select task priority level",
                    key=f"priority_{i}"
                )
                task_status = st.selectbox(
                    "Task Status*",
                    ["", "In Progress", "Completed"],
                    help="Select current task status",
                    key=f"status_{i}"
                )
                effort = st.number_input(
                    "Effort (in hours)*",
                    min_value=0.0,
                    value=1.0,  # Default to 1 hour
                    step=0.5,
                    help="Hours spent on this task (must be >0)",
                    key=f"effort_{i}"
                )
                comments = st.text_area(
                    "Support Request",
                    placeholder="Provide any supporting information...",
                    height=80,
                    help="Optional comments",
                    key=f"comments_{i}"
                )
                availability = st.selectbox(
                    "Availability",
                    ["", "Fully Busy", "Partially Busy", "Underutilized"],
                    help="Select availability status for this task",
                    key=f"availability_{i}"
                )
    
    st.markdown("---")
    st.subheader("📅 Plan for Tomorrow")
    
    plan_for_next_day = st.text_area(
        "Plan for Next Day*",
        placeholder="What are your plans for tomorrow?",
        height=100,
        help="Required field"
    )
    
    submitted = st.button("✅ Submit Daily Report", use_container_width=True)
    
    if submitted:
        # Validate employee information
        employee_fields = {
            "Date": date,
            "Work Mode": work_mode,
            "Employee ID": emp_id,
            "Name": name
        }
        
        missing_employee_fields = [field for field, value in employee_fields.items() if not value]
        
        if missing_employee_fields:
            st.error(f"❌ Please fill in all employee information: {', '.join(missing_employee_fields)}")
        elif st.session_state.num_tasks == 0:
            st.error("❌ Please add at least one task to your report.")
        elif not plan_for_next_day:
            st.error("❌ Please fill in your plan for next day.")
        else:
            # Collect all task data from session_state (widget values are stored there with keys)
            task_data_list = []
            invalid_tasks = []
            
            for i in range(st.session_state.num_tasks):
                # Get values from session_state (widgets with keys store values there with keys)
                project_name = st.session_state.get(f"project_{i}", "")
                task_title = st.session_state.get(f"title_{i}", "")
                task_assigned_by = st.session_state.get(f"assigned_{i}", "")
                task_priority = st.session_state.get(f"priority_{i}", "")
                task_status = st.session_state.get(f"status_{i}", "")
                effort = st.session_state.get(f"effort_{i}", 0.0)
                comments = st.session_state.get(f"comments_{i}", "")
                
                # Validate task
                if not all([project_name, task_title, task_assigned_by, task_priority, task_status]) or effort <= 0:
                    invalid_tasks.append(i + 1)
                else:
                    availability = st.session_state.get(f"availability_{i}", "")

                    task_data_list.append({
                        'Date': date.strftime("%Y-%m-%d"),
                        'Work Mode': work_mode,
                        'Emp Id': emp_id,
                        'Name': name,
                        'Project Name': project_name,
                        'Task Title': task_title,
                        'Task Assigned By': task_assigned_by,
                        'Task Priority': task_priority,
                        'Task Status': task_status,
                        'Plan for next day': plan_for_next_day,
                                'Support Request': comments if comments else '',
                            'Availability': availability if availability else '',
                            'Effort (in hours)': effort,
                        # 'Employee Performance (%)' calculated below
                    })
            
            # Calculate overall performance for the day using the new priority/effort formula
            if task_data_list:
                performance = calculate_performance(task_data_list)
                for row in task_data_list:
                    row['Employee Performance (%)'] = performance

            if invalid_tasks:
                st.error(f"❌ Please fill in all required fields for task(s): {', '.join(map(str, invalid_tasks))}")
            elif not task_data_list:
                st.error("❌ No valid tasks to submit. Please add at least one complete task.")
            else:
                # Append all tasks to Excel file
                with st.spinner(f"Saving your daily report with {len(task_data_list)} task(s)..."):
                    success = append_to_excel(task_data_list, excel_path)
                
                if success:
                    st.success(f"✅ Your daily work progress report has been submitted successfully! ({len(task_data_list)} task(s) recorded)")
                    st.balloons()
                    # Reset task count for next submission
                    st.session_state.num_tasks = 1
                    # Clear form values by clearing session state keys
                    for i in range(10):  # Clear up to 10 task slots
                        for key_suffix in ['project', 'title', 'assigned', 'priority', 'status', 'comments', 'availability', 'effort']:
                            key = f"{key_suffix}_{i}"
                            if key in st.session_state:
                                del st.session_state[key]
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Failed to save report. Please try again or contact administrator.")

# Main App

def main():
    """Main application"""

    # Sidebar navigation
    with st.sidebar:
        st.title("📊 Progress Tracker")
        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["📝 Submit Report", "📈 Dashboard", "⚙️ Settings", "📧 Reminders"],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("### 🔄 Quick Actions")

        if st.button("🔄 Refresh Data"):
            st.rerun()

        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load configuration
    config = load_config()

    # Main content
    if page == "📝 Submit Report":
        show_submit_report()
    
    elif page == "📈 Dashboard":
        st.title("📈 Employee Progress Dashboard")

        excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)

        # Load data
        with st.spinner("Loading data..."):
            df = read_excel_data(excel_path)
            if df is not None and not df.empty:
                try:
                    workbook = load_workbook(excel_path)
                    summary_needs_refresh = SUMMARY_SHEET_NAME not in workbook.sheetnames

                    if not summary_needs_refresh:
                        ws_summary = workbook[SUMMARY_SHEET_NAME]
                        summary_headers = [
                            cell.value for cell in next(ws_summary.iter_rows(min_row=1, max_row=1))
                            if cell.value
                        ]
                        if "Employee Performance (%)" not in summary_headers:
                            summary_needs_refresh = True
                    if summary_needs_refresh:
                        update_dashboard_sheets(excel_path, df)
                except Exception as dashboard_error:
                    logging.warning(f"Dashboard sheet auto-refresh failed: {dashboard_error}")
                finally:
                    try:
                        workbook.close()
                    except Exception:
                        pass

        if df is None:
            st.error("Failed to load data. Check the Excel file path in Settings.")
            return

        if df.empty:
            st.info("📋 No data available yet. Start submitting reports to see data here.")
            return

        # Show metrics
        show_metrics(df)

        st.markdown("---")

        # Show filters
        filtered_df = show_filters(df)

        st.markdown("---")

        # Show charts
        show_charts(filtered_df)

        st.markdown("---")

        # Show employee specific dashboard
        show_employee_dashboard(filtered_df if filtered_df is not None and not filtered_df.empty else df)

        st.markdown("---")

        # Show data table
        show_data_table(filtered_df)

    elif page == "⚙️ Settings":
        show_settings()

    elif page == "📧 Reminders":
        st.title("📧 Reminder Management")

        st.info("""
**Reminder System Setup**

The reminder system will automatically send emails to employees who haven't submitted their daily report.

To enable automated reminders:
1. Set up reminder time and days in Settings
2. Configure employee emails
3. Run the reminder service: `python reminder_service.py`
""")

        excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)

        # Manual reminder test
        st.subheader("🧪 Test Reminder")

        if st.button("Check Missing Reports Today"):
            with st.spinner("Checking..."):
                df = read_excel_data(excel_path)
                if df is not None:
                    missing = get_missing_reporters(df, datetime.now())

                    if missing:
                        st.warning(f"📋 {len(missing)} employees haven't reported today:")
                        for emp in missing:
                            st.write(f"- {emp}")
                    else:
                        st.success("✅ All employees have submitted their reports today!")
                else:
                    st.error("Failed to load data")

if __name__ == "__main__":
    main()