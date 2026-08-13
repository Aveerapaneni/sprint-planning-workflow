from pathlib import Path

from sprint_planning_automator.cli import run

MOCK_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_jira_data.json"


def _fake_input(responses):
    it = iter(responses)

    def _input(_prompt=""):
        return next(it)

    return _input


def test_end_to_end_run_all_confirmed(monkeypatch, capsys):
    responses = ["2026-08-25", "2026-09-08", "y", "y", "y"]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    assert "Finalized: ['Team Alpha', 'Team Bravo', 'Team Charlie']" in out
    assert "Declined:  none" in out
    assert "Processing time (excluding PO input):" in out


def test_end_to_end_run_mixed_confirmation(monkeypatch, capsys):
    responses = ["2026-08-25", "2026-09-08", "y", "n", "y"]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    assert "Finalized: ['Team Alpha', 'Team Charlie']" in out
    assert "Declined:  ['Team Bravo']" in out


def test_invalid_date_order_reprompts(monkeypatch, capsys):
    # Each rejection re-prompts for BOTH start and end, so every retry supplies a full pair.
    responses = [
        "2026-09-08",
        "2026-08-25",  # end before start -> rejected, re-prompt both
        "2026-08-25",
        "not-a-date",  # bad end format -> rejected, re-prompt both
        "2026-08-25",
        "2026-09-08",  # valid pair
        "y",
        "y",
        "y",
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    assert "End date must be after start date" in out
    assert "Could not parse" in out
    assert "New sprint window: 2026-08-25 -> 2026-09-08" in out


def test_processing_completes_within_ten_seconds(monkeypatch, capsys):
    responses = ["2026-08-25", "2026-09-08", "y", "y", "y"]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    line = next(l for l in out.splitlines() if l.startswith("Processing time"))
    seconds = float(line.split(":")[1].strip().rstrip("s"))
    assert seconds < 10
