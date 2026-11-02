from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEV_SECRET_KEY = "testflow-dev-only-not-for-production"
_KNOWN_UNSAFE_SECRETS = {
    "testflow-super-secret-dev-key-change-in-production-2026",
    "testflow-dev-only-not-for-production",
    "secret",
    "changeme",
    "password",
    "admin",
}


class Settings(BaseSettings):
    PROJECT_NAME: str = "TestFlow API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"

    # Security: no production-usable default. Required when ENVIRONMENT=production.
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    COOKIE_SECURE: Optional[bool] = None

    # Database: SQLite default; POSTGRES_URL overrides DATABASE_URL when set
    DATABASE_URL: str = "sqlite:///./testflow.db"
    POSTGRES_URL: Optional[str] = None

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ])

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @property
    def sqlalchemy_database_uri(self) -> str:
        uri = self.POSTGRES_URL or self.DATABASE_URL
        if uri and uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri

    @property
    def cookie_secure(self) -> bool:
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        return self.is_production

    def get_secret_key(self) -> str:
        if self.SECRET_KEY:
            if self.is_production and self.SECRET_KEY.strip() in _KNOWN_UNSAFE_SECRETS:
                raise ValueError("Insecure known SECRET_KEY detected in production. You must set a strong unique secret.")
            return self.SECRET_KEY
        if self.is_production:
            raise ValueError("SECRET_KEY must be set when ENVIRONMENT=production")
        return _DEV_SECRET_KEY

    @model_validator(mode="after")
    def _validate_production_security(self):
        if self.is_production:
            if not self.SECRET_KEY or self.SECRET_KEY.strip() in _KNOWN_UNSAFE_SECRETS:
                raise ValueError("Production environment requires a unique, non-default SECRET_KEY")
            db_uri = self.sqlalchemy_database_uri
            if not db_uri or db_uri.startswith("sqlite"):
                raise ValueError(
                    "Production environment cannot use default SQLite. "
                    "Configure POSTGRES_URL or a PostgreSQL DATABASE_URL."
                )
        return self


settings = Settings()
