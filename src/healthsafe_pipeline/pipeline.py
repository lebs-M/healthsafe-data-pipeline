"""Orchestrates one repeatable run: extract -> bronze -> silver -> gold -> report."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine

from . import clean, config, db, extract, quality

log = logging.getLogger(__name__)


def run(source: Path | None = None, engine: Engine | None = None, report_dir: Path | None = None) -> dict:
    source = Path(source or config.SOURCE_CSV)
    engine = engine or db.get_engine()
    started = datetime.now(timezone.utc)
    log.info("pipeline started: %s", source)

    db.init_schema(engine)

    raw = extract.read_raw_csv(source)
    db.load_bronze(engine, raw, source.name)

    result = clean.clean_wards(db.read_bronze(engine))
    report = quality.build_report(result)
    db.load_silver(engine, result)

    db.refresh_gold(engine)
    db.record_run(engine, report, started, datetime.now(timezone.utc))
    path = quality.write_report(report, report_dir or config.REPORT_DIR)

    log.info("pipeline finished: %d raw rows -> %d wards (%d duplicates merged, %d rejected), "
             "quality score %.1f, report: %s",
             report["raw_rows"], report["cleaned_wards"], report["duplicates_merged"],
             report["rejected_rows"], report["quality_score"], path)
    return report
