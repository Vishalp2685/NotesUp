import os
from dotenv import load_dotenv

# Error handling for loading .env
try:
    load_dotenv()
except Exception as e:
    print(f"[ERROR] Failed to load .env: {e}")

class Config:
    # Error handling for missing env variables
    try:
        SECRET_KEY = os.getenv("SECRET_KEY")
        if not SECRET_KEY:
            raise ValueError("SECRET_KEY is not set in .env")
        UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
        MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size
        ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx"}
    except Exception as e:
        print(f"[ERROR] Config initialization: {e}")