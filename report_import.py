import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_uploaded_file(uploaded_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Parse uploaded CSV or XLSX file and return DataFrame
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Tuple of (DataFrame, error_message)
        If successful: (df, None)
        If failed: (None, error_message)
    """
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'csv':
            # Try multiple encodings for CSV files
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            last_error = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    df = pd.read_csv(uploaded_file, encoding=encoding)
                    logger.info(f"Successfully read CSV with {encoding} encoding")
                    break
                except (UnicodeDecodeError, Exception) as e:
                    last_error = e
                    continue
            
            if df is None:
                return None, f"Could not read CSV file with any supported encoding. Last error: {str(last_error)}"
                
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file)
        else:
            return None, f"Unsupported file format: .{file_extension}. Please upload CSV or XLSX files only."
        
        if df.empty:
            return None, "The uploaded file is empty. Please upload a file with data."
        
        logger.info(f"Successfully parsed {file_extension.upper()} file with {len(df)} rows and {len(df.columns)} columns")
        return df, None
        
    except Exception as e:
        logger.error(f"Error parsing file: {str(e)}")
        return None, f"Error reading file: {str(e)}"


def validate_report_data(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    """
    Validate that the DataFrame has required columns and proper data
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if df is None or df.empty:
        return False, "DataFrame is empty"
    
    # Check for at least one employee identifier column
    identifier_columns = ['Name', 'name', 'Employee Name', 'emp_id', 'Employee ID', 'EMP_ID']
    has_identifier = any(col in df.columns for col in identifier_columns)
    
    if not has_identifier:
        return False, f"Missing employee identifier column. Expected one of: {', '.join(identifier_columns)}"
    
    # Optional but recommended columns
    recommended_columns = ['Employee Performance (%)', 'Performance', 'Task Status', 'Date']
    missing_recommended = [col for col in recommended_columns if col not in df.columns]
    
    if missing_recommended:
        logger.warning(f"Missing recommended columns: {', '.join(missing_recommended)}")
    
    return True, None


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to standard format for easier processing
    
    Args:
        df: DataFrame with potentially varied column names
        
    Returns:
        DataFrame with normalized column names
    """
    df = df.copy()
    
    # Create a mapping of common variations to standard names
    column_mapping = {
        # Employee identifier variations
        'employee name': 'Name',
        'emp_id': 'Name',
        'employee id': 'Name',
        'employee': 'Name',
        
        # Performance variations
        'performance': 'Employee Performance (%)',
        'performance (%)': 'Employee Performance (%)',
        'employee performance': 'Employee Performance (%)',
        'perf': 'Employee Performance (%)',
        
        # Status variations
        'status': 'Task Status',
        'task_status': 'Task Status',
        'work status': 'Task Status',
        
        # Date variations
        'date': 'Date',
        'submission date': 'Date',
        'report date': 'Date',
    }
    
    # Apply mapping (case-insensitive)
    for col in df.columns:
        # Convert column to string to handle numeric or other types
        col_str = str(col)
        col_lower = col_str.lower().strip()
        if col_lower in column_mapping:
            df.rename(columns={col: column_mapping[col_lower]}, inplace=True)
    
    return df


def calculate_overall_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate aggregate metrics across all employees
    
    Args:
        df: DataFrame with employee data
        
    Returns:
        Dictionary with overall metrics
    """
    metrics = {}
    
    # Total employees
    name_col = next((col for col in ['Name', 'Employee Name', 'emp_id'] if col in df.columns), None)
    if name_col:
        metrics['total_employees'] = df[name_col].nunique()
        metrics['total_records'] = len(df)
    else:
        metrics['total_employees'] = 0
        metrics['total_records'] = len(df)
    
    # Performance metrics
    perf_col = next((col for col in ['Employee Performance (%)', 'Performance', 'performance'] if col in df.columns), None)
    if perf_col:
        # Ensure numeric
        df[perf_col] = pd.to_numeric(df[perf_col], errors='coerce')
        metrics['avg_performance'] = round(df[perf_col].mean(), 2)
        metrics['min_performance'] = round(df[perf_col].min(), 2)
        metrics['max_performance'] = round(df[perf_col].max(), 2)
        metrics['median_performance'] = round(df[perf_col].median(), 2)
    else:
        metrics['avg_performance'] = 0
        metrics['min_performance'] = 0
        metrics['max_performance'] = 0
        metrics['median_performance'] = 0
    
    # Task completion metrics
    status_col = next((col for col in ['Task Status', 'Status', 'status'] if col in df.columns), None)
    if status_col:
        total_tasks = len(df)
        completed_tasks = len(df[df[status_col].astype(str).str.lower().str.contains('complet', na=False)])
        metrics['total_tasks'] = total_tasks
        metrics['completed_tasks'] = completed_tasks
        metrics['completion_rate'] = round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0
    else:
        metrics['total_tasks'] = len(df)
        metrics['completed_tasks'] = 0
        metrics['completion_rate'] = 0
    
    # Date range
    date_col = next((col for col in ['Date', 'Submission Date', 'date'] if col in df.columns), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        valid_dates = df[date_col].dropna()
        if not valid_dates.empty:
            metrics['date_range_start'] = valid_dates.min().strftime('%Y-%m-%d')
            metrics['date_range_end'] = valid_dates.max().strftime('%Y-%m-%d')
        else:
            metrics['date_range_start'] = None
            metrics['date_range_end'] = None
    else:
        metrics['date_range_start'] = None
        metrics['date_range_end'] = None
    
    return metrics


def calculate_employee_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate per-employee performance metrics
    
    Args:
        df: DataFrame with employee data
        
    Returns:
        DataFrame with per-employee metrics
    """
    name_col = next((col for col in ['Name', 'Employee Name', 'emp_id'] if col in df.columns), None)
    if not name_col:
        return pd.DataFrame()
    
    employee_metrics = []
    
    for emp_name in df[name_col].unique():
        emp_df = df[df[name_col] == emp_name]
        emp_metric = {'Employee': emp_name}
        
        # Performance
        perf_col = next((col for col in ['Employee Performance (%)', 'Performance'] if col in df.columns), None)
        if perf_col:
            emp_df[perf_col] = pd.to_numeric(emp_df[perf_col], errors='coerce')
            emp_metric['Avg Performance (%)'] = round(emp_df[perf_col].mean(), 2)
            emp_metric['Max Performance (%)'] = round(emp_df[perf_col].max(), 2)
            emp_metric['Min Performance (%)'] = round(emp_df[perf_col].min(), 2)
        else:
            # Add default values if performance column doesn't exist
            emp_metric['Avg Performance (%)'] = 0
            emp_metric['Max Performance (%)'] = 0
            emp_metric['Min Performance (%)'] = 0
        
        # Task counts
        status_col = next((col for col in ['Task Status', 'Status'] if col in df.columns), None)
        if status_col:
            emp_metric['Total Tasks'] = len(emp_df)
            emp_metric['Completed Tasks'] = len(emp_df[emp_df[status_col].astype(str).str.lower().str.contains('complet', na=False)])
            emp_metric['Completion Rate (%)'] = round((emp_metric['Completed Tasks'] / emp_metric['Total Tasks'] * 100), 2) if emp_metric['Total Tasks'] > 0 else 0
        else:
            emp_metric['Total Tasks'] = len(emp_df)
            emp_metric['Completed Tasks'] = 0
            emp_metric['Completion Rate (%)'] = 0
        
        # Submissions count
        emp_metric['Submissions'] = len(emp_df)
        
        employee_metrics.append(emp_metric)
    
    result_df = pd.DataFrame(employee_metrics)
    
    # Only sort by performance if the column exists and has valid data
    if 'Avg Performance (%)' in result_df.columns and result_df['Avg Performance (%)'].notna().any():
        return result_df.sort_values('Avg Performance (%)', ascending=False, na_position='last')
    else:
        return result_df


def calculate_resource_utilization(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate resource utilization and efficiency metrics
    
    Args:
        df: DataFrame with employee data
        
    Returns:
        Dictionary with resource utilization metrics
    """
    metrics = {}
    
    # Performance distribution
    perf_col = next((col for col in ['Employee Performance (%)', 'Performance'] if col in df.columns), None)
    if perf_col:
        df[perf_col] = pd.to_numeric(df[perf_col], errors='coerce')
        
        # Categorize performance
        excellent = len(df[df[perf_col] >= 90])
        good = len(df[(df[perf_col] >= 70) & (df[perf_col] < 90)])
        needs_improvement = len(df[df[perf_col] < 70])
        
        total = len(df[df[perf_col].notna()])
        
        metrics['performance_distribution'] = {
            'excellent': excellent,
            'good': good,
            'needs_improvement': needs_improvement,
            'excellent_pct': round((excellent / total * 100), 2) if total > 0 else 0,
            'good_pct': round((good / total * 100), 2) if total > 0 else 0,
            'needs_improvement_pct': round((needs_improvement / total * 100), 2) if total > 0 else 0,
        }
    else:
        metrics['performance_distribution'] = {
            'excellent': 0, 'good': 0, 'needs_improvement': 0,
            'excellent_pct': 0, 'good_pct': 0, 'needs_improvement_pct': 0
        }
    
    # Task productivity
    status_col = next((col for col in ['Task Status', 'Status'] if col in df.columns), None)
    if status_col:
        total_tasks = len(df)
        completed = len(df[df[status_col].astype(str).str.lower().str.contains('complet', na=False)])
        in_progress = len(df[df[status_col].astype(str).str.lower().str.contains('progress', na=False)])
        
        metrics['productivity'] = {
            'completion_rate': round((completed / total_tasks * 100), 2) if total_tasks > 0 else 0,
            'in_progress_rate': round((in_progress / total_tasks * 100), 2) if total_tasks > 0 else 0,
        }
    else:
        metrics['productivity'] = {'completion_rate': 0, 'in_progress_rate': 0}
    
    # Workload distribution
    name_col = next((col for col in ['Name', 'Employee Name', 'emp_id'] if col in df.columns), None)
    if name_col:
        tasks_per_employee = df[name_col].value_counts()
        metrics['workload'] = {
            'avg_tasks_per_employee': round(tasks_per_employee.mean(), 2),
            'max_tasks': int(tasks_per_employee.max()),
            'min_tasks': int(tasks_per_employee.min()),
            'std_dev': round(tasks_per_employee.std(), 2),
            'workload_balance': 'Balanced' if tasks_per_employee.std() < tasks_per_employee.mean() * 0.5 else 'Unbalanced'
        }
    else:
        metrics['workload'] = {
            'avg_tasks_per_employee': 0,
            'max_tasks': 0,
            'min_tasks': 0,
            'std_dev': 0,
            'workload_balance': 'Unknown'
        }
    
    # Overall utilization score (0-100)
    perf_score = metrics.get('performance_distribution', {}).get('excellent_pct', 0) + \
                 (metrics.get('performance_distribution', {}).get('good_pct', 0) * 0.7)
    productivity_score = metrics.get('productivity', {}).get('completion_rate', 0)
    
    utilization_score = round((perf_score * 0.6 + productivity_score * 0.4), 2)
    metrics['overall_utilization'] = min(100, max(0, utilization_score))
    
    return metrics


def get_performance_tier(performance: float) -> str:
    """
    Categorize performance score into tier
    
    Args:
        performance: Performance percentage
        
    Returns:
        Performance tier string
    """
    if pd.isna(performance):
        return "N/A"
    elif performance >= 90:
        return "Excellent"
    elif performance >= 70:
        return "Good"
    elif performance >= 50:
        return "Average"
    else:
        return "Needs Improvement"
