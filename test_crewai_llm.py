import os
from config import GOOGLE_API_KEY, LLM_MODEL
from crewai import Agent

print("Testing CrewAI LLM instantiation...")

try:
    from crewai import LLM
    print("crewai.LLM is available. Testing instantiation...")
    my_llm = LLM(model=f"gemini/{LLM_MODEL}", api_key=GOOGLE_API_KEY)
    agent = Agent(role="Test", goal="Test", backstory="Test", llm=my_llm)
    print("Successfully created Agent with crewai.LLM!")
except Exception as e:
    print("crewai.LLM approach failed:", e)

    print("Falling back to os.environ GEMINI_API_KEY string approach...")
    os.environ["GEMINI_API_KEY"] = GOOGLE_API_KEY
    try:
        agent = Agent(role="Test", goal="Test", backstory="Test", llm=f"gemini/{LLM_MODEL}")
        print("Successfully created Agent with string LLM!")
    except Exception as e2:
        print("String approach failed:", e2)
