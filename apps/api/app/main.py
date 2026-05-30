from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    run_seed()
    yield


app = FastAPI(title="AIMS API", version="0.1.0", lifespan=lifespan)
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
