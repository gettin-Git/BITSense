import sys
import time
from io import StringIO
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import json
import queue
import threading
from typing import List
from crew import run_query
from tools import clear_last_retrieved_metadata, get_last_retrieved_metadata
import uvicorn

app = FastAPI(title="Hybrid Institutional Intelligence Assistant")

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    logs: str
    screenshots: List[str] = []
    sources: List[dict] = []

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    # Capture standard output to get the verbose agent logs AND print them to the terminal live
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = Tee(old_stdout, captured_output)
    
    # Clear metadata registry for this query session
    clear_last_retrieved_metadata()
    
    try:
        result = run_query(request.query)
    except Exception as e:
        import traceback
        result = f"CRITICAL CRASH:\n```\n{traceback.format_exc()}\n```"
    finally:
        sys.stdout = old_stdout
        
    # Collect visual verification screenshots for the user
    retrieved_items = get_last_retrieved_metadata()
    screenshots = []
    sources = []
    for item in retrieved_items:
        s_path = item.get("screenshot", "")
        if s_path and os.path.exists(s_path) and s_path not in screenshots:
            screenshots.append(s_path)
            
        if item.get("content") and not any(s["content"] == item["content"] for s in sources):
            sources.append({
                "source": item.get("source", "Unknown"),
                "content": item.get("content", "")
            })
        
    return ChatResponse(
        response=result, 
        logs=captured_output.getvalue(),
        screenshots=screenshots,
        sources=sources
    )

class QueueTee:
    def __init__(self, q, *files):
        self.q = q
        self.files = files
        import time
        self.start_time = time.time()
        self.last_event_time = self.start_time
        self.breakdown = []
        self.buffer = ""
        
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
        if obj:
            self.q.put({"type": "log", "content": obj})
            self.buffer += obj
            
            if "Action Input:" in self.buffer:
                import time
                elapsed = time.time() - self.last_event_time
                self.breakdown.append({"step": "AI Thinking (Analyzing & Deciding)", "time": elapsed})
                self.last_event_time = time.time()
                self.buffer = ""
                
            elif "[⏱️" in self.buffer and "Execution Time:" in self.buffer and "]" in self.buffer:
                import time
                import re
                elapsed = time.time() - self.last_event_time
                match = re.search(r"\[⏱️ (.*?) Execution Time:", self.buffer)
                step_name = match.group(1) if match else "Tool Execution"
                self.breakdown.append({"step": step_name, "time": elapsed})
                self.last_event_time = time.time()
                self.buffer = ""
                
    def flush(self):
        for f in self.files:
            f.flush()
            
    def get_final_breakdown(self):
        import time
        elapsed = time.time() - self.last_event_time
        if elapsed > 0.1:
            self.breakdown.append({"step": "AI Thinking (Formulating Final Answer)", "time": elapsed})
        return self.breakdown

def run_query_background(q: queue.Queue, query: str):
    start_time = time.time()
    old_stdout = sys.stdout
    q_tee = QueueTee(q, old_stdout)
    sys.stdout = q_tee
    
    clear_last_retrieved_metadata()
    try:
        result = run_query(query)
    except Exception as e:
        import traceback
        result = f"CRITICAL CRASH:\n```\n{traceback.format_exc()}\n```"
    finally:
        sys.stdout = old_stdout
        
    retrieved_items = get_last_retrieved_metadata()
    screenshots = []
    sources = []
    for item in retrieved_items:
        s_path = item.get("screenshot", "")
        if s_path and os.path.exists(s_path) and s_path not in screenshots:
            screenshots.append(s_path)
            
        if item.get("content") and not any(s["content"] == item["content"] for s in sources):
            sources.append({
                "source": item.get("source", "Unknown"),
                "content": item.get("content", "")
            })
            
    execution_time = time.time() - start_time
    breakdown = q_tee.get_final_breakdown()
    q.put({"type": "result", "response": result, "screenshots": screenshots, "sources": sources, "execution_time": execution_time, "breakdown": breakdown})
    q.put(None)  # Sentinel to end the stream

@app.post("/chat_stream")
def chat_stream_endpoint(request: ChatRequest):
    q = queue.Queue()
    threading.Thread(target=run_query_background, args=(q, request.query)).start()
    
    def event_generator():
        while True:
            item = q.get()
            if item is None:
                break
            yield json.dumps(item) + "\n"
            
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
