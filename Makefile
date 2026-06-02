.PHONY: up down api web seed prod prod-logs prod-down

up:
	docker compose up -d db

# 一键线上（Postgres + API + Web + Caddy → :8080）
prod:
	docker compose -f docker-compose.prod.yml up -d --build

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

prod-down:
	docker compose -f docker-compose.prod.yml down

down:
	docker compose down

api:
	cd apps/api && pip3 install -q -r requirements.txt && \
		python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd apps/web && npm install && npm run dev

seed:
	cd apps/api && DATABASE_URL=postgresql://aims:aims@localhost:5432/aims SCHEMAS_DIR=$(CURDIR)/schemas python -c "from scripts.seed import run_seed; run_seed()"

onboarding-check:
	cd apps/api && RUN_SEED=true python3 -c "\
from app.database import SessionLocal; \
from app.models import Portfolio; \
from sqlalchemy import select; \
from scripts.seed import run_seed; \
from app.services.onboarding_service import get_phase1_dod; \
run_seed(); \
db = SessionLocal(); \
p = db.scalar(select(Portfolio).limit(1)); \
print(get_phase1_dod(db, p.id) if p else 'no portfolio'); \
db.close()"
