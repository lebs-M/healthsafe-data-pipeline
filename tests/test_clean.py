import pandas as pd
import pytest

from healthsafe_pipeline import clean


def raw(*rows):
    return pd.DataFrame(
        [(i + 1, *r) for i, r in enumerate(rows)],
        columns=["source_row", "ward_id", "wing", "department", "beds_available"],
    )


@pytest.mark.parametrize("value", ["", "N/A", "n/a", "TBD", "-", "NaN", "unknown", "  "])
def test_placeholders_become_null(value):
    assert clean.clean_text(value) is None


def test_trims_collapses_and_fixes_case():
    assert clean.normalize_id(" w-03 ") == "W-03"
    assert clean.normalize_wing("south  wing") == "South Wing"
    assert clean.normalize_department("PAEDIATRICS") == "Paediatrics"


def test_department_spelling_variants_are_unified():
    assert clean.normalize_department("Pediatrics") == "Paediatrics"
    assert clean.normalize_department("intensive care") == "ICU"


@pytest.mark.parametrize("value,expected", [("3", 3), ("0", 0), (" 12 ", 12), ("N/A", None), ("TBD", None)])
def test_valid_and_missing_beds(value, expected):
    beds, note = clean.parse_beds(value)
    assert beds == expected and note is None


@pytest.mark.parametrize("value", ["five", "full", "-1", "2023"])
def test_invalid_beds_become_null_with_note(value):
    beds, note = clean.parse_beds(value)
    assert beds is None and note


def test_capacity_status():
    assert clean.capacity_status(0) == "Full"
    assert clean.capacity_status(2) == "Low"
    assert clean.capacity_status(3) == "Available"
    assert clean.capacity_status(None) == "Unknown"


def test_duplicates_merge_first_valid_value_wins_and_leave_a_note():
    result = clean.clean_wards(raw(
        ("W-05", "East Wing", "Paediatrics", "5"),
        ("w-05", "east wing ", "PAEDIATRICS", "five"),
    ))
    assert len(result.wards) == 1 and result.duplicates_merged == 1
    ward = result.wards.iloc[0]
    assert ward["beds_available"] == 5
    assert ward["merged_duplicates"]
    assert ward["source_rows"] == "1,2"
    assert "merged duplicate rows" in ward["notes"] and "non-numeric" in ward["notes"]


def test_duplicate_fills_gaps_in_first_row():
    result = clean.clean_wards(raw(("W-1", "East Wing", "Oncology", "N/A"), ("w-1", "", "", "4")))
    assert result.wards.iloc[0]["beds_available"] == 4


def test_rows_without_an_id_are_rejected_not_dropped_silently():
    result = clean.clean_wards(raw((" ", "East Wing", "Oncology", "3"), ("W-2", "East Wing", "Oncology", "3")))
    assert len(result.wards) == 1
    assert len(result.rejected) == 1 and result.rejected.iloc[0]["reason"] == "missing ward_id"


def test_bad_rows_never_crash_the_run():
    result = clean.clean_wards(raw(("W-1", "", "", "five"), ("W-2", None, None, None)))
    assert len(result.wards) == 2
    assert result.wards["beds_available"].isna().all()
    assert (result.wards["capacity_status"] == "Unknown").all()


@pytest.mark.parametrize("value", ["none", "null", "NA", " – ", "—", "?"])
def test_more_placeholders_become_null(value):
    assert clean.clean_text(value) is None


def test_ids_and_labels_handle_placeholders_and_unknown_departments():
    assert clean.normalize_id("N/A") is None
    assert clean.normalize_wing("TBD") is None
    assert clean.normalize_department("intensive care unit") == "ICU"
    assert clean.normalize_department("NEUROLOGY") == "Neurology"


def test_collapse_handles_none_tabs_and_newlines():
    assert clean.collapse(None) == ""
    assert clean.collapse("  east\t\twing\n") == "east wing"


@pytest.mark.parametrize("value,expected", [("200", 200), ("201", None), ("-0", 0)])
def test_bed_boundaries(value, expected):
    beds, note = clean.parse_beds(value)
    assert beds == expected
    assert (note is None) == (expected is not None)


def test_capacity_status_handles_missing_integer_values():
    assert clean.capacity_status(pd.NA) == "Unknown"
    assert clean.capacity_status(1) == "Low"


def test_multiple_duplicate_groups_are_merged_and_counted():
    result = clean.clean_wards(raw(
        ("W-10", "East Wing", "Oncology", "4"),
        ("W-2", "West Wing", "ICU", "2"),
        ("w-10", "East Wing", "Oncology", "N/A"),
        ("W-2", "West Wing", "ICU", "full"),
    ))
    assert list(result.wards["ward_id"]) == ["W-10", "W-2"]
    assert result.duplicates_merged == 2
    assert result.wards["merged_duplicates"].all()
    assert result.wards.iloc[0]["notes"] == "merged duplicate rows [1, 3]"
    assert "non-numeric" in result.wards.iloc[1]["notes"]


def test_rows_without_duplicates_have_no_merge_metadata():
    result = clean.clean_wards(raw(("W-1", "East Wing", "Oncology", "3")))
    ward = result.wards.iloc[0]
    assert result.duplicates_merged == 0
    assert not ward["merged_duplicates"]
    assert ward["source_rows"] == "1"
    assert ward["notes"] is None


def test_rejected_rows_keep_the_raw_record_for_auditing():
    result = clean.clean_wards(raw(("N/A", "East Wing", "Oncology", "five")))
    assert result.wards.empty
    rejected = result.rejected.iloc[0]
    assert rejected["source_row"] == 1
    assert rejected["raw_record"] == "N/A,East Wing,Oncology,five"


def test_empty_input_produces_empty_tables_with_the_right_columns():
    empty = pd.DataFrame(columns=["source_row", "ward_id", "wing", "department", "beds_available"])
    result = clean.clean_wards(empty)
    assert result.raw_rows == 0
    assert result.wards.empty and result.rejected.empty
    assert list(result.wards.columns) == [
        "ward_id", "wing", "department", "beds_available", "capacity_status",
        "merged_duplicates", "source_rows", "notes",
    ]
