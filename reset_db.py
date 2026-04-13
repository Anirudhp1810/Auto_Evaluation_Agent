import sqlite3
import os

def reset_student_data():
    db_path = 'evaluations.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist.")
        return

    conn = sqlite3.connect(db_path)
    
    # Enable foreign keys so cascading deletes work if defined
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        # Delete dependent data first to respect any FK constraints
        cursor.execute("DELETE FROM reports")
        cursor.execute("DELETE FROM evaluations")
        cursor.execute("DELETE FROM submissions")
        
        # Finally delete students
        cursor.execute("DELETE FROM students")
        
        # Reset auto-increment counters for cleanly wiped tables
        tables = ['reports', 'evaluations', 'submissions', 'students']
        for table in tables:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
            
        conn.commit()
        print("✅ Successfully cleared all student-related data (students, submissions, evaluations, reports).")
        
    except sqlite3.Error as e:
        print(f"❌ Database error during reset: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_student_data()
