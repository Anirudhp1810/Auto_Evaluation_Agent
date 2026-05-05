import sqlite3
import json
import re
import os
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("google.generativeai not installed. Gemini provider will not be available.")

# We are no longer using Gemini! The system will now use local Llama 3.

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

def run_grading_agents(raw_text: str, rubric_json_str: str) -> dict:
    """Invokes the configured AI to evaluate student answers against a rubric."""
    
    # Parse rubric to build a richer prompt section
    rubric_section = rubric_json_str
    try:
        rubric_obj = json.loads(rubric_json_str)
        questions = rubric_obj.get("questions", [])
        if questions and isinstance(questions, list):
            lines = []
            for q in questions:
                q_no = q.get("q_no", "?")
                max_m = q.get("max_marks", 10)
                topic = q.get("topic", "")
                keywords = q.get("expected_keywords", "")
                line = f"Question {q_no} ({max_m} marks)"
                if topic and topic.strip() and not topic.startswith("e.g."):
                    line += f" — Topic: {topic}"
                if keywords and keywords.strip():
                    line += f" — Key concepts (accept synonyms): {keywords}"
                lines.append(line)
            rubric_section = "\n".join(lines)
    except:
        pass  # If rubric is not valid JSON, pass raw string
    
    prompt = f"""You are a strict but fair university exam grader. Your job is to evaluate a student's handwritten answers that were extracted via OCR.

IMPORTANT GRADING RULES:
- Award marks based on correctness, completeness, and clarity of the answer.
- The rubric may list "expected_keywords". These are GUIDE CONCEPTS, not exact strings. Accept synonyms, abbreviations, equivalent terms, and conceptually similar explanations. For example: "VM" = "virtual machine", "attention mechanism" = "self-attention", "cloud storage" = "S3", "bias" = "prejudice in training data". The student does NOT need to use the exact words from the rubric.
- If the rubric only has question numbers and max marks (no topic/keywords), use your subject expertise to evaluate the quality of the response.
- Award partial marks proportionally. Do NOT give 0 unless the answer is completely wrong or missing.
- If OCR text is garbled or unreadable for a question, award 0 and note "Answer unreadable (OCR failure)" as the reason.
- The "reason" field MUST explain specifically why marks were awarded or deducted.

Student's Extracted Answers (from OCR):
---
{raw_text}
---

Rubric / Answer Key:
---
{rubric_section}
---

Respond with ONLY valid JSON in this exact format (no markdown, no explanation outside JSON):
{{
    "grades": {{
        "1": {{"score": 7, "max": 10, "reason": "Correct concept but missed edge case X"}},
        "2": {{"score": 10, "max": 10, "reason": "Complete and accurate answer"}}
    }},
    "report_text": "2-3 sentence summary of student performance, mentioning strongest and weakest areas."
}}

The keys inside "grades" MUST match the question numbers from the rubric exactly.
"""

    provider = os.environ.get("AI_PROVIDER", "ollama").lower()
    model_used = "unknown"
    
    try:
        if provider == "gemini":
            print("Sending evaluation request to Google Gemini API...")
            if not HAS_GENAI:
                raise Exception("google.generativeai package is not installed.")
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise Exception("GEMINI_API_KEY is not set in settings.")
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            grader_output = response.text
            model_used = "Gemini 1.5 Pro"
        else:
            ollama_model = os.environ.get("OLLAMA_MODEL", "llama3")
            print(f"Sending evaluation request to Local Ollama ({ollama_model})...")
            payload = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 8192}
            }
            res = requests.post("http://127.0.0.1:11434/api/generate", json=payload)
            res.raise_for_status()
            grader_output = res.json().get("response", "")
            model_used = f"Ollama ({ollama_model})"
        
        try:
            start_idx = grader_output.find('{')
            end_idx = grader_output.rfind('}') + 1
            json_str = grader_output[start_idx:end_idx]
            data = json.loads(json_str)
            
            grades_data = data.get("grades", {})
            report_text = data.get("report_text", "AI Evaluation Completed.")
        except Exception as e:
            print(f"Error parsing Gemini response root JSON: {e}. Attempting fallback parser.")
            grades_data = clean_json_output(grader_output)
            report_text = "AI evaluation completed but detailed feedback synthesis failed."

        total_score = 0
        total_max = 0
        for q_id, q_data in grades_data.items():
            if isinstance(q_data, dict):
                total_score += float(q_data.get("score", 0))
                total_max += float(q_data.get("max", 10))

        return {
            "grades_data": grades_data,
            "total_score": total_score,
            "total_max": total_max,
            "report_text": report_text,
            "raw_grader_output": grader_output,
            "extracted_answers": raw_text,
            "model_used": model_used
        }
    except Exception as e:
        print(f"AI Execution Error: {e}")
        return {"model_used": model_used}

