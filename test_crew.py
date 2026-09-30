from crew import run_query

try:
    print("Testing CrewAI directly...")
    result = run_query("How many active students in campus G?")
    print("Result:")
    print(result)
except Exception as e:
    import traceback
    traceback.print_exc()
