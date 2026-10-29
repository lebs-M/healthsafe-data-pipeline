import pandas as pd
import pytest

from healthsafe_pipeline import extract


def test_reads_raw_csv_as_text_and_ignores_extra_columns(tmp_path):
    source = tmp_path / "wards.csv"
    source.write_text(
        " ward_id , Wing ,department,beds_available,unused\n"
        " W-01 , East Wing ,Cardiology,3,x\n"
        "w-02,West Wing ,paediatrics,N/A,y\n",
        encoding="utf-8",
    )
    raw = extract.read_raw_csv(source)

    assert list(raw.columns) == ["source_row", *extract.RAW_COLUMNS]
    assert list(raw["source_row"]) == [1, 2]
    assert raw.loc[0, "ward_id"] == " W-01 "
    assert raw.loc[1, "beds_available"] == "N/A"


def test_missing_expected_columns_raise_a_clear_error(tmp_path):
    source = tmp_path / "broken.csv"
    source.write_text("ward_id,wing\nW-01,East Wing\n", encoding="utf-8")
    with pytest.raises(ValueError, match="department.*beds_available"):
        extract.read_raw_csv(source)


def test_header_only_csv_returns_an_empty_frame_with_columns(tmp_path):
    source = tmp_path / "empty.csv"
    source.write_text("ward_id,wing,department,beds_available\n", encoding="utf-8")
    raw = extract.read_raw_csv(source)
    assert raw.empty
    assert list(raw.columns) == ["source_row", *extract.RAW_COLUMNS]
    assert isinstance(raw, pd.DataFrame)
