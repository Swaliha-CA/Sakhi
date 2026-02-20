"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "she-health-ledger"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis (Cache)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # OCR Configuration
    OCR_CACHE_TTL: int = 86400  # 24 hours in seconds
    OCR_CONFIDENCE_THRESHOLD: float = 0.85
    OCR_SUPPORTED_LANGUAGES: list[str] = ["en", "hi", "ta", "te"]  # Bengali not available in PaddleOCR 3.x
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"  # "openai" or "gemini"
    LLM_MODEL_SIMPLE: str = "gpt-4o-mini"  # For simple cases
    LLM_MODEL_COMPLEX: str = "gpt-4o"  # For complex labels
    GEMINI_MODEL_SIMPLE: str = "gemini-1.5-flash"
    GEMINI_MODEL_COMPLEX: str = "gemini-1.5-pro"
    LLM_CACHE_TTL: int = 604800  # 7 days in seconds
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 30  # seconds
    LLM_TEMPERATURE: float = 0.1  # Low temperature for consistent extraction
    
    # Toxicity Database Configuration
    COMPTOX_API_KEY: Optional[str] = None
    COMPTOX_API_URL: str = "https://comptox.epa.gov/dashboard-api"
    OPENFOODTOX_API_URL: str = "https://api.openfoodtox.org"
    FSSAI_API_KEY: Optional[str] = None
    FSSAI_API_URL: str = "https://api.fssai.gov.in"
    CHEMICAL_CACHE_TTL: int = 604800  # 7 days in seconds
    CHEMICAL_MATCHING_THRESHOLD: float = 0.85  # Bio-SIM fuzzy matching threshold
    
    # SQLite Configuration (Offline-first storage)
    SQLITE_DB_PATH: str = "./data/local.db"
    SQLITE_ENCRYPTION_KEY: str = "change-this-encryption-key-in-production"
    
    # Bhashini Voice AI Configuration
    BHASHINI_API_KEY: Optional[str] = None
    BHASHINI_API_URL: str = "https://api.bhashini.gov.in"
    VOICE_CONFIDENCE_THRESHOLD: float = 0.80
    VOICE_MAX_RETRIES: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


settings = Settings()
