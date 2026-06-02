from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_config_file = Path(__file__).resolve()
_REPO_ROOT = next(
    (p for p in _config_file.parents if (p / "schemas").exists()),
    _config_file.parents[1],
)


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
    quote_sync_incremental: bool = True
    quote_sync_overlap_days: int = 5
    quote_sync_retries: int = 2
    data_stale_days: int = 3
    data_sync_cron_enabled: bool = False
    data_sync_cron_time: str = "18:30"
    data_sync_cron_tz: str = "Asia/Shanghai"
    auto_nav_after_sync: bool = True
    auto_daily_report_after_sync: bool = False
    rebalance_cron_enabled: bool = False
    rebalance_cron_time: str = "19:00"
    rebalance_cron_chain_after_sync: bool = False
    daily_report_cron_enabled: bool = False
    daily_report_cron_time: str = "19:05"
    event_research_refresh_enabled: bool = True
    event_research_refresh_force_draft: bool = False
    review_cron_enabled: bool = False
    review_cron_time: str = "20:00"
    review_cron_max_per_run: int = 5
    news_sync_cron_enabled: bool = False
    news_sync_cron_time: str = "09:00"
    news_sync_max_symbols: int = 8
    jwt_secret: str | None = None
    auth_password: str | None = None
    # Postgres 等已有卷需迁移；sqlite 本地可关
    alembic_upgrade_on_start: bool = True
    cron_secret: str | None = None
    # CIO 证据驱动决策
    cio_decision_mode: str = "batch"  # batch | per_symbol
    cio_refresh_research: bool = False
    cio_max_symbols: int = 12
    run_seed: bool = False
    # Agent：rule=规则引擎 | llm=大模型 CIO（需 OPENAI_API_KEY）
    agent_mode: str = "rule"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_timeout_s: int = 120
    structuring_mode: str = "rule"  # rule | llm
    # 低证据（grade C）决策禁止批准，除非关闭
    require_low_evidence_block: bool = True
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
