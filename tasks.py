from crewai import Task
from textwrap import dedent

def create_user_task(query: str, agent):
    return Task(
        agent=agent,
        description=dedent(f"""\
            Address the following user query comprehensively:
            "{query}"
            
            Instructions:
            1. Analyze the query to determine if it requires policy information, student data analysis, or both.
            2. Use the appropriate tool(s) to retrieve the necessary information.
            3. Synthesize your findings into a clear, comprehensive, and accurate final answer.
        """),
        expected_output="A comprehensive final answer that directly addresses the user's query, incorporating relevant policy details and accurate data statistics."
    )
