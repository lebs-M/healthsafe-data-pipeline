"""End-to-end test against a real PostgreSQL. Skipped unless DATABASE_URL is set
(docker compose up -d, then: DATABASE_URL=postgresql+psycopg://healthsafe:healthsafe@localhost:5432/healthsafe pytest)."""
import json
import os

import pytest
from sqlalchemy import text

from healthsafe_pipeline import config, db, pipeline

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")


@pytest.fixture(scope="module")
def engine():
    return db.get_engine(os.environ["DATABASE_URL"])


def scalar(engine, sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def test_full_run_loads_all_layers(engine, tmp_path):
    report = pipeline.run(config.SOURCE_CSV, engine, tmp_path)

    assert scalar(engine, "SELECT COUNT(*) FROM bronze.wards_raw") == 18      # raw, untouched
    assert scalar(engine, "SELECT COUNT(*) FROM silver.wards") == 17          # W-05 duplicate merged
    assert report["duplicates_merged"] == 1
    assert scalar(engine, "SELECT beds_available FROM silver.wards WHERE ward_id = 'W-05'") == 5
    assert scalar(engine, "SELECT COUNT(*) FROM silver.wards WHERE beds_available < 0") == 0
    assert scalar(engine, "SELECT COUNT(*) FROM gold.beds_by_wing") >= 4
    assert scalar(engine, "SELECT total_wards FROM gold.data_quality_summary") == 17
    assert scalar(engine, "SELECT COUNT(*) FROM gold.wards_needing_attention") > 0
    assert (tmp_path / "quality_report.json").exists()


def test_pipeline_is_repeatable(engine, tmp_path):
    pipeline.run(config.SOURCE_CSV, engine, tmp_path)
    pipeline.run(config.SOURCE_CSV, engine, tmp_path)                         # same result, no duplicates
    assert scalar(engine, "SELECT COUNT(*) FROM silver.wards") == 17
    assert scalar(engine, "SELECT COUNT(*) FROM bronze.wards_raw") == 18
    assert scalar(engine, "SELECT COUNT(*) FROM silver.pipeline_runs") >= 2


def test_messy_source_records_rejections_and_audit_trail(engine, tmp_path):
    source = tmp_path / "messy.csv"
    source.write_text(
        "ward_id,wing,department,beds_available\n"
        "W-20,East Wing,Oncology,4\n"
        "w-20,east wing ,oncology,five\n"
        ",West Wing,ICU,2\n",
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"
    report = pipeline.run(source, engine, report_dir)

    assert report["raw_rows"] == 3
    assert report["cleaned_wards"] == 1
    assert report["duplicates_merged"] == 1
    assert report["rejected_rows"] == 1
    assert scalar(engine, "SELECT COUNT(*) FROM bronze.wards_raw") == 3
    assert scalar(engine, "SELECT COUNT(*) FROM silver.wards") == 1
    assert scalar(engine, "SELECT COUNT(*) FROM silver.rejected_rows") == 1
    assert scalar(engine, "SELECT reason FROM silver.rejected_rows") == "missing ward_id"
    assert scalar(engine, "SELECT beds_available FROM silver.wards WHERE ward_id = 'W-20'") == 4
    assert scalar(engine, "SELECT source_rows FROM silver.wards WHERE ward_id = 'W-20'") == "1,2"
    assert "non-numeric" in scalar(engine, "SELECT notes FROM silver.wards WHERE ward_id = 'W-20'")
    assert scalar(engine, "SELECT rejected_rows FROM gold.data_quality_summary") == 1

    latest = with_engine(engine, """
        SELECT raw_rows, cleaned_wards, duplicates_merged, rejected_rows, quality_score
        FROM silver.pipeline_runs ORDER BY run_id DESC LIMIT 1
    """)
    assert latest == (3, 1, 1, 1, report["quality_score"])

    assert json.loads((report_dir / "quality_report.json").read_text()) == report


def with_engine(engine, sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).one()