def generate_class_insight(class_data: list) -> dict:
    """Analyzes aggregated class performance data and generates actionable insights."""
    if not class_data:
        return {"summary": "No evaluation data available to analyze.", "strengths": [], "weaknesses": [], "recommendations": []}

    # Pre-aggregate statistics so the LLM gets clean numbers, not raw dumps
    total_students = len(class_data)
    grade_counts = {}
    question_stats = {}  # q_no -> {total_awarded, total_max, count, sample_comments}
    
    for student in class_data:
        g = student.get("grade", "?")
        grade_counts[g] = grade_counts.get(g, 0) + 1
        for q_line in student.get("performance", []):
            try:
                # Parse "Q1: 9/10 - comment" format
                parts = q_line.split(" - ", 1)
                q_and_marks = parts[0]
                comment = parts[1] if len(parts) > 1 else ""
                q_no = q_and_marks.split(":")[0].strip()
                marks_str = q_and_marks.split(":")[1].strip()
                awarded, maximum = marks_str.split("/")
                awarded, maximum = float(awarded), float(maximum)
                
                if q_no not in question_stats:
                    question_stats[q_no] = {"total_awarded": 0, "total_max": 0, "count": 0, "comments": []}
                question_stats[q_no]["total_awarded"] += awarded
                question_stats[q_no]["total_max"] += maximum
                question_stats[q_no]["count"] += 1
                if comment and len(question_stats[q_no]["comments"]) < 3:
                    question_stats[q_no]["comments"].append(comment.strip())
            except:
                pass
    
    # Build a clean summary table
    q_summary_lines = []
    for q_no in sorted(question_stats.keys()):
        s = question_stats[q_no]
        avg_pct = round((s["total_awarded"] / s["total_max"] * 100), 1) if s["total_max"] > 0 else 0
        avg_awarded = round(s["total_awarded"] / s["count"], 1)
        avg_max = round(s["total_max"] / s["count"], 1)
        comments_str = "; ".join(s["comments"]) if s["comments"] else "No comments"
        q_summary_lines.append(f"{q_no}: Avg {avg_awarded}/{avg_max} ({avg_pct}%) — Grader notes: {comments_str}")
    
    q_summary = "\n".join(q_summary_lines) if q_summary_lines else "No question-level data available."
    grade_summary = ", ".join([f"{g}: {c} students" for g, c in sorted(grade_counts.items())])
    
    prompt = f"""You are a university teaching assistant analyzing exam results for a professor.

Here is a statistical summary of {total_students} students' performance:

Grade Distribution: {grade_summary}

Question-by-Question Average Performance:
{q_summary}

Based on this data, write a clear and actionable insight report. Be SPECIFIC — reference actual question numbers and the grader comments.

Respond with ONLY valid JSON (no markdown, no extra text):
{{
    "summary": "2-3 sentence overview: how many students, overall pass rate, general trend.",
    "strengths": ["Question X: students scored well because [specific reason from grader comments]"],
    "weaknesses": ["Question Y: students struggled because [specific reason from grader comments]"],
    "recommendations": ["Review [specific topic from weak questions] before the next exam"]
}}
"""

    provider = os.environ.get("AI_PROVIDER", "ollama").lower()
    
    try:
        if provider == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            output = response.text
        else:
            ollama_model = os.environ.get("OLLAMA_MODEL", "llama3")
            payload = {"model": ollama_model, "prompt": prompt, "stream": False, "options": {"num_ctx": 8192}}
            res = requests.post("http://127.0.0.1:11434/api/generate", json=payload)
            res.raise_for_status()
            output = res.json().get("response", "")
            
        start_idx = output.find('{')
        end_idx = output.rfind('}') + 1
        return json.loads(output[start_idx:end_idx])
    except Exception as e:
        print(f"Insight Gen Error: {e}")
        return {"summary": "Failed to generate insights due to AI error.", "strengths": [], "weaknesses": [], "recommendations": []}

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
        model_used = result.get('model_used', 'unknown')

        if not grades_data and not report_text:
            raise Exception("No evaluation was returned by the AI agent.")

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
            "INSERT INTO evaluations (submission_id, total_score, grade, feedback, breakdown_json, pdf_path, status, model_used) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sub_id, calc_total_score, grade, feedback, json.dumps(breakdown), pdf_path, 'evaluated', model_used)
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
