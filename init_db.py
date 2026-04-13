import sqlite3
import os

DB_PATH = "evaluations.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Teachers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        institute_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Default teacher for testing
    cursor.execute("INSERT OR IGNORE INTO teachers (name, email, password_hash) VALUES ('Admin Teacher', 'admin@evalai.edu', 'password123')")

    # 2. Students
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        roll_no TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Courses
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        teacher_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(teacher_id) REFERENCES teachers(id)
    )
    """)

    # 4. Exams
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        course_id INTEGER,
        date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(course_id) REFERENCES courses(id)
    )
    """)

    # 5. Submissions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        exam_id INTEGER,
        file_path TEXT,
        file_name TEXT,
        status TEXT DEFAULT 'pending',
        total_marks REAL,
        max_marks REAL,
        grade TEXT,
        overall_feedback TEXT,
        student_name TEXT,
        roll_no TEXT,
        ocr_text TEXT,
        rubrics_json TEXT,
        passing_marks INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(exam_id) REFERENCES exams(id)
    )
    """)

    # 6. Evaluations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER,
        total_score REAL DEFAULT 0,
        grade TEXT DEFAULT '',
        feedback TEXT DEFAULT '',
        breakdown_json TEXT DEFAULT '[]',
        status TEXT DEFAULT 'evaluated',
        pdf_path TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(submission_id) REFERENCES submissions(id)
    )
    """)

    # 7. Reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER,
        sub_id INTEGER,
        student_id TEXT,
        exam_name TEXT,
        path TEXT DEFAULT '',
        file_path TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(submission_id) REFERENCES submissions(id)
    )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized/updated at {DB_PATH}")

if __name__ == "__main__":
    init_db()
