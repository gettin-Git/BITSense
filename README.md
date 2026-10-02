# Hybrid Institutional Intelligence Assistant

A production-grade AI assistant utilizing the CrewAI framework, LangChain, and Ragas for evaluation. This assistant is capable of answering academic policy questions using RAG (Retrieval-Augmented Generation) and analyzing tabular student records using a DuckDB SQL execution tool.

## System Architecture

The project consists of several core components working together:

1. **Institutional AI Assistant**: A single generalist agent built with CrewAI that has access to multiple tools. It analyzes user queries and directly decides which tool to use.
2. **Policy RAG Tool**: A custom RAG tool with a Parent-Child Document Retriever to search through academic policies.
3. **Student Data Analyst Tool**: A DuckDB SQL execution tool to analyze structured student data (`student_records.csv`).
4. **API and UI**: A robust FastAPI backend with a `/chat` POST endpoint, and a Streamlit UI to display the conversation flow and agent thought processes.
5. **Evaluation Pipeline**: Uses the `ragas` library to calculate and print scores for faithfulness, answer relevancy, context precision, and context recall.

## Setup Instructions

### Step 1: Prepare Your Data

Before running the code, you need to provide your authentic data files in the `data/` directory:
1. **Policies:** Place your policy `.pdf` files inside the `data/policies/` folder.
2. **Student Data:** Place your student records CSV file exactly at `data/student_records.csv`. *(Note: For privacy and security, no actual student records are populated or provided in this repository. You must create and provide your own dataset).*
3. **Evaluation Data (Optional):** If you want to use the Ragas evaluator, place your questions at `data/eval_questions.csv`. It must have `question` and `ground_truth` columns.

### Step 2: Set up a Virtual Environment and Install Dependencies

It is highly recommended to use a virtual environment to keep your project dependencies isolated. Open a terminal in the project directory and run:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Environment

Ensure you have a `.env` file in the root of the project with your API keys and preferred models:
```
GOOGLE_API_KEY=your_google_api_key_here
LLM_MODEL=gemini-1.5-pro
JUDGE_MODEL=gemini-1.5-pro
EMBEDDING_MODEL=models/embedding-001
```

### Step 4: Scavenge the Policies (Optional)

If you need to fetch the latest academic policies from the BITS Pilani domains, you can run the scraper.

```bash
python scavenge_docs.py
```

By default, the script will interactively ask if you want to auto-approve the documents. You can bypass this with flags:
- `python scavenge_docs.py --stage`: Downloads PDFs into `data/staging/` so you can manually review and approve them using the Admin UI (`streamlit run admin_ui.py`).
- `python scavenge_docs.py --auto-approve`: Downloads directly into `data/policies/` for immediate ingestion.

### Step 5: Ingest the Policies

Run the ingestion script. This will read your PDFs, split them into parent/child chunks, and save them to a local vector database (ChromaDB + LocalFileStore). You only need to run this once, or whenever you add/modify PDFs in `data/policies/`.
```bash
python ingest_policies.py
```

## Running the Application

The application is split into a backend API and a frontend UI. It is best to open **two separate terminals** in your project folder to run them.

**Terminal 1 (Start the Backend API):**
This starts the FastAPI server that executes the CrewAI agents.
```bash
uvicorn main:app --reload
```

**Terminal 2 (Start the Frontend UI):**
This starts the Streamlit user interface.
```bash
streamlit run app.py
```
A browser window will automatically open (usually at `http://localhost:8501`) where you can start chatting with your AI assistant!

## Evaluating the Pipeline

If you provided the `eval_questions.csv` and want to test the accuracy of the bot using Ragas, run:
```bash
python evaluate_pipeline.py
```
The script will output the Ragas metrics (`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`) to the console and save them in `data/eval_results.csv`.
