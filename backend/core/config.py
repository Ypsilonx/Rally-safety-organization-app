"""Configuration management for Rally Safety App."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""
    
    # App settings
    APP_NAME: str = "Rally Safety App"
    APP_VERSION: str = "0.1.0"
    # Bezpečný default je False - DEBUG (a s ním veřejný /api/debug/pins)
    # se zapíná výslovně jen v lokálním .env pro vývoj.
    DEBUG: bool = False

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    # CORS - čárkou oddělený seznam originů frontendu, nebo "*" pro vývoj
    ALLOWED_ORIGINS: str = "*"

    # WebSocket settings
    WS_MAX_CONNECTIONS: int = 200
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds

    # Auth settings
    SESSION_EXPIRE_MINUTES: int = 480  # 8 hours
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def cors_origins(self) -> list[str]:
        """Rozparsuje ALLOWED_ORIGINS na seznam pro CORSMiddleware.

        Returns:
            ["*"] pro vývojový wildcard, jinak seznam konkrétních originů.
        """
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
