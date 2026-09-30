import os
import pandas as pd
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from langchain_community.vectorstores import Chroma
from langchain_classic.storage import LocalFileStore, create_kv_docstore
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from config import CHROMA_DB_DIR, LOCAL_FILE_STORE_DIR, STUDENT_RECORDS_CSV, EMBEDDING_MODEL
import re
import sys
from io import StringIO

LAST_RETRIEVED_METADATA = []

def get_last_retrieved_metadata():
    return list(LAST_RETRIEVED_METADATA)

def clear_last_retrieved_metadata():
    global LAST_RETRIEVED_METADATA
    LAST_RETRIEVED_METADATA = []

class PolicyQueryInput(BaseModel):
    query: str = Field(..., description="The policy-related question to search for.")

class PolicyRAGTool(BaseTool):
    name: str = "Policy RAG Tool"
    description: str = "Use this tool to search for institutional academic policies."
    args_schema: Type[BaseModel] = PolicyQueryInput
    
    def _run(self, query: str) -> str:
        # Initialize embeddings
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        
        # Initialize Chroma and FileStore
        if not os.path.exists(CHROMA_DB_DIR) or not os.path.exists(LOCAL_FILE_STORE_DIR):
            return "Error: Document store not found. Please run ingestion first."
            
        vectorstore = Chroma(collection_name="policies_child_chunks", embedding_function=embeddings, persist_directory=CHROMA_DB_DIR)
        store = create_kv_docstore(LocalFileStore(LOCAL_FILE_STORE_DIR))
        
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=0)
        
        retriever = ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=store,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
        )
        
        docs = retriever.invoke(query)
        if not docs:
            return "No relevant policies found."
        
        context_chunks = []
        for doc in docs:
            src = os.path.basename(doc.metadata.get('source', 'Unknown PDF'))
            url = doc.metadata.get('source_url', 'Unknown URL')
            screenshot = doc.metadata.get('screenshot', '')
            
            # Store in registry for human verification UI (NOT for the AI model)
            LAST_RETRIEVED_METADATA.append({
                "source": src,
                "source_url": url,
                "screenshot": screenshot
            })
            
            # Context for AI: pure text, source doc name, and source website URL
            context_chunks.append(f"Source Document: {src}\nSource Website: {url}\nContent: {doc.page_content}")
            
        context = "\n\n".join(context_chunks)
        return f"Retrieved Policy Context:\n{context}"

class StudentDataInput(BaseModel):
    python_code: str = Field(..., description="Python code to analyze `df`. The DataFrame `df` is already loaded with student records. Print the final result to return it. You can use `pd` and `re`.")

class StudentDataTool(BaseTool):
    name: str = "Student Data Analyst Tool"
    description: str = "Use this tool to execute Python code on student data. `df` is pre-loaded. Use pandas and regex to extract insights. Example: `print(df['ID'].str.extract(r'(?P<discipline>[A-Z0-9]+)').value_counts())`"
    args_schema: Type[BaseModel] = StudentDataInput
    
    def _run(self, python_code: str) -> str:
        if not os.path.exists(STUDENT_RECORDS_CSV):
            return "Error: Student records CSV not found."
            
        try:
            df = pd.read_csv(STUDENT_RECORDS_CSV)
            local_env = {"df": df, "pd": pd, "re": re}
            
            old_stdout = sys.stdout
            redirected_output = sys.stdout = StringIO()
            
            try:
                exec(python_code, {}, local_env)
                output = redirected_output.getvalue()
            except Exception as e:
                output = f"Execution error: {str(e)}"
            finally:
                sys.stdout = old_stdout
                
            return output.strip() if output.strip() else "Code executed successfully but produced no output. Did you forget to print()?"
        except Exception as e:
            return f"Error loading data: {str(e)}"
