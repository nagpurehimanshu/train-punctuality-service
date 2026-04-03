import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

NTES_BASE_URL = os.getenv("NTES_BASE_URL", "https://enquiry.indianrail.gov.in/mntes/")
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
COLLECTION_RATE_LIMIT = float(os.getenv("COLLECTION_RATE_LIMIT", "1.0"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
