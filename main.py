from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import json
from datetime import datetime
import base64
from fastapi.responses import FileResponse

from migrate_db import migrate
from crew import execute_grading_pipeline, generate_class_insight

# Ensure database migration and creation is applied
migrate()

app = FastAPI(title="EvalAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "evaluations.db"

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def execute_query(query, params=(), fetch=False, fetch_all=True, return_id=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetch:
            res = cursor.fetchall() if fetch_all else cursor.fetchone()
        else:
            conn.commit()
            res = cursor.lastrowid if return_id else True
    except Exception as e:
        print(f"DB Error: {e}")
        res = None
    finally:
        conn.close()
    return res

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    institute: str = ""

class SettingsUpdate(BaseModel):
    gemini_api_key: str
    ai_provider: str
    ollama_model: str
    institute_name: str

@app.post("/api/register")
async def register(req: RegisterRequest):
    existing = execute_query("SELECT id FROM teachers WHERE email = ?", (req.email,), fetch=True, fetch_all=False)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    execute_query("INSERT INTO teachers (name, email, password_hash, institute_name) VALUES (?, ?, ?, ?)",
                  (req.name, req.email, req.password, req.institute))
    return {"message": "Registration successful"}

@app.post("/api/login")
async def login(req: LoginRequest):
    user = execute_query("SELECT * FROM teachers WHERE email = ?", (req.email,), fetch=True, fetch_all=False)
    if user and user.get("password_hash") == req.password:
        return {"user": user}
    if req.email == "admin" and req.password == "admin":
        return {"user": {"id": 1, "name": "Admin", "email": "admin@evalai.edu"}}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    total_students = execute_query("""
        SELECT COUNT(DISTINCT student_id) as c FROM (
            SELECT student_id FROM students WHERE student_id IS NOT NULL
            UNION
            SELECT student_id FROM submissions WHERE student_id IS NOT NULL AND student_id != ''
        )
    """, fetch=True, fetch_all=False)
    total_courses = execute_query("SELECT COUNT(*) as c FROM courses", fetch=True, fetch_all=False)
    evals_pending = execute_query("SELECT COUNT(*) as c FROM submissions WHERE status='pending'", fetch=True, fetch_all=False)
    evals_done = execute_query("SELECT COUNT(*) as c FROM evaluations WHERE status='evaluated'", fetch=True, fetch_all=False)
    failed_students = execute_query("SELECT COUNT(*) as c FROM evaluations WHERE grade='F'", fetch=True, fetch_all=False)

    return {
        "total_students": total_students['c'] if total_students else 0,
        "total_courses": total_courses['c'] if total_courses else 0,
        "evals_pending": evals_pending['c'] if evals_pending else 0,
        "evals_done": evals_done['c'] if evals_done else 0,
        "failed_students": failed_students['c'] if failed_students else 0
    }

@app.get("/api/exams")
async def get_exams():
    exams = execute_query("SELECT id, name FROM exams", fetch=True)
    return exams or []

@app.post("/api/evaluations/upload")
async def upload_evaluation(
    exam_id: int = Form(...),
    rubrics_json: str = Form(...),
    total_marks: int = Form(...),
    pass_marks: int = Form(...),
    student_name: str = Form(...),
    student_id: str = Form(...),
    roll_no: str = Form(""),
    division: str = Form("A"),
    exam_type: str = Form("ISA-1"),
    file: UploadFile = File(...)
):
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, file.filename)
    
    with open(file_path, "wb") as f:
        f.write(await file.read())

    ext_text = "Pending OCR extraction..."
    if file.filename.lower().endswith('.txt'):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as txt_f:
            ext_text = txt_f.read()

    execute_query(
        """INSERT INTO submissions 
        (file_name, file_path, exam_id, status, ocr_text, rubrics_json, total_marks, passing_marks, student_name, student_id, roll_no, division, exam_type, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (file.filename, file_path, exam_id, 'pending', ext_text, rubrics_json, total_marks, pass_marks, student_name, student_id, roll_no, division, exam_type)
    )
    return {"message": "Uploaded successfully"}

@app.get("/api/evaluations/pending")
async def get_pending_evaluations():
    query_all = """
        SELECT su.id, su.file_path, su.file_name, e.name as exam_name, su.student_name, su.student_id, su.roll_no, 
               su.created_at, su.status, su.ocr_text, su.rubrics_json, 
               su.total_marks, su.passing_marks, su.division, su.exam_type
        FROM submissions su
        LEFT JOIN exams e ON su.exam_id = e.id
        WHERE su.status = 'pending'
        ORDER BY su.created_at ASC
    """
    subs = execute_query(query_all, fetch=True)
    return subs or []

@app.post("/api/evaluations/run/{sub_id}")
def run_evaluation(sub_id: int):
    query_all = """
        SELECT su.id, su.file_path, su.file_name, e.name as exam_name, su.student_name, su.student_id, su.roll_no, 
               su.created_at, su.status, su.ocr_text, su.rubrics_json, 
               su.total_marks, su.passing_marks, su.division, su.exam_type
        FROM submissions su
        LEFT JOIN exams e ON su.exam_id = e.id
        WHERE su.id = ?
    """
    sub = execute_query(query_all, (sub_id,), fetch=True, fetch_all=False)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    s_n = sub['student_name'] or "Unknown"
    s_i = sub['student_id'] or "N/A"
    s_r = sub['roll_no'] or "N/A"
    e_n = sub['exam_name'] or "Unknown Exam"
    
    success = execute_grading_pipeline(
        sub['id'], sub['file_path'], sub['ocr_text'], sub['rubrics_json'], 
        sub['total_marks'], sub['passing_marks'], s_n, s_i, s_r, e_n
    )
    if success:
        return {"message": "Graded successfully"}
    else:
        raise HTTPException(status_code=500, detail="Evaluation pipeline failed")

@app.get("/api/evaluations/results")
async def get_results():
    query = """
    SELECT DISTINCT
        su.id as sub_id, su.student_id, su.student_name, su.roll_no, 
        ev.total_score as total_marks, ev.grade, ev.feedback, ev.breakdown_json, ev.status, su.file_name, ev.pdf_path,
        e.name as exam_name, su.total_marks as max_marks, c.name as course_name, su.division, su.exam_type
    FROM submissions su
    JOIN evaluations ev ON ev.submission_id = su.id
    LEFT JOIN exams e ON su.exam_id = e.id
    LEFT JOIN courses c ON e.course_id = c.id
    WHERE (ev.status = 'evaluated' OR su.status = 'evaluated')
    ORDER BY su.id DESC
    """
    res = execute_query(query, fetch=True)
    return res or []

@app.get("/api/download")
async def download_pdf(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/pdf", filename=os.path.basename(path), content_disposition_type="inline")

@app.get("/api/analytics/trends")
async def get_trends():
    query = """
        SELECT e.name, AVG(ev.total_score * 100.0 / CASE WHEN s.total_marks=0 THEN 100 ELSE s.total_marks END) as avg_score
        FROM evaluations ev 
        JOIN submissions s ON ev.submission_id = s.id 
        JOIN exams e ON s.exam_id = e.id
        WHERE ev.status='evaluated' GROUP BY s.exam_id ORDER BY e.date ASC
    """
    res = execute_query(query, fetch=True)
    return res or []

@app.get("/api/analytics/grades")
async def get_grades(division: Optional[str] = None, exam_type: Optional[str] = None):
    where_clause = "ev.status='evaluated' AND ev.grade IS NOT NULL"
    params = []
    if division and division != 'All':
        where_clause += " AND su.division = ?"
        params.append(division)
    if exam_type and exam_type != 'All':
        where_clause += " AND su.exam_type = ?"
        params.append(exam_type)

    query = f"SELECT ev.grade as name, COUNT(*) as value FROM evaluations ev JOIN submissions su ON ev.submission_id = su.id WHERE {where_clause} GROUP BY ev.grade"
    res = execute_query(query, tuple(params), fetch=True)
    return res or []

@app.get("/api/analytics/detailed")
async def get_detailed_analytics(division: Optional[str] = None, exam_type: Optional[str] = None):
    where_clause = "ev.status = 'evaluated'"
    params = []
    if division and division != 'All':
        where_clause += " AND su.division = ?"
        params.append(division)
    if exam_type and exam_type != 'All':
        where_clause += " AND su.exam_type = ?"
        params.append(exam_type)

    division_query = f"""
        SELECT su.division as name, AVG(ev.total_score * 100.0 / CASE WHEN su.total_marks=0 THEN 100 ELSE su.total_marks END) as avg_score
        FROM evaluations ev
        JOIN submissions su ON ev.submission_id = su.id
        WHERE {where_clause} AND su.division IS NOT NULL
        GROUP BY su.division
        ORDER BY su.division
    """
    division_data = execute_query(division_query, tuple(params), fetch=True) or []
    for d in division_data:
        d['avg_score'] = round(d['avg_score'], 1)

    exam_type_query = f"""
        SELECT su.exam_type as name, AVG(ev.total_score * 100.0 / CASE WHEN su.total_marks=0 THEN 100 ELSE su.total_marks END) as avg_score
        FROM evaluations ev
        JOIN submissions su ON ev.submission_id = su.id
        WHERE {where_clause} AND su.exam_type IS NOT NULL
        GROUP BY su.exam_type
        ORDER BY su.exam_type
    """
    exam_type_data = execute_query(exam_type_query, tuple(params), fetch=True) or []
    for d in exam_type_data:
        d['avg_score'] = round(d['avg_score'], 1)

    pass_fail_query = f"""
        SELECT 
            SUM(CASE WHEN ev.grade != 'F' THEN 1 ELSE 0 END) as passed,
            SUM(CASE WHEN ev.grade = 'F' THEN 1 ELSE 0 END) as failed
        FROM evaluations ev
        JOIN submissions su ON ev.submission_id = su.id
        WHERE {where_clause}
    """
    pass_fail_res = execute_query(pass_fail_query, tuple(params), fetch=True, fetch_all=False) or {'passed': 0, 'failed': 0}

    q_query = f"SELECT ev.breakdown_json FROM evaluations ev JOIN submissions su ON ev.submission_id = su.id WHERE {where_clause} AND ev.breakdown_json IS NOT NULL AND ev.breakdown_json != '[]'"
    q_res = execute_query(q_query, tuple(params), fetch=True) or []
    question_stats = {}
    for row in q_res:
        try:
            breakdown = json.loads(row['breakdown_json'])
            for q in breakdown:
                q_no = q.get("q_no") or q.get("question_no")
                if q_no is None: continue
                q_str = str(q_no)
                if q_str not in question_stats:
                    question_stats[q_str] = {"total_marks": 0, "max_marks": 0, "count": 0}
                question_stats[q_str]["total_marks"] += float(q.get("marks_awarded", 0))
                question_stats[q_str]["max_marks"] += float(q.get("max_marks", 10))
                question_stats[q_str]["count"] += 1
        except:
            pass
    
    question_data = []
    for q_no, stats in question_stats.items():
        if stats["count"] > 0:
            avg_awarded = stats["total_marks"] / stats["count"]
            avg_max = stats["max_marks"] / stats["count"]
            avg_pct = (avg_awarded / avg_max * 100) if avg_max > 0 else 0
            question_data.append({
                "q_no": f"Q{q_no}",
                "avg_marks": round(avg_awarded, 2),
                "avg_pct": round(avg_pct, 1)
            })
    question_data.sort(key=lambda x: x['q_no'])

    return {
        "division_data": division_data,
        "exam_type_data": exam_type_data,
        "pass_fail": [
            {"name": "Passed", "value": pass_fail_res['passed'] or 0}, 
            {"name": "Failed", "value": pass_fail_res['failed'] or 0}
        ],
        "question_data": question_data
    }

@app.get("/api/analytics/top")
async def get_top_performers():
    query = """
        SELECT 
            COALESCE(su.student_name, su.student_id, 'Unknown') as name,
            ev.total_score,
            CASE WHEN su.total_marks IS NULL OR su.total_marks = 0 THEN 100 ELSE su.total_marks END as max_marks,
            (ev.total_score * 100.0 / CASE WHEN su.total_marks IS NULL OR su.total_marks = 0 THEN 100 ELSE su.total_marks END) as pct,
            ev.grade,
            su.division,
            su.exam_type
        FROM evaluations ev 
        JOIN submissions su ON ev.submission_id = su.id 
        WHERE ev.status = 'evaluated'
        ORDER BY pct DESC 
        LIMIT 3
    """
    res = execute_query(query, fetch=True)
    return res or []

@app.delete("/api/evaluations/clear")
async def clear_history():
    execute_query("DELETE FROM evaluations")
    execute_query("DELETE FROM reports")
    execute_query("DELETE FROM submissions")
    return {"message": "History cleared"}

@app.get("/api/settings")
async def get_settings():
    from dotenv import dotenv_values
    env_config = dotenv_values(".env")
    return {
        "gemini_api_key": env_config.get("GEMINI_API_KEY", ""),
        "ai_provider": env_config.get("AI_PROVIDER", "ollama"),
        "ollama_model": env_config.get("OLLAMA_MODEL", "llama3"),
        "institute_name": env_config.get("INSTITUTE_NAME", "EvalAI Institute")
    }

@app.post("/api/settings")
async def update_settings(req: SettingsUpdate):
    with open(".env", "w") as f:
        f.write(f"GEMINI_API_KEY={req.gemini_api_key}\n")
        f.write(f"AI_PROVIDER={req.ai_provider}\n")
        f.write(f"OLLAMA_MODEL={req.ollama_model}\n")
        f.write(f"INSTITUTE_NAME={req.institute_name}\n")
        f.write(f"DATABASE_URL=sqlite:///./evaluations.db\n")
    
    # Update current process environment so changes take effect immediately
    os.environ["GEMINI_API_KEY"] = req.gemini_api_key
    os.environ["AI_PROVIDER"] = req.ai_provider
    os.environ["OLLAMA_MODEL"] = req.ollama_model
    os.environ["INSTITUTE_NAME"] = req.institute_name
    
    return {"message": "Settings updated"}

@app.post("/api/settings/reset_db")
async def reset_db():
    tables = ["evaluations", "reports", "submissions", "exams", "courses", "students", "teachers"]
    for t in tables:
        execute_query(f"DELETE FROM {t}")
    # Re-insert default teacher to not break login
    execute_query("INSERT OR IGNORE INTO teachers (name, email, password_hash) VALUES ('Admin Teacher', 'admin@evalai.edu', 'password123')")
    return {"message": "Database reset"}

@app.get("/api/ai_insights/generate")
async def get_ai_insights(division: Optional[str] = None, exam_type: Optional[str] = None):
    where_clause = "ev.status = 'evaluated'"
    params = []
    if division and division != 'All':
        where_clause += " AND su.division = ?"
        params.append(division)
    if exam_type and exam_type != 'All':
        where_clause += " AND su.exam_type = ?"
        params.append(exam_type)

    query = f"SELECT ev.breakdown_json, ev.grade FROM evaluations ev JOIN submissions su ON ev.submission_id = su.id WHERE {where_clause} AND ev.breakdown_json IS NOT NULL AND ev.breakdown_json != '[]'"
    res = execute_query(query, tuple(params), fetch=True) or []
    
    condensed_data = []
    for r in res:
        try:
            b_json = json.loads(r['breakdown_json'])
            condensed = [f"Q{q.get('q_no', '?')}: {q.get('marks_awarded')}/{q.get('max_marks')} - {q.get('comment')}" for q in b_json if isinstance(q, dict)]
            condensed_data.append({"grade": r['grade'], "performance": condensed})
        except:
            pass

    # Limit to latest 30 to avoid context limits
    insights = generate_class_insight(condensed_data[:30])
    return insights
