import json

import pandas as pd

from healthsafe_pipeline import clean, quality


def sample():
    raw = pd.DataFrame(
        [(1, "W-1", "East Wing", "Oncology", "3"),
         (2, "W-2", "", "Oncology", "N/A"),
         (3, "", "East Wing", "Oncology", "1")],
        columns=["source_row", "ward_id", "wing", "department", "beds_available"],
    )
    return clean.clean_wards(raw)


def test_report_counts_and_completeness():
    report = quality.build_report(sample())
    assert report["raw_rows"] == 3
    assert report["cleaned_wards"] == 2
    assert report["rejected_rows"] == 1
    assert report["completeness_percent"] == {"wing": 50.0, "department": 100.0, "beds_available": 50.0}
    assert report["quality_score"] == 66.7


def test_report_is_written_as_json(tmp_path):
    path = quality.write_report(quality.build_report(sample()), tmp_path)
    assert json.loads(path.read_text())["cleaned_wards"] == 2


def test_report_counts_capacity_statuses_and_notes():
    raw = pd.DataFrame(
        [(1, "W-1", "East Wing", "Oncology", "0"),
         (2, "W-2", "East Wing", "Oncology", "1"),
         (3, "W-3", "East Wing", "Oncology", "3"),
         (4, "W-4", "East Wing", "Oncology", "N/A"),
         (5, "W-5", "East Wing", "Oncology", "five")],
        columns=["source_row", "ward_id", "wing", "department", "beds_available"],
    )
    report = quality.build_report(clean.clean_wards(raw))
    assert report["capacity_status_counts"] == {"Full": 1, "Low": 1, "Available": 1, "Unknown": 2}
    assert report["wards_with_notes"] == 1
    assert report["completeness_percent"]["beds_available"] == 60.0
    assert report["quality_score"] == 86.7


def test_empty_report_scores_full_completeness():
    empty = pd.DataFrame(columns=["source_row", "ward_id", "wing", "department", "beds_available"])
    report = quality.build_report(clean.clean_wards(empty))
    assert report["cleaned_wards"] == 0
    assert report["completeness_percent"] == {"wing": 100.0, "department": 100.0, "beds_available": 100.0}
    assert report["quality_score"] == 100.0
    assert report["capacity_status_counts"] == {}


def test_report_file_is_created_in_a_nested_directory_and_overwritten(tmp_path):
    target = tmp_path / "nested" / "reports"
    first = quality.write_report(quality.build_report(sample()), target)
    assert first == target / "quality_report.json"
    quality.write_report({"quality_score": 1.0}, target)
    assert json.loads(first.read_text()) == {"quality_score": 1.0}
