from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables
    or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # General API Configuration
    PROJECT_NAME: str = "GoodRabbits API"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # CORS Settings
    # Supports comma-separated strings or parsed lists
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "chrome-extension://<EXTENSION_ID_PLACEHOLDER>"
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v

    # Redis Cloud Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Firebase Admin Configuration
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # Anti-Cheat & Gamification Economy Rules
    XP_PER_MINUTE: int = 10
    CARROTS_PER_MINUTE: int = 5
    MINIMUM_FOCUS_SECONDS: int = 60  # Minimum duration to earn rewards (1 min)
    MAX_SESSION_HOURS: int = 4       # Max TTL for focus session key to avoid orphans
    BLOCKLIST_CACHE_TTL_SECONDS: int = 86400  # 24 hours TTL for blocklist cache


settings = Settings()
