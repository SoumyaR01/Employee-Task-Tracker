import streamlit as st
import pandas as pd
from datetime import datetime
import json
from pathlib import Path

try:
    from jira_integration import JiraIntegration
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False


def show_jira_settings_panel(config, save_callback=None):
    """
    Display Jira configuration panel in admin settings
    
    Args:
        config: Current configuration dictionary
        save_callback: Optional function to save configuration to disk
        
    Returns:
        Updated configuration dictionary
    """
    st.subheader("🔗 Jira Integration Settings")
    
    if not JIRA_AVAILABLE:
        st.error("❌ Jira library not installed. Run: `pip install jira>=3.5.0`")
        return config
    
    # Get current Jira config
    jira_config = config.get('jira', {})
    
    with st.form("jira_settings_form"):
        st.markdown("### Connection Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            jira_url = st.text_input(
                "Jira URL",
                value=jira_config.get('url', ''),
                placeholder="https://your-domain.atlassian.net",
                help="Your Jira instance URL"
            )
        
        with col2:
            jira_email = st.text_input(


def show_jira_connection_test():
    """Display Jira connection test panel"""
    st.markdown("---")
    st.subheader("🔌 Test Jira Connection")
    
    if not JIRA_AVAILABLE:
        st.error("Jira library not available")
        return
    
    if st.button("🧪 Test Connection", use_container_width=True):
        with st.spinner("Testing Jira connection..."):
            try:
                jira = JiraIntegration()
                success, message = jira.test_connection()
                
                if success:
                    st.success(f"✅ {message}")
                    
                    # Show available projects
                    st.markdown("#### Available Projects")
                    projects = jira.get_projects()
                    if projects:
                        df = pd.DataFrame(projects)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No projects found or no access")
                else:
                    st.error(f"❌ {message}")
                    st.info("Please check your credentials in `.env` file")
                    
            except Exception as e:
                st.error(f"❌ Connection test failed: {str(e)}")


def show_jira_sync_panel(config, excel_file_path=None, read_excel_data_func=None):
    """
    Display Jira sync operations panel for admin
    
    Args:
        config: Application configuration
        excel_file_path: Path to Excel file (if None, will prompt user)
        read_excel_data_func: Function to read Excel data (if None, will use pandas)
    """
    st.markdown("---")
    st.subheader("🔄 Jira Sync Operations")
    
    jira_config = config.get('jira', {})
    
    if not jira_config.get('enabled', False):
        st.warning("Jira integration is disabled. Enable it in settings first.")
        return
    
    if not JIRA_AVAILABLE:
        st.error("Jira library not available")
        return
    
    # Sync tasks to Jira
    st.markdown("#### Bulk Create Issues from Tasks")
    st.caption("Create Jira issues from existing employee tasks")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From Date", value=datetime.now().date())
    with col2:
        end_date = st.date_input("To Date", value=datetime.now().date())
    
    project_key = st.text_input(
        "Target Project",
        value=jira_config.get('default_project', ''),
        placeholder="PROJ"
    )
    
    if st.button("🚀 Sync Tasks to Jira", use_container_width=True):
        if not project_key:
            st.error("Please specify a project key")
            return
        
        # Check if we have the required parameters
        if not excel_file_path:
            st.error("Excel file path not configured. Please configure in Settings.")
            return
        
        with st.spinner("Syncing tasks to Jira..."):
            try:
                # Read Excel data
                if read_excel_data_func:
                    df = read_excel_data_func(excel_file_path)
                else:
                    # Fallback to direct pandas read
                    import os
                    if not os.path.exists(excel_file_path):
                        st.error(f"Excel file not found: {excel_file_path}")
                        return
                    df = pd.read_excel(excel_file_path, engine='openpyxl')
                
                if df is None or df.empty:
                    st.warning("No tasks found to sync")
                    return
                
                # Filter by date
                df['Date'] = pd.to_datetime(df['Date'])
                filtered_df = df[
                    (df['Date'].dt.date >= start_date) &
                    (df['Date'].dt.date <= end_date)
                ]
                
                if filtered_df.empty:
                    st.info(f"No tasks found between {start_date} and {end_date}")
                    return
                
                # Convert to task list
                tasks = []
                for _, row in filtered_df.iterrows():
                    task = {
                        'summary': row.get('Task Title', 'Untitled Task'),
                        'description': f"""
**Employee:** {row.get('Name', 'Unknown')}
**Project:** {row.get('Project Name', 'N/A')}
**Date:** {row.get('Date', 'N/A')}
**Assigned By:** {row.get('Task Assigned By', 'N/A')}

**Details:**
{row.get('Plan for next day', '')}

**Support Request:**
{row.get('Support Request', 'None')}
                        """.strip(),
                        'priority': row.get('Task Priority', 'Medium')
                    }
                    tasks.append(task)
                
                # Sync to Jira
                jira = JiraIntegration()
                success, message = jira.connect()
                
                if not success:
                    st.error(f"Failed to connect: {message}")
                    return
                
                results = jira.bulk_create_issues_from_tasks(
                    tasks=tasks,
                    project_key=project_key,
                    issue_type=jira_config.get('default_issue_type', 'Task')
                )
                
                # Show results
                st.success(f"✅ Created {results['success_count']} issues")
                
                if results['failure_count'] > 0:
                    st.warning(f"⚠️ {results['failure_count']} failures")
                    with st.expander("View Errors"):
                        for error in results['errors']:
                            st.error(error)
                
                if results['created_issues']:
                    st.markdown("**Created Issues:**")
                    for issue_key in results['created_issues']:
                        jira_url = jira.jira_url
                        st.markdown(f"- [{issue_key}]({jira_url}/browse/{issue_key})")
                        
            except Exception as e:
                st.error(f"❌ Sync failed: {str(e)}")



def show_jira_dashboard_tab():
    """Display Jira issues in a dashboard tab"""
    st.subheader("📋 Jira Issues")
    
    if not JIRA_AVAILABLE:
        st.error("Jira integration not available")
        return
    
    try:
        jira = JiraIntegration()
        success, message = jira.connect()
        
        if not success:
            st.error(f"Connection failed: {message}")
            return
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            projects = jira.get_projects()
            project_options = ['All'] + [p['key'] for p in projects]
            selected_project = st.selectbox("Project", project_options)
        
        with col2:
            status_filter = st.selectbox(
                "Status",
                ['All', 'To Do', 'In Progress', 'Done', 'Blocked']
            )
        
        with col3:
            max_results = st.number_input("Max Results", min_value=10, max_value=100, value=50)
        
        # Search issues
        issues = jira.search_issues(
            project_key=selected_project if selected_project != 'All' else None,
            status=status_filter if status_filter != 'All' else None,
            max_results=max_results
        )
        
        if issues:
            st.markdown(f"**Found {len(issues)} issues**")
            
            # Convert to DataFrame
            df = pd.DataFrame(issues)
            
            # Format for display
            display_df = df[[
                'key', 'summary', 'status', 'priority',
                'assignee', 'created', 'updated'
            ]].copy()
            
            display_df['created'] = pd.to_datetime(display_df['created']).dt.strftime('%Y-%m-%d')
            display_df['updated'] = pd.to_datetime(display_df['updated']).dt.strftime('%Y-%m-%d')
            
            st.dataframe(display_df, use_container_width=True)
            
            # Add links to Jira
            st.markdown("**Quick Links:**")
            for _, issue in df.iterrows():
                st.markdown(f"- [{issue['key']}: {issue['summary']}]({issue['url']})")
        else:
            st.info("No issues found matching the criteria")
            
    except Exception as e:
        st.error(f"Failed to load Jira issues: {str(e)}")


def add_jira_create_checkbox(task_data, config):
    """
    Add 'Create Jira Issue' checkbox to task submission form
    
    Args:
        task_data: Dictionary containing task information
        config: Application configuration
        
    Returns:
        Tuple of (should_create_jira_issue: bool, updated_task_data: dict)
    """
    jira_config = config.get('jira', {})
    
    if not jira_config.get('enabled', False) or not JIRA_AVAILABLE:
        return False, task_data
    
    st.markdown("---")
    st.markdown("#### 🔗 Jira Integration")
    
    create_jira = st.checkbox(
        "Create Jira Issue",
        value=jira_config.get('auto_create_on_submit', False),
        help="Automatically create a Jira issue for this task"
    )
    
    if create_jira:
        col1, col2 = st.columns(2)
        with col1:
            issue_type = st.selectbox(
                "Issue Type",
                options=["Task", "Story", "Bug"],
                index=0
            )
        with col2:
            project_key = st.text_input(
                "Project Key",
                value=jira_config.get('default_project', ''),
                placeholder="PROJ"
            )
        
        task_data['jira_issue_type'] = issue_type
        task_data['jira_project_key'] = project_key
    
    return create_jira, task_data


def create_jira_issue_from_task(task_data, config):
    """
    Create a Jira issue from task data
    
    Args:
        task_data: Dictionary containing task information
        config: Application configuration
        
    Returns:
        Tuple of (success: bool, message: str, issue_key: str or None)
    """
    if not JIRA_AVAILABLE:
        return False, "Jira integration not available", None
    
    jira_config = config.get('jira', {})
    
    try:
        jira = JiraIntegration()
        success, message = jira.connect()
        
        if not success:
            return False, f"Connection failed: {message}", None
        
        # Build issue
        summary = task_data.get('Task Title', 'Untitled Task')
        description = f"""
**Employee:** {task_data.get('Name', 'Unknown')}
**Project:** {task_data.get('Project Name', 'N/A')}
**Date:** {task_data.get('Date', 'N/A')}
**Priority:** {task_data.get('Task Priority', 'Medium')}
**Status:** {task_data.get('Task Status', 'Not Started')}

**Task Details:**
{task_data.get('Plan for next day', 'No details provided')}

**Support Request:**
{task_data.get('Support Request', 'None')}

**Effort:** {task_data.get('Effort (in hours)', 'N/A')} hours
        """.strip()
        
        priority = jira_config.get('priority_mappings', {}).get(
            task_data.get('Task Priority', 'Medium'),
            'Medium'
        )
        
        success, msg, issue_key = jira.create_issue(
            project_key=task_data.get('jira_project_key', jira_config.get('default_project', '')),
            summary=summary,
            description=description,
            issue_type=task_data.get('jira_issue_type', jira_config.get('default_issue_type', 'Task')),
            priority=priority,
            labels=['employee-tracker', 'auto-created']
        )
        
        return success, msg, issue_key
        
    except Exception as e:
        return False, f"Failed to create issue: {str(e)}", None
