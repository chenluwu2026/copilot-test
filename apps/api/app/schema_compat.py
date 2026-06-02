"""对已有库补齐模型新增列（create_all 不会 ALTER 已有表）。"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_memory_entry_columns(engine: Engine) -> None:
    insp = inspect(engine)
    if "memory_entries" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("memory_entries")}
    dialect = engine.dialect.name
    json_type = "JSONB" if dialect == "postgresql" else "JSON"

    with engine.begin() as conn:
        if "memory_tier" not in cols:
            logger.info("schema_compat: adding memory_entries.memory_tier")
            conn.execute(
                text(
                    "ALTER TABLE memory_entries "
                    "ADD COLUMN memory_tier VARCHAR(32) NOT NULL DEFAULT 'lesson'"
                )
            )
        if "embedding" not in cols:
            logger.info("schema_compat: adding memory_entries.embedding")
            conn.execute(
                text(f"ALTER TABLE memory_entries ADD COLUMN embedding {json_type}")
            )


def apply_schema_compat(engine: Engine) -> None:
    try:
        ensure_memory_entry_columns(engine)
    except Exception:
        logger.warning("schema_compat failed", exc_info=True)
