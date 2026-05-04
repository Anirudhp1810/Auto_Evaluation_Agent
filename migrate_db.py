import sqlite3

def migrate():
    conn = sqlite3.connect('evaluations.db')
    cursor = conn.cursor()
    
    # Tables and columns that MUST exist
    tables_to_create = [
        ("teachers", """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            institute_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """),
        ("students", """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            roll_no TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """),
        ("courses", """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            teacher_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(teacher_id) REFERENCES teachers(id)
        """),
        ("exams", """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            course_id INTEGER,
            date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(course_id) REFERENCES courses(id)
        """),
        ("submissions", """
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
            division TEXT DEFAULT 'A',
            exam_type TEXT DEFAULT 'ISA-1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """),
        ("evaluations", """
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
        """),
        ("reports", """
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
        """)
    ]

    for table_name, schema in tables_to_create:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})")

    # Safe column additions for existing tables
    columns_to_add = [
        ("submissions", "student_name", "TEXT DEFAULT 'Unknown'"),
        ("submissions", "student_id", "TEXT DEFAULT ''"),
        ("submissions", "roll_no", "TEXT DEFAULT ''"),
        ("submissions", "ocr_text", "TEXT"),
        ("submissions", "rubrics_json", "TEXT"),
        ("submissions", "total_marks", "REAL DEFAULT 0"),
        ("submissions", "passing_marks", "INTEGER DEFAULT 0"),
        ("submissions", "status", "TEXT DEFAULT 'pending'"),
        ("submissions", "division", "TEXT DEFAULT 'A'"),
        ("submissions", "exam_type", "TEXT DEFAULT 'ISA-1'"),
        ("evaluations", "breakdown_json", "TEXT DEFAULT '[]'"),
        ("evaluations", "pdf_path", "TEXT DEFAULT ''"),
        ("evaluations", "status", "TEXT DEFAULT 'evaluated'"),
        ("reports", "sub_id", "INTEGER"),
        ("reports", "exam_name", "TEXT"),
        ("reports", "path", "TEXT"),
        ("reports", "file_path", "TEXT"),
    ]
    
    for table, column, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            print(f"Added {column} to {table}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
