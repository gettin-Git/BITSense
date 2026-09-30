import os
from config import GOOGLE_API_KEY
from crewai import LLM

os.environ["GEMINI_API_KEY"] = GOOGLE_API_KEY

models_to_try = [
    "gemini/gemini-1.5-pro",
    "gemini-1.5-pro",
    "models/gemini-1.5-pro"
]

for m in models_to_try:
    print(f"Testing model string: {m}")
    try:
        llm = LLM(model=m, api_key=GOOGLE_API_KEY)
        response = llm.call(messages=[{"role": "user", "content": "Say hello!"}])
        print(f"✅ Success with {m}")
        print("Response:", response)
        break
    except Exception as e:
        print(f"❌ Failed with {m}. Error: {str(e)[:100]}...")
