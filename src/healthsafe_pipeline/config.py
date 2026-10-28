"""Configuration, overridable via environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://healthsafe:healthsafe@localhost:5432/healthsafe"
)
SOURCE_CSV = Path(os.getenv("SOURCE_CSV", ROOT / "data" / "wards-outdated.csv"))
REPORT_DIR = Path(os.getenv("REPORT_DIR", ROOT / "reports"))
SQL_DIR = ROOT / "sql"

# A single ward is assumed to have at most this many beds; larger values
# (e.g. a year typed into the wrong column) are treated as bad data.
MAX_REALISTIC_BEDS = 200
