"""Bronze extract: read the raw CSV as text, change nothing."""
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

RAW_COLUMNS = ["ward_id", "wing", "department", "beds_available"]


def read_raw_csv(path: Path) -> pd.DataFrame:
    """Read every cell as a string. Column names are trimmed/lower-cased because the
    legacy export has padding in headers (e.g. ' Wing ')."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, skipinitialspace=False)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing expected columns: {missing}")
    df = df[RAW_COLUMNS].copy()
    df.insert(0, "source_row", range(1, len(df) + 1))
    log.info("extracted %d raw rows from %s", len(df), path)
    return df
