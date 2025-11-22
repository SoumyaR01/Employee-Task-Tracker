import os
import json
from datetime import datetime, timedelta, time as dtime
import pandas as pd
from dotenv import dotenv_values
import threading
import numpy as np
import attendance_store

try:
    import faiss
except Exception:
    faiss = None
try:
    from sentence_transformers import SentenceTransformer
    _st_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    _st_model = None

env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")

_vs_lock = threading.Lock()
_faiss_index = None
_faiss_ids = []
_faiss_metas = []
_faiss_texts = []
_faiss_dim = 0
_last_refresh_ts = None
_vocab = {}

EXCEL_FILE_PATH = r"D:\Employee Track Report\task_tracker.xlsx"
LATE_THRESHOLD_HOUR = 10
LATE_THRESHOLD_MINUTE = 30

System = f"""Hello, I am Sir, You are a very accurate and advanced AI chatbot named {Assistantname}.
You are connected to an internal Employee Performance and Attendance system.
For general questions, behave like a helpful assistant.
For employee questions, you MUST only use the data explicitly provided in the context.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""
SystemChatBot = [{"role": "system", "content": System}]

data_dir = "Data"
chat_log_path = os.path.join(data_dir, "ChatLog.json")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
if not os.path.exists(chat_log_path):
    with open(chat_log_path, "w") as f:
        json.dump([], f, indent=4)

def RealtimeInformation():
    current_date_time = datetime.now()
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

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def _load_employees():
    try:
        return attendance_store.load_employees()
    except Exception as exc:
        print(f"Error loading employees: {exc}")
        return {}

def _load_attendance_records():
    try:
        return attendance_store.load_attendance()
    except Exception as exc:
        print(f"Error loading attendance records: {exc}")
        return []

def _load_performance_df():
    try:
        if not os.path.exists(EXCEL_FILE_PATH):
            return None
        df = pd.read_excel(EXCEL_FILE_PATH, engine="openpyxl")
        if df is None or df.empty:
            return None
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
    employees = _load_employees()
    if not employees:
        return None, None
    q_lower = query.lower()
    for emp_id, info in employees.items():
        if emp_id.lower() in q_lower:
            return emp_id, info
    for emp_id, info in employees.items():
        name = str(info.get("name") or "").strip()
        if name and name.lower() in q_lower:
            return emp_id, info
    for emp_id, info in employees.items():
        name = str(info.get("name") or "").strip().lower()
        name_parts = name.split()
        for part in name_parts:
            if part in q_lower and len(part) > 2:
                return emp_id, info
    return None, None

def _summarise_attendance(emp_id: str):
    records = _load_attendance_records()
    if not records:
        return None
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=7)
    thirty_days_ago = today - timedelta(days=30)
    def _parse_date(ts: str):
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
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
    df = _load_performance_df()
    if df is None:
        return None
    emp_df = None
    if "Emp Id" in df.columns and emp_id:
        emp_df = df[df["Emp Id"].astype(str).str.upper() == emp_id.upper()]
    if (emp_df is None or emp_df.empty) and emp_name and "Name" in df.columns:
        emp_df = df[df["Name"].astype(str).str.strip().str.lower() == emp_name.strip().lower()]
    if emp_df is None or emp_df.empty:
        return None
    total_tasks = len(emp_df)
    completed_tasks = int((emp_df.get("Task Status") == "Completed").sum()) if "Task Status" in emp_df.columns else 0
    in_progress_tasks = int((emp_df.get("Task Status") == "In Progress").sum()) if "Task Status" in emp_df.columns else 0
    pending_tasks = int((emp_df.get("Task Status") == "Pending").sum()) if "Task Status" in emp_df.columns else 0
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
    productivity_score = round(avg_perf, 1)
    quality_score = round(min(avg_perf * 1.1, 100.0), 1)
    efficiency_score = round(min(avg_perf * 0.95, 100.0), 1)
    primary_project = None
    if "Project Name" in emp_df.columns and not emp_df["Project Name"].dropna().empty:
        primary_project = emp_df.sort_values("Date")["Project Name"].iloc[-1]
    weekly_perf = None
    if "Date" in emp_df.columns and not emp_df["Date"].dropna().empty:
        today = datetime.now().date()
        seven_days_ago = today - timedelta(days=7)
        weekly_df = emp_df[(emp_df["Date"].dt.date >= seven_days_ago) & (emp_df["Date"].dt.date <= today)]
        if not weekly_df.empty:
            weekly_perf = round(weekly_df["Employee Performance (%)"].mean(), 2)
    availability = "Unknown"
    if "Availability" in emp_df.columns:
        avail_data = emp_df[emp_df["Availability"].notna()]
        if not avail_data.empty:
            availability = avail_data["Availability"].iloc[-1]
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
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
        "availability": availability,
    }

def _build_employee_dashboard(emp_id: str, emp_info: dict):
    name = emp_info.get("name", "Unknown")
    email = emp_info.get("email", "-")
    department = emp_info.get("department", "-")
    role = emp_info.get("role", "-")
    attendance = _summarise_attendance(emp_id)
    performance = _summarise_performance(emp_id, name)
    lines = []
    lines.append("=" * 70)
    lines.append(f"EMPLOYEE DASHBOARD: {name} ({emp_id})")
    lines.append("=" * 70)
    lines.append("")
    lines.append("📋 EMPLOYEE DETAILS")
    lines.append("-" * 70)
    lines.append(f"Name         : {name}")
    lines.append(f"Employee ID  : {emp_id}")
    lines.append(f"Email        : {email}")
    lines.append(f"Department   : {department}")
    lines.append(f"Role         : {role}")
    lines.append("")
    lines.append("📅 ATTENDANCE SUMMARY")
    lines.append("-" * 70)
    if not attendance:
        lines.append("No attendance records found for this employee.")
    else:
        today = attendance.get("today")
        weekly = attendance.get("weekly") or {}
        monthly = attendance.get("monthly") or {}
        lines.append("TODAY'S STATUS:")
        if today:
            lines.append(f"  Status         : {today.get('status', 'N/A')}")
            if today.get("check_in_time"):
                lines.append(f"  Check-in Time  : {today['check_in_time']}")
            if today.get("notes"):
                lines.append(f"  Notes          : {today['notes']}")
        else:
            lines.append("  Status         : Not marked yet")
        lines.append("")
        lines.append("LAST 7 DAYS (Rolling):")
        lines.append(f"  Days with Records  : {weekly.get('distinct_days', 0)}")
        lines.append(f"  Present Days       : {weekly.get('present_days', 0)}")
        lines.append(f"  Leave Days         : {weekly.get('leave_days', 0)}")
        lines.append(f"  WFO Entries        : {weekly.get('wfo', 0)}")
        lines.append(f"  WFH Entries        : {weekly.get('wfh', 0)}")
        lines.append(f"  Attendance Rate    : {weekly.get('attendance_rate', 0.0)}%")
        lines.append("")
        lines.append("LAST 30 DAYS (Rolling):")
        lines.append(f"  Days with Records  : {monthly.get('distinct_days', 0)}")
        lines.append(f"  Present Days       : {monthly.get('present_days', 0)}")
        lines.append(f"  Leave Days         : {monthly.get('leave_days', 0)}")
        lines.append(f"  WFO Entries        : {monthly.get('wfo', 0)}")
        lines.append(f"  WFH Entries        : {monthly.get('wfh', 0)}")
        lines.append(f"  Attendance Rate    : {monthly.get('attendance_rate', 0.0)}%")
    lines.append("")
    lines.append("📊 PERFORMANCE DASHBOARD")
    lines.append("-" * 70)
    if not performance:
        lines.append("No performance records found for this employee in the tracker.")
    else:
        lines.append("TASK SUMMARY:")
        lines.append(f"  Total Tasks         : {performance['total_tasks']}")
        lines.append(f"  Completed           : {performance['completed_tasks']}")
        lines.append(f"  In Progress         : {performance['in_progress_tasks']}")
        lines.append(f"  Pending             : {performance['pending_tasks']}")
        lines.append(f"  Completion Rate     : {performance['completion_rate']}%")
        lines.append("")
        lines.append("PERFORMANCE METRICS:")
        lines.append(f"  Average Performance : {performance['avg_performance']}%")
        lines.append(f"  Latest Performance  : {performance['latest_performance']}%")
        if performance.get("weekly_avg_performance") is not None:
            lines.append(f"  Last 7-Day Avg      : {performance['weekly_avg_performance']}%")
        lines.append(f"  Productivity Score  : {performance['productivity_score']}%")
        lines.append(f"  Quality Score       : {performance['quality_score']}%")
        lines.append(f"  Efficiency Score    : {performance['efficiency_score']}%")
        lines.append("")
        lines.append("WORK STATUS:")
        lines.append(f"  Current Availability: {performance['availability']}")
        if performance.get("primary_project"):
            lines.append(f"  Primary Project     : {performance['primary_project']}")
        lines.append(f"  Data Period         : {performance['first_record_date']} to {performance['last_record_date']}")
    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)

def _get_today_attendance_summary():
    try:
        records = _load_attendance_records()
        employees = _load_employees() or {}
        today = datetime.now().date()
        present_employees = {}
        wfo_list = []
        wfh_list = []
        leave_list = []
        late_list = []
        for rec in records:
            ts = rec.get('timestamp')
            try:
                ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
            except Exception:
                ts_dt = None
            if ts_dt and ts_dt.date() == today:
                emp_id = (rec.get('emp_id') or '').upper()
                status = rec.get('status', '')
                check_in = rec.get('check_in_time', '')
                if emp_id and emp_id not in present_employees:
                    emp_name = employees.get(emp_id, {}).get('name', emp_id)
                    present_employees[emp_id] = {
                        'name': emp_name,
                        'status': status,
                        'check_in': check_in
                    }
                    if status == 'WFO':
                        wfo_list.append(f"{emp_name} ({emp_id})")
                    elif status == 'WFH':
                        wfh_list.append(f"{emp_name} ({emp_id})")
                    elif status == 'On Leave':
                        leave_list.append(f"{emp_name} ({emp_id})")
                    if check_in:
                        try:
                            check_time = datetime.strptime(check_in, "%I:%M %p").time()
                            threshold = dtime(LATE_THRESHOLD_HOUR, LATE_THRESHOLD_MINUTE)
                            if check_time > threshold:
                                late_list.append(f"{emp_name} ({emp_id}) - {check_in}")
                        except Exception:
                            pass
        total_emps = len(employees)
        present_count = len(present_employees)
        absent_count = total_emps - present_count
        absent_list = []
        for emp_id, emp_data in employees.items():
            if emp_id not in present_employees:
                absent_list.append(f"{emp_data.get('name', emp_id)} ({emp_id})")
        return {
            'total': total_emps,
            'present': present_count,
            'absent': absent_count,
            'wfo': wfo_list,
            'wfh': wfh_list,
            'leave': leave_list,
            'absent_list': absent_list,
            'late_list': late_list,
            'ratio': round((present_count/total_emps*100) if total_emps else 0, 1)
        }
    except Exception as e:
        print(f"Error in attendance summary: {e}")
        return None

def _build_vocab(texts):
    global _vocab
    terms = set()
    for t in texts:
        for w in t.lower().split():
            terms.add(w)
    _vocab = {w: i for i, w in enumerate(sorted(terms))}

def _embed(texts):
    if _st_model is not None:
        arr = _st_model.encode(texts, normalize_embeddings=True)
        return np.array(arr, dtype='float32')
    if not _vocab:
        _build_vocab(texts)
    dim = len(_vocab)
    vecs = []
    for t in texts:
        v = np.zeros((dim,), dtype='float32')
        for w in t.lower().split():
            j = _vocab.get(w)
            if j is not None:
                v[j] += 1.0
        n = np.linalg.norm(v)
        vecs.append(v / n if n > 0 else v)
    return np.stack(vecs).astype('float32')

def _build_employee_doc(emp_id, info, df, records):
    name = info.get('name', emp_id)
    email = info.get('email', '')
    department = info.get('department', '')
    role = info.get('role', '')
    today = datetime.now().date()
    emp_records = []
    for rec in records:
        if (rec.get('emp_id') or '').upper() == emp_id.upper():
            ts = rec.get('timestamp')
            try:
                d = datetime.fromisoformat(ts.replace('Z','+00:00')).date() if isinstance(ts, str) else ts.date()
            except Exception:
                continue
            emp_records.append({'date': d, 'status': rec.get('status'), 'check_in_time': rec.get('check_in_time')})
    weekly_days = len({r['date'] for r in emp_records if (today - r['date']).days <= 7})
    weekly_present = len({r['date'] for r in emp_records if (today - r['date']).days <= 7 and r['status'] in ('WFO','WFH')})
    monthly_days = len({r['date'] for r in emp_records if (today - r['date']).days <= 30})
    monthly_present = len({r['date'] for r in emp_records if (today - r['date']).days <= 30 and r['status'] in ('WFO','WFH')})
    today_status = None
    today_checkin = None
    for r in emp_records:
        if r['date'] == today:
            today_status = r['status']
            today_checkin = r.get('check_in_time')
    emp_df = None
    if df is not None and not df.empty:
        emp_df = df
        if 'Emp Id' in df.columns:
            emp_df = emp_df[emp_df['Emp Id'].astype(str).str.upper() == emp_id.upper()]
        if (emp_df is None or emp_df.empty) and 'Name' in df.columns:
            emp_df = df[df['Name'].astype(str).str.strip().str.lower() == name.strip().lower()]
    total_tasks = len(emp_df) if emp_df is not None else 0
    completed = int((emp_df.get('Task Status') == 'Completed').sum()) if emp_df is not None and 'Task Status' in emp_df.columns else 0
    in_progress = int((emp_df.get('Task Status') == 'In Progress').sum()) if emp_df is not None and 'Task Status' in emp_df.columns else 0
    pending = int((emp_df.get('Task Status') == 'Pending').sum()) if emp_df is not None and 'Task Status' in emp_df.columns else 0
    avg_perf = round(emp_df['Employee Performance (%)'].mean(), 2) if emp_df is not None and 'Employee Performance (%)' in emp_df.columns and not emp_df.empty else 0.0
    availability = 'Unknown'
    if emp_df is not None and 'Availability' in emp_df.columns:
        avail_data = emp_df[emp_df['Availability'].notna()]
        if not avail_data.empty:
            availability = str(avail_data['Availability'].iloc[-1])
    rating = 'Excellent' if avg_perf >= 80 else ('Good' if avg_perf >= 60 else ('Fair' if avg_perf >= 40 else 'Needs Improvement'))
    meta = {
        'kind': 'employee', 'emp_id': emp_id, 'name': name, 'email': email, 'department': department, 'role': role,
        'attendance_weekly_days': weekly_days, 'attendance_weekly_present': weekly_present,
        'attendance_monthly_days': monthly_days, 'attendance_monthly_present': monthly_present,
        'today_status': today_status, 'today_checkin': today_checkin,
        'total_tasks': total_tasks, 'completed_tasks': completed, 'in_progress_tasks': in_progress, 'pending_tasks': pending,
        'avg_performance': avg_perf, 'availability': availability, 'rating': rating
    }
    text = f"employee {name} {emp_id} performance {avg_perf} rating {rating} availability {availability} tasks {total_tasks} completed {completed} in_progress {in_progress} pending {pending} attendance weekly {weekly_present}/{weekly_days} monthly {monthly_present}/{monthly_days} status {today_status or 'Unknown'} checkin {today_checkin or ''}"
    return text, meta

def _build_corpus():
    employees = _load_employees() or {}
    records = _load_attendance_records() or []
    df = _load_performance_df()
    docs, ids, metas = [], [], []
    today = datetime.now().date()
    present = {}
    wfo, wfh, leave = [], [], []
    for rec in records:
        ts = rec.get('timestamp')
        try:
            dt = datetime.fromisoformat(ts.replace('Z','+00:00')) if isinstance(ts, str) else ts
        except Exception:
            dt = None
        if dt and dt.date() == today:
            eid = (rec.get('emp_id') or '').upper()
            nm = employees.get(eid, {}).get('name', eid)
            present[eid] = nm
            stt = rec.get('status')
            if stt == 'WFO':
                wfo.append(f"{nm} ({eid})")
            elif stt == 'WFH':
                wfh.append(f"{nm} ({eid})")
            elif stt == 'On Leave':
                leave.append(f"{nm} ({eid})")
    total_emps = len(employees)
    present_count = len(present)
    absent_count = total_emps - present_count
    ratio = round((present_count/total_emps*100) if total_emps else 0, 1)
    docs.append(f"checked in today {present_count} employees: {'; '.join(sorted(list(present.values())))}")
    ids.append("agg_checked_in_today")
    metas.append({'kind':'aggregate','type':'checked_in_today','present_list':sorted(list(present.values())),'present_count':present_count})
    docs.append(f"on leave today {len(leave)} employees: {'; '.join(leave)}")
    ids.append("agg_on_leave_today")
    metas.append({'kind':'aggregate','type':'on_leave_today','leave_list':leave,'leave_count':len(leave)})
    docs.append(f"in office WFO today {len(wfo)} employees: {'; '.join(wfo)}")
    ids.append("agg_wfo_today")
    metas.append({'kind':'aggregate','type':'wfo_today','wfo_list':wfo,'wfo_count':len(wfo)})
    docs.append(f"working from home WFH today {len(wfh)} employees: {'; '.join(wfh)}")
    ids.append("agg_wfh_today")
    metas.append({'kind':'aggregate','type':'wfh_today','wfh_list':wfh,'wfh_count':len(wfh)})
    docs.append(f"attendance ratio today {ratio}% present {present_count} absent {absent_count} total {total_emps}")
    ids.append("agg_attendance_ratio_today")
    metas.append({'kind':'aggregate','type':'attendance_ratio_today','present':present_count,'absent':absent_count,'total':total_emps,'ratio':ratio})
    for eid, info in employees.items():
        t, m = _build_employee_doc(eid, info, df, records)
        docs.append(t)
        ids.append(eid)
        metas.append(m)
    return docs, ids, metas

def _rebuild_index():
    global _faiss_index, _faiss_ids, _faiss_metas, _faiss_texts, _faiss_dim, _last_refresh_ts
    docs, ids, metas = _build_corpus()
    if not docs:
        _faiss_index = None
        _faiss_ids = []
        _faiss_metas = []
        _faiss_texts = []
        return False
    if _st_model is None:
        _build_vocab(docs)
    vecs = _embed(docs)
    vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    _faiss_ids = ids
    _faiss_metas = metas
    _faiss_texts = docs
    if faiss is not None:
        dim = vecs.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vecs)
        _faiss_index = index
        _faiss_dim = dim
        try:
            faiss.write_index(index, os.path.join(data_dir, "faiss.index"))
            with open(os.path.join(data_dir, "faiss_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"ids": ids, "metas": metas}, f)
        except Exception:
            pass
    else:
        _faiss_index = None
        _faiss_dim = vecs.shape[1]
    _last_refresh_ts = datetime.now()
    return True

def refresh_vectorstore():
    with _vs_lock:
        return _rebuild_index()

def _faiss_query(text, k=5):
    if not _faiss_texts:
        return []
    if faiss is None or _faiss_index is None:
        return []
    if _st_model is None and not _vocab:
        _build_vocab(_faiss_texts)
    q = _embed([text])
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
    D, I = _faiss_index.search(q.astype('float32'), min(k, len(_faiss_ids)))
    idxs = I[0].tolist()
    scores = D[0].tolist()
    return [( _faiss_ids[i], _faiss_texts[i], _faiss_metas[i], float(scores[j]) ) for j,i in enumerate(idxs)]

def _aggregate_answer_from_hits(q):
    hits = _faiss_query(q, k=8)
    if not hits:
        return None
    for hid, _, meta, _ in hits:
        if isinstance(meta, dict) and meta.get('kind') == 'aggregate':
            t = meta.get('type')
            if t == 'on_leave_today':
                lst = meta.get('leave_list') or []
                return (f"Employees on leave today ({len(lst)}):\n" + "\n".join(lst)) if lst else "No matching information found."
            if t == 'checked_in_today':
                lst = meta.get('present_list') or []
                return (f"Checked-in today ({len(lst)}):\n" + "\n".join(lst)) if lst else "No matching information found."
            if t == 'attendance_ratio_today':
                return f"Attendance ratio today: {meta.get('ratio',0)}% ({meta.get('present',0)}/{meta.get('total',0)} present)"
            if t == 'wfo_today':
                lst = meta.get('wfo_list') or []
                return (f"In office (WFO) today ({len(lst)}):\n" + "\n".join(lst)) if lst else "No matching information found."
            if t == 'wfh_today':
                lst = meta.get('wfh_list') or []
                return (f"Working from home (WFH) today ({len(lst)}):\n" + "\n".join(lst)) if lst else "No matching information found."
    return None

def _maybe_answer_with_dashboard(query: str):
    emp_id, emp_info = _find_employee_in_query(query)
    if not emp_id or not emp_info:
        return None
    return _build_employee_dashboard(emp_id, emp_info)

def ChatBot(Query):
    q = Query.strip().lower()
    allowed = ["performance","attendance","ratio","check-in","checkins","work mode","wfh","wfo","leave","status","dashboard","employee","checked-in"]
    if not any(t in q for t in allowed):
        return "No matching information found."
    with _vs_lock:
        if _last_refresh_ts is None or (datetime.now() - _last_refresh_ts).seconds > 30:
            _rebuild_index()
    agg = None
    if any(k in q for k in ["leave today","on leave","who is on leave"]):
        agg = _aggregate_answer_from_hits("on leave today")
    elif any(k in q for k in ["checked-in today","who checked-in","checked in today"]):
        agg = _aggregate_answer_from_hits("checked in today")
    elif "attendance ratio" in q:
        agg = _aggregate_answer_from_hits("attendance ratio today")
    elif "work mode" in q or "wfh" in q or "wfo" in q:
        agg = _aggregate_answer_from_hits("work mode today") or _aggregate_answer_from_hits("wfo today")
    if agg:
        try:
            with open(chat_log_path, "r") as f:
                messages = json.load(f)
        except Exception:
            messages = []
        messages.append({"role": "user", "content": f"{Query}"})
        messages.append({"role": "assistant", "content": agg})
        with open(chat_log_path, "w") as f:
            json.dump(messages, f, indent=4)
        return AnswerModifier(agg)
    hits = _faiss_query(Query, k=8)
    emp_hit = None
    for hid, _, meta, score in hits:
        if isinstance(meta, dict) and meta.get('kind') == 'employee':
            emp_hit = (hid, meta)
            break
    if not emp_hit:
        return "No matching information found."
    eid, meta = emp_hit
    lines = []
    lines.append(f"Employee Summary: {meta.get('name', eid)} ({eid})")
    lines.append("Attendance:")
    lines.append(f"- Today: {meta.get('today_status','Unknown')} | Check-in: {meta.get('today_checkin','N/A')}")
    lines.append(f"- Weekly: {meta.get('attendance_weekly_present',0)}/{meta.get('attendance_weekly_days',0)} present")
    lines.append(f"- Monthly: {meta.get('attendance_monthly_present',0)}/{meta.get('attendance_monthly_days',0)} present")
    lines.append("Performance:")
    lines.append(f"- Average: {meta.get('avg_performance',0)}% | Rating: {meta.get('rating','N/A')}")
    lines.append(f"- Tasks: {meta.get('completed_tasks',0)}/{meta.get('total_tasks',0)} completed")
    lines.append(f"- Availability: {meta.get('availability','Unknown')}")
    answer = "\n".join(lines)
    try:
        with open(chat_log_path, "r") as f:
            messages = json.load(f)
    except Exception:
        messages = []
    messages.append({"role": "user", "content": f"{Query}"})
    messages.append({"role": "assistant", "content": answer})
    with open(chat_log_path, "w") as f:
        json.dump(messages, f, indent=4)
    return AnswerModifier(answer)

if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        print(ChatBot(user_input))