        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.jira_url or not self.email or not self.api_token:
            return False, "Missing Jira credentials. Please configure JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN."
        
        try:
            self.jira_client = JIRA(
                server=self.jira_url,
                basic_auth=(self.email, self.api_token)
            )
            
            # Test connection by fetching user info
            current_user = self.jira_client.current_user()
            self._is_connected = True
            
            logger.info(f"Successfully connected to Jira as {current_user}")
            return True, f"Connected to Jira as {current_user}"
            
        except JIRAError as e:
            error_msg = f"Jira connection failed: {str(e)}"
            logger.error(error_msg)
            self._is_connected = False
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error connecting to Jira: {str(e)}"
            logger.error(error_msg)
            self._is_connected = False
            return False, error_msg
    
    def is_connected(self) -> bool:
        """Check if Jira client is connected"""
        return self._is_connected and self.jira_client is not None
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the Jira connection
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        return self.connect()
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of all accessible Jira projects
        
        Returns:
            List of project dictionaries with key, name, and id
        """
        if not self.is_connected():
            logger.warning("Not connected to Jira")
            return []
        
        try:
            projects = self.jira_client.projects()
            return [
                {
                    'key': project.key,
                    'name': project.name,
                    'id': project.id
                }
                for project in projects
            ]
        except JIRAError as e:
            logger.error(f"Failed to fetch projects: {str(e)}")
            return []
    
    def get_project_issue_types(self, project_key: str) -> List[Dict[str, str]]:
        """
        Get available issue types for a project
        
        Args:
            project_key: Jira project key
            
        Returns:
            List of issue type dictionaries
        """
        if not self.is_connected():
            return []
        
        try:
            project = self.jira_client.project(project_key)
            issue_types = self.jira_client.issue_types()
            
            return [
                {
                    'id': issue_type.id,
                    'name': issue_type.name,
                    'description': getattr(issue_type, 'description', '')
                }
                for issue_type in issue_types
            ]
        except JIRAError as e:
            logger.error(f"Failed to fetch issue types for {project_key}: {str(e)}")
            return []
    
    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str = "",
        issue_type: str = "Task",
        priority: str = "Medium",
        assignee: str = None,
        labels: List[str] = None,
        **custom_fields
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new Jira issue
        
        Args:
            project_key: Jira project key
            summary: Issue summary/title
            description: Issue description
            issue_type: Type of issue (Task, Story, Bug, etc.)
            priority: Priority level
            assignee: Username to assign (optional)
            labels: List of labels (optional)
            **custom_fields: Additional custom fields
            
        Returns:
            Tuple of (success: bool, message: str, issue_key: Optional[str])
        """
        if not self.is_connected():
            return False, "Not connected to Jira", None
        
        try:
            # Build issue dictionary
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
            
            # Add priority if specified
            if priority:
                issue_dict['priority'] = {'name': priority}
            
            # Add assignee if specified
            if assignee:
                issue_dict['assignee'] = {'name': assignee}
            
            # Add labels if specified
            if labels:
                issue_dict['labels'] = labels
            
            # Add any custom fields
            issue_dict.update(custom_fields)
            
            # Create the issue
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            
            logger.info(f"Created Jira issue: {new_issue.key}")
            return True, f"Issue created successfully: {new_issue.key}", new_issue.key
            
        except JIRAError as e:
            error_msg = f"Failed to create issue: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Unexpected error creating issue: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def update_issue_status(self, issue_key: str, status: str) -> Tuple[bool, str]:
        """
        Update issue status/transition
        
        Args:
            issue_key: Jira issue key (e.g., PROJ-123)
            status: Target status name
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_connected():
            return False, "Not connected to Jira"
        
        try:
            issue = self.jira_client.issue(issue_key)
            transitions = self.jira_client.transitions(issue)
            
            # Find matching transition
            transition_id = None
            for t in transitions:
                if t['name'].lower() == status.lower():
                    transition_id = t['id']
                    break
            
            if transition_id:
                self.jira_client.transition_issue(issue, transition_id)
                logger.info(f"Updated {issue_key} status to {status}")
                return True, f"Status updated to {status}"
            else:
                available = [t['name'] for t in transitions]
                return False, f"Status '{status}' not available. Available: {', '.join(available)}"
                
        except JIRAError as e:
            error_msg = f"Failed to update status: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error updating status: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def update_issue(self, issue_key: str, **fields) -> Tuple[bool, str]:
        """
        Update issue fields
        
        Args:
            issue_key: Jira issue key
            **fields: Fields to update
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_connected():
            return False, "Not connected to Jira"
        
        try:
            issue = self.jira_client.issue(issue_key)
            issue.update(fields=fields)
            
            logger.info(f"Updated issue {issue_key}")
            return True, f"Issue {issue_key} updated successfully"
            
        except JIRAError as e:
            error_msg = f"Failed to update issue: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def search_issues(
        self,
        project_key: str = None,
        assignee: str = None,
        status: str = None,
        jql: str = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for Jira issues
        
        Args:
            project_key: Filter by project
            assignee: Filter by assignee
            status: Filter by status
            jql: Custom JQL query (overrides other filters)
            max_results: Maximum number of results
            
        Returns:
            List of issue dictionaries
        """
        if not self.is_connected():
            return []
        
        try:
            # Build JQL query
            if jql:
                query = jql
            else:
                conditions = []
                if project_key:
                    conditions.append(f'project = {project_key}')
                if assignee:
                    conditions.append(f'assignee = {assignee}')
                if status:
                    conditions.append(f'status = "{status}"')
                
                query = ' AND '.join(conditions) if conditions else 'order by created DESC'
            
            # Search issues
            issues = self.jira_client.search_issues(query, maxResults=max_results)
            
            # Convert to dictionaries
            result = []
            for issue in issues:
                result.append({
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'description': getattr(issue.fields, 'description', ''),
                    'status': issue.fields.status.name,
                    'priority': getattr(issue.fields.priority, 'name', 'None'),
                    'assignee': getattr(issue.fields.assignee, 'displayName', 'Unassigned'),
                    'created': issue.fields.created,
                    'updated': issue.fields.updated,
                    'issue_type': issue.fields.issuetype.name,
                    'url': f"{self.jira_url}/browse/{issue.key}"
                })
            
            return result
            
        except JIRAError as e:
            logger.error(f"Failed to search issues: {str(e)}")
            return []
    
    def get_issue_details(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific issue
        
        Args:
            issue_key: Jira issue key
            
        Returns:
            Issue details dictionary or None
        """
        if not self.is_connected():
            return None
        
        try:
            issue = self.jira_client.issue(issue_key)
            
            return {
                'key': issue.key,
                'summary': issue.fields.summary,
                'description': getattr(issue.fields, 'description', ''),
                'status': issue.fields.status.name,
                'priority': getattr(issue.fields.priority, 'name', 'None'),
                'assignee': getattr(issue.fields.assignee, 'displayName', 'Unassigned'),
                'reporter': getattr(issue.fields.reporter, 'displayName', 'Unknown'),
                'created': issue.fields.created,
                'updated': issue.fields.updated,
                'issue_type': issue.fields.issuetype.name,
                'labels': issue.fields.labels,
                'url': f"{self.jira_url}/browse/{issue.key}"
            }
            
        except JIRAError as e:
            logger.error(f"Failed to get issue details: {str(e)}")
            return None
    
    def map_status_to_jira(self, internal_status: str) -> str:
        """
        Map internal status to Jira status
        
        Args:
            internal_status: Status from internal tracker
            
        Returns:
            Mapped Jira status
        """
        return self.status_mappings.get(internal_status, internal_status)
    
    def set_status_mapping(self, internal_status: str, jira_status: str):
        """
        Set custom status mapping
        
        Args:
            internal_status: Internal tracker status
            jira_status: Corresponding Jira status
        """
        self.status_mappings[internal_status] = jira_status
        logger.info(f"Set status mapping: {internal_status} -> {jira_status}")
    
    def bulk_create_issues_from_tasks(
        self,
        tasks: List[Dict[str, Any]],
        project_key: str,
        issue_type: str = "Task"
    ) -> Dict[str, Any]:
        """
        Bulk create Jira issues from task list
        
        Args:
            tasks: List of task dictionaries with keys: summary, description, priority, status
            project_key: Jira project key
            issue_type: Default issue type
            
        Returns:
            Dictionary with success count, failures, and created issue keys
        """
        if not self.is_connected():
            return {
                'success_count': 0,
                'failure_count': 0,
                'created_issues': [],
                'errors': ['Not connected to Jira']
            }
        
        results = {
            'success_count': 0,
            'failure_count': 0,
            'created_issues': [],
            'errors': []
        }
        
        for task in tasks:
            success, message, issue_key = self.create_issue(
                project_key=project_key,
                summary=task.get('summary', 'Untitled Task'),
                description=task.get('description', ''),
                issue_type=issue_type,
                priority=task.get('priority', 'Medium')
            )
            
            if success and issue_key:
                results['success_count'] += 1
                results['created_issues'].append(issue_key)
            else:
                results['failure_count'] += 1
                results['errors'].append(f"Failed: {task.get('summary', 'Unknown')} - {message}")
        
        return results
    
    def get_sprints(self, board_id: int) -> List[Dict[str, Any]]:
        """
        Get sprints for an agile board
        
        Args:
            board_id: Jira board ID
            
        Returns:
            List of sprint dictionaries
        """
        if not self.is_connected():
            return []
        
        try:
            sprints = self.jira_client.sprints(board_id)
            return [
                {
                    'id': sprint.id,
                    'name': sprint.name,
                    'state': sprint.state,
                    'startDate': getattr(sprint, 'startDate', None),
                    'endDate': getattr(sprint, 'endDate', None)
                }
                for sprint in sprints
            ]
        except Exception as e:
            logger.error(f"Failed to fetch sprints: {str(e)}")
            return []


