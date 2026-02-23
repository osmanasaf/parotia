import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/parotia")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Email
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    FROM_EMAIL: Optional[str] = os.getenv("FROM_EMAIL")
    # Resend
    RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY")
    RESEND_FROM_EMAIL: Optional[str] = os.getenv("RESEND_FROM_EMAIL")
    
    # CORS
    CORS_ALLOW_ORIGINS: Optional[str] = os.getenv("CORS_ALLOW_ORIGINS")

    # Verification
    VERIFICATION_CODE_EXPIRE_MINUTES: int = int(os.getenv("VERIFICATION_CODE_EXPIRE_MINUTES", "10"))
    
    # TMDB API
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    
    # Redis
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Scheduler
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    SCHEDULE_HOUR: int = int(os.getenv("SCHEDULE_HOUR", "2"))
    SCHEDULE_MINUTE: int = int(os.getenv("SCHEDULE_MINUTE", "0"))
    SCHEDULE_MOVIE_BATCH_PAGES: int = int(os.getenv("SCHEDULE_MOVIE_BATCH_PAGES", "25"))
    SCHEDULE_TV_BATCH_PAGES: int = int(os.getenv("SCHEDULE_TV_BATCH_PAGES", "25"))

    # Embedding/Index storage
    INDEX_DIR: str = os.getenv("INDEX_DIR", ".")


    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Singleton instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get settings singleton instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 