from crewai import Agent, Task
from crewai.tools import tool
import fitz
import pytesseract
from PIL import Image
import io

@tool("PDF Reader")
def read_pdf(pdf_path: str) -> str:
    """Reads a PDF and returns all text content."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

@tool("Image OCR")
def ocr_image(image_path: str) -> str:
    """Reads handwritten or scanned answer sheet images."""
    img = Image.open(image_path)
    return pytesseract.image_to_string(img)

def create_extractor(llm):
    return Agent(
        role="Document Extractor",
        goal="Read answer sheets and extract structured student answers for each question.",
        backstory="""You are an expert at reading messy handwriting and noisy OCR text.
        Your job is to identify student answers Even if the question numbers are misread
        (e.g., 'Qt' instead of 'Q1', 'Run' instead of 'Q4').
        
        You map each detected answer to the closest matching Question ID from the official rubric.
        If an answer is found but the question ID is ambiguous, you use context to determine which question it belongs to.""",
        tools=[read_pdf, ocr_image],
        llm=llm,
        verbose=True
    )

def create_extraction_task(agent, raw_text, rubric_json):
    return Task(
        description=f"""
        Analyze the raw student answer text and map each answer to the correct Question ID from the rubric.
        
        ══ RAW OCR TEXT ══
        {raw_text}
        
        ══ OFFICIAL RUBRIC QUESTIONS ══
        {rubric_json}
        
        ══ EXTRACTION RULES ══
        1. Identify EVERY student answer present in the raw text.
        2. Map each answer to its Question ID (e.g., Q1, Q2, Q3, Q4) using the provided rubric IDs.
        3. Be smart about misread question labels (e.g., 'Qt' is likely Q1, 'Run' might be Q4 if it follows Q3).
        4. Extract the FULL text of the student's answer for that question.
        5. If a question from the rubric is missing from the student text, mark it as "Answer not found".
        6. Provide the results in a clear, structured JSON format.
        
        Output Format:
        {{
          "Q1": "Student's full answer text...",
          "Q2": "Student's full answer text...",
          ...
        }}
        """,
        agent=agent,
        expected_output="A JSON object mapping Question IDs to the extracted student answer text. No markdown."
    )
