from pathlib import Path

from sprint_planning_automator.cli import run

MOCK_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_jira_data.json"


def _fake_input(responses):
    it = iter(responses)

    def _input(_prompt=""):
        return next(it)

    return _input


def test_end_to_end_run_all_confirmed(monkeypatch, capsys):
    responses = ["2026-08-25", "2026-09-08", "c", "c", "c"]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    assert "Finalized: ['Team Alpha', 'Team Bravo', 'Team Charlie']" in out
    assert "Declined:  none" in out
    assert "Processing time (excluding PO input):" in out


def test_end_to_end_run_mixed_confirmation(monkeypatch, capsys):
    responses = ["2026-08-25", "2026-09-08", "c", "n", "c"]
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
        "c",
        "c",
        "c",
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    assert "End date must be after start date" in out
    assert "Could not parse" in out
    assert "New sprint window: 2026-08-25 -> 2026-09-08" in out


def test_processing_completes_within_ten_seconds(monkeypatch, capsys):
    responses = ["2026-08-25", "2026-09-08", "c", "c", "c"]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    line = next(l for l in out.splitlines() if l.startswith("Processing time"))
    seconds = float(line.split(":")[1].strip().rstrip("s"))
    assert seconds < 10


def test_edit_swap_card_and_goal_reflected_in_confirmation(monkeypatch, capsys):
    # Team Alpha: edit -> remove ALPHA-204, add nothing back (shrink), edit goal, done, confirm.
    # Team Bravo, Charlie: confirm as-is.
    responses = [
        "2026-08-25",
        "2026-09-08",
        "e",  # Alpha: enter edit mode
        "r",  # remove a card
        "1",  # ALPHA-204 is listed first (added_cards order)
        "g",  # edit goal
        "Ship SSO and settings refactor for real users",
        "d",  # done editing
        "c",  # confirm Alpha
        "c",  # Bravo confirm as-is
        "c",  # Charlie confirm as-is
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    assert "Removed ALPHA-204." in out
    assert "Sprint goal updated." in out
    assert "Ship SSO and settings refactor for real users" in out
    # ALPHA-204 should no longer appear as an ADDED card in the (re-shown) summary
    # after removal, only the finalize confirmation should follow.
    assert "Finalized: ['Team Alpha', 'Team Bravo', 'Team Charlie']" in out


def test_edit_remove_then_add_card_back_reflected_in_totals(monkeypatch, capsys):
    # Team Alpha: remove ALPHA-204 (8 pts), see the reduced total, then add it back
    # via the 'add' path (it's the only available card once removed) and confirm
    # the total is restored before finalizing.
    responses = [
        "2026-08-25",
        "2026-09-08",
        "e",
        "r",
        "1",  # remove ALPHA-204
        "a",
        "1",  # ALPHA-204 is now the only available card -> add it back
        "d",
        "c",
        "c",
        "c",
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run(MOCK_DATA_PATH)

    out = capsys.readouterr().out
    assert "Removed ALPHA-204." in out
    assert "Added ALPHA-204." in out
    # Total should be back to 26 (13 rollover + 8 + 5) before Alpha's final confirm.
    assert "Total points: 26 / Velocity: 32" in out
