import logging
from pathlib import Path

from healthsafe_pipeline import __main__ as cli


def test_cli_passes_the_source_option_to_the_pipeline(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(cli.pipeline, "run", lambda source=None: calls.update(source=source))
    source = tmp_path / "input.csv"
    monkeypatch.setattr(cli.sys, "argv", ["healthsafe", "--source", str(source)])

    assert cli.main() == 0
    assert calls["source"] == Path(source)


def test_cli_uses_the_default_source_when_no_option_is_given(monkeypatch):
    calls = {}
    monkeypatch.setattr(cli.pipeline, "run", lambda source=None: calls.update(source=source))
    monkeypatch.setattr(cli.sys, "argv", ["healthsafe"])

    assert cli.main() == 0
    assert calls["source"] is None


def test_cli_returns_non_zero_and_logs_when_the_pipeline_fails(monkeypatch, caplog):
    def fail(source=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli.pipeline, "run", fail)
    monkeypatch.setattr(cli.sys, "argv", ["healthsafe"])

    with caplog.at_level(logging.ERROR):
        assert cli.main() == 1
    assert "pipeline failed" in caplog.text
