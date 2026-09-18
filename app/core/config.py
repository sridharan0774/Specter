import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SPECTER — Blockchain Intelligence & VASP Attribution Engine"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    # Default to local SQLite for rapid execution/testing; configurable to PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./specter.db")
    
    # Cache configuration (optional Redis)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)
    CACHE_TTL_SECONDS: int = 3600
    
    # Blockchain Data Provider API Keys
    TRONGRID_API_KEY: Optional[str] = os.getenv("TRONGRID_API_KEY", None)
    ETHERSCAN_API_KEY: Optional[str] = os.getenv("ETHERSCAN_API_KEY", None)
    POLYGONSCAN_API_KEY: Optional[str] = os.getenv("POLYGONSCAN_API_KEY", None)
    BSCSCAN_API_KEY: Optional[str] = os.getenv("BSCSCAN_API_KEY", None)
    
    # Operational configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
