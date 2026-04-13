from crewai import Agent, Task
from crewai.tools import tool
import json
import os

@tool("Calculate Score")
def calculate_total(grades_json: str) -> str:
    """Calculates total score and percentage from grades JSON."""
    grades = json.loads(grades_json)
    total = sum(v["score"] for v in grades.values())
    max_total = sum(v["max"] for v in grades.values())
    pct = round((total / max_total) * 100, 1)
    return f"Score: {total}/{max_total} ({pct}%)"

@tool("Save Report")
def save_report(report_text: str) -> str:
    """Saves the final evaluation report as a text file."""
    os.makedirs("results", exist_ok=True)
    with open("results/report.txt", "w") as f:
        f.write(report_text)
    return "Report saved to results/report.txt"

def create_reporter(llm):
    return Agent(
        role="Feedback Reporter",
        goal="Write a clear, helpful evaluation report",
        backstory="""You are a compassionate educator who turns
        raw scores into meaningful feedback. Your reports
        are structured, easy to read, and motivating.

        Always include:
        - Total score
        - Summary of performance
        - Per-question feedback
        - Top 3 strengths
        - Top 3 areas to improve
        - Study tips""",
        tools=[],
        llm=llm,
        verbose=True
    )

def create_report_task(agent, grades, total_score, max_score):
    return Task(
        description=f"""
        Create a complete evaluation report from these grading results:
        {grades}

        The student has officially scored {total_score} out of a maximum {max_score}. 
        Display the final calculated score explicitly at the top of the report exactly as "Total Score: {total_score} / {max_score}".
        Format it nicely with sections and an encouraging
        tone for the student.
        """,
        agent=agent,
        expected_output="Formatted evaluation report as text beginning with the exact calculated total score"
    )
