# Employee Progress Tracker - Project Documentation

## Image 1: Settings Page - Email Configuration
The Settings page provides email configuration options for the reminder system. Administrators can configure admin email addresses and employee email lists (one per line) for automated reminder notifications. The page includes a "Save Settings" button and a diagnostic tool to test Excel file connections and check for potential issues.

## Image 2: Settings Page - Excel File and Reminder Configuration
This view shows the Excel file path configuration (`D:\Employee Track Report\task_tracker.xlsx`) and reminder settings interface. Users can set the reminder time (18:00) and select which days of the week reminders should be sent (Monday through Saturday are enabled, Sunday is disabled). These settings ensure automated reminders are sent only on specified workdays.

## Image 3: Reminder Management Page
The Reminder Management page displays information about the automated email reminder system for daily reports. It includes a test functionality that checks for missing reports and shows a success message when all employees have submitted their reports for the day. This page helps administrators monitor and test the reminder system's functionality.

## Image 4: Dashboard - Recent Submissions Table
The Recent Submissions table displays all submitted work progress reports with detailed information including date, work mode, employee ID, name, project name, task details, priority, status, and plans for the next day. The table includes search functionality, row count selection (currently set to 50), and a CSV download option for data export and analysis.

## Image 5: Dashboard - Task Status and Priority Distribution Charts
This dashboard view shows two analytical charts: a pie chart displaying task status distribution (showing 100% completed tasks) and a bar chart showing priority distribution (displaying Medium priority tasks). These visualizations help managers quickly understand task completion rates and priority levels across all employee submissions.

## Image 6: Dashboard - Weekly Submission Trend
The Weekly Submission Trend chart displays a line graph showing the number of submissions over time, with dates on the X-axis and submission counts on the Y-axis. This visualization helps track submission patterns and identify trends in employee reporting behavior throughout the week.

## Image 7: Dashboard - Employee Progress Overview with KPIs
The Employee Progress Dashboard displays four key performance indicators: Total Submissions (3), Today's Reports (3), Active Employees (1), and Completed Tasks (2). Below the KPIs, a comprehensive filter section allows filtering by employee, project, status, priority, and date range (2025/11/01 to 2025/11/08) for detailed analysis.

## Image 8: Submit Report Page - Employee Information Section
The Submit Report page features the IITM PRAVARTAK logo and a form for employees to submit their daily work progress reports. The Employee Information section is pre-filled with date (2025/11/08), employee ID (P-1260), work mode (PTF), and name (Soumya Ranjan), followed by a section for entering today's tasks.

## Image 9: Submit Report Page with Excel Integration
This split-screen view shows the Submit Report web application interface alongside the corresponding Excel spreadsheet (`task_tracker.xlsx`). The image demonstrates how employee submissions are directly recorded in the Excel file, with task details including employee information, project name, task title, assigned by, status, and priority being synchronized between the web form and the Excel database.

---

## Summary
The Employee Progress Tracker is a comprehensive web-based application built with Streamlit that enables employees to submit daily work progress reports, which are automatically stored in an Excel file. The system includes a dashboard with analytics, automated email reminders for missing reports, configurable settings, and real-time data visualization to help managers track employee productivity and task completion across projects.



