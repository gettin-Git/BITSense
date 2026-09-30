import os
import ssl

# --- Global SSL Bypass (Fixes "self-signed certificate in certificate chain" errors) ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
# --------------------------------------------------------------------------------------

from dotenv import load_dotenv

# Load environment variables from .env file, overriding any existing system vars
load_dotenv(override=True)

def get_env_var(var_name: str, default: str = None) -> str:
    """Retrieve an environment variable, raising an error if it's missing and has no default."""
    value = os.getenv(var_name, default)
    if not value:
        raise ValueError(f"Environment variable '{var_name}' is required but not set.")
    return value

# Configuration variables
GOOGLE_API_KEY = get_env_var("GOOGLE_API_KEY")
LLM_MODEL = get_env_var("LLM_MODEL", "gemini-1.5-pro")
JUDGE_MODEL = get_env_var("JUDGE_MODEL", "gemini-1.5-pro")
EMBEDDING_MODEL = get_env_var("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Database paths
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "data", "db", "chroma")
LOCAL_FILE_STORE_DIR = os.path.join(os.path.dirname(__file__), "data", "db", "store")
POLICIES_DIR = os.path.join(os.path.dirname(__file__), "data", "policies")
STUDENT_RECORDS_CSV = os.path.join(os.path.dirname(__file__), "data", "student_records.csv")
EVAL_QUESTIONS_CSV = os.path.join(os.path.dirname(__file__), "data", "eval_questions.csv")
