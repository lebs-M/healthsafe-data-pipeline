"""Silver transform: validation, standardisation and duplicate handling (pandas).

Rules (each one is covered by a test):
  * trim, collapse double spaces, fix casing
  * placeholders (N/A, TBD, blank, -, NaN, unknown ...) -> NULL
  * department spelling variants -> one canonical label
  * beds_available: non-numeric, negative or unrealistic (> 200) -> NULL + note
  * duplicate ward ids are merged, first valid value wins, and the merge is noted
  * rows with no ward id are rejected (kept in a rejected table, never dropped silently)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from . import config

PLACEHOLDERS = {"", "-", "–", "—", "?", "n/a", "na", "tbd", "unknown", "nan", "null", "none"}

DEPARTMENT_SYNONYMS = {
    "paediatrics": "Paediatrics",
    "pediatrics": "Paediatrics",
    "cardiology": "Cardiology",
    "oncology": "Oncology",
    "radiology": "Radiology",
    "icu": "ICU",
    "intensive care": "ICU",
    "intensive care unit": "ICU",
    "maternity": "Maternity",
}

LOW_BEDS_THRESHOLD = 2


def collapse(value) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def clean_text(value) -> str | None:
    s = collapse(value)
    return None if s.lower() in PLACEHOLDERS else s


def normalize_id(value) -> str | None:
    s = clean_text(value)
    return s.upper() if s else None


def normalize_wing(value) -> str | None:
    s = clean_text(value)
    return s.title() if s else None


def normalize_department(value) -> str | None:
    s = clean_text(value)
    if not s:
        return None
    return DEPARTMENT_SYNONYMS.get(s.lower(), s.title())


def parse_beds(value) -> tuple[int | None, str | None]:
    """Return (beds, note). Missing -> (None, None); bad values -> (None, note)."""
    s = clean_text(value)
    if s is None:
        return None, None
    if not re.fullmatch(r"-?\d+", s):
        return None, f"beds_available was non-numeric ('{s}')"
    beds = int(s)
    if beds < 0:
        return None, f"beds_available was negative ({beds})"
    if beds > config.MAX_REALISTIC_BEDS:
        return None, f"beds_available was unrealistic ({beds})"
    return beds, None


def capacity_status(beds) -> str:
    """Derived column: Full / Low / Available / Unknown."""
    if beds is None or pd.isna(beds):
        return "Unknown"
    if beds == 0:
        return "Full"
    if beds <= LOW_BEDS_THRESHOLD:
        return "Low"
    return "Available"


@dataclass
class CleanResult:
    wards: pd.DataFrame
    rejected: pd.DataFrame
    raw_rows: int
    duplicates_merged: int


def clean_wards(raw: pd.DataFrame) -> CleanResult:
    """Clean bronze rows (columns: source_row, ward_id, wing, department, beds_available)."""
    rows, rejected = [], []
    for r in raw.itertuples(index=False):
        ward_id = normalize_id(r.ward_id)
        if ward_id is None:
            rejected.append({
                "source_row": int(r.source_row),
                "reason": "missing ward_id",
                "raw_record": f"{r.ward_id},{r.wing},{r.department},{r.beds_available}",
            })
            continue
        beds, note = parse_beds(r.beds_available)
        rows.append({
            "source_row": int(r.source_row),
            "ward_id": ward_id,
            "wing": normalize_wing(r.wing),
            "department": normalize_department(r.department),
            "beds_available": beds,
            "note": note,
        })

    cleaned = pd.DataFrame(rows, columns=["source_row", "ward_id", "wing", "department", "beds_available", "note"])
    merged, duplicates = [], 0
    for ward_id, group in cleaned.groupby("ward_id", sort=True):
        record = {"ward_id": ward_id}
        for col in ("wing", "department", "beds_available"):
            valid = group[col].dropna()
            record[col] = valid.iloc[0] if len(valid) else None      # first valid value wins
        notes = [n for n in group["note"].dropna()]
        source_rows = [int(x) for x in group["source_row"]]
        if len(group) > 1:
            duplicates += len(group) - 1
            notes.append(f"merged duplicate rows {source_rows}")
        record.update(
            merged_duplicates=len(group) > 1,
            source_rows=",".join(map(str, source_rows)),
            notes="; ".join(notes) if notes else None,
        )
        merged.append(record)

    wards = pd.DataFrame(merged, columns=[
        "ward_id", "wing", "department", "beds_available",
        "merged_duplicates", "source_rows", "notes"])
    wards["beds_available"] = wards["beds_available"].astype("Int64")
    wards.insert(4, "capacity_status", wards["beds_available"].map(capacity_status))

    rejected_df = pd.DataFrame(rejected, columns=["source_row", "reason", "raw_record"])
    return CleanResult(wards, rejected_df, raw_rows=len(raw), duplicates_merged=duplicates)
