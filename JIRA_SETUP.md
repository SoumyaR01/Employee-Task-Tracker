# Jira Integration Setup & Usage Guide

This guide will help you set up and use the Jira integration in the Employee Progress Tracker application.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
3. [Configuration](#configuration)
4. [Using Jira Integration](#using-jira-integration)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have:

- ✅ A Jira account (Cloud or Server)
- ✅ Access to a Jira project
- ✅ Permission to create issues in that project
- ✅ Python 3.7+ installed

## Setup Instructions

### Step 1: Install Dependencies

The Jira library has been added to `requirements.txt`. Install it by running:

```bash
pip install -r requirements.txt
```

Or install just the Jira library:

```bash
pip install jira>=3.5.0
```

### Step 2: Generate Jira API Token

1. **Log in to your Atlassian account**
   - Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

2. **Create API Token**
   - Click **"Create API token"**
   - Give it a descriptive label (e.g., "Employee Tracker Integration")
   - Click **"Create"**

3. **Copy the Token**
   - **IMPORTANT:** Copy the token immediately! You won't be able to see it again
   - Store it securely (do NOT commit it to version control)

### Step 3: Configure Environment Variables

Create or edit your `.env` file in the project root directory:

```env
# Jira Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_api_token_here
JIRA_DEFAULT_PROJECT=PROJ
```

Replace:
- `your-domain` with your Jira workspace name
- `your.email@company.com` with the email associated with your Jira account
- `your_api_token_here` with the API token you generated
- `PROJ` with your default project key

**Security Note:** Never commit your `.env` file to version control! It's already in `.gitignore`.

## Configuration

### Admin Panel Configuration

1. **Launch the application:**
   ```bash
   streamlit run main.py
   ```

2. **Log in as Admin**

3. **Navigate to Settings** (⚙️ Settings in the admin panel)

4. **Scroll to Jira Integration Settings**

5. **Configure the following:**

   - **Jira URL:** Your Jira instance URL
   - **Jira Email:** Your Jira account email
   - **Default Project Key:** The project where issues will be created (e.g., `PROJ`)
   - **Default Issue Type:** Task, Story, or Bug
   - **Enable Jira Integration:** Check this box to activate
   - **Auto-create on submission:** Optionally auto-create Jira issues when tasks are submitted

6. **Configure Status Mappings:**
   
   Map your internal task statuses to Jira workflow states:
   | Internal Status | Jira Status |
   |----------------|-------------|
   | Not Started    | To Do       |
   | In Progress    | In Progress |
   | Completed      | Done        |
   | On Hold        | On Hold     |
   | Blocked        | Blocked     |

7. **Save Settings**

### Test the Connection

After configuration:

1. Scroll to **Test Jira Connection** section
2. Click **🧪 Test Connection**
3. Verify that:
   - Connection is successful ✅
   - Your projects are listed

## Using Jira Integration

### For Admins

#### View Jira Issues Dashboard

1. Navigate to **📊 Performance Dashboard**
2. Switch to the **Jira Issues** tab
3. Filter issues by:
   - Project
   - Status
   - Assignee
4. Click on issue links to open them in Jira

#### Bulk Sync Tasks to Jira

1. Go to **⚙️ Settings**
2. Scroll to **🔄 Jira Sync Operations**
3. Select date range for tasks to sync
4. Specify target project
5. Click **🚀 Sync Tasks to Jira**
6. Review results:
   - Success count
   - Created issue links
   - Any errors

### For Employees

#### Create Jira Issue with Task Submission

1. Go to **📝 Submit Report**
2. Fill in your task details
3. Scroll to **🔗 Jira Integration** section
4. Check **Create Jira Issue**
5. Select:
   - Issue Type (Task/Story/Bug)
   - Project Key (or use default)
6. Submit the form
7. View the created Jira issue link in the success message

## Troubleshooting

### Connection Issues

**Problem:** "Connection failed: Unauthorized"

**Solutions:**
- Verify your API token is correct
- Ensure your email matches your Jira account
- Check that the API token hasn't expired
- Regenerate the API token if necessary

---

**Problem:** "Connection failed: Could not reach Jira"

**Solutions:**
- Check your Jira URL format (should be `https://your-domain.atlassian.net`)
- Verify you have internet connectivity
- Check if Jira is accessible from your network

---

### Issue Creation Failures

**Problem:** "Failed to create issue: Project not found"

**Solutions:**
- Verify the project key is correct (case-sensitive!)
- Ensure you have access to the project
- Check project permissions in Jira

---

**Problem:** "Failed to create issue: Field validation failed"

**Solutions:**
- Some Jira projects have required custom fields
- Check your Jira project settings
- Contact your Jira admin to make custom fields optional or provide defaults

---

### Import Errors

**Problem:** "Jira library not installed"

**Solution:**
```bash
pip install jira>=3.5.0
```

---

**Problem:** "ImportError: No module named 'jira_integration'"

**Solutions:**
- Ensure`jira_integration.py` is in the project directory
- Verify you're running from the correct directory
- Try restarting the Streamlit app

---

### Status Mapping Issues

**Problem:** "Status 'XYZ' not available"

**Solutions:**
- The target status doesn't exist in your Jira workflow
- Check available transitions in Jira
- Update status mappings in the settings to match your Jira workflow

---

## Advanced Configuration

### Custom Status Mappings

Edit `config.json` manually to add custom status mappings:

```json
{
  "jira": {
    "status_mappings": {
      "Not Started": "To Do",
      "In Progress": "In Progress",
      "Testing": "In Review",
      "Completed": "Done",
      "Custom Status": "Your Jira Status"
    }
  }
}
```

### Priority Mappings

```json
{
  "jira": {
    "priority_mappings": {
      "Low": "Low",
      "Medium": "Medium",
      "High": "High",
      "Critical": "Highest"
    }
  }
}
```

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Rotate API tokens** regularly (every 90 days recommended)
3. **Use read/write permissions** only for necessary projects
4. **Revoke unused tokens** from your Atlassian account
5. **Use environment variables** for all sensitive data

## Support

If you encounter issues not covered in this guide:

1. Check Jira's [API documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
2. Review the [jira-python library docs](https://jira.readthedocs.io/)
3. Check the application logs for detailed error messages
4. Contact your system administrator

## Features Overview

### ✅ Implemented Features

- ✅ Connect to Jira Cloud/Server via API
- ✅ Create issues from employee tasks
- ✅ Bulk sync existing tasks
- ✅ View Jira issues in dashboard
- ✅ Customizable status/priority mappings
- ✅ Auto-create on task submission
- ✅ Connection testing

### 🔮 Potential Future Enhancements

- 🔮 Bidirectional sync (Jira → Tracker)
- 🔮 Webhook support for real-time updates
- 🔮 Attach files to Jira issues
- 🔮 Link tasks to existing issues
- 🔮 Sprint management
- 🔮 Worklog tracking

---

**Happy syncing! 🎉**
