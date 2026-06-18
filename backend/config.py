"""
Application configuration loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    raw_db_url = os.getenv("DATABASE_URL", "")
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_db_url.startswith("postgresql://"):
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    if "sslmode=require" in raw_db_url:
        raw_db_url = raw_db_url.replace("sslmode=require", "ssl=require")
        
    DATABASE_URL: str = raw_db_url

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    # Email defaults
    DEFAULT_SMTP_EMAIL: str = os.getenv("DEFAULT_SMTP_EMAIL", "")
    DEFAULT_SMTP_PASSWORD: str = os.getenv("DEFAULT_SMTP_PASSWORD", "")

    # AI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Payments
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # App
    APP_NAME: str = os.getenv("APP_NAME", "MailPilot")
    _app_url = os.getenv("APP_URL", "http://localhost:8000")
    if not _app_url.startswith("http"):
        _app_url = "https://" + _app_url
    APP_URL: str = _app_url
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")
    SUPER_ADMIN_EMAIL: str = os.getenv("SUPER_ADMIN_EMAIL", "")

    # Engine defaults
    GLOBAL_RATE_LIMIT_PER_HOUR: int = 500
    DEFAULT_BATCH_SIZE: int = 10
    DEFAULT_DELAY_SECONDS: int = 3


settings = Settings()
