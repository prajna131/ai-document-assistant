"""
config.py
---------
Central place for all settings, paths, and model names.
Loads secret keys from the .env file so they never get hard-coded.
"""

import os

# Turn off ChromaDB's anonymous telemetry. This also stops the harmless
# "Failed to send telemetry event ... capture() takes 1 positional argument"
# messages that some ChromaDB versions print. (Must be set before chromadb loads.)
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# --- Make Python trust the system (Windows) certificate store ---
# Networks that inspect SSL (college/office/proxy Wi-Fi) use a custom root
# certificate. Your browser already trusts it via the Windows cert store.
# truststore makes Python's HTTPS (REST) calls use that same store, which
# fixes "CERTIFICATE_VERIFY_FAILED" errors when calling the Gemini API.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    # If truststore isn't installed, we just continue; the app may still work
    # on networks that don't intercept SSL.
    pass

from dotenv import load_dotenv

# Load variables from the .env file into the environment
load_dotenv()

# --- Secret keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Folder paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")      # where uploaded files are saved
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")    # where the vector database lives

# --- AI model names (Google Gemini, all free tier) ---
# Tip: run `python list_models.py` to see the exact models YOUR key supports.
#   LLM options (need 'generateContent'):  "gemini-flash-latest", "gemini-3.5-flash"
#   Embedding options (need 'embedContent'): "models/gemini-embedding-001"
# "gemini-flash-latest" always points to the current Flash model, so it won't
# go stale/deprecated like a hard-coded version can.
LLM_MODEL = "gemini-flash-lite-latest"
EMBEDDING_MODEL = "models/gemini-embedding-001"

# --- RAG tuning knobs ---
CHUNK_SIZE = 1000      # characters per chunk
CHUNK_OVERLAP = 150    # overlap so we don't cut sentences in half
TOP_K = 6              # how many chunks to feed the LLM per question
FETCH_K = 25           # how many candidates MMR considers before picking TOP_K
MMR_LAMBDA = 0.5       # 0 = max diversity, 1 = max relevance (0.5 = balanced)

# Make sure the data folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
