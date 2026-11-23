from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # Backend project root


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"
    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 8001
    MCP_PATH: str = "/mcp"
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "deepseek-flash"
    # 15 allows one input-review step, six model/tool round trips and a final answer, including graph completion.
    # Revalidate this budget when adding middleware or changing the execution graph.
    AGENT_RECURSION_LIMIT: int = 15

    # Comma-separated browser origins allowed to call the API. Never use "*" with credentials.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limiting. Each chat message costs at least two paid model calls, and registration is open,
    # so unauthenticated and per-account limits protect both brute-force and spend.
    # "memory://" is per process; use e.g. "redis://redis:6379" when running several workers.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    LOGIN_RATE_LIMIT: str = "10/minute"
    REGISTER_RATE_LIMIT: str = "10/hour"
    CHAT_RATE_LIMIT: str = "20/minute"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def reject_weak_jwt_secret(cls, value: str) -> str:
        """Fail at startup instead of signing tokens with a guessable secret."""
        if len(value) < 32 or value.startswith("replace-with"):
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters and must not be the example placeholder. "
                'Generate one with: python3 -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100M, course documents

# /api/files/upload is used for avatars only, so it accepts small images and nothing else.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5M
STUDY_PLAN_MAX_LENGTH = 2000
KB_DIR = BASE_DIR / "data" / "kb"
KB_DIR.mkdir(parents=True, exist_ok=True)
