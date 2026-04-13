from crewai import Crew, Task, LLM
from agents.grader import create_grader, create_grading_task
from agents.reporter import create_reporter, create_report_task
from agents.extractor import create_extractor, create_extraction_task
from tools.pdf_reader import extract_text_from_pdf
import sqlite3
import json
import re
import os
from datetime import datetime

# Load local LLM
llm = LLM(model="ollama/llama3", base_url="http://localhost:11434")

def clean_json_output(output_text: str) -> dict:
    """Extracts and parses JSON from LLM output, handling markdown blocks and other noise."""
    try:
        # Find the first { and last }
        start_idx = output_text.find('{')
        end_idx = output_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            return {}

        json_str = output_text[start_idx:end_idx]
        
        # Remove common markdown artifacting
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
        
        data = json.loads(json_str)
        
        # Normalize structure: if it's wrapped in a "questions" key
        if "questions" in data:
            if isinstance(data["questions"], dict):
                return data["questions"]
            elif isinstance(data["questions"], list):
                # Map list of questions to a dict keyed by question number
                return {item.get("q_no", f"Q{idx+1}"): item for idx, item in enumerate(data["questions"])}
        
        return data
    except Exception as e:
        print(f"JSON Parse Warning: {e}")
        return {}

def evaluate_answer_sheet(pdf_path: str, student_name: str) -> str:
    """Main entry point for evaluating a single PDF. Extracted for CLI or simple scripts."""
    raw_text = extract_text_from_pdf(pdf_path)
    
    with open("rubric.txt", "r") as f:
        rubric = f.read()

    grader = create_grader(llm)
    reporter = create_reporter(llm)

    task2 = create_grading_task(grader, raw_text, rubric)
    grader_result = Crew(agents=[grader], tasks=[task2], verbose=True).kickoff()
    
    grades_data = clean_json_output(str(grader_result))
    
    total_score = sum(float(q.get("score", 0)) for q in grades_data.values() if isinstance(q, dict))
    total_max = sum(float(q.get("max", 10)) for q in grades_data.values() if isinstance(q, dict))

    task3 = create_report_task(reporter, json.dumps(grades_data) if grades_data else str(grader_result), total_score, total_max)
    result = Crew(agents=[reporter], tasks=[task3], verbose=True).kickoff()
    
    return str(result)

def run_grading_agents(raw_text: str, rubric_json_str: str) -> dict:
    """Invokes extractor, grader and reporter agents sequentially. Used by dashboard."""
    # 1. Initialize Agents
    extractor = create_extractor(llm)
    grader = create_grader(llm)
    reporter = create_reporter(llm)

    # 2. Extract Answers from Raw Text (OCR cleanup)
    task1 = create_extraction_task(extractor, raw_text, rubric_json_str)
    extraction_result = Crew(agents=[extractor], tasks=[task1], verbose=True).kickoff()
    
    extracted_text = str(extraction_result)
    print(f"--- Extracted Text ---\n{extracted_text}\n----------------------")

    # 3. Grade the Extracted Answers
    task2 = create_grading_task(grader, extracted_text, rubric_json_str)
    grader_result = Crew(agents=[grader], tasks=[task2], verbose=True).kickoff()
    
    grader_output = str(grader_result)
    grades_data = clean_json_output(grader_output)
    
    total_score = 0
    total_max = 0
    for q_id, q_data in grades_data.items():
        if isinstance(q_data, dict):
            total_score += float(q_data.get("score", 0))
            total_max += float(q_data.get("max", 10))

    # 4. Generate Final Report
    task3 = create_report_task(reporter, json.dumps(grades_data) if grades_data else grader_output, total_score, total_max)
    report_result = Crew(agents=[reporter], tasks=[task3], verbose=True).kickoff()
    
    return {
        "grades_data": grades_data,
        "total_score": total_score,
        "total_max": total_max,
        "report_text": str(report_result),
        "raw_grader_output": grader_output,
        "extracted_answers": extracted_text
    }

def execute_grading_pipeline(sub_id, file_path, ocr_text, rubrics_json_str, total_marks, pass_marks, s_name, s_id, s_roll, exam_name):
    """Refactored high-level pipeline for AI grading, PDF generation, and DB updates."""
    from tools.pdf_reader import extract_text_from_pdf, extract_from_image
    from pdf_generator import generate_student_report
    
    # Defaults
    total_marks = int(total_marks) if total_marks else 100
    pass_marks  = int(pass_marks)  if pass_marks  else 40
    student_id_str = s_id if s_id and s_id not in ('N/A', '---') else f"SUB-{sub_id}"
    
    grade, feedback, calc_total_score, breakdown, pdf_path = "F", "Evaluation failed.", 0, [], ""
    ai_success = False

    try:
        # OCR Phase
        if "Pending OCR" in str(ocr_text) or not str(ocr_text).strip():
            if file_path and os.path.exists(file_path):
                if file_path.lower().endswith('.pdf'):
                    ocr_text = extract_text_from_pdf(file_path)
                elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    ocr_text = extract_from_image(file_path)
                
                # Update OCR text back to DB
                conn = sqlite3.connect("evaluations.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE submissions SET ocr_text=? WHERE id=?", (ocr_text, sub_id))
                conn.commit()
                conn.close()

        # AI Grading Phase
        result = run_grading_agents(ocr_text, rubrics_json_str)
        calc_total_score = result.get('total_score', 0)
        report_text = result.get('report_text', '')
        grades_data = result.get('grades_data', {})

        for q_id, q_data in grades_data.items():
            breakdown.append({
                "q_no": q_id,
                "topic": "Evaluation",
                "marks_awarded": q_data.get("score", 0),
                "max_marks": q_data.get("max", 10),
                "comment": q_data.get("reason", "Evaluated by AI")
            })

        final_max = total_marks if total_marks else result.get('total_max', 100)
        if not final_max or final_max == 0: final_max = 100

        perc = (calc_total_score / final_max) * 100
        if perc >= 90:          grade = "A+"
        elif perc >= 80:        grade = "A"
        elif perc >= 70:        grade = "B"
        elif perc >= pass_marks: grade = "C"
        else:                   grade = "F"

        feedback = report_text if report_text else "AI evaluation completed."
        ai_success = True

    except Exception as e:
        feedback = f"Evaluation error: {e}"
        print(f"Pipeline Error: {e}")

    # PDF Phase
    try:
        formatted_marks = [{"question_id": b["q_no"], "awarded": b["marks_awarded"],
                             "max": b["max_marks"], "feedback": b["comment"]} for b in breakdown]
        pdf_path = generate_student_report(
            student_name=s_name, student_id=student_id_str, roll_no=s_roll,
            exam_name=exam_name, marks_data=formatted_marks,
            total_marks=int(calc_total_score), max_marks=int(total_marks or 100),
            grade=grade, overall_feedback=feedback
        )
    except Exception as e:
        print(f"PDF Gen Error: {e}")

    # DB Commit Phase
    try:
        conn = sqlite3.connect("evaluations.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO evaluations (submission_id, total_score, grade, feedback, breakdown_json, pdf_path, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sub_id, calc_total_score, grade, feedback, json.dumps(breakdown), pdf_path, 'evaluated')
        )
        
        if pdf_path:
            cursor.execute("INSERT INTO reports (submission_id, sub_id, student_id, exam_name, path, file_path) VALUES (?, ?, ?, ?, ?, ?)",
                         (sub_id, sub_id, student_id_str, exam_name, pdf_path, pdf_path))

        cursor.execute("UPDATE submissions SET status='evaluated' WHERE id=?", (sub_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Update Error: {e}")

    return ai_success
