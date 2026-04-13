# 🤖 Answer Sheet Evaluation System (CrewAI + Ollama)

## 📌 Project Overview
This project is an AI-powered student answer sheet evaluation system that leverages a multi-agent architectural pattern using **CrewAI** and **Ollama**. The system automates the grading process by utilizing an ensemble of specialized AI agents: an Extractor to read documents, a Grader to evaluate answers against a rubric, and a Reporter to construct a final feedback breakdown. 

## ✨ Key Features
1. **Intelligent Document Extraction**: Extracts textual answers directly from PDFs using PyMuPDF and utilizes PyTesseract (OCR) for scanned images or handwritten sheets.
2. **Multi-Agent Evaluation Strategy**:
   - 🔍 **Extractor Agent**: Specializes in reading academic documents. It locates question numbers and student answers clearly, even addressing messy handwriting contexts.
   - 🧠 **Grader Agent**: An experienced evaluator responsible for contrasting extracted student answers against standard answer keys (rubrics), outputting valid structured JSON scores with reasons.
   - 📊 **Reporter Agent**: A compassionate educator that synthesizes JSON grade artifacts, converting them into structured, constructive, and motivating reports emphasizing strengths and providing study tips.
3. **Local Privacy-First Processing**: Uses `llama3` running locally via **Ollama**, ensuring student data logic is processed completely offline without third-party API dependencies.
4. **Interactive Dashboard**: A user-friendly Streamlit web application providing a split-pane interface. Users can input a dynamic rubric on the sidebar, upload PDF/image answer scripts on the main pane, and immediately kick off the CrewAI pipeline to view and download reports.

## 🛠️ Technology Stack
- **Frameworks**: [CrewAI](https://crewai.com/) (Agent Orchestration), [LangChain](https://langchain.com/) (LLM chaining utility abstractions)
- **Local AI Provider**: [Ollama](https://ollama.com/) running `llama3`
- **Frontend / UI**: [Streamlit](https://streamlit.io/)
- **Document Processing**: `PyMuPDF` (text-based PDF text extraction), `PyTesseract` + `Pillow` (Optical Character Recognition)

## 📁 Project Structure
```text
.
├── agents/             # Define the CrewAI Agents 
│   ├── extractor.py    # Extracts answer text using tools.
│   ├── grader.py       # Scores responses via the provided Rubric JSON.
│   └── reporter.py     # Drafts and saves formatted performance feedback.
├── tools/
│   └── pdf_reader.py   # OCR and PDF parsing utilities. 
├── results/            # Agent Output directory (auto-generated)
│   ├── grades.json     # Raw json output from Grader agent.
│   └── report.txt      # Synthesized txt report from Reporter agent.
├── crew.py             # Instantiates the Crew, task definitions, & logic.
├── dashboard.py        # Main entrypoint Streamlit user-interface.
└── rubric.txt          # Transient file storing the dynamic correct answers for grading.
```

## 🚀 Getting Started

### Prerequisites
1. Install [Ollama](https://ollama.com/download).
2. Start the engine and pull the llama3 model:
```bash
ollama serve
ollama pull llama3
```
3. Ensure Tesseract OCR is installed on your OS:
- **macOS (Homebrew)**: `brew install tesseract`
- **Ubuntu/Debian**: `sudo apt install tesseract-ocr`

### Installation
Install python module dependencies:
```bash
pip install crewai langchain-community pytesseract pymupdf pillow streamlit
```

### Running the System
Start the dashboard UI server in your terminal via the Streamlit CLI:
```bash
streamlit run dashboard.py
```
Open up your browser to the local port (usually `http://localhost:8501`). Add in your correct answers into the sidebar rubric utility, and upload the student's sheet to evaluate!
