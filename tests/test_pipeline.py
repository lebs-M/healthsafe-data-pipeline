import json

import pandas as pd

from healthsafe_pipeline import pipeline


def test_run_orchestrates_every_layer_in_order(monkeypatch, tmp_path):
    source = tmp_path / "wards.csv"
    source.write_text(
        "ward_id,wing,department,beds_available\n"
        "W-1,East Wing,Oncology,3\n"
        "W-2,West Wing,Cardiology,0\n",
        encoding="utf-8",
    )
    state = {}
    events = []

    def load_bronze(engine, raw, source_file):
        state["raw"] = raw
        events.append(("bronze", len(raw), source_file))

    monkeypatch.setattr(pipeline.db, "init_schema", lambda engine: events.append("init"))
    monkeypatch.setattr(pipeline.db, "load_bronze", load_bronze)
    monkeypatch.setattr(pipeline.db, "read_bronze", lambda engine: state["raw"].copy())
    monkeypatch.setattr(
        pipeline.db, "load_silver",
        lambda engine, result: events.append(("silver", len(result.wards), len(result.rejected))),
    )
    monkeypatch.setattr(pipeline.db, "refresh_gold", lambda engine: events.append("gold"))
    monkeypatch.setattr(
        pipeline.db, "record_run",
        lambda engine, report, started, finished: events.append(("record", report["cleaned_wards"])),
    )

    report_dir = tmp_path / "reports"
    report = pipeline.run(source, engine=object(), report_dir=report_dir)

    assert events == [
        "init",
        ("bronze", 2, "wards.csv"),
        ("silver", 2, 0),
        "gold",
        ("record", 2),
    ]
    assert report["raw_rows"] == 2
    assert report["cleaned_wards"] == 2
    assert report["rejected_rows"] == 0
    assert report["duplicates_merged"] == 0
    written = json.loads((report_dir / "quality_report.json").read_text())
    assert written == report
    assert isinstance(state["raw"], pd.DataFrame)
