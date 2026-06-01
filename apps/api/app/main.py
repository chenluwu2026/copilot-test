from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import (
    agents,
    data,
    decisions,
    events,
    memory,
    portfolios,
    research,
    review,
    securities,
    users,
    watchlists,
)
from scripts.seed import run_seed
from app.services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.run_seed:
        run_seed()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="AIMS API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def optional_api_key(request: Request, call_next):
    exempt = request.url.path in ("/health", "/docs", "/openapi.json") or request.url.path.endswith(
        "/data/sync/cron"
    )
    if settings.api_key and not exempt:
        key = request.headers.get("x-api-key")
        if key != settings.api_key:
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
app.include_router(research.router, prefix=prefix)
app.include_router(agents.router, prefix=prefix)
app.include_router(memory.router, prefix=prefix)
app.include_router(review.router, prefix=prefix)
app.include_router(data.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)


@app.get("/health")
def health():
    return {"status": "ok"}
