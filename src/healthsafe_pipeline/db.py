"""PostgreSQL access: schema setup, full loads per layer, gold view refresh."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from . import config
from .clean import CleanResult

log = logging.getLogger(__name__)


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or config.DATABASE_URL)


def run_sql_file(engine: Engine, path: Path) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def init_schema(engine: Engine) -> None:
    run_sql_file(engine, config.SQL_DIR / "01_schema.sql")


def refresh_gold(engine: Engine) -> None:
    run_sql_file(engine, config.SQL_DIR / "02_gold_views.sql")


def _nullable(df: pd.DataFrame) -> pd.DataFrame:
    """pandas NA -> None so every driver stores a proper SQL NULL."""
    return df.astype(object).where(df.notna(), None)


def load_bronze(engine: Engine, raw: pd.DataFrame, source_file: str) -> None:
    """Full load: replace bronze with exactly what the source contained."""
    df = raw.copy()
    df["source_file"] = source_file
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE bronze.wards_raw"))
        _nullable(df).to_sql("wards_raw", conn, schema="bronze", if_exists="append", index=False)
    log.info("bronze: loaded %d rows", len(df))


def read_bronze(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        text("SELECT source_row, ward_id, wing, department, beds_available "
             "FROM bronze.wards_raw ORDER BY source_row"),
        engine,
    )


def load_silver(engine: Engine, result: CleanResult) -> None:
    """Full load of the cleaned tables in one transaction (all-or-nothing)."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE silver.wards, silver.rejected_rows"))
        _nullable(result.wards).to_sql("wards", conn, schema="silver", if_exists="append", index=False)
        _nullable(result.rejected).to_sql("rejected_rows", conn, schema="silver", if_exists="append", index=False)
    log.info("silver: %d wards, %d rejected rows", len(result.wards), len(result.rejected))


def record_run(engine: Engine, report: dict, started: datetime, finished: datetime) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO silver.pipeline_runs
                    (started_at, finished_at, raw_rows, cleaned_wards, duplicates_merged,
                     rejected_rows, quality_score)
                    VALUES (:s, :f, :raw, :cleaned, :dups, :rej, :score)"""),
            {"s": started, "f": finished, "raw": report["raw_rows"], "cleaned": report["cleaned_wards"],
             "dups": report["duplicates_merged"], "rej": report["rejected_rows"],
             "score": report["quality_score"]},
        )
