import os
from dotenv import load_dotenv

load_dotenv()

# Ollama (local)
OLLAMA_API_KEY = "ollama"  # Ollama doesn't require a real key
OLLAMA_BASE_URL = "http://localhost:11434/v1"
# Model must be pulled via: ollama pull llama3
LLM_MODEL = "llama3.2:latest"
LLM_FALLBACK_MODELS = ["qwen2.5:3b"]

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# Email (Gmail SMTP)
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))

# RAG
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FAISS_INDEX_PATH = os.path.join(DATA_DIR, "vector_store")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 4

# Fallback prices file
PRICES_FALLBACK_PATH = os.path.join(DATA_DIR, "prices.json")
