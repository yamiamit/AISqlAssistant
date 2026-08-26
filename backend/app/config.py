"""
Centralized application settings, loaded from environment variables (.env in dev).

Using pydantic-settings means every setting is typed and validated once at
startup instead of scattered `os.getenv()` calls throughout the codebase.
"""
from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that must never be accepted as a real secret: the placeholders from
# .env.example (copying that file and forgetting to edit it is the single most
# common setup mistake) and the fallback key this file used to ship with, which
# is public in this repo's git history and therefore permanently compromised.
REJECTED_SECRETS = frozenset({
    "change-me-in-production",
    "replace-with-a-long-random-string",
    "replace-with-a-generated-fernet-key",
    "5DGqf6L1Pz6nU2m6b3s0k8x1vQe7h4jZcR9tYw2AbCd=",
})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App metadata database (stores users, connections, chats, saved queries) ---
    APP_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/app_db"

    # --- Auth ---
    # Deliberately no default. A default here is a *fallback*, not a placeholder:
    # if the env var is missing in production the app would boot happily on a
    # secret published in this file, and get_current_user() trusts a valid
    # signature as proof of identity — so anyone could mint a token for any user.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # --- Encryption for storing target-database credentials at rest ---
    # Must be a urlsafe-base64-encoded 32-byte key. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # No default, for the same reason as JWT_SECRET_KEY, and with a worse blast
    # radius: this key guards *other people's* database passwords. A shared
    # fallback key is strictly worse than refusing to start.
    ENCRYPTION_KEY: str

    # --- AI provider ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    AI_REQUEST_TIMEOUT_SECONDS: int = 30

    # --- Demo database (shared, read-only sample data visitors can try instantly) ---
    # A Postgres connection string loaded with backend/demo/schema.sql + seed.sql.
    # Left empty, "Try with sample data" is unavailable rather than erroring at startup.
    DEMO_DATABASE_URL: str = ""

    # --- SQL execution safety ---
    SQL_STATEMENT_TIMEOUT_MS: int = 10_000
    SQL_DEFAULT_ROW_LIMIT: int = 500

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- File uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 15

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if value in REJECTED_SECRETS:
            raise ValueError(
                "is still a placeholder. Generate a real one with:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if len(value) < 32:
            raise ValueError(
                f"is too short ({len(value)} chars); use at least 32. Generate one with:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def _validate_encryption_key(cls, value: str) -> str:
        generate_hint = (
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
        if value in REJECTED_SECRETS:
            raise ValueError(f"is a placeholder or a known-compromised key. Generate a real one with:\n{generate_hint}")
        try:
            Fernet(value.encode())
        except Exception as exc:
            raise ValueError(
                f"must be a urlsafe-base64-encoded 32-byte Fernet key. Generate one with:\n{generate_hint}"
            ) from exc
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so Settings is only parsed once per process."""
    return Settings()


settings = get_settings()
