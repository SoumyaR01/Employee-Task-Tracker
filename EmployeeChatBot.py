import os
from groq import Groq
from json import load, dump
import datetime

import pandas as pd

import attendance_store
from dotenv import dotenv_values

# Load environment variables from the .env file
env_vars = dotenv_values(".env")

# Retrieve specific environment variables
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")

# Initialize the Groq client
client = Groq(api_key=GroqAPIKey)

# Initialize an empty list to store chat messages
messages = []

# ========= Data source configuration =========
# Excel used by the Performance Dashboard
EXCEL_FILE_PATH = r"D:\\Employee Track Report\\task_tracker.xlsx"

# ========= System prompts for Groq =========
# NOTE: For employee-specific dashboards we bypass the LLM completely
# and answer directly from the local data sources so that values
# always come from the database/CSV/Excel files.
System = f"""Hello, I am Sir, You are a very accurate and advanced AI chatbot named {Assistantname}.
You are connected to an internal Employee Performance and Attendance system.
For general questions, behave like a helpful assistant.
For employee questions, you MUST only use the data explicitly provided in the context.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""
SystemChatBot = [{"role": "system", "content": System}]

# Ensure the Data directory and ChatLog.json exist
data_dir = "Data"
chat_log_path = os.path.join(data_dir, "ChatLog.json")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
if not os.path.exists(chat_log_path):
    with open(chat_log_path, "w") as f:
        dump([], f, indent=4)

# Function to get real-time date and time information
def RealtimeInformation():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")
    data = f"Please use this real-time information if needed:\n"
    data += f"Day: {day}\nDate: {date}\nMonth: {month}\nYear: {year}\n"
    data += f"Time: {hour} hours : {minute} minutes : {second} seconds.\n"
    return data

# Function to modify the chatbot's response for better formatting
def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer


# ========= Helper functions to read real data =========

def _load_employees():
    """Load all employees from Employee Management (attendance_store)."""
    try:
        return attendance_store.load_employees()
    except Exception as exc:
        print(f"Error loading employees: {exc}")
        return {}


def _load_attendance_records():
    """Load all attendance records from Staff Attendance View backend."""
    try:
        return attendance_store.load_attendance()
    except Exception as exc:
        print(f"Error loading attendance records: {exc}")
        return []


def _load_performance_df():
    """Load performance data from the Excel file used by the Performance Dashboard."""
    try:
        if not os.path.exists(EXCEL_FILE_PATH):
            return None
        df = pd.read_excel(EXCEL_FILE_PATH, engine="openpyxl")
        if df is None or df.empty:
            return None
        # Normalise key numeric columns
        if "Employee Performance (%)" not in df.columns:
            df["Employee Performance (%)"] = 0.0
        df["Employee Performance (%)"] = (
            pd.to_numeric(df["Employee Performance (%)"], errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        if "Effort (in hours)" in df.columns:
            df["Effort (in hours)"] = (
                pd.to_numeric(df["Effort (in hours)"], errors="coerce")
                .fillna(0.0)
                .astype(float)
            )
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df
    except Exception as exc:
        print(f"Error loading performance data: {exc}")
        return None


def _find_employee_in_query(query: str):
    """Infer employee from the natural-language query using ID or name.

    Returns (emp_id, employee_dict) or (None, None) if not found.
    """
    employees = _load_employees()
    if not employees:
        return None, None

    q_lower = query.lower()

    # 1) Match by employee ID (keys in employees.json, e.g. EMP001)
    for emp_id, info in employees.items():
        if emp_id.lower() in q_lower:
            return emp_id, info

    # 2) Match by full employee name contained in the query
    for emp_id, info in employees.items():
        name = str(info.get("name") or "").strip()
        if name and name.lower() in q_lower:
            return emp_id, info

    return None, None


def _summarise_attendance(emp_id: str):
    """Create daily / weekly / monthly attendance summary for the given employee.

    Data is pulled directly from attendance_records.csv via attendance_store.
    """
    records = _load_attendance_records()
    if not records:
        return None

    today = datetime.datetime.now().date()
    seven_days_ago = today - datetime.timedelta(days=7)
    thirty_days_ago = today - datetime.timedelta(days=30)

    def _parse_date(ts: str):
        if not ts:
            return None
        try:
            return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        except Exception:
            return None

    emp_records = []
    for rec in records:
        if rec.get("emp_id") != emp_id:
            continue
        d = _parse_date(rec.get("timestamp"))
        if not d:
            continue
        emp_records.append({
            "date": d,
            "status": rec.get("status"),
            "check_in_time": rec.get("check_in_time"),
            "notes": rec.get("notes") or "",
        })

    if not emp_records:
        return None

    # Today's latest status (if any)
    latest_today = None
    for rec in emp_records:
        if rec["date"] == today:
            latest_today = rec

    def _range_stats(start_date):
        subset = [r for r in emp_records if r["date"] >= start_date]
        if not subset:
            return {
                "records": 0,
                "distinct_days": 0,
                "present_days": 0,
                "leave_days": 0,
                "attendance_rate": 0.0,
                "wfo": 0,
                "wfh": 0,
            }
        distinct_days = len({r["date"] for r in subset})
        present_days = len({r["date"] for r in subset if r["status"] in ("WFO", "WFH")})
        leave_days = len({r["date"] for r in subset if r["status"] == "On Leave"})
        return {
            "records": len(subset),
            "distinct_days": distinct_days,
            "present_days": present_days,
            "leave_days": leave_days,
            "attendance_rate": round((present_days / distinct_days) * 100, 1) if distinct_days else 0.0,
            "wfo": sum(1 for r in subset if r["status"] == "WFO"),
            "wfh": sum(1 for r in subset if r["status"] == "WFH"),
        }

    weekly = _range_stats(seven_days_ago)
    monthly = _range_stats(thirty_days_ago)

    return {
        "today": latest_today,
        "weekly": weekly,
        "monthly": monthly,
    }


def _summarise_performance(emp_id, emp_name):
    """Build performance KPIs, progress, and ratings for an employee.

    This uses the same Excel file that powers the Performance Dashboard.
    """
    df = _load_performance_df()
    if df is None:
        return None

    emp_df = None

    # Prefer matching by Emp Id if available
    if "Emp Id" in df.columns and emp_id:
        emp_df = df[df["Emp Id"].astype(str).str.upper() == emp_id.upper()]

    # Fallback: match by Name if needed
    if (emp_df is None or emp_df.empty) and emp_name and "Name" in df.columns:
        emp_df = df[df["Name"].astype(str).str.strip().str.lower() == emp_name.strip().lower()]

    if emp_df is None or emp_df.empty:
        return None

    total_tasks = len(emp_df)
    completed_tasks = int((emp_df.get("Task Status") == "Completed").sum()) if "Task Status" in emp_df.columns else 0
    pending_tasks = max(total_tasks - completed_tasks, 0)
    avg_perf = round(emp_df["Employee Performance (%)"].mean(), 2)

    if "Date" in emp_df.columns and not emp_df["Date"].dropna().empty:
        sorted_df = emp_df.sort_values("Date")
        latest_perf = float(sorted_df["Employee Performance (%)"].iloc[-1])
        last_update = sorted_df["Date"].iloc[-1].date().isoformat()
        first_update = sorted_df["Date"].iloc[0].date().isoformat()
    else:
        latest_perf = avg_perf
        last_update = "N/A"
        first_update = "N/A"

    completion_rate = round((completed_tasks / total_tasks) * 100, 1) if total_tasks else 0.0

    # Simple derived scores similar to the Streamlit dashboard
    productivity_score = round(avg_perf, 1)
    quality_score = round(min(avg_perf * 1.1, 100.0), 1)
    efficiency_score = round(min(avg_perf * 0.95, 100.0), 1)

    primary_project = None
    if "Project Name" in emp_df.columns and not emp_df["Project Name"].dropna().empty:
        primary_project = emp_df.sort_values("Date")["Project Name"].iloc[-1]

    # Simple 7‑day snapshot
    weekly_perf = None
    if "Date" in emp_df.columns and not emp_df["Date"].dropna().empty:
        today = datetime.datetime.now().date()
        seven_days_ago = today - datetime.timedelta(days=7)
        weekly_df = emp_df[(emp_df["Date"].dt.date >= seven_days_ago) & (emp_df["Date"].dt.date <= today)]
        if not weekly_df.empty:
            weekly_perf = round(weekly_df["Employee Performance (%)"].mean(), 2)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "avg_performance": avg_perf,
        "latest_performance": round(latest_perf, 2),
        "completion_rate": completion_rate,
        "productivity_score": productivity_score,
        "quality_score": quality_score,
        "efficiency_score": efficiency_score,
        "first_record_date": first_update,
        "last_record_date": last_update,
        "primary_project": primary_project,
        "weekly_avg_performance": weekly_perf,
    }


def _build_employee_dashboard(emp_id: str, emp_info: dict):
    """Return a human‑readable dashboard string with real values only."""
    name = emp_info.get("name", "Unknown")
    email = emp_info.get("email", "-")
    department = emp_info.get("department", "-")
    role = emp_info.get("role", "-")

    attendance = _summarise_attendance(emp_id)
    performance = _summarise_performance(emp_id, name)

    lines = []
    lines.append(f"Employee Dashboard for {name} ({emp_id})")
    lines.append("".ljust(40, "="))
    lines.append("")

    # Employee details (Employee Management)
    lines.append("[Employee Details]")
    lines.append(f"- Name       : {name}")
    lines.append(f"- Employee ID: {emp_id}")
    lines.append(f"- Email      : {email}")
    lines.append(f"- Department : {department}")
    lines.append(f"- Role       : {role}")
    lines.append("")

    # Attendance summary (Staff Attendance View)
    lines.append("[Attendance Summary]")
    if not attendance:
        lines.append("No attendance records found for this employee.")
    else:
        today = attendance.get("today")
        weekly = attendance.get("weekly") or {}
        monthly = attendance.get("monthly") or {}

        if today:
            lines.append("Today:")
            lines.append(f"  - Status       : {today.get('status', 'N/A')}")
            if today.get("check_in_time"):
                lines.append(f"  - Check‑in time: {today['check_in_time']}")
            if today.get("notes"):
                lines.append(f"  - Notes        : {today['notes']}")
        else:
            lines.append("Today: No status marked.")

        lines.append("")
        lines.append("Last 7 days (rolling):")
        lines.append(f"  - Days with records : {weekly.get('distinct_days', 0)}")
        lines.append(f"  - Present days      : {weekly.get('present_days', 0)}")
        lines.append(f"  - Leave days        : {weekly.get('leave_days', 0)}")
        lines.append(f"  - WFO entries       : {weekly.get('wfo', 0)}")
        lines.append(f"  - WFH entries       : {weekly.get('wfh', 0)}")
        lines.append(f"  - Attendance rate   : {weekly.get('attendance_rate', 0.0)}%")

        lines.append("")
        lines.append("Last 30 days (rolling):")
        lines.append(f"  - Days with records : {monthly.get('distinct_days', 0)}")
        lines.append(f"  - Present days      : {monthly.get('present_days', 0)}")
        lines.append(f"  - Leave days        : {monthly.get('leave_days', 0)}")
        lines.append(f"  - WFO entries       : {monthly.get('wfo', 0)}")
        lines.append(f"  - WFH entries       : {monthly.get('wfh', 0)}")
        lines.append(f"  - Attendance rate   : {monthly.get('attendance_rate', 0.0)}%")
    lines.append("")

    # Performance KPIs (Performance Dashboard)
    lines.append("[Performance KPIs & Progress]")
    if not performance:
        lines.append("No performance records found for this employee in the tracker.")
    else:
        lines.append(f"- Total tasks           : {performance['total_tasks']}")
        lines.append(f"- Completed tasks       : {performance['completed_tasks']}")
        lines.append(f"- Pending tasks         : {performance['pending_tasks']}")
        lines.append(f"- Task completion rate  : {performance['completion_rate']}%")
        lines.append(f"- Average performance   : {performance['avg_performance']}%")
        lines.append(f"- Latest performance    : {performance['latest_performance']}% (as of {performance['last_record_date']})")
        if performance.get("weekly_avg_performance") is not None:
            lines.append(f"- Last 7‑day avg perf.  : {performance['weekly_avg_performance']}%")
        lines.append(f"- Productivity score    : {performance['productivity_score']}%")
        lines.append(f"- Quality score         : {performance['quality_score']}%")
        lines.append(f"- Efficiency score      : {performance['efficiency_score']}%")
        if performance.get("primary_project"):
            lines.append(f"- Primary project       : {performance['primary_project']}")
        lines.append(f"- Data from             : {performance['first_record_date']} to {performance['last_record_date']}")

    return "\n".join(lines)


def _maybe_answer_with_dashboard(query: str):
    """If the query looks like an admin asking about an employee,
    return a full dashboard string; otherwise return None.
    """
    emp_id, emp_info = _find_employee_in_query(query)
    if not emp_id or not emp_info:
        return None

    # Any query mentioning a known employee is treated as a request
    # for their latest dashboard (details + attendance + performance).
    return _build_employee_dashboard(emp_id, emp_info)


# Main chatbot function to handle user queries
def ChatBot(Query):
    """Answer user queries.

    - For employee-specific questions, return a structured dashboard using
      real data from Employee Management, Attendance, and Performance modules.
    - For all other questions, fall back to the Groq LLM.
    """
    # 1) Try answering directly from internal data (no LLM, no randomness)
    dashboard_answer = _maybe_answer_with_dashboard(Query)
    if dashboard_answer is not None:
        # Persist this Q&A in the same chat log used for LLM answers
        try:
            with open(chat_log_path, "r") as f:
                messages = load(f)
        except Exception:
            messages = []
        messages.append({"role": "user", "content": f"{Query}"})
        messages.append({"role": "assistant", "content": dashboard_answer})
        with open(chat_log_path, "w") as f:
            dump(messages, f, indent=4)
        return AnswerModifier(dashboard_answer)

    # 2) Fall back to Groq LLM for generic questions
    try:
        # Load the existing chat log
        with open(chat_log_path, "r") as f:
            messages = load(f)

        # Append the user's query
        messages.append({"role": "user", "content": f"{Query}"})

        # Limit chat history to last 10 messages for faster processing
        recent_messages = messages[-10:] if len(messages) > 10 else messages

        # Make a request to the Groq API
        completion = client.chat.completions.create(
            #model='Gemma2-9b-It',
            #model = 'llama-3.1-8b-instant',  # Fastest option
            model='llama-3.3-70b-versatile',  # Balanced: fast + high quality
            #model = 'openai/gpt-oss-20b',
            messages=SystemChatBot + [{"role": "system", "content": RealtimeInformation()}] + recent_messages,
            max_tokens=512,  # Reduced for faster responses
            temperature=0.7,
            top_p=1,
            stream=True
        )

        Answer = ""
        # Process the streamed response
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content

        Answer = Answer.replace("</s>", "")

        # Append the chatbot's response to the messages
        messages.append({"role": "assistant", "content": Answer})

        # Save the updated chat log
        with open(chat_log_path, "w") as f:
            dump(messages, f, indent=4)

        # Return the formatted response
        return AnswerModifier(Answer)

    except Exception as e:
        print(f"Error: {e}")
        with open(chat_log_path, "w") as f:
            dump([], f, indent=4)
        return "An error occurred. Chat log reset. Please try again."

# Main program entry point
if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        print(ChatBot(user_input))