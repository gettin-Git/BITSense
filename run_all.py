import subprocess
import time
import sys
import os

if __name__ == "__main__":
    print("🚀 Starting the AI Backend (FastAPI)...")
    backend_process = subprocess.Popen([sys.executable, "main.py"])
    
    # Give backend a couple of seconds to boot up and bind to port 8000
    time.sleep(3)
    
    print("🚀 Starting the AI Frontend (Streamlit)...")
    frontend_process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py"])
    
    print("\n" + "="*60)
    print("✅ BOTH SERVERS ARE NOW RUNNING!")
    print("⚠️  DO NOT PRESS CTRL+C! Leave this terminal completely open.")
    print("="*60 + "\n")
    
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down both servers safely...")
        backend_process.terminate()
        frontend_process.terminate()
