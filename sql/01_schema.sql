-- Medallion layers: bronze = raw, silver = cleaned, gold = business-ready views.
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- BRONZE: raw data exactly as received (everything TEXT), full load each run.
CREATE TABLE IF NOT EXISTS bronze.wards_raw (
    source_row      INTEGER     NOT NULL,
    ward_id         TEXT,
    wing            TEXT,
    department      TEXT,
    beds_available  TEXT,
    source_file     TEXT        NOT NULL,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- SILVER: cleaned, standardised, de-duplicated.
CREATE TABLE IF NOT EXISTS silver.wards (
    ward_id            TEXT PRIMARY KEY,
    wing               TEXT,
    department         TEXT,
    beds_available     INTEGER CHECK (beds_available BETWEEN 0 AND 200),
    capacity_status    TEXT    NOT NULL CHECK (capacity_status IN ('Full', 'Low', 'Available', 'Unknown')),
    merged_duplicates  BOOLEAN NOT NULL,
    source_rows        TEXT    NOT NULL,
    notes              TEXT,
    loaded_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rows that could not be identified at all are kept here, never silently dropped.
CREATE TABLE IF NOT EXISTS silver.rejected_rows (
    source_row  INTEGER NOT NULL,
    reason      TEXT    NOT NULL,
    raw_record  TEXT,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per pipeline execution (audit trail for repeatable runs).
CREATE TABLE IF NOT EXISTS silver.pipeline_runs (
    run_id            SERIAL PRIMARY KEY,
    started_at        TIMESTAMPTZ NOT NULL,
    finished_at       TIMESTAMPTZ NOT NULL,
    raw_rows          INTEGER NOT NULL,
    cleaned_wards     INTEGER NOT NULL,
    duplicates_merged INTEGER NOT NULL,
    rejected_rows     INTEGER NOT NULL,
    quality_score     NUMERIC(5, 1) NOT NULL
);
