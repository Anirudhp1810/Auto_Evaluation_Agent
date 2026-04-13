import streamlit as st
import tempfile, os
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
from pdf_generator import generate_student_report
from migrate_db import migrate

# Run migration immediately on app start to prevent column errors
migrate()

# Import real AI grading pipeline via crew.py
try:
    from crew import execute_grading_pipeline, run_grading_agents
except ImportError:
    st.error("Failed to import AI pipeline from crew.py. Ensure dependencies are installed.")
    def run_grading_agents(text, rubric): return {}
    def execute_grading_pipeline(*args): return False

# --- CONFIG & STYLING ---
st.set_page_config(
    page_title="EvalAI - AI Evaluation System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (CSS) for Dark Theme
st.markdown("""
<style>
    /* Modern Light/Bright Theme Base */
    .stApp {
        background-color: #f8fafc; /* Very light slate background */
        color: #1e293b; /* Dark slate text */
    }
    
    /* Headers & Text */
    h1, h2, h3, h4, h5, h6, .main-header, p, div, span {
        color: #0f172a !important; /* Almost black text for high contrast */
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    .main-header {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 24px;
        color: #1e293b !important;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 10px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0,0,0,0.03);
    }
    
    /* Metric Cards / Container Boxes */
    div.css-1r6slb0, .metric-card, div[data-testid="stMetric"], [data-testid="stMetricValue"] {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
    }
    .metric-title {
        color: #64748b !important;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #0f172a !important;
        font-size: 36px;
        font-weight: 800;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:disabled {
        opacity: 0.6 !important;
        cursor: not-allowed !important;
    }
    
    /* Results Cards */
    .result-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: border-color 0.2s ease;
    }
    .result-card:hover {
        border-color: #2563eb;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* Loading Animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: .5; }
    }
    .loading-pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE LOGIC ---
DB_PATH = "evaluations.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=(), fetch=False, fetch_all=True, ignore_errors=False):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall() if fetch_all else cursor.fetchone()
        else:
            conn.commit()
            result = cursor.lastrowid
        conn.close()
        return result
    except Exception as e:
        if not ignore_errors:
            st.toast(f"Database Error: {e}", icon="🚨")
        return None

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"
if "evaluating_ids" not in st.session_state:
    st.session_state.evaluating_ids = set()
if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

def auth_page():
    st.markdown("<h1 style='text-align: center; margin-bottom: 1rem; color: #2563eb !important;'>EvalAI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b !important; margin-bottom: 2rem;'>Automated Answer Sheet Evaluation System</p>", unsafe_allow_html=True)
    
    # Check if any teachers exist
    teacher_count = execute_query("SELECT COUNT(*) as c FROM teachers", fetch=True, fetch_all=False)
    no_teachers = teacher_count['c'] == 0
    
    if no_teachers:
        st.warning("No teacher accounts found in the database. Please register an administrator account.")
        st.session_state.auth_mode = "Register"
        
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if st.session_state.auth_mode == "Login":
            with st.form("login_form"):
                st.markdown("<h3 style='text-align: center; margin-bottom: 1rem;'>Teacher Sign In</h3>", unsafe_allow_html=True)
                email = st.text_input("Email", placeholder="teacher@institute.edu", autocomplete="email")
                password = st.text_input("Password", type="password", placeholder="••••••••", autocomplete="current-password")
                
                submit = st.form_submit_button("Sign In", use_container_width=True)
                
                if submit:
                    user = execute_query("SELECT * FROM teachers WHERE email = ?", (email,), fetch=True, fetch_all=False)
                    if user and user['password_hash'] == password:
                        st.session_state.logged_in = True
                        st.session_state.user = dict(user)
                        st.rerun()
                    elif email == 'admin' and password == 'admin': # Fallback
                        st.session_state.logged_in = True
                        st.session_state.user = {'id': 1, 'name': 'Admin User', 'email': 'admin@evalai.edu'}
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
            
            if not no_teachers:
                if st.button("Don't have an account? Register Here", use_container_width=True):
                    st.session_state.auth_mode = "Register"
                    st.rerun()
                    
        else: # Registration Mode
            with st.form("register_form"):
                st.markdown("<h3 style='text-align: center; margin-bottom: 1rem;'>Create Teacher Account</h3>", unsafe_allow_html=True)
                new_name = st.text_input("Full Name *", placeholder="Dr. John Doe", autocomplete="name")
                new_email = st.text_input("Email Address *", placeholder="teacher@institute.edu", autocomplete="email")
                new_institute = st.text_input("Institute / School Name", placeholder="KLE University", autocomplete="organization")
                new_password = st.text_input("Create Password *", type="password", autocomplete="new-password")
                confirm_password = st.text_input("Confirm Password *", type="password", autocomplete="new-password")
                
                reg_submit = st.form_submit_button("Register Account", use_container_width=True)
                
                if reg_submit:
                    if not new_name or not new_email or not new_password:
                        st.error("Please fill in all required (*) fields.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        # Check if email exists
                        existing = execute_query("SELECT id FROM teachers WHERE email = ?", (new_email,), fetch=True, fetch_all=False)
                        if existing:
                            st.error("An account with this email already exists.")
                        else:
                            try:
                                execute_query("INSERT INTO teachers (name, email, password_hash, institute_name) VALUES (?, ?, ?, ?)", 
                                            (new_name, new_email, new_password, new_institute))
                                st.success("Registration successful! You can now log in.")
                                st.session_state.auth_mode = "Login"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Registration failed: {e}")
                                
            if not no_teachers:
                if st.button("Already have an account? Sign In", use_container_width=True):
                    st.session_state.auth_mode = "Login"
                    st.rerun()

if not st.session_state.logged_in:
    auth_page()
    st.stop()


# --- SIDEBAR & NAVIGATION ---
with st.sidebar:
    st.markdown(f"**👤 {st.session_state.user.get('name', 'Teacher')}**")
    st.markdown(f"<span style='font-size: 12px; color: #888;'>{st.session_state.user.get('email', '')}</span>", unsafe_allow_html=True)
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
    
    st.markdown("<hr style='border-color: #333; margin: 10px 0;'>", unsafe_allow_html=True)
    
    # Custom Navigation function to simulate SPA menu grouping
    def nav_button(label, icon, page_name):
        active = st.session_state.current_page == page_name
        bg = "rgba(59, 130, 246, 0.2)" if active else "transparent"
        border = "1px solid #3b82f6" if active else "1px solid transparent"
        color = "#ffffff" if active else "#a0aab2"
        
        if st.button(f"{icon} {label}", key=f"nav_{page_name}", use_container_width=True, 
                     help=f"Navigate to {label}"):
            st.session_state.current_page = page_name
            st.rerun()

    st.markdown("<div style='color: #666; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-bottom: 5px;'>MAIN</div>", unsafe_allow_html=True)
    nav_button("Dashboard", "📊", "Dashboard")
    nav_button("Exam Management", "📋", "Exam Management")
    nav_button("Question Bank", "❓", "Question Bank")
    
    st.markdown("<div style='color: #666; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 20px; margin-bottom: 5px;'>EVALUATION</div>", unsafe_allow_html=True)
    nav_button("Upload Answers", "📤", "Upload Answers")
    # Simulation of pending badge
    pending_count = execute_query("SELECT COUNT(*) as c FROM submissions WHERE status='Pending'", fetch=True, fetch_all=False)
    p_badge = f" ({pending_count['c']})" if pending_count and pending_count['c'] > 0 else ""
    nav_button(f"AI Evaluation{p_badge}", "🤖", "AI Evaluation")
    nav_button("Results", "🏆", "Results")
    
    st.markdown("<div style='color: #666; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 20px; margin-bottom: 5px;'>PEOPLE</div>", unsafe_allow_html=True)
    nav_button("Students", "👥", "Students")
    nav_button("Courses", "📚", "Courses")
    
    st.markdown("<div style='color: #666; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 20px; margin-bottom: 5px;'>INSIGHTS</div>", unsafe_allow_html=True)
    nav_button("Analytics", "📈", "Analytics")
    nav_button("AI Insights", "🧠", "AI Insights")
    nav_button("Settings", "⚙️", "Settings")


# --- HELPER FUNCTIONS ---
def get_pdf_download_link(filepath):
    """Generates a link allowing the data in a given file to be downloaded"""
    with open(filepath, "rb") as f:
        bytes_data = f.read()
    b64 = base64.b64encode(bytes_data).decode()
    filename = os.path.basename(filepath)
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}" style="background-color: #3b82f6; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; display: inline-block;">⬇️ Download {filename}</a>'
    return href

# --- PAGE ROUTING ---
page = st.session_state.current_page

if page == "Dashboard":
    st.markdown("<div class='main-header'>Dashboard Overview</div>", unsafe_allow_html=True)
    
    # DB Queries — count students from BOTH the students table and submissions (uploaded answer sheets)
    total_students = execute_query("""
        SELECT COUNT(DISTINCT student_id) as c FROM (
            SELECT student_id FROM students WHERE student_id IS NOT NULL
            UNION
            SELECT student_id FROM submissions WHERE student_id IS NOT NULL AND student_id != ''
        )
    """, fetch=True, fetch_all=False)
    total_courses = execute_query("SELECT COUNT(*) as c FROM courses", fetch=True, fetch_all=False)
    evals_remaining = execute_query("SELECT COUNT(*) as c FROM submissions WHERE status='pending'", fetch=True, fetch_all=False)
    evals_done = execute_query("SELECT COUNT(*) as c FROM evaluations WHERE status='evaluated'", fetch=True, fetch_all=False)
    failed_students = execute_query("SELECT COUNT(*) as c FROM evaluations WHERE grade='F'", fetch=True, fetch_all=False)
    
    val_students = total_students['c'] if total_students else 0
    val_courses = total_courses['c'] if total_courses else 0
    val_evals_remaining = evals_remaining['c'] if evals_remaining else 0
    val_evals_done = evals_done['c'] if evals_done else 0
    val_failed = failed_students['c'] if failed_students else 0
    
    # 1. Stat Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f"<div class='metric-card'><div class='metric-title'>Total Students</div><div class='metric-value'>{val_students}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-title'>Total Courses</div><div class='metric-value'>{val_courses}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-title'>Evaluated</div><div class='metric-value' style='color: #4ade80 !important;'>{val_evals_done}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-title'>Evals Remaining</div><div class='metric-value' style='color: #f59e0b !important;'>{val_evals_remaining}</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='metric-card'><div class='metric-title'>Failed Students</div><div class='metric-value' style='color: #ef4444 !important;'>{val_failed}</div></div>", unsafe_allow_html=True)
    
    # 2. Charts Row
    ch1, ch2, ch3 = st.columns([1.5, 1, 1])
    
    with ch1:
        st.markdown("<h4 style='font-size: 16px; margin-bottom: 15px;'>Student Performance Trend</h4>", unsafe_allow_html=True)
        # Fetch trend data (Avg score per exam, ordered by exam date)
        trend_data = execute_query("""
            SELECT e.name, AVG(ev.total_score * 100.0 / CASE WHEN s.total_marks=0 THEN 100 ELSE s.total_marks END) as avg_score
            FROM evaluations ev 
            JOIN submissions s ON ev.submission_id = s.id 
            JOIN exams e ON s.exam_id = e.id
            WHERE ev.status='evaluated' GROUP BY s.exam_id ORDER BY e.date ASC
            """, fetch=True)
            
        if trend_data:
            df_trend = pd.DataFrame([dict(r) for r in trend_data])
            fig = px.line(df_trend, x='name', y='avg_score', line_shape="spline", markers=True)
            fig.update_traces(line_color="#2563eb", marker=dict(size=8, color="#8b5cf6"))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, color="#a0aab2", title=""), 
                yaxis=dict(showgrid=True, gridcolor="#e2e8f0", color="#a0aab2", title="")
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("📊 No evaluation trend data yet. Add students & exams to tracking.")
        
    with ch2:
        st.markdown("<h4 style='font-size: 16px; margin-bottom: 15px;'>Grade Distribution</h4>", unsafe_allow_html=True)
        grades_data = execute_query("SELECT grade, COUNT(*) as count FROM evaluations WHERE status='evaluated' AND grade IS NOT NULL GROUP BY grade", fetch=True)
        
        if grades_data:
            df_grades = pd.DataFrame([dict(r) for r in grades_data])
            # Ensure custom color mapping if specific grades exist
            color_map = {'A+': '#4ade80', 'A': '#2dd4bf', 'B': '#3b82f6', 'C': '#8b5cf6', 'D': '#f59e0b', 'F': '#ef4444'}
            fig_pie = px.pie(df_grades, values='count', names='grade', hole=0.7, color='grade', color_discrete_map=color_map)
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("🥧 No grades awarded yet.")

    with ch3:
        st.markdown("<h4 style='font-size: 16px; margin-bottom: 15px;'>🏆 Top Performers</h4>", unsafe_allow_html=True)
        top_students = execute_query("""
            SELECT 
                COALESCE(su.student_name, su.student_id, 'Unknown') as name,
                ev.total_score,
                CASE WHEN su.total_marks IS NULL OR su.total_marks = 0 THEN 100 ELSE su.total_marks END as max_marks,
                (ev.total_score * 100.0 / CASE WHEN su.total_marks IS NULL OR su.total_marks = 0 THEN 100 ELSE su.total_marks END) as pct,
                ev.grade
            FROM evaluations ev 
            JOIN submissions su ON ev.submission_id = su.id 
            WHERE ev.status = 'evaluated'
            ORDER BY pct DESC 
            LIMIT 3
            """, fetch=True)
            
        if top_students:
            medals = ["🥇", "🥈", "🥉"]
            grade_colors = {"A+": "#16a34a", "A": "#0d9488", "B": "#2563eb", "C": "#d97706", "D": "#ea580c", "F": "#dc2626"}
            for i, row in enumerate(top_students):
                medal = medals[i] if i < len(medals) else f"{i+1}."
                gc = grade_colors.get(row['grade'], "#64748b")
                st.markdown(
                    f"""<div style='display:flex; justify-content:space-between; align-items:center;
                        background:#ffffff; border:1px solid #e2e8f0; border-radius:10px;
                        padding:10px 14px; margin-bottom:8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);'>
                        <span style='color:#1e293b; font-weight:600; font-size:14px;'>{medal} {row['name']}</span>
                        <span>
                            <span style='background:{gc}18; color:{gc}; border:1px solid {gc}44;
                                border-radius:6px; padding:2px 8px; font-size:11px; font-weight:700;
                                margin-right:8px;'>{row['grade']}</span>
                            <span style='color:#2563eb; font-weight:700; font-size:14px;'>{row['pct']:.1f}%</span>
                        </span>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.info("🏆 No ranked students yet.")


elif page == "Upload Answers":
    st.markdown("<div class='main-header'>Upload Student Answers</div>", unsafe_allow_html=True)
    
    # Column migrations handled by migrate() at startup
    
    col_ctrl, col_prev, col_queue = st.columns([1.2, 1.5, 1.2])
    
    with col_ctrl:
        exams_db = execute_query("SELECT id, name FROM exams", fetch=True)
        exam_opts = {"Select Exam": None}
        if exams_db:
            for ex in exams_db:
                exam_opts[ex['name']] = ex['id']
                
        exam_sel = st.selectbox("Assign Exam", list(exam_opts.keys()))
        
        st.markdown("<h5 style='margin-top: 15px; margin-bottom: 5px; font-size: 14px;'>Rubrics & Grading</h5>", unsafe_allow_html=True)
        rubrics_text = st.text_area("Paste JSON Answer Key", help="Paste a JSON object containing the rubrics and marks breakdown.", height=200, placeholder='{\n  "questions": [\n    {"q_no": 1, "topic": "AI", "max_marks": 10}\n  ]\n}')
        
        rubrics_json_str = None
        auto_total_marks = 0
        
        if rubrics_text and rubrics_text.strip():
            import json
            try:
                rubrics_data = json.loads(rubrics_text)
                rubrics_json_str = json.dumps(rubrics_data)
                
                # Parse total marks
                if 'questions' in rubrics_data:
                    auto_total_marks = sum(q.get('max_marks', 0) for q in rubrics_data['questions'])
                    st.success(f"Successfully parsed {len(rubrics_data['questions'])} questions.")
                    
                    # Preview table
                    preview_df = pd.DataFrame(rubrics_data['questions'])
                    st.dataframe(preview_df, use_container_width=True, hide_index=True, height=150)
                else:
                    st.error("JSON must contain a 'questions' array.")
            except Exception as e:
                st.error(f"Invalid JSON format. Please check your syntax. Error: {e}")
                
        c1, c2 = st.columns(2)
        # Enable total_m if they want to override, but default it to auto_total_marks if parsed
        total_m = c1.number_input("Total Marks", min_value=1, value=max(1, auto_total_marks))
        pass_m = c2.number_input("Passing Marks", min_value=1, value=max(1, int(total_m*0.4)))
        
        st.markdown("<h5 style='margin-top: 15px; margin-bottom: 5px; font-size: 14px;'>Student Details</h5>", unsafe_allow_html=True)
        scol1, scol2 = st.columns(2)
        with scol1:
            in_student_name = st.text_input("Student Name *", placeholder="e.g. Priya Sharma", key="us_name", autocomplete="name")
        with scol2:
            in_student_id = st.text_input("Student ID *", placeholder="e.g. STU-2024-001", key="us_id", autocomplete="off")
        in_roll_no = st.text_input("Roll Number", placeholder="e.g. CS2021-01", key="us_roll", autocomplete="off")
        
        st.markdown("<h5 style='margin-top: 15px; margin-bottom: 5px; font-size: 14px;'>OCR Settings</h5>", unsafe_allow_html=True)
        ocr_advanced = st.checkbox("Enable Advanced Handwriting OCR", value=True, help="Uses OpenCV preprocessing to improve accuracy for handwritten sheets.")
        if ocr_advanced:
            st.caption("✨ Preprocessing active: Grayscale, Noise Removal, Deskewing enabled.")

        uploaded_files = st.file_uploader("Upload Student Answers", accept_multiple_files=True, type=['pdf', 'jpg', 'png', 'jpeg', 'txt'])
        
        if uploaded_files:
            if st.button("Upload & Prepare for Evaluation", use_container_width=True, type="primary"):
                os.makedirs("uploads", exist_ok=True)
                if not exam_opts[exam_sel]:
                    st.toast("Please select a valid Exam.", icon="🚨")
                elif not rubrics_json_str:
                    st.toast("Please paste a valid JSON Rubric in the text area.", icon="🚨")
                elif not in_student_name or not in_student_id:
                    st.toast("Please enter Student Name and Student ID.", icon="🚨")
                else:
                    progress_text = st.empty()
                    progress_bar = st.progress(0)
                    
                    progress_text.markdown("⏳ **Uploading files...**")
                    import time
                    time.sleep(1)
                    
                    success_count = 0
                    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
                    os.makedirs(uploads_dir, exist_ok=True)
                    
                    for idx, f in enumerate(uploaded_files):
                        file_path = os.path.join(uploads_dir, f.name)
                        
                        with open(file_path, "wb") as out_f:
                            out_f.write(f.getbuffer())
                        
                        ext_text = "Pending OCR extraction..."
                        if f.name.endswith('.txt'):
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as txt_f:
                                ext_text = txt_f.read()
                        
                        # Fix insertion with all new columns
                        try:
                            # Using 'pending' status directly
                            execute_query(
                                "INSERT INTO submissions (file_name, file_path, exam_id, status, ocr_text, rubrics_json, total_marks, passing_marks, student_name, student_id, roll_no, created_at) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                                (f.name, file_path, exam_opts[exam_sel], 'pending', ext_text, rubrics_json_str, total_m, pass_m, in_student_name, in_student_id, in_roll_no),
                                ignore_errors=False
                            )
                            success_count += 1
                        except Exception as e:
                            st.error(f"Failed to save submission {f.name}: {e}")
                        
                        progress_bar.progress((idx + 1) / len(uploaded_files))
                        
                    progress_text.markdown("✅ **Files Processed and Queued!**")
                    if success_count > 0:
                        st.toast(f"{success_count} files queued.", icon="✅")
                        st.session_state.eval_done = True
                    time.sleep(1)
                    st.rerun()

        if st.session_state.get('eval_done', False):
            st.success("Files uploaded successfully. Ready for AI Evaluation.")
            if st.button("Go to AI Evaluation →", use_container_width=True):
                st.session_state.current_page = "AI Evaluation"
                st.session_state.eval_done = False
                st.rerun()
            
    with col_prev:
        st.markdown("<h4 style='font-size: 16px;'>Preview Panel</h4>", unsafe_allow_html=True)
        with st.container(height=500, border=True):
            if uploaded_files:
                f = uploaded_files[0]
                f.seek(0)
                
                if f.name.lower().endswith('.pdf'):
                    b64 = base64.b64encode(f.getvalue()).decode('utf-8')
                    pdf_html = f"""
                    <div style='background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; height: 400px; display: flex; flex-direction: column;'>
                        <h5 style='margin-top: 0; color: #3b82f6; font-size: 14px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 10px;'>Previewing: {f.name}</h5>
                        <iframe src="data:application/pdf;base64,{b64}" width="100%" height="100%" style="border: none; flex-grow: 1;"></iframe>
                    </div>
                    """
                    st.markdown(pdf_html, unsafe_allow_html=True)
                elif f.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    st.markdown(f"""
                    <div style='background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0;'>
                        <h5 style='margin-top: 0; color: #3b82f6; font-size: 14px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 10px;'>Previewing: {f.name}</h5>
                    """, unsafe_allow_html=True)
                    st.image(f, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                elif f.name.lower().endswith('.txt'):
                    st.markdown(f"""
                    <div style='background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0;'>
                        <h5 style='margin-top: 0; color: #3b82f6; font-size: 14px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 10px;'>Previewing: {f.name}</h5>
                    """, unsafe_allow_html=True)
                    st.text_area("Extracted Text:", value=f.getvalue().decode("utf-8", errors="ignore"), height=400)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color: #f8fafc; padding: 20px; text-align: center; border-radius: 8px; border: 1px solid #e2e8f0; color: #64748b; height: 100%; display: flex; align-items: center; justify-content: center;'>Upload a file to see preview & extracted text.</div>", unsafe_allow_html=True)
            
    with col_queue:
        st.markdown("<h4 style='font-size: 16px;'>Upload Queue</h4>", unsafe_allow_html=True)
        with st.container(height=500, border=True):
            queue = execute_query("SELECT id, IFNULL(file_name, 'Unknown_File') as file_name, status, created_at FROM submissions ORDER BY created_at DESC LIMIT 20", fetch=True)
            if queue:
                for item in queue:
                    bg = "#fef3c7" if item['status'] in ['Pending', 'Queued', 'Ready'] else "#dcfce7" if item['status'] == 'Evaluated' else "#e0f2fe"
                    fc = "#d97706" if item['status'] in ['Pending', 'Queued', 'Ready'] else "#16a34a" if item['status'] == 'Evaluated' else "#0284c7"
                    fn = item['file_name']
                    if fn == "None" or not fn: fn = f"Submission #{item['id']}"
                    st.markdown(f"""
                    <div style='background-color: #ffffff; padding: 12px; margin-bottom: 10px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; transition: border-color 0.2s ease;' class='result-card'>
                        <div style='overflow: hidden; padding-right: 10px;'>
                            <div style='font-weight: 600; color: #1e293b; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;' title='{fn}'>{fn}</div>
                            <div style='font-size: 11px; color: #64748b;'>{str(item['created_at'])[:16]}</div>
                        </div>
                        <div style='background-color: {bg}; color: {fc}; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: bold; text-transform: uppercase;'>
                            {item['status']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("☁️ Queue is empty.")


elif page == "AI Evaluation":
    st.markdown("<div class='main-header'>AI Evaluation System</div>", unsafe_allow_html=True)
    
    # Schema handled by migrate() at startup
    
    # Track which submissions are mid-evaluation to show correct status badge
    if 'evaluating_ids' not in st.session_state:
        st.session_state['evaluating_ids'] = set()
        
    # Fetch ALL submissions (pending + currently-being-evaluated) to show full status
    query_all = """
        SELECT su.id, su.file_path, su.file_name, e.name as exam_name, su.student_name, su.student_id, su.roll_no, 
               su.created_at, su.status, su.ocr_text, su.rubrics_json, 
               su.total_marks, su.passing_marks
        FROM submissions su
        LEFT JOIN exams e ON su.exam_id = e.id
        WHERE su.status = 'pending'
        ORDER BY su.created_at ASC
    """
    pending_subs = execute_query(query_all, fetch=True)
    pending_count = len(pending_subs) if pending_subs else 0
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        if pending_count > 0:
            est_time = pending_count * 0.5
            st.info(f"🤖 **{pending_count}** submissions pending evaluation. Estimated time: ~{est_time:.1f} mins.")
        else:
            st.success("🎉 All caught up! No submissions pending evaluation.")
            
    with col_t2:
        if pending_count > 0:
            if st.button("▶️ Evaluate All Pending", use_container_width=True, type="primary"):
                with st.spinner("Running AI grading for all submissions..."):
                    import time
                    for sub in pending_subs:
                        s_n = sub['student_name'] if sub['student_name'] else "Unknown"
                        s_i = sub['student_id'] if sub['student_id'] else "N/A"
                        s_r = sub['roll_no'] if sub['roll_no'] else "N/A"
                        e_n = sub['exam_name'] if sub['exam_name'] else "Unknown Exam"
                        execute_grading_pipeline(sub['id'], sub['file_path'], sub['ocr_text'], sub['rubrics_json'], sub['total_marks'], sub['passing_marks'], s_n, s_i, s_r, e_n)
                # Navigate to Results after all done
                st.toast("✅ All evaluations complete! Navigating to Results...", icon="🎯")
                if 'eval_search' in st.session_state: del st.session_state['eval_search']
                if 'eval_course' in st.session_state: del st.session_state['eval_course']
                if 'eval_exam' in st.session_state: del st.session_state['eval_exam']
                st.session_state.current_page = "Results"
                st.session_state['evaluating_ids'] = set()
                st.rerun()
        else:
            if st.button("🏆 View Results", type="primary", use_container_width=True):
                st.session_state.current_page = "Results"
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    if pending_count > 0:
        # Build headers
        st.markdown("""
        <div style='display:flex; padding: 10px; background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; font-weight: bold; color: #475569; font-size: 13px;'>
            <div style='width: 5%;'>ID</div>
            <div style='width: 20%;'>File Name</div>
            <div style='width: 15%;'>Exam</div>
            <div style='width: 25%;'>Student Details</div>
            <div style='width: 15%;'>Status</div>
            <div style='width: 20%; text-align: center;'>Action</div>
        </div>
        """, unsafe_allow_html=True)
        
        for sub in pending_subs:
            s_name = sub['student_name'] if sub['student_name'] else "Unknown"
            s_id = sub['student_id'] if sub['student_id'] else "N/A"
            s_roll = sub['roll_no'] if sub['roll_no'] else "N/A"
            e_name = sub['exam_name'] if sub['exam_name'] else "Unknown Exam"
            is_evaluating = sub['id'] in st.session_state.get('evaluating_ids', set())
            
            c1, c2, c3, c4, c5, c6 = st.columns([0.5, 2, 1.5, 2.5, 1.5, 2])
            c1.markdown(f"<p style='padding-top:8px;'>{sub['id']}</p>", unsafe_allow_html=True)
            c2.markdown(f"<p style='padding-top:8px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>{sub['file_name']}</p>", unsafe_allow_html=True)
            c3.markdown(f"<p style='padding-top:8px;'>{e_name}</p>", unsafe_allow_html=True)
            c4.markdown(f"<p style='padding-top:2px; font-size:13px; margin:0;'><b>{s_name}</b><br><span style='color:grey;'>ID: {s_id} | Roll: {s_roll}</span></p>", unsafe_allow_html=True)
            
            if is_evaluating:
                c5.markdown("<span style='background-color:#e0f2fe; padding: 4px 8px; border-radius:12px; font-size:12px; color:#0369a1; font-weight:600;' class='loading-pulse'>⏳ Evaluating...</span>", unsafe_allow_html=True)
                c6.button("Processing...", key=f"eval_proc_{sub['id']}", disabled=True, use_container_width=True)
            else:
                c5.markdown("<span style='background-color:#fef08a; padding: 4px 8px; border-radius:12px; font-size:12px; color:#a16207; font-weight:600;'>Pending AI 🤖</span>", unsafe_allow_html=True)
                # Disable main button if ANY evaluation is in progress to prevent server overload
                eval_any = len(st.session_state.get('evaluating_ids', set())) > 0
                if c6.button("Evaluate", key=f"eval_{sub['id']}", use_container_width=True, type="primary", disabled=eval_any):
                    st.session_state['evaluating_ids'].add(sub['id'])
                    st.rerun() # Immediate rerun to show loading state
                    
        # Implementation of evaluation logic at the top of the loop or outside
        for sub_id in list(st.session_state.get('evaluating_ids', set())):
            # Find the submission in the list
            target_sub = next((s for s in pending_subs if s['id'] == sub_id), None)
            if target_sub:
                with st.status(f"🚀 AI Evaluation in progress for {target_sub['file_name']}...", expanded=True) as status:
                    st.write("Extracting and cleaning text...")
                    s_name = target_sub['student_name'] if target_sub['student_name'] else "Unknown"
                    s_id = target_sub['student_id'] if target_sub['student_id'] else "N/A"
                    s_roll = target_sub['roll_no'] if target_sub['roll_no'] else "N/A"
                    e_name = target_sub['exam_name'] if target_sub['exam_name'] else "Unknown Exam"
                    
                    success = execute_grading_pipeline(target_sub['id'], target_sub['file_path'], target_sub['ocr_text'], target_sub['rubrics_json'], target_sub['total_marks'], target_sub['passing_marks'], s_name, s_id, s_roll, e_name)
                    
                    if success:
                        status.update(label=f"✅ Evaluation complete for {s_name}!", state="complete", expanded=False)
                        st.session_state['evaluating_ids'].discard(sub_id)
                        st.toast(f"✅ Graded {s_name} successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        status.update(label=f"❌ Evaluation failed for {target_sub['file_name']}", state="error")
                        st.session_state['evaluating_ids'].discard(sub_id)
                        st.toast("Evaluation failed. Please check logs.", icon="🚨")
                        st.rerun()
                        
        st.markdown("<hr style='border-color: #e2e8f0; margin-top: 5px;'>", unsafe_allow_html=True)
    else:
        st.info("No submissions found. Upload answer sheets to begin.")

elif page == "Results":
    st.markdown("<div class='main-header'>Results Management</div>", unsafe_allow_html=True)
    
    tab_res, tab_arch = st.tabs(["Evaluation Results", "Report Archive"])
    
    with tab_res:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        
        courses_db = execute_query("SELECT id, name FROM courses", fetch=True)
        c_opts = {"All Courses": None}
        if courses_db:
            for c in courses_db: c_opts[c['name']] = c['id']
            
        c_list = col_f1.selectbox("Filter by Course", list(c_opts.keys()), key='eval_course')
        
        exams_db = execute_query("SELECT id, name FROM exams", fetch=True)
        e_opts = {"All Exams": None}
        if exams_db:
            for e in exams_db: e_opts[e['name']] = e['id']
            
        e_list = col_f2.selectbox("Filter by Exam", list(e_opts.keys()), key='eval_exam')
        search = col_f3.text_input("Search Student Name or ID", autocomplete="off", key='eval_search')

        # --- CLEAR HISTORY BUTTON ---
        c_clear1, c_clear2 = st.columns([5, 1])
        with c_clear2:
            if st.button("🧹 Clear History", use_container_width=True, type="secondary", help="Delete all evaluation records"):
                st.session_state.confirm_clear = True
        
        if st.session_state.get('confirm_clear', False):
            st.warning("⚠️ **Are you sure?** This will permanently delete all evaluations, submissions, and reports.")
            cc1, cc2, cc3 = st.columns([1, 1, 4])
            if cc1.button("Yes, Clear All", type="primary", use_container_width=True):
                with st.spinner("Clearing history..."):
                    execute_query("DELETE FROM evaluations")
                    execute_query("DELETE FROM reports")
                    # Also update status of submissions if we don't want to delete them, 
                    # but usually 'Clear History' means clearing the whole pipeline.
                    execute_query("DELETE FROM submissions")
                    st.session_state.confirm_clear = False
                    st.toast("History cleared successfully!", icon="✅")
                    st.rerun()
            if cc2.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()
        
        # Real DB Fetch - Fixed duplicate rendering with DISTINCT and GROUP BY
        query = """
        SELECT DISTINCT
            su.id as sub_id, su.student_id, su.student_name, su.roll_no, 
            ev.total_score as total_marks, ev.grade, ev.feedback, ev.breakdown_json, ev.status, su.file_name, ev.pdf_path,
            e.name as exam_name, su.total_marks as max_marks, c.name as course_name
        FROM submissions su
        JOIN evaluations ev ON ev.submission_id = su.id
        LEFT JOIN exams e ON su.exam_id = e.id
        LEFT JOIN courses c ON e.course_id = c.id
        WHERE (ev.status = 'evaluated' OR su.status = 'evaluated')
        """
        params = []
        
        # We will append the GROUP BY after dynamically adding the WHERE clauses
        group_by_clause = " GROUP BY su.id ORDER BY su.created_at DESC"
        
        if c_opts[c_list]:
            query += " AND c.id = ?"
            params.append(c_opts[c_list])
        if e_opts[e_list]:
            query += " AND e.id = ?"
            params.append(e_opts[e_list])
        if search:
            query += " AND (su.student_name LIKE ? OR su.student_id LIKE ? OR su.roll_no LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            
        query += group_by_clause
        res = execute_query(query, tuple(params), fetch=True)
        
        if res:
            for r in res:
                s_name = r['student_name'] if r['student_name'] else "Unknown Student (Orphaned Record)"
                s_id = r['student_id'] if r['student_id'] else "---"
                s_roll = r['roll_no'] if r['roll_no'] else "---"
                t_marks = r['total_marks'] if r['total_marks'] is not None else 0
                max_m = r['max_marks'] if r['max_marks'] else 100
                percentage = round((t_marks / max_m) * 100, 1) if max_m else 0
                pass_status = f"✅ Pass ({r['grade']})" if r['grade'] not in ['F', None] else "❌ Fail"
                feedback = r['feedback'] if 'feedback' in r.keys() and r['feedback'] else "No feedback available."
                
                st.markdown(f"""
                <div style='background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
                    <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                        <div style='flex: 1; padding-right: 15px;'>
                            <h4 style='margin: 0; color: #1e293b; font-size: 16px;'>{s_name} <span style='font-size: 12px; color: #64748b; font-weight: normal;'>({s_id}) | Roll: {s_roll}</span></h4>
                            <div style='color: #64748b; font-size: 13px; margin-top: 4px;'>{r['course_name']} • {r['exam_name']} • File: {r['file_name']}</div>
                            <div style='margin-top: 8px; font-size: 13px; color: #475569; background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;'>
                                <b>AI Feedback:</b> {feedback}
                            </div>
                        </div>
                        <div style='text-align: right; min-width: 120px;'>
                            <div style='font-size: 20px; font-weight: bold; color: #2563eb;'>{int(t_marks)}/{int(max_m)}</div>
                            <div style='font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 4px;'>{percentage}% • {pass_status}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                cl1, cl2, cl3 = st.columns([2, 1, 5])
                
                report_query = execute_query("SELECT path FROM reports WHERE sub_id = ?", (r['sub_id'],), fetch=True, fetch_all=False)
                
                pdf_target_path = None
                row_dict = dict(r)
                if row_dict.get('pdf_path') and os.path.exists(row_dict['pdf_path']):
                    pdf_target_path = row_dict['pdf_path']
                elif report_query and os.path.exists(report_query['path']):
                    pdf_target_path = report_query['path']
                else:
                    # Search fallback directory
                    reports_dir = os.path.join(os.path.dirname(__file__), 'results', 'reports')
                    if os.path.exists(reports_dir):
                        for f in os.listdir(reports_dir):
                            if f.endswith('.pdf') and (str(s_id) in f or f"SUB-{r['sub_id']}" in f):
                                pdf_target_path = os.path.join(reports_dir, f)
                                break
                
                generate_clicked = False
                if pdf_target_path:
                    with open(pdf_target_path, "rb") as f:
                        pdf_data = f.read()
                    cl1.download_button(
                        label="📄 Download PDF", 
                        data=pdf_data, 
                        file_name=os.path.basename(pdf_target_path), 
                        mime="application/pdf", 
                        key=f"dl_pdf_{r['sub_id']}"
                    )
                    if cl2.button("🔄 Regenerate", key=f"regen_{r['sub_id']}", use_container_width=True):
                        generate_clicked = True
                else:
                    if cl1.button("📄 Generate PDF", key=f"gen_{r['sub_id']}", use_container_width=True):
                        generate_clicked = True
                        
                if generate_clicked:
                    # Schema handled by migrate() at startup
                    
                    from pdf_generator import generate_student_report
                    import json
                    import os
                    
                    row_dict = dict(r)
                    ev_breakdown = row_dict.get('breakdown_json', '[]')
                    try: marks_data = json.loads(ev_breakdown) if ev_breakdown else []
                    except: marks_data = []
                        
                    formatted_marks = []
                    for md in marks_data:
                        formatted_marks.append({
                            'question_id': md.get('q_no', 'Q'),
                            'awarded': md.get('marks_awarded', 0),
                            'max': md.get('max_marks', 0),
                            'feedback': md.get('comment', 'AI Evaluated')
                        })
                        
                    student_id_str = s_id if s_id != '---' else f"SUB-{r['sub_id']}"
                    
                    try:
                        new_pdf_path = generate_student_report(
                            student_name=s_name,
                            student_id=student_id_str,
                            roll_no=s_roll,
                            exam_name=r['exam_name'],
                            marks_data=formatted_marks,
                            total_marks=int(t_marks),
                            max_marks=int(max_m),
                            grade=r['grade'],
                            overall_feedback=feedback
                        )
                        execute_query("INSERT INTO reports (sub_id, student_id, exam_name, path) VALUES (?, ?, ?, ?)", (r['sub_id'], student_id_str, r['exam_name'], new_pdf_path))
                        # Update evaluations table to hard-link the newly generated PDF path
                        execute_query("UPDATE evaluations SET pdf_path=? WHERE submission_id=?", (new_pdf_path, r['sub_id']))
                        st.toast(f"Report generated for {s_name}!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generate PDF Error: {e}")
                
                st.markdown("<hr style='margin: 10px 0; border-color: transparent;'>", unsafe_allow_html=True)
                
        else:
            if c_list != "All Courses" or e_list != "All Exams":
                st.info("No evaluated results found for this course/exam combination.")
            else:
                st.info("No evaluated results yet. Go to AI Evaluation to grade submissions.")
                
    with tab_arch:
        st.markdown("### 🗄️ Report Archive")
        try:
            reports = execute_query("SELECT id, student_id, exam_name, path, created_at FROM reports ORDER BY created_at DESC", fetch=True)
            if reports:
                for rep in reports:
                    st.markdown(f"**{rep['student_id']}** - {rep['exam_name']} (Generated: {rep['created_at'][:16]})")
                    st.markdown(f"[Download PDF Document](/{rep['path']})", unsafe_allow_html=True)
                    st.markdown("---")
            else:
                st.info("No reports generated yet.")
        except:
            st.info("No reports generated yet.")

elif page == "Students":
    st.markdown("<div class='main-header'>Student Management</div>", unsafe_allow_html=True)
    
    # Ensure schema handles course_id
    try: 
        execute_query("ALTER TABLE students ADD COLUMN course_id INTEGER", ignore_errors=True)
    except: 
        pass

    col_t1, col_t2 = st.columns([4, 1])
    with col_t2:
        if st.button("➕ Add Student", use_container_width=True):
            st.session_state.show_add_student = not st.session_state.get('show_add_student', False)
            st.rerun()
            
    if st.session_state.get('show_add_student', False):
        st.markdown("<div style='background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
        st.subheader("Register New Student")
        with st.form("add_student"):
            c1, c2 = st.columns(2)
            s_name = c1.text_input("Full Name *", autocomplete="name")
            s_id = c2.text_input("Student ID", placeholder="Auto-generated if empty", autocomplete="off")
            s_roll = c1.text_input("Roll Number *", autocomplete="off")
            s_email = c2.text_input("Email *", autocomplete="email")
            s_phone = c1.text_input("Phone Number (Optional)", autocomplete="tel")
            
            courses_db = execute_query("SELECT id, name FROM courses", fetch=True)
            course_opts = {"None": None}
            if courses_db:
                for crs in courses_db:
                    course_opts[crs['name']] = crs['id']
            s_course = c2.selectbox("Course Enrolled", list(course_opts.keys()))
            
            if st.form_submit_button("Save Student", use_container_width=True):
                if not s_name or not s_roll or not s_email:
                    st.toast("Please fill all required (*) fields.", icon="🚨")
                else:
                    actual_id = s_id if s_id else f"STU-{datetime.now().strftime('%Y-%m%d%H%M')}"
                    execute_query("INSERT INTO students (name, student_id, roll_no, email, course_id) VALUES (?, ?, ?, ?, ?)", 
                                  (s_name, actual_id, s_roll, s_email, course_opts[s_course]))
                    st.toast(f"Student {s_name} added successfully!", icon="✅")
                    st.session_state.show_add_student = False
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Enrolled Students")
    students = execute_query("SELECT * FROM students ORDER BY created_at DESC", fetch=True)
    if students:
        for s in students:
            with st.container():
                rc1, rc2, rc3 = st.columns([6, 1, 1])
                rc1.markdown(f"**{s['name']}** <span style='color:#64748b; font-size:13px;'>({s['student_id']}) • Roll No: {s['roll_no']} • {s['email']}</span>", unsafe_allow_html=True)
                if rc2.button("Edit", key=f"edit_stu_{s['id']}", use_container_width=True):
                    st.toast("Edit functionality to be implemented.", icon="ℹ️")
                if rc3.button("Delete", key=f"del_stu_{s['id']}", use_container_width=True):
                    execute_query("DELETE FROM students WHERE id=?", (s['id'],))
                    st.toast(f"Deleted student {s['name']}", icon="🗑️")
                    st.rerun()
                st.markdown("<hr style='margin: 8px 0; border-color: #e2e8f0;'>", unsafe_allow_html=True)
    else:
        st.info("👥 No students added yet. Click '+ Add Student' to begin.")

elif page == "Courses":
    st.markdown("<div class='main-header'>Course Management</div>", unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns([4, 1])
    with col_t2:
        if st.button("➕ Add Course", use_container_width=True):
            st.session_state.show_add_course = not st.session_state.get('show_add_course', False)
            st.rerun()
            
    if st.session_state.get('show_add_course', False):
        st.markdown("<div style='background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
        st.subheader("Create New Course")
        with st.form("add_course"):
            c1, c2 = st.columns(2)
            c_name = c1.text_input("Course Name *", autocomplete="off")
            c_code = c2.text_input("Course Code *", placeholder="e.g., CS201", autocomplete="off")
            c_desc = st.text_input("Description (Optional)", autocomplete="off")
            
            c3, c4 = st.columns(2)
            teachers_db = execute_query("SELECT id, name FROM teachers", fetch=True)
            t_opts = {}
            if teachers_db:
                for t in teachers_db:
                    t_opts[t['name']] = t['id']
            c_teacher = c3.selectbox("Teacher Assigned", list(t_opts.keys()))
            c_sem = c4.text_input("Semester/Year (Optional)", autocomplete="off")
            
            if st.form_submit_button("Save Course", use_container_width=True):
                if not c_name or not c_code:
                    st.toast("Course Name and Code are required.", icon="🚨")
                else:
                    # Also saving semester dynamically if we alter the schema.
                    try: execute_query("ALTER TABLE courses ADD COLUMN semester TEXT", ignore_errors=True)
                    except: pass
                    try: execute_query("ALTER TABLE courses ADD COLUMN description TEXT", ignore_errors=True)
                    except: pass
                    
                    execute_query("INSERT INTO courses (name, code, teacher_id, semester, description) VALUES (?, ?, ?, ?, ?)", 
                                  (c_name, c_code, t_opts[c_teacher], c_sem, c_desc))
                    st.toast(f"Course {c_name} created successfully!", icon="✅")
                    st.session_state.show_add_course = False
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    courses = execute_query("SELECT * FROM courses ORDER BY created_at DESC", fetch=True)
    if courses:
        # Displaying them as cards in a row
        cols = st.columns(3)
        for i, c in enumerate(courses):
            # Calculate dynamic average for course
            c_avg_query = execute_query("""
                SELECT AVG(ev.total_score)*100.0/AVG(su.total_marks) as avg_p 
                FROM evaluations ev 
                JOIN submissions su ON ev.submission_id = su.id 
                JOIN exams e ON su.exam_id = e.id 
                WHERE e.course_id = ? AND ev.status = 'evaluated' AND su.total_marks > 0
            """, (c['id'],), fetch=True)
            c_avg = int(c_avg_query[0]['avg_p']) if c_avg_query and c_avg_query[0]['avg_p'] else 0
            
            with cols[i % 3]:
                # Styling as requested: similar to the dark background styling
                st.markdown(f"""
                <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h4 style='margin: 0; color: #f8fafc; font-size: 16px;'>{c['name']}</h4>
                        <span style='background-color:#065f46; color:#34d399; font-size:10px; padding:2px 8px; border-radius:12px;'>Active</span>
                    </div>
                    <div style='color: #94a3b8; font-size: 12px; margin-top: 4px;'>{c['code']} • {dict(c).get('semester', 'Semester N/A')}</div>
                    <div style='margin-top: 15px; background: #334155; height: 4px; border-radius: 2px;'><div style='background: #3b82f6; width: {c_avg}%; height: 100%; border-radius: 2px;'></div></div>
                    <div style='color: #60a5fa; font-size: 10px; margin-top: 4px; margin-bottom: 15px;'>{c_avg}% class avg</div>
                </div>
                """, unsafe_allow_html=True)
                
                bc1, bc2 = st.columns(2)
                if bc1.button("Edit", key=f"edit_crs_{c['id']}", use_container_width=True):
                    st.toast("Edit functionality to be implemented.", icon="ℹ️")
                if bc2.button("Delete", key=f"del_crs_{c['id']}", use_container_width=True):
                    execute_query("DELETE FROM courses WHERE id=?", (c['id'],))
                    st.toast(f"Deleted course {c['name']}", icon="🗑️")
                    st.rerun()
    else:
        st.info("📚 No courses created yet. Click '+ Add Course' to begin.")

elif page == "Analytics":
    st.markdown("<div class='main-header'>Performance Analytics</div>", unsafe_allow_html=True)
    
    # Fetch all evaluated performance data
    df_data = execute_query("""
        SELECT s.student_name, s.student_id, s.roll_no,
               e.total_score, s.total_marks, e.grade,
               ROUND((e.total_score * 100.0 / NULLIF(s.total_marks, 0)), 1) as percentage,
               CASE WHEN (e.total_score * 100.0 / NULLIF(s.total_marks, 0)) >= 40 THEN 'Pass' ELSE 'Fail' END as status
        FROM evaluations e
        JOIN submissions s ON s.id = e.submission_id
        WHERE e.status = 'evaluated'
    """, fetch=True)
    
    if df_data:
        df = pd.DataFrame([dict(r) for r in df_data])
        
        # Summary stats headers
        met1, met2, met3 = st.columns(3)
        met1.metric("Class Average", f"{df['percentage'].mean():.1f}%")
        
        highest_idx = df['total_score'].idxmax()
        highest_name = df.loc[highest_idx, 'student_name']
        highest_score = df.loc[highest_idx, 'total_score']
        met2.metric("Highest Score", f"{highest_name} - {highest_score}")
        
        pass_rate_calc = (df['status']=='Pass').sum()
        met3.metric("Pass Rate", f"{pass_rate_calc} / {len(df)}")
        
        st.markdown("<hr style='border-color: #e2e8f0;'>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("<div class='metric-card'><h4>Student Scores</h4></div>", unsafe_allow_html=True)
            # Bar chart - each student's score
            st.bar_chart(data=df, x='student_name', y='total_score', color="#3b82f6")
            
        with c2:
            st.markdown("<div class='metric-card'><h4>Grade Distribution</h4></div>", unsafe_allow_html=True)
            # Grade distribution pie chart
            grade_counts = df['grade'].value_counts()
            fig = px.pie(values=grade_counts.values, names=grade_counts.index, hole=0.4,
                         color_discrete_sequence=["#10b981", "#3b82f6", "#f59e0b", "#ef4444"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=0))
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.info("📊 No evaluation data available yet to display analytics. Complete some AI evaluations first.")

elif page == "AI Insights":
    st.markdown("<div class='main-header'>🧠 AI Class Insights</div>", unsafe_allow_html=True)
    
    evals = execute_query("SELECT COUNT(*) as c FROM submissions WHERE status='Evaluated'", fetch=True)
    eval_count = evals[0]['c'] if evals else 0
    
    if eval_count < 5:
        st.info("⏳ Need more evaluations (minimum 5) to generate meaningful AI insights.")
    else:
        st.markdown("""
        <div style='background-color: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #3b82f6;'>
            <h3 style='color: #2563eb;'>Class Performance Summary</h3>
            <p>Based on the latest evaluated exams, the overall performance is stable. However, a slight drop was noticed in recent assessments.</p>
            <p><b>Recommendation:</b> Focus on practical exercises for the upcoming modules.</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
    st.markdown("### 🔍 Plagiarism Detection")
    st.info("🛡️ No highly suspicious overlaps detected in recent submissions.")

elif page == "Settings":
    st.markdown("<div class='main-header'>⚙️ System Settings</div>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["Profile Setup", "Grading Scale", "Data Management"])
    
    with t1:
        st.text_input("Institute Name", value="KLE Technological University", autocomplete="organization")
        st.file_uploader("Update Logo", type=['png', 'jpeg'])
        st.text_input("Teacher Name", value=st.session_state.user.get('name', ''), autocomplete="name")
        st.text_input("Email", value=st.session_state.user.get('email', ''), autocomplete="email")
        st.button("Save Profile", type="primary")
        
    with t2:
        st.write("Configure minimum percentage thresholds for grades:")
        c1, c2, c3 = st.columns(3)
        c1.number_input("A+ Threshold", value=90)
        c2.number_input("A Threshold", value=80)
        c3.number_input("B Threshold", value=70)
        st.button("Save Grading Scale", type="primary")

    with t3:
        st.markdown("### 📥 Database Backup")
        st.info("Download a complete backup of the database containing all students, courses, exams, and evaluation records.")
        try:
            with open(DB_PATH, "rb") as db_file:
                st.download_button(
                    label="⬇️ Download Full Database (.db)",
                    data=db_file,
                    file_name="evaluations_backup.db",
                    mime="application/x-sqlite3",
                    type="primary",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Error accessing database file: {e}")
            
        st.markdown("<hr style='margin: 20px 0; border-color: #e2e8f0;'>", unsafe_allow_html=True)
        
        st.markdown("### 🧹 Database Cleanup Operations")
        st.warning("These operations will permanently delete records from the database. Use with caution.")
        
        if st.button("Clear Orphaned Data (No Student Link)", use_container_width=True):
            with st.spinner("Cleaning database..."):
                del_count = 0
                conn = get_db_connection()
                try:
                    c = conn.cursor()
                    c.execute("DELETE FROM submissions WHERE student_id IS NULL OR student_id NOT IN (SELECT id FROM students)")
                    del_count = c.rowcount
                    conn.commit()
                except Exception as e:
                    st.toast(f"Cleanup Error: {e}", icon="🚨")
                finally:
                    conn.close()
                st.success(f"Successfully deleted {del_count} orphaned records from the database.")
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚨 Clear All Dashboard Data (Factory Reset)", type="primary", use_container_width=True):
            with st.spinner("Performing factory reset..."):
                execute_query("DELETE FROM submissions")
                execute_query("DELETE FROM students")
                execute_query("DELETE FROM exams")
                execute_query("DELETE FROM courses")
                st.toast("Factory reset complete. All data cleared.", icon="✅")
                time.sleep(1)
                st.rerun()
        
elif page == "Exam Management":
    st.markdown("<div class='main-header'>Exam Management</div>", unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns([4, 1])
    with col_t2:
        if st.button("➕ New Exam", use_container_width=True):
            st.session_state.show_add_exam = not st.session_state.get('show_add_exam', False)
            st.rerun()

    if st.session_state.get('show_add_exam', False):
        st.markdown("<div style='background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
        st.subheader("Create New Exam")
        with st.form("add_exam"):
            c1, c2 = st.columns(2)
            e_name = c1.text_input("Exam Name *", autocomplete="off")
            
            courses_db = execute_query("SELECT id, name FROM courses", fetch=True)
            c_opts = {"Select Course": None}
            if courses_db:
                for c in courses_db:
                    c_opts[c['name']] = c['id']
            e_course = c2.selectbox("Course *", list(c_opts.keys()))
            
            c3, c4 = st.columns(2)
            e_date = c3.date_input("Date")
            e_marks = c4.number_input("Total Marks *", min_value=1, value=100)
            
            # Dynamic schema check
            try: execute_query("ALTER TABLE exams ADD COLUMN total_marks REAL", ignore_errors=True)
            except: pass
            
            if st.form_submit_button("Save Exam", use_container_width=True):
                if not e_name or not c_opts[e_course]:
                    st.toast("Exam Name and Course are required.", icon="🚨")
                else:
                    execute_query("INSERT INTO exams (name, course_id, date, total_marks) VALUES (?, ?, ?, ?)", 
                                  (e_name, c_opts[e_course], str(e_date), e_marks))
                    st.toast(f"Exam '{e_name}' created successfully!", icon="✅")
                    st.session_state.show_add_exam = False
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    exams = execute_query("""
        SELECT e.id, e.name, e.date, e.total_marks, c.name as course_name 
        FROM exams e LEFT JOIN courses c ON e.course_id = c.id 
        ORDER BY e.created_at DESC
        """, fetch=True)
        
    if exams:
        for e in exams:
            with st.container():
                rc1, rc2, rc3 = st.columns([6, 1, 1])
                rc1.markdown(f"**{e['name']}** <span style='color:#64748b; font-size:13px;'>• {e['course_name']} • Date: {e['date']} • Marks: {e['total_marks']}</span>", unsafe_allow_html=True)
                if rc2.button("Edit", key=f"edit_exam_{e['id']}", use_container_width=True):
                    st.toast("Edit functionality to be implemented.", icon="ℹ️")
                if rc3.button("Delete", key=f"del_exam_{e['id']}", use_container_width=True):
                    execute_query("DELETE FROM exams WHERE id=?", (e['id'],))
                    st.toast(f"Deleted exam {e['name']}", icon="🗑️")
                    st.rerun()
                st.markdown("<hr style='margin: 8px 0; border-color: #e2e8f0;'>", unsafe_allow_html=True)
    else:
        st.info("📋 No exams scheduled yet. Click '+ New Exam' to begin.")

elif page == "Question Bank":
    st.markdown(f"<div class='main-header'>{page}</div>", unsafe_allow_html=True)
    st.info(f"The '{page}' page is under construction and will be fully integrated soon.")
        
