import os
import time
from crewai import Agent, Crew, Task
from langchain_core.callbacks import BaseCallbackHandler
from config import GOOGLE_API_KEY, LLM_MODEL

os.environ["GEMINI_API_KEY"] = GOOGLE_API_KEY

class TimingCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.llm_start_time = 0

    def on_llm_start(self, serialized, prompts, **kwargs):
        self.llm_start_time = time.time()
        print("\n[LLM START]\n")
        
    def on_llm_end(self, response, **kwargs):
        t = time.time() - self.llm_start_time
        print(f"\n[⏱️ Agent LLM Thinking Time: {t:.2f}s]\n")

agent = Agent(
    role="Test",
    goal="Test",
    backstory="Test",
    llm=f"gemini/{LLM_MODEL}",
    callbacks=[TimingCallbackHandler()],
    verbose=True
)

task = Task(description="Say hi.", expected_output="Hi.", agent=agent)
crew = Crew(agents=[agent], tasks=[task], verbose=True)
crew.kickoff()
