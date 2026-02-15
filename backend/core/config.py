"""Configuration management for Rally Safety App."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""
    
    # App settings
    APP_NAME: str = "Rally Safety App"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # WebSocket settings
    WS_MAX_CONNECTIONS: int = 200
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    
    # Auth settings
    SESSION_SECRET: str = "change-this-in-production-use-random-32-chars"
    SESSION_EXPIRE_MINUTES: int = 480  # 8 hours
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
