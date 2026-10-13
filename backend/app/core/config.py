# Application configuration
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "cloud-cost-optimizer-alan-vo"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # Auth / OIDC
    OIDC_ISSUER_URL: Optional[str] = None
    OIDC_CLIENT_ID: Optional[str] = None
    OIDC_CLIENT_SECRET: Optional[str] = None
    OIDC_REDIRECT_URI: Optional[str] = None
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    SESSION_COOKIE_NAME: str = "cc_session"
    CSRF_COOKIE_NAME: str = "cc_csrf"

    # Demo mode (localhost only)
    DEMO_MODE: bool = True

    # LLM
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_PROVIDER: str = "openai"  # openai, anthropic, gemini, ollama

    # Cloud SDKs (optional)
    AWS_DEFAULT_REGION: str = "us-east-1"
    GCP_PROJECT_ID: Optional[str] = None
    AZURE_SUBSCRIPTION_ID: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def is_demo_mode() -> bool:
    """Check if running in demo mode (localhost only)."""
    return settings.DEMO_MODE and settings.HOST in ("127.0.0.1", "localhost", "0.0.0.0")


def require_production_auth() -> bool:
    """Return True if production auth should be enforced."""
    return not is_demo_mode()