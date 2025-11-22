import os
import datetime
from json import load, dump
import pandas as pd

try:
    from main import read_excel_data, load_config, EXCEL_FILE_PATH
except Exception:
    read_excel_data = None
    load_config = None
    EXCEL_FILE_PATH = os.path.join(os.path.dirname(__file__), 'task_tracker.xlsx')

try:
    from attendance_store import load_attendance, load_employees
except Exception:
    def load_attendance():
        return []
    def load_employees():
        return {}

data_dir = "Data"
chat_log_path = os.path.join(data_dir, "ChatLog.json")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
if not os.path.exists(chat_log_path):
    with open(chat_log_path, "w") as f:
        dump([], f, indent=4)

def _get_df():
    try:
        excel_path = EXCEL_FILE_PATH if load_config is None else load_config().get('excel_file_path', EXCEL_FILE_PATH)
        if read_excel_data:
            return read_excel_data(excel_path)
        if os.path.exists(excel_path):
            return pd.read_excel(excel_path)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def _today_counts_attendance():
    try:
        records = load_attendance()
        today = datetime.datetime.now().date()
        wfo = wfh = leave = 0
        seen = set()
        present = 0
        for r in records:
            ts = r.get('timestamp')
            try:
                ts_dt = datetime.datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            except Exception:
                ts_dt = None
            if ts_dt and ts_dt.date() == today:
                emp = (r.get('emp_id') or '').upper()
                if emp and emp not in seen:
                    present += 1
                    seen.add(emp)
                stt = r.get('status')
                if stt == 'WFO':
                    wfo += 1
                elif stt == 'WFH':
                    wfh += 1
                elif stt == 'On Leave':
                    leave += 1
        total_emps = len(load_employees() or {})
        ratio = round((present/total_emps*100) if total_emps else 0, 1)
        return wfo, wfh, leave, present, total_emps, ratio
    except Exception:
        return 0, 0, 0, 0, 0, 0.0

def _availability_counts_from_df(df: pd.DataFrame):
    try:
        if df is None or df.empty or 'Availability' not in df.columns:
            return 0, 0, 0
        latest = df[df['Availability'].notna()]['Availability']
        fully = int((latest == 'Fully Busy').sum())
        partial = int((latest == 'Partially Busy').sum())
        under = int((latest == 'Underutilized').sum())
        return fully, partial, under
    except Exception:
        return 0, 0, 0

def _employee_dashboard(emp_query: str):
    employees = load_employees() or {}
    df = _get_df()
    emp_id = None
    emp_name = None
    q = emp_query.strip().lower()
    for k, v in employees.items():
        name = str(v.get('name', '')).lower()
        if q == k.lower() or q in name:
            emp_id = k
            emp_name = v.get('name', k)
            break
    if emp_id is None and 'Name' in df.columns:
        for nm in df['Name'].dropna().unique().tolist():
            if q in str(nm).lower():
                emp_name = nm
                break
    perf_df = pd.DataFrame()
    if emp_name and not df.empty:
        perf_df = df[df['Name'].astype(str).str.lower() == str(emp_name).lower()].copy()
    records = load_attendance()
    today = datetime.datetime.now().date()
    last_checkin = "N/A"
    daily = weekly = monthly = 0
    try:
        for r in records:
            eid = (r.get('emp_id') or '').upper()
            if emp_id and eid != emp_id:
                continue
            ts = r.get('timestamp')
            try:
                ts_dt = datetime.datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            except Exception:
                ts_dt = None
            if not ts_dt:
                continue
            d = ts_dt.date()
            if d == today:
                daily += 1
                last_checkin = r.get('check_in_time') or ts_dt.strftime('%I:%M %p')
            if (today - d).days <= 7:
                weekly += 1
            if (today - d).days <= 30:
                monthly += 1
    except Exception:
        pass
    details = employees.get(emp_id, {}) if emp_id else {}
    dept = details.get('department', '')
    role = details.get('role', '')
    email = details.get('email', '')
    total_tasks = len(perf_df)
    completed_tasks = int((perf_df.get('Task Status') == 'Completed').sum()) if 'Task Status' in perf_df.columns else 0
    avg_perf = round(perf_df['Employee Performance (%)'].mean(), 2) if 'Employee Performance (%)' in perf_df.columns and not perf_df.empty else 0
    latest_status = "Unknown"
    try:
        if 'Availability' in perf_df.columns and not perf_df[perf_df['Availability'].notna()].empty:
            latest_status = perf_df[perf_df['Availability'].notna()]['Availability'].iloc[-1]
    except Exception:
        pass
    return (
        f"Employee: {emp_name or emp_id or emp_query}\n"
        f"Department: {dept} | Role: {role} | Email: {email}\n"
        f"Performance → Total Tasks: {total_tasks}, Completed: {completed_tasks}, Avg Performance (%): {avg_perf}, Latest Availability: {latest_status}\n"
        f"Attendance → Daily: {daily}, Weekly: {weekly}, Monthly: {monthly}, Last Check-in: {last_checkin}"
    )

def ChatBot(Query):
    try:
        with open(chat_log_path, "r") as f:
            messages = load(f)
        messages.append({"role": "user", "content": f"{Query}"})
        q = Query.strip().lower()
        df = _get_df()
        wfo, wfh, leave, present, total_emps, ratio = _today_counts_attendance()
        if any(k in q for k in ["leave today", "how many leave", "on leave"]):
            answer = f"Employees on leave today: {leave}"
        elif "work mode counts" in q or "work mode" in q:
            fully, partial, under = _availability_counts_from_df(df)
            answer = f"Work mode counts (Fully Busy/WFO={wfo or fully}, Partially Busy/WFH={wfh or partial}, Underutilized={under})"
        elif "attendance ratio" in q or "ratio" in q:
            answer = f"Attendance ratio today: {ratio}% ({present}/{total_emps} present)"
        elif any(k in q for k in ["performance", "attendance", "check-in", "checkins"]) and ("employee" in q or "emp" in q):
            tokens = Query.split()
            candidate = None
            for t in tokens:
                if t.upper().startswith("EMP") or len(t) > 2:
                    candidate = t
                    break
            answer = _employee_dashboard(candidate or Query)
        else:
            answer = "I answer only work-related queries: performance, attendance status/ratio, daily check-ins, and work mode details."
        messages.append({"role": "assistant", "content": answer})
        with open(chat_log_path, "w") as f:
            dump(messages, f, indent=4)
        return answer
    except Exception as e:
        with open(chat_log_path, "w") as f:
            dump([], f, indent=4)
        return "An error occurred. Chat log reset. Please try again."

if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        print(ChatBot(user_input))