import os
import google.generativeai as genai
from config import GOOGLE_API_KEY

genai.configure(api_key=GOOGLE_API_KEY)

print("Let's see exactly what Google is allowing your API key to access...")
print("------------------------------------------------------------------")
print("Available Embedding Models:")
found_any = False
try:
    for m in genai.list_models():
        if 'embedContent' in m.supported_generation_methods:
            print(f"✅ Found: {m.name}")
            found_any = True
    
    if not found_any:
        print("❌ CRITICAL ERROR: Your API key does not have access to ANY embedding models!")
        print("This usually happens if you are using an older API key or a restricted Google Cloud project.")
        
except Exception as e:
    print(f"Failed to query the API: {e}")
