from crewai import Crew, Process
from agents import create_generalist_agent
from tasks import create_user_task
import os

# Create data directories if they don't exist yet so things don't crash
os.makedirs("data/policies", exist_ok=True)
os.makedirs("data/db", exist_ok=True)

def run_query(query: str) -> str:
    generalist = create_generalist_agent()
    
    task = create_user_task(query, generalist)
    
    crew = Crew(
        agents=[generalist],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    # CrewAI kickoff returns a CrewOutput object. We return its raw string representation.
    result = crew.kickoff()
    return str(result)
