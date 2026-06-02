#!/usr/bin/env python3
"""本地 Phase 1 DoD 检查（sqlite，幂等）。"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / ".onboarding.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["RUN_SEED"] = "true"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as database
from app.config import settings
from app.database import Base
from app.models import Portfolio
from app.services.onboarding_service import get_phase1_dod
from scripts.seed import run_seed
from sqlalchemy import select

settings.database_url = os.environ["DATABASE_URL"]
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
database.engine = engine
database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
SessionLocal = database.SessionLocal

run_seed()
db = SessionLocal()
try:
    p = db.scalar(select(Portfolio).limit(1))
    if not p:
        print("no portfolio", file=sys.stderr)
        sys.exit(1)
    result = get_phase1_dod(db, p.id)
    print(result)
    if not result.get("all_complete"):
        sys.exit(1)
finally:
    db.close()
