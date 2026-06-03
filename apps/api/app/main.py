from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.schema_compat import apply_schema_compat
from app.routers import (
    agents,
    auth,
    dashboard,
    onboarding,
    data,
    decisions,
    events,
    fm,
    memory,
    portfolios,
    research,
    review,
    rules,
    scenarios,
    securities,
    users,
    watchlists,
)
from scripts.seed import run_seed
from app.services.scheduler_service import start_scheduler, stop_scheduler


def _maybe_alembic_upgrade() -> None:
    if not settings.alembic_upgrade_on_start:
        return
    try:
        from alembic import command
        from alembic.config import Config

        ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        if ini.exists():
            cfg = Config(str(ini))
            command.upgrade(cfg, "head")
    except Exception:
        import logging

        logging.getLogger(__name__).warning("alembic upgrade skipped", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _maybe_alembic_upgrade()
    Base.metadata.create_all(bind=engine)
    apply_schema_compat(engine)
    if settings.run_seed:
        run_seed()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="AIMS API", version="0.1.0", lifespan=lifespan)


def _bearer_token_valid(request: Request) -> bool:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    try:
        import jwt

        secret = settings.jwt_secret or settings.api_key or "aims-dev-secret-change-me"
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except Exception:
        return False


@app.middleware("http")
async def optional_api_key(request: Request, call_next):
    exempt = request.url.path in ("/health", "/docs", "/openapi.json") or request.url.path.endswith(
        "/data/sync/cron"
    ) or request.url.path.endswith("/auth/login")
    if settings.api_key and not exempt:
        key = request.headers.get("x-api-key")
        if key != settings.api_key and not _bearer_token_valid(request):
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


_cors: dict = {
    "allow_origins": settings.cors_origin_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.cors_allow_railway:
    _cors["allow_origin_regex"] = r"https://[\w-]+\.up\.railway\.app"
app.add_middleware(CORSMiddleware, **_cors)

prefix = settings.api_prefix
app.include_router(securities.router, prefix=prefix)
app.include_router(portfolios.router, prefix=prefix)
app.include_router(decisions.router, prefix=prefix)
app.include_router(watchlists.router, prefix=prefix)
app.include_router(events.router, prefix=prefix)
app.include_router(fm.router, prefix=prefix)
app.include_router(research.router, prefix=prefix)
app.include_router(agents.router, prefix=prefix)
app.include_router(memory.router, prefix=prefix)
app.include_router(review.router, prefix=prefix)
app.include_router(data.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(onboarding.router, prefix=prefix)
app.include_router(rules.router, prefix=prefix)
app.include_router(scenarios.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)


@app.get("/health")
def health():
    return {"status": "ok"}
