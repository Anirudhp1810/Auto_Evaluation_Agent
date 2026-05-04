import sqlite3
import json
import re
import os
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

from dotenv import load_dotenv
import requests

load_dotenv()

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
    """Invokes Gemini directly to evaluate the extracted answers against the rubric."""
    prompt = f"""
You are an expert AI grader evaluator. 
Evaluate the following student's extracted answers against the provided Rubric JSON.

Student's Extracted Answers (from OCR):
{raw_text}

Rubric JSON (Answer Key & Marks):
{rubric_json_str}

Output your evaluation strictly in the following JSON format:
{{
    "grades": {{
        "1": {{"score": 5, "max": 10, "reason": "explanation of marks awarded/deducted"}},
        "2": {{"score": 10, "max": 10, "reason": "perfect answer"}}
    }},
    "report_text": "Write a friendly, paragraph-long overview summarizing the student's performance, highlighting strengths and suggesting areas for improvement."
}}

Do not add extra markdown formatting around the output, just valid JSON output.
The keys inside "grades" must perfectly match the question numbers in the rubric.
"""

    provider = os.environ.get("AI_PROVIDER", "ollama").lower()
    
    try:
        if provider == "gemini":
            print("Sending evaluation request to Google Gemini API...")
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise Exception("GEMINI_API_KEY is not set in settings.")
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            grader_output = response.text
        else:
            print("Sending evaluation request to Local Ollama...")
            ollama_model = os.environ.get("OLLAMA_MODEL", "llama3")
            payload = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 8192}
            }
            res = requests.post("http://127.0.0.1:11434/api/generate", json=payload)
            res.raise_for_status()
            grader_output = res.json().get("response", "")
        
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
            "extracted_answers": raw_text
        }
    except Exception as e:
        return {}

def generate_class_insight(class_data: list) -> dict:
    """Takes a list of student performance data (grades, question scores, comments) and asks the LLM to generate class-level insights."""
    if not class_data:
        return {"summary": "No evaluation data available to analyze.", "strengths": [], "weaknesses": [], "recommendations": []}

    data_str = json.dumps(class_data, indent=2)
    prompt = f"""
You are an expert AI Education Analyst. 
Analyze the following detailed performance data for a class. It includes the overall grades, question-by-question marks, and specific grader comments for students.

Class Performance Data:
{data_str}

Based strictly on this data, provide a highly accurate class-level insight report. Look at which questions have low marks and read the associated comments to identify the actual weaknesses. Look at high marks to identify strengths.

Output strictly in the following JSON format:
{{
    "summary": "A friendly 2-3 sentence overview of the class's general performance and overall accuracy.",
    "strengths": ["Specific Topic/Concept from questions they scored high on", "Another specific strength"],
    "weaknesses": ["Specific topic/concept from questions they scored poorly on", "Another specific weakness"],
    "recommendations": ["Actionable advice for the teacher on what topics to review next", "Another specific recommendation"]
}}
Do not add extra markdown formatting, only valid JSON. Do not hallucinate. Base everything strictly on the data provided.
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
