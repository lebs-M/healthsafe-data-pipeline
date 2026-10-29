"""Data quality report: completeness, flagged records and an overall score."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .clean import CleanResult

CHECKED_COLUMNS = ["wing", "department", "beds_available"]


def build_report(result: CleanResult) -> dict:
    wards = result.wards
    total = len(wards)
    completeness = {
        col: round(100.0 * wards[col].notna().sum() / total, 1) if total else 100.0
        for col in CHECKED_COLUMNS
    }
    score = round(sum(completeness.values()) / len(completeness), 1)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_rows": result.raw_rows,
        "cleaned_wards": total,
        "duplicates_merged": result.duplicates_merged,
        "rejected_rows": len(result.rejected),
        "wards_with_notes": int(wards["notes"].notna().sum()),
        "completeness_percent": completeness,
        "capacity_status_counts": {k: int(v) for k, v in wards["capacity_status"].value_counts().items()},
        "quality_score": score,
    }


def write_report(report: dict, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "quality_report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path
