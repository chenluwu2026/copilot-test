from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{_REPO_ROOT / 'data' / 'aims.db'}"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    default_user_email: str = "demo@aims.local"
    schemas_dir: str = str(_REPO_ROOT / "schemas")
    data_provider: str = "akshare"  # akshare | mock
    quote_sync_days: int = 120
    filing_sync_days: int = 90
    run_seed: bool = False
    # 可选：简单保护公开 API（个人部署建议设置）
    api_key: str | None = None
    # Railway 等分域名部署：放行 https://*.up.railway.app
    cors_allow_railway: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql") and "sslmode=" not in url:
            if "rlwy.net" in url or ".railway.app" in url:
                url += "&" if "?" in url else "?"
                url += "sslmode=require"
        return url


settings = Settings()
