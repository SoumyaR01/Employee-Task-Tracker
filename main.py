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
        use_container_width=True,
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
    st.markdown("<h1 style='text-align: center; margin-top: 10px; color: #2c3e50;'>PTF Daily Work Progress Report</h1>", unsafe_allow_html=True)
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
                comments = st.text_area(
                    "Comments",
                    placeholder="Any additional comments or notes...",
                    height=80,
                    help="Optional comments",
                    key=f"comments_{i}"
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
                # Get values from session_state (widgets with keys store values there)
                project_name = st.session_state.get(f"project_{i}", "")
                task_title = st.session_state.get(f"title_{i}", "")
                task_assigned_by = st.session_state.get(f"assigned_{i}", "")
                task_priority = st.session_state.get(f"priority_{i}", "")
                task_status = st.session_state.get(f"status_{i}", "")
                comments = st.session_state.get(f"comments_{i}", "")
                
                # Validate task
                if not all([project_name, task_title, task_assigned_by, task_priority, task_status]):
                    invalid_tasks.append(i + 1)
                else:
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
                        'Comments': comments if comments else ''
                    })
            
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
                        for key_suffix in ['project', 'title', 'assigned', 'priority', 'status', 'comments']:
                            key = f"{key_suffix}_{i}"
                            if key in st.session_state:
                                del st.session_state[key]
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Failed to save report. Please try again or contact administrator.")

# Main App

def is_admin():
    """Check if user is admin (via query param)"""
    try:
        query_params = st.query_params
        return query_params.get('admin', '').lower() == 'true'
    except:
        return False

def main():
    """Main application"""

    admin = is_admin()

    # Sidebar navigation
    with st.sidebar:
        st.title("📊 Progress Tracker")
        st.markdown("---")

        if admin:
            nav_options = ["📝 Submit Report", "📈 Dashboard", "⚙️ Settings", "📧 Reminders"]
        else:
            nav_options = ["📝 Submit Report"]

        page = st.radio(
            "Navigation",
            nav_options,
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
    
    elif page == "📈 Dashboard" and admin:
        st.title("📈 Employee Progress Dashboard")

        excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)

        # Load data
        with st.spinner("Loading data..."):
            df = read_excel_data(excel_path)

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

        # Show data table
        show_data_table(filtered_df)

    elif page == "⚙️ Settings" and admin:
        show_settings()

    elif page == "📧 Reminders" and admin:

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