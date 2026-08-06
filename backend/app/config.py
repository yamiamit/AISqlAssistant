"""
Centralized application settings, loaded from environment variables (.env in dev).

Using pydantic-settings means every setting is typed and validated once at
startup instead of scattered `os.getenv()` calls throughout the codebase.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App metadata database (stores users, connections, chats, saved queries) ---
    APP_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/app_db"

    # --- Auth ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # --- Encryption for storing target-database credentials at rest ---
    # Must be a urlsafe-base64-encoded 32-byte key. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = "5DGqf6L1Pz6nU2m6b3s0k8x1vQe7h4jZcR9tYw2AbCd="

    # --- AI provider ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_REQUEST_TIMEOUT_SECONDS: int = 30

    # --- SQL execution safety ---
    SQL_STATEMENT_TIMEOUT_MS: int = 10_000
    SQL_DEFAULT_ROW_LIMIT: int = 500

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- File uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 15

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so Settings is only parsed once per process."""
    return Settings()


settings = get_settings()
