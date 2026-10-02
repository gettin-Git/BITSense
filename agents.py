import os
from crewai import Agent, LLM
from config import LLM_MODEL, GOOGLE_API_KEY
from tools import PolicyRAGTool, StudentDataTool

# Set GEMINI_API_KEY for LiteLLM under the hood
os.environ["GEMINI_API_KEY"] = GOOGLE_API_KEY

# Initialize LLM using the modern CrewAI wrapper
llm = LLM(
    model=f"gemini/{LLM_MODEL}",
    api_key=GOOGLE_API_KEY,
)

# Tool instances
policy_tool = PolicyRAGTool()
data_tool = StudentDataTool()

def create_generalist_agent():
    return Agent(
        role="Institutional AI Assistant",
        goal="Accurately retrieve institutional policies or extract insights from student data to answer the user's question. Always cite your sources.",
        backstory="""You are an expert AI assistant for the institution. You have direct access to two tools:
1. Policy RAG Tool: For searching university regulations, hostel rules, and guidelines.
2. Student Data Analyst Tool: For running SQL queries to extract insights from student records.
You NEVER guess. You use the tools provided to answer the question directly. 
If you use the Policy RAG Tool, explicitly cite the source document name and URL at the end of your response.
Be very comprehensive in your answers. 
""",
        tools=[policy_tool, data_tool],
        allow_delegation=False,
        llm=llm,
        verbose=True,
        max_iter=3
    )