# Convenience functions for quick operations

def quick_connect() -> Optional[JiraIntegration]:
    """
    Quick connect to Jira using environment variables
    
    Returns:
        JiraIntegration instance if successful, None otherwise
    """
    try:
        jira = JiraIntegration()
        success, message = jira.connect()
        if success:
            return jira
        else:
            logger.error(f"Quick connect failed: {message}")
            return None
    except Exception as e:
        logger.error(f"Quick connect error: {str(e)}")
        return None


def create_task_issue(
    summary: str,
    description: str = "",
    project_key: str = None,
    priority: str = "Medium"
) -> Tuple[bool, str, Optional[str]]:
    """
    Quick function to create a task issue
    
    Args:
        summary: Task summary
        description: Task description
        project_key: Jira project key (uses JIRA_DEFAULT_PROJECT env if not provided)
        priority: Task priority
        
    Returns:
        Tuple of (success, message, issue_key)
    """
    project_key = project_key or os.getenv('JIRA_DEFAULT_PROJECT', '')
    
    if not project_key:
        return False, "No project key specified", None
    
    jira = quick_connect()
    if not jira:
        return False, "Failed to connect to Jira", None
    
    return jira.create_issue(
        project_key=project_key,
        summary=summary,
        description=description,
        priority=priority
    )