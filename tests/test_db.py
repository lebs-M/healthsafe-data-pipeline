import pandas as pd

from healthsafe_pipeline import db


def test_nullable_turns_pandas_missing_values_into_sql_null():
    frame = pd.DataFrame({
        "number": [1, None],
        "label": ["ward", None],
        "flag": [True, False],
        "mixed": [pd.NA, "value"],
    })
    result = db._nullable(frame)

    assert result.loc[0, "number"] == 1
    assert result.loc[1, "number"] is None
    assert result.loc[1, "label"] is None
    assert result.loc[0, "flag"] is True
    assert result.loc[0, "mixed"] is None
    assert result.loc[1, "mixed"] == "value"
    assert frame.loc[0, "mixed"] is pd.NA


def test_get_engine_uses_the_supplied_url():
    engine = db.get_engine("sqlite://")
    try:
        assert engine.url.drivername == "sqlite"
    finally:
        engine.dispose()
