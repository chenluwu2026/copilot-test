from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{_REPO_ROOT / 'data' / 'aims.db'}"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"
    default_user_email: str = "demo@aims.local"
    schemas_dir: str = str(_REPO_ROOT / "schemas")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
