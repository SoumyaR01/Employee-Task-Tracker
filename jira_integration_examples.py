"""
Example Integration Code for Jira into main.py

This file demonstrates how to integrate the Jira UI components into your main.py file.
Copy and paste these code snippets into the appropriate locations in main.py.
"""

# ========================================================================
# 1. ADD TO IMPORTS SECTION (Already done in main.py around line 26)
# ========================================================================
"""
try:
    from jira_ui_components import (
        show_jira_settings_panel,
        show_jira_connection_test,
        show_jira_sync_panel,
        show_jira_dashboard_tab,
        add_jira_create_checkbox,
        create_jira_issue_from_task
    )
    JIRA_UI_AVAILABLE = True
except ImportError:
    JIRA_UI_AVAILABLE = False
"""

# ========================================================================
# 2. ADD TO ADMIN SETTINGS PAGE (in show_settings or show_admin_settings function)
# ========================================================================
"""
def show_admin_settings():
    # ... existing code ...
    
    # ADD THIS SECTION:
    # Jira Integration Settings
    if JIRA_UI_AVAILABLE:
        st.markdown("---")
        config = show_jira_settings_panel(config)
        show_jira_connection_test()
        
        # Pass excel_file_path and read_excel_data function to avoid circular import
        excel_path = config.get('excel_file_path', EXCEL_FILE_PATH)
        show_jira_sync_panel(config, excel_file_path=excel_path, read_excel_data_func=read_excel_data)
    else:
        st.warning("Jira UI components not available. Install jira library.")
    
    # ... rest of existing code ...
"""

# ========================================================================
# 3. ADD JIRA TAB TO PERFORMANCE DASHBOARD
# ========================================================================
"""
def render_full_performance_dashboard():
    # ... existing tabs code ...
    
    # Modify your tabs section to include Jira:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "👥 Employee Performance",
        "📈 Performance Trends",
        "📋 Recent Submissions",
        "🔗 Jira Issues"  # <-- Add this tab
    ])
    
    # ... existing tab content ...
    
    # ADD THIS NEW TAB:
    with tab5:
        if JIRA_UI_AVAILABLE:
            show_jira_dashboard_tab()
        else:
            st.warning("Jira integration not available")
"""

# ========================================================================
# 4. ADD TO TASK SUBMISSION FORM
# ========================================================================
"""
def show_submit_report():
    # ... existing form code ...
    
    with st.form("task_submission_form"):
        # ... existing form fields ...
        
        # ADD THIS BEFORE THE SUBMIT BUTTON:
        create_jira_issue = False
        task_data = {}  # Your existing task data dictionary
        
        if JIRA_UI_AVAILABLE:
            create_jira_issue, task_data = add_jira_create_checkbox(task_data, config)
        
        submitted = st.form_submit_button("Submit Report")
        
        if submitted:
            # ... existing validation ...
            
            # Prepare task data
            task_data = {
                'Date': str(datetime.now().date()),
                'Work Mode': work_mode,
                'Emp Id': st.session_state.emp_id,
                'Name': st.session_state.emp_name,
                'Project Name': project_name,
                'Task Title': task_title,
                'Task Assigned By': task_assigned_by,
                'Task Priority': task_priority,
                'Task Status': task_status,
                'Plan for next day': PLAN_FOR_NEXT_DAY,
                'Support Request': support_request,
                'Availability': availability,
                'Effort (in hours)': effort,
                'Employee Performance (%)': performance
            }
            
            # ... existing save to Excel code ...
            
            # ADD THIS AFTER SUCCESSFUL EXCEL SAVE:
            jira_issue_key = None
            if create_jira_issue and JIRA_UI_AVAILABLE:
                success, message, jira_issue_key = create_jira_issue_from_task(task_data, config)
                if success:
                    jira_url = config.get('jira', {}).get('url', '')
                    st.success(f"✅ Jira issue created: [{jira_issue_key}]({jira_url}/browse/{jira_issue_key})")
                else:
                    st.warning(f"⚠️ Task saved but Jira issue creation failed: {message}")
"""

# ========================================================================
# 5. ADD TO ADMIN MENU (if needed)
# ========================================================================
"""
def show_admin_dashboard():
    # In the admin menu, you can add a dedicated Jira management page
    admin_pages = [
        "📊 Performance Dashboard",
        "Staff Attendance View",
        "💬 Chatbot",
        "👤 Employee Management",
        "⚙️ Settings",
        "📧 Reminders",
        "🔗 Jira Management"  # <-- Add this option
    ]
    
    # ... existing code ...
    
    elif admin_page == "🔗 Jira Management":
        st.title("🔗 Jira Integration Management")
        if JIRA_UI_AVAILABLE:
            config = load_config()
            show_jira_connection_test()
            st.markdown("---")
            show_jira_sync_panel(config)
            st.markdown("---")
            show_jira_dashboard_tab()
        else:
            st.error("Jira integration not available")
"""

# ========================================================================
# COMPLETE EXAMPLE: Full Integration Snippet
# ========================================================================

# At the top of main.py, after existing imports:
INTEGRATION_EXAMPLE = """
# Import Jira UI components
try:
    from jira_ui_components import (
        show_jira_settings_panel,
        show_jira_connection_test,
        show_jira_sync_panel,
        show_jira_dashboard_tab,
        add_jira_create_checkbox,
        create_jira_issue_from_task
    )
    JIRA_UI_AVAILABLE = True
except ImportError:
    JIRA_UI_AVAILABLE = False
    print("Warning: Jira UI components not available")
"""

print(__doc__)
print("\nIntegration complete! Follow the examples above to add Jira to your main.py")
