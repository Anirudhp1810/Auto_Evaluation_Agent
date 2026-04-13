from crewai import Agent, Task
from crewai.tools import tool
import json

@tool("Load Rubric")
def load_rubric(path: str) -> str:
    """Loads the answer rubric / answer key from a text file."""
    with open(path) as f:
        return f.read()

@tool("Save Grades")
def save_grades(grades_json: str) -> str:
    """Saves the grading results to a JSON file."""
    import os
    os.makedirs("results", exist_ok=True)
    with open("results/grades.json", "w") as f:
        f.write(grades_json)
    return "Grades saved!"

def create_grader(llm):
    return Agent(
        role="Strict Rubric-Based Answer Grader",
        goal=(
            "Evaluate each student answer SOLELY against the provided rubric answer key. "
            "Award the FULL maximum marks if the student's answer covers all the key points in the rubric. "
            "Do NOT deduct marks for style, verbosity, or minor phrasing differences. "
            "Only deduct marks if the student's answer is factually wrong or missing a key rubric point."
        ),
        backstory="""You are a senior examiner at a university with 20 years of experience.
        Your job is to compare a student's answer strictly against the official answer key / rubric.

        YOUR CORE RULES:
        1. FULL MARKS → if the student covered ALL the required points from the rubric for a question.
        2. PARTIAL MARKS → only if specific required rubric points are clearly missing or incorrect.
        3. ZERO MARKS → only if the answer is completely off-topic or blank.
        4. NEVER deduct marks based on your personal preferences, writing style, or extra detail level.
        5. NEVER invent rubric criteria that are not explicitly stated.
        6. The rubric is the ONLY source of truth. If the student's answer matches the rubric — award full marks.

        Output format (strict JSON, no markdown):
        {
          "Q1": {"score": 10, "max": 10, "reason": "Covered all required points."},
          "Q2": {"score": 3, "max": 5, "reason": "Missing explanation of X."}
        }
        """,
        tools=[],
        llm=llm,
        verbose=True
    )

def create_grading_task(agent, extracted_answers, rubric):
    return Task(
        description=f"""
        You are grading a student's exam. Follow these rules STRICTLY.

        ══ STUDENT'S ANSWERS ══
        {extracted_answers}

        ══ OFFICIAL RUBRIC / ANSWER KEY ══
        {rubric}

        ══ MANDATORY GRADING RULES ══
        1. Grade ONLY the questions that appear in the rubric. Ignore any extra questions.
        2. For each rubric question:
           - Read the rubric's expected answer / key points.
           - Read the student's answer for that question.
           - If the student's answer covers ALL the key points → award FULL marks (score == max).
           - If the student is missing specific points → deduct proportionally and state exactly what is missing.
           - If the answer is off-topic or blank → award 0.
        3. DO NOT penalise the student for:
           - Using different wording or synonyms
           - Providing more detail than required
           - Writing style or grammar
        4. DO NOT add rubric criteria that don't exist in the provided rubric.
        5. If the rubric does not specify max marks for a question, use 10 as the default.
        6. Output ONLY a raw JSON object. No markdown. No extra text.

        Expected format:
        {{"Q1": {{"score": <int>, "max": <int>, "reason": "<specific justification>"}}, ...}}
        """,
        agent=agent,
        expected_output="A raw JSON object with scores only for the questions in the rubric. No markdown. No extra text."
    )
