# HealthSafe Data Pipeline

Takes HealthSafe's messy legacy ward export (`data/wards-outdated.csv`), validates and cleans it with
**pandas**, stores it in **PostgreSQL** using a bronze / silver / gold (medallion) layout, builds analytical
**SQL views**, and writes a data-quality report. Tested with **pytest**, run in CI with **GitHub Actions**.

## Architecture

| Layer | Where | What happens | Load |
|---|---|---|---|
| Source | `data/wards-outdated.csv` | External CSV (`--source` / `SOURCE_CSV` to change) | - |
| Bronze | `bronze.wards_raw` | Raw rows as text, no transformation | Batch, full load |
| Silver | `silver.wards`, `silver.rejected_rows` | Cleaned, standardised, de-duplicated, derived `capacity_status` | Batch, full load |
| Gold | `gold.*` views (`sql/02_gold_views.sql`) | Aggregations and business logic | None (views) |
| Consume | `sql/queries.sql`, `reports/quality_report.json` | Ad-hoc SQL, BI tools, ML | - |

Audit trail of every run: `silver.pipeline_runs`.

```
src/healthsafe_pipeline/
  extract.py   read CSV as text           clean.py    validation + transforms (pure pandas)
  db.py        PostgreSQL loads           quality.py  completeness + score report
  pipeline.py  one repeatable run         __main__.py CLI
sql/           schema, gold views, example queries
tests/         unit tests + PostgreSQL integration test
```

## Setup and run

Requirements: Python 3.11+, Docker (for PostgreSQL).

```
docker compose up -d                       # PostgreSQL on :5432
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export PYTHONPATH=src
python -m healthsafe_pipeline              # run the pipeline (safe to repeat)
psql postgresql://healthsafe:healthsafe@localhost:5432/healthsafe -f sql/queries.sql
```

Config (env vars): `DATABASE_URL`, `SOURCE_CSV`, `REPORT_DIR`.

## Tests

```
pytest                                     # unit tests (integration test skipped without a DB)
DATABASE_URL=postgresql+psycopg://healthsafe:healthsafe@localhost:5432/healthsafe pytest   # everything
```

CI (`.github/workflows/ci.yml`) starts a PostgreSQL service, runs all tests, then runs the pipeline.

## Cleaning rules and decisions

- Trim, collapse double spaces, normalise casing (ids upper, wings title case)
- Placeholders (`N/A`, `TBD`, blank, `-`, `NaN`, `unknown`) become NULL
- Department variants unified (`Pediatrics` -> `Paediatrics`, `intensive care` -> `ICU`)
- `beds_available`: non-numeric (`five`, `full`), negative, or > 200 (e.g. `2023`) become NULL with a note
- Duplicate ward ids (`W-05` / `w-05`) are **merged, first valid value wins**; the merge is recorded in `notes` and `source_rows`
- Rows without a ward id go to `silver.rejected_rows` - nothing is dropped silently
- A bad row never crashes a run; a failed run exits non-zero and silver loads are all-or-nothing (one transaction)
- Derived `capacity_status`: `Full` (0 beds), `Low` (1-2), `Available`, `Unknown`

## Gold views

`gold.beds_by_wing`, `gold.beds_by_department`, `gold.wards_needing_attention`, `gold.data_quality_summary`

## Sample result (included CSV)

18 raw rows -> 17 wards, 1 duplicate merged, 0 rejected; bed-count completeness 52.9%, quality score 82.3.

## Ideas to extend

Ingest from the ingestion-service REST API as a second source, add staffing/alert-level data for a star schema
(`dim_ward`, `fact_staffing`), schedule the run (cron / GitHub Actions `schedule`), add `ruff` to CI.

verification WTC-QKY56JRN
