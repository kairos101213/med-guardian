# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ------------------ Security ------------------
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 10080))  # 7 days by default

# ------------------ Database ------------------
raw_db_url = os.getenv("DATABASE_URL")
# Enforce SSL connection to Render Postgres
if raw_db_url and "sslmode=" not in raw_db_url:
    DATABASE_URL = raw_db_url + "?sslmode=require"
else:
    DATABASE_URL = raw_db_url

# ------------------ Firebase ------------------
# Use either JSON path (local dev) or inline JSON string (deployment)
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")
