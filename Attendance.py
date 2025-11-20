import streamlit as st
from datetime import datetime
import pandas as pd
import hashlib
import plotly.express as px
import attendance_store
from dateutil import parser as _dateparser

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="Employee Attendance System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== CUSTOM CSS (same beautiful design) ====================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
        color: #e6eef2;
    }
    .block-container {
        padding: 2rem 1rem;
        background: rgba(10, 10, 10, 0.85);
        border-radius: 15px;
        backdrop-filter: blur(8px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 12px;
        color: white !important;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        transition: transform 0.3s ease;
    }
    .metric-card:hover { transform: translateY(-5px); }
    .metric-value { font-size: 2.8rem; font-weight: bold; margin: 10px 0; }
    .metric-label { font-size: 1.1rem; opacity: 0.95; text-transform: uppercase; letter-spacing: 1px; }
    .status-card-wfo { background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px 0; }
    .status-card-wfh { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px 0; }
    .status-card-leave { background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px 0; }
    .stButton > button {
        width: 100%; border-radius: 8px; height: 3.5rem; font-weight: 600;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important; border: none; font-size: 1.1rem;
    }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); }
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #e6eef2 !important; }
</style>
""", unsafe_allow_html=True)

# ==================== IN-MEMORY DATA INITIALIZATION ====================
def init_in_memory_data():
    if "employees" not in st.session_state:
        # Load persisted employees from attendance_store (this will not include demo accounts)
        try:
            employees = attendance_store.load_employees()
        except Exception:
            employees = {}
        # Ensure ADMIN account exists for admin access
        if "ADMIN" not in employees:
            employees["ADMIN"] = {"password": hashlib.sha256("admin123".encode()).hexdigest(), "name": "Administrator", "email": "admin@company.com", "department": "Management", "role": "Admin"}
        st.session_state.employees = employees
        # Persist any changes (e.g., added ADMIN)
        try:
            attendance_store.save_employees(st.session_state.employees)
        except Exception:
            pass

    if "attendance" not in st.session_state:
        # Load persisted attendance records (if any)
        raw = attendance_store.load_attendance()
        parsed = []
        for r in raw:
            try:
                ts = _dateparser.isoparse(r.get("timestamp")) if r.get("timestamp") else datetime.now()
            except Exception:
                ts = datetime.now()
            parsed.append({
                "emp_id": r.get("emp_id"),
                "status": r.get("status"),
                "timestamp": ts,
                "check_in_time": r.get("check_in_time"),
                "notes": r.get("notes", "")
            })
        st.session_state.attendance = parsed

init_in_memory_data()

# ==================== AUTHENTICATION ====================
def verify_login(emp_id, password):
    emp = st.session_state.employees.get(emp_id.upper())
    if emp and emp["password"] == hashlib.sha256(password.encode()).hexdigest():
        return True, emp["name"], emp["role"]
    return False, None, None

# ==================== ATTENDANCE FUNCTIONS (In-Memory) ====================
def update_attendance(emp_id, status, notes=""):
    timestamp = datetime.now()
    record = {
        "emp_id": emp_id,
        "status": status,
        "timestamp": timestamp,
        "check_in_time": timestamp.strftime('%H:%M:%S') if status in ["WFO", "WFH"] else None,
        "notes": notes
    }
    # Remove previous record for today (optional: allow only one per day)
    today = timestamp.strftime('%Y-%m-%d')
    st.session_state.attendance = [
        r for r in st.session_state.attendance
        if not (r["emp_id"] == emp_id and r["timestamp"].strftime('%Y-%m-%d') == today)
    ]
    st.session_state.attendance.append(record)
    # Append to persistent store for cross-app visibility
    try:
        attendance_store.append_attendance(emp_id, status, notes)
    except Exception:
        pass

def get_latest_status_all():
    df = pd.DataFrame(st.session_state.attendance)
    if df.empty:
        return pd.DataFrame()
    latest = df.loc[df.groupby("emp_id")["timestamp"].idxmax()]
    emp_df = pd.DataFrame.from_dict(st.session_state.employees, orient="index").reset_index().rename(columns={"index": "emp_id"})
    result = emp_df.merge(latest, on="emp_id", how="left")
    result = result[result["emp_id"] != "ADMIN"]
    return result

def get_employee_history(emp_id, days=30):
    cutoff = datetime.now() - pd.Timedelta(days=days)
    df = pd.DataFrame(st.session_state.attendance)
    if df.empty:
        return pd.DataFrame()
    return df[(df["emp_id"] == emp_id) & (df["timestamp"] >= cutoff)].sort_values("timestamp", ascending=False)

def get_attendance_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    df = pd.DataFrame(st.session_state.attendance)
    today_df = df[df["timestamp"].dt.strftime('%Y-%m-%d') == today] if not df.empty else pd.DataFrame()
    
    total = len([e for e in st.session_state.employees.keys() if e != "ADMIN"])
    present = today_df["emp_id"].nunique() if not today_df.empty else 0
    wfo = len(today_df[today_df["status"] == "WFO"]) if not today_df.empty else 0
    wfh = len(today_df[today_df["status"] == "WFH"]) if not today_df.empty else 0
    leave = len(today_df[today_df["status"] == "On Leave"]) if not today_df.empty else 0
    
    return {"total": total, "present": present, "wfo": wfo, "wfh": wfh, "leave": leave, "absent": total-present}

def get_weekly_trend():
    cutoff = datetime.now() - pd.Timedelta(days=7)
    df = pd.DataFrame(st.session_state.attendance)
    if df.empty:
        return pd.DataFrame()
    recent = df[df["timestamp"] >= cutoff]
    recent["date"] = recent["timestamp"].dt.strftime('%Y-%m-%d')
    return recent.groupby(["date", "status"]).size().reset_index(name="count")

# ==================== UI HELPERS ====================
def show_status_badge(status):
    return {"WFO": "🟢 Work From Office", "WFH": "🔵 Work From Home", "On Leave": "⚪ On Leave"}.get(status, "⚫ No Status")

# ==================== DASHBOARDS (unchanged logic, just using in-memory data) ====================
def show_employee_dashboard():
    # Main heading requested by the user
    st.title("Employee Attendance Dashboard")
    st.markdown(f"### Welcome, {st.session_state.emp_name}!")
    st.markdown(f"**Employee ID:** {st.session_state.emp_id}")

    # Show categorized real-time lists: Work in Office, Work From Home, Leave
    st.markdown("---")
    st.markdown("### Work in Office")
    latest = get_latest_status_all()
    if latest.empty:
        st.info("No attendance records yet.")
    else:
        wfo = latest[latest["status"] == "WFO"][['emp_id','name','department','role','timestamp']]
        if not wfo.empty:
            for _, r in wfo.sort_values('name').iterrows():
                st.markdown(f"- **{r['name']}** (`{r['emp_id']}`) — {r['department']} — {r['role']} — {r['timestamp'].strftime('%I:%M %p')}")
        else:
            st.write("No one is marked as Work in Office.")

    st.markdown("### Work From Home")
    if not latest.empty:
        wfh = latest[latest["status"] == "WFH"][['emp_id','name','department','role','timestamp']]
        if not wfh.empty:
            for _, r in wfh.sort_values('name').iterrows():
                st.markdown(f"- **{r['name']}** (`{r['emp_id']}`) — {r['department']} — {r['role']} — {r['timestamp'].strftime('%I:%M %p')}")
        else:
            st.write("No one is marked as Work From Home.")

    st.markdown("### Leave")
    if not latest.empty:
        leave = latest[latest['status'] == 'On Leave'][['emp_id','name','department','role','timestamp']]
        if not leave.empty:
            for _, r in leave.sort_values('name').iterrows():
                st.markdown(f"- **{r['name']}** (`{r['emp_id']}`) — {r['department']} — {r['role']} — {r['timestamp'].strftime('%Y-%m-%d')}")
        else:
            st.write("No one is marked On Leave.")

    st.markdown("---")
    # Personal quick actions and history remain useful for the employee
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### 📍 Mark Your Attendance")
        today = datetime.now().strftime('%Y-%m-%d')
        history = get_employee_history(st.session_state.emp_id, days=1)
        already_marked = not history.empty and history.iloc[0]["timestamp"].strftime('%Y-%m-%d') == today

        if already_marked:
            status = history.iloc[0]["status"]
            st.success(f"✅ Already marked today: **{show_status_badge(status)}**")

        status_option = st.radio("Select status:", ["WFO", "WFH", "On Leave"], horizontal=True)
        notes = st.text_area("Notes (optional)", height=100)

        if st.button("✅ Submit Attendance", type="primary", use_container_width=True):
            update_attendance(st.session_state.emp_id, status_option, notes)
            st.success(f"✅ Marked as **{show_status_badge(status_option)}**")
            st.balloons()
            st.rerun()

    with col2:
        st.markdown("### Status Guide")
        for txt, color in [("🟢 Work From Office", "status-card-wfo"), ("🔵 Work From Home", "status-card-wfh"), ("⚪ On Leave", "status-card-leave")]:
            st.markdown(f'<div class="{color}"><h4>{txt.split(" ",1)[1]}</h4><p>{txt}</p></div>', unsafe_allow_html=True)

    st.markdown("### 📅 Your History (Last 30 Days)")
    hist_df = get_employee_history(st.session_state.emp_id, days=30)
    if not hist_df.empty:
        hist_df["Date"] = hist_df["timestamp"].dt.strftime('%Y-%m-%d')
        hist_df["Time"] = hist_df["timestamp"].dt.strftime('%I:%M %p')
        hist_df["Status"] = hist_df["status"].apply(show_status_badge)
        st.dataframe(hist_df[["Date", "Time", "Status", "notes"]], use_container_width=True, hide_index=True)

        fig = px.pie(hist_df["status"].value_counts(), names=hist_df["status"].value_counts().index,
                     color=hist_df["status"].value_counts().index,
                     color_discrete_map={"WFO":"#10b981","WFH":"#3b82f6","On Leave":"#6b7280"})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)

def show_admin_dashboard():
    st.title("👨‍💼 Admin Dashboard")
    if st.button("🔄 Refresh"): st.rerun()

    stats = get_attendance_stats()
    c1,c2,c3,c4,c5 = st.columns(5)
    for col, label, val, color in zip(
        [c1,c2,c3,c4,c5],
        ["Total Employees","Present","🟢 WFO","🔵 WFH","⚪ Leave"],
        [stats["total"], stats["present"], stats["wfo"], stats["wfh"], stats["leave"]],
        [None,None,"#10b981","#3b82f6","#6b7280"]
    ):
        bg = f'style="background: linear-gradient(135deg, {color} 0%, {color}dd 100%);"' if color else ''
        col.markdown(f'<div class="metric-card" {bg}><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

    st.markdown("### 👥 All Employee Status")
    df = get_latest_status_all()
    if not df.empty:
        df["status"] = df["status"].fillna("No Status")
        df["Status"] = df["status"].apply(show_status_badge)
        display = df[["emp_id","name","department","role","Status","timestamp","notes"]].rename(columns={
            "emp_id":"ID","name":"Name","department":"Dept","role":"Role","timestamp":"Last Update"
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode()
        st.download_button("📥 Download Report", csv, f"report_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

    c1, c2 = st.columns(2)
    with c1:
        if not df.empty:
            fig = px.pie(df["status"].value_counts(), names=df["status"].value_counts().index,
                         color_discrete_map={"WFO":"#10b981","WFH":"#3b82f6","On Leave":"#6b7280","No Status":"#374151"})
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        trend = get_weekly_trend()
        if not trend.empty:
            fig = px.bar(trend, x="date", y="count", color="status", barmode="stack",
                         color_discrete_map={"WFO":"#10b981","WFH":"#3b82f6","On Leave":"#6b7280"})
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)

# ==================== LOGIN PAGE ====================
def show_login():
    st.title("🏢 Employee Attendance System")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### 🔐 Login")
        with st.form("login"):
            emp_id = st.text_input("Employee ID", placeholder="e.g. EMP001 or ADMIN")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("🚀 Login", use_container_width=True):
                success, name, role = verify_login(emp_id, pwd)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.emp_id = emp_id.upper()
                    st.session_state.emp_name = name
                    st.session_state.emp_role = role
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        # Note: demo accounts removed; use Signup to create an account or contact admin.
        st.info("No demo accounts are available. Please create an account or contact your administrator.")

# ==================== MAIN ====================
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    with st.sidebar:
        st.title("🏢 Attendance System")
        if st.session_state.logged_in:
            st.success(f"👋 {st.session_state.emp_name}")
            st.caption(f"Role: {st.session_state.emp_role}")
            if st.button("🚪 Logout"):
                for key in ["logged_in","emp_id","emp_name","emp_role"]:
                    st.session_state.pop(key, None)
                st.rerun()
        st.markdown("---")
        st.caption(f"🕐 {datetime.now().strftime('%I:%M %p')}")
        st.caption(f"📅 {datetime.now().strftime('%B %d, %Y')}")

    if not st.session_state.logged_in:
        show_login()
    elif st.session_state.emp_id == "ADMIN":
        show_admin_dashboard()
    else:
        show_employee_dashboard()

if __name__ == "__main__":
    main()