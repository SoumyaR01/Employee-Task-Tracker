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

st.set_page_config(
    page_title="Employee Progress Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .filter-container {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stButton > button {
        width: 100%;
        border-radius: 5px;
        height: 3rem;
        font-weight: 600;
    }
    @media (max-width: 768px) {
        .main > div {
            padding: 0.5rem;
        }
        .metric-value {
            font-size: 1.8rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Constants
EXCEL_FILE_PATH = r'D:\Employee Track Report\task_tracker.xlsx'
CONFIG_FILE = 'config.json'

# Helper Functions

def load_config():
    """Load configuration from file"""
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'excel_file_path': EXCEL_FILE_PATH,
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
            columns = [
                'Date', 'Work Mode', 'Emp Id', 'Name', 'Project Name', 
                'Task Title', 'Task Assigned By', 'Task Priority', 
                'Task Status', 'Plan for next day', 'Comments'
            ]
            df = pd.DataFrame(columns=columns)
            df.to_excel(excel_path, index=False, engine='openpyxl')
            return df
        
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Handle empty file
        if df.empty:
            return pd.DataFrame()
        
        return df
    
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
            columns = [
                'Date', 'Work Mode', 'Emp Id', 'Name', 'Project Name', 
                'Task Title', 'Task Assigned By', 'Task Priority', 
                'Task Status', 'Plan for next day', 'Comments'
            ]
            
            # Combine with existing data
            if existing_df.empty:
                combined_df = new_rows
            else:
                # Ensure column order matches
                # Add missing columns if any
                for col in columns:
                    if col not in existing_df.columns:
                        existing_df[col] = ''
                    if col not in new_rows.columns:
                        new_rows[col] = ''
                
                # Reorder columns
                existing_df = existing_df[columns]
                new_rows = new_rows[columns]
                
                combined_df = pd.concat([existing_df, new_rows], ignore_index=True)
            
            # Ensure all columns are in the right order
            combined_df = combined_df[columns]
            
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
            st.plotly_chart(fig, width="stretch")

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
            st.plotly_chart(fig, width="stretch")

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
        st.plotly_chart(fig, width="stretch")

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

    # Show data
    st.dataframe(
        display_df.head(rows_to_show),
        width="stretch",
        height=400
    )

    # Download button
    if not display_df.empty:
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
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
                            st.dataframe(df.head(), width="stretch")
                        else:
                            st.info("📋 Excel file is empty. Start submitting reports to add data.")
                    else:
                        st.error("