from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import (
    agents,
    decisions,
    events,
    memory,
    portfolios,
    research,
    review,
    securities,
    watchlists,
    data,
)
from scripts.seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.run_seed:
        run_seed()
    yield


app = FastAPI(title="AIMS API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def optional_api_key(request: Request, call_next):
    if settings.api_key and request.url.path not in ("/health", "/docs", "/openapi.json"):
        key = request.headers.get("x-api-key")
        if key != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/health")
def health():
    return {"status": "ok"}
