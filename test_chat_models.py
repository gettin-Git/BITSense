import os
import google.generativeai as genai
from config import GOOGLE_API_KEY

genai.configure(api_key=GOOGLE_API_KEY)

print("Checking which Chat models your API key is allowed to use...")
print("------------------------------------------------------------------")
print("Available Generation Models:")
found_any = False
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Found: {m.name}")
            found_any = True
    
    if not found_any:
        print("❌ CRITICAL ERROR: Your API key does not have access to ANY generation models!")
        
except Exception as e:
    print(f"Failed to query the API: {e}")
