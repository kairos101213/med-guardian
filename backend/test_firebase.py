import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials

# Load the .env file
load_dotenv()

# Load the path from your environment variable
firebase_path = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_path:
    raise Exception("FIREBASE_CREDENTIALS not set in .env")

cred = credentials.Certificate(firebase_path)
firebase_admin.initialize_app(cred)

print("✅ Firebase initialized successfully!")
