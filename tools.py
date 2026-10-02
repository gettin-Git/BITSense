import os
import time
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
        start_time = time.time()
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
                "screenshot": screenshot,
                "content": doc.page_content
            })
            
            # Context for AI: pure text, source doc name, and source website URL
            context_chunks.append(f"Source Document: {src}\nSource Website: {url}\nContent: {doc.page_content}")
            
        context = "\n\n".join(context_chunks)
        execution_time = time.time() - start_time
        print(f"\n[⏱️ Policy RAG Tool Execution Time: {execution_time:.2f}s]\n")
        return f"Retrieved Policy Context:\n{context}"

class StudentDataInput(BaseModel):
    sql_query: str = Field(..., description="SQL query to analyze the student records. The data is in a table called `student_records`. Just write a standard SQL SELECT query against the `student_records` table.")

class StudentDataTool(BaseTool):
    name: str = "Student Data Analyst Tool"
    description: str = "Use this tool to execute SQL queries on student data. The data is available in a table named `student_records`. Example: `SELECT major, COUNT(*) FROM student_records GROUP BY major`"
    args_schema: Type[BaseModel] = StudentDataInput
    
    def _run(self, sql_query: str) -> str:
        start_time = time.time()
        import duckdb
        if not os.path.exists(STUDENT_RECORDS_CSV):
            return "Error: Student records CSV not found."
            
        if any(keyword in sql_query.upper() for keyword in ["DROP", "INSERT", "UPDATE", "DELETE", "ALTER", "CREATE"]):
            return "Error: Only SELECT queries are allowed."
            
        try:
            con = duckdb.connect(database=':memory:', read_only=False)
            con.execute(f"CREATE VIEW student_records AS SELECT * FROM read_csv_auto('{STUDENT_RECORDS_CSV}')")
            result = con.execute(sql_query).df()
            
            execution_time = time.time() - start_time
            print(f"\n[⏱️ Student Data Tool Execution Time: {execution_time:.2f}s]\n")
            return result.to_string()
        except Exception as e:
            return f"SQL Error: {str(e)}"
