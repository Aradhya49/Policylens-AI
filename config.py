import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'policylens-secret-key-change-this')

    # MySQL Database
    DB_HOST     = os.getenv('DB_HOST', 'localhost')
    DB_USER     = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME     = os.getenv('DB_NAME', 'policylens_db')

    # AI API Keys
    GROQ_API_KEY       = os.getenv('GROQ_API_KEY', '')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')

    # File Uploads
    UPLOAD_FOLDER      = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
