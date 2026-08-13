from pathlib import Path

from sprint_planning_automator.mid_sprint_edit import run_edit_mode
from sprint_planning_automator.state_store import (
    ActiveSprintState,
    load_active_sprints,
    save_active_sprints,
)

MOCK_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_jira_data.json"


def _fake_input(responses):
    it = iter(responses)

    def _input(_prompt=""):
        return next(it)

    return _input


def _seed_alpha_state(state_path):
    from sprint_planning_automator.models import Card

    state = ActiveSprintState(
        team_id="team_alpha",
        team_name="Team Alpha",
        sprint_id="sprint_12_next",
        start_date="2026-08-25",
        end_date="2026-09-08",
        sprint_goal="Ship SSO and payment retry work",
        baseline_velocity=32,
        adjusted_velocity=24,
        cards=[
            Card("ALPHA-202", "team_alpha", "sprint_12_next", "Payment retry queue logic", "high", 13, "in_progress", is_rollover=True),
            Card("ALPHA-204", "team_alpha", "sprint_12_next", "Add SSO login option", "high", 8, "sprint_ready"),
        ],
    )
    save_active_sprints({"team_alpha": state}, state_path)


def test_no_active_sprints_prints_message_and_exits(tmp_path, capsys, monkeypatch):
    # No input() should be needed at all -- nothing to pick from.
    monkeypatch.setattr("builtins.input", _fake_input([]))
    state_path = tmp_path / "state.json"

    run_edit_mode(MOCK_DATA_PATH, state_path)

    out = capsys.readouterr().out
    assert "No active sprints found." in out


def test_remove_card_requires_reason_and_is_persisted(tmp_path, capsys, monkeypatch):
    state_path = tmp_path / "state.json"
    _seed_alpha_state(state_path)

    responses = [
        "1",  # pick Team Alpha
        "r",  # remove a card
        "2",  # ALPHA-204 is second in the committed-cards list
        "Deprioritized after stakeholder review",
        "d",  # done editing this team
        "n",  # don't edit another team
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run_edit_mode(MOCK_DATA_PATH, state_path)

    out = capsys.readouterr().out
    assert "Removed ALPHA-204." in out
    assert "Changes saved for Team Alpha." in out

    reloaded = load_active_sprints(state_path)["team_alpha"]
    assert [c.card_id for c in reloaded.cards] == ["ALPHA-202"]
    assert len(reloaded.change_log) == 1
    assert reloaded.change_log[0].action == "remove"
    assert reloaded.change_log[0].card_id == "ALPHA-204"
    assert reloaded.change_log[0].reason == "Deprioritized after stakeholder review"


def test_add_card_from_sprint_ready_pool_is_persisted(tmp_path, capsys, monkeypatch):
    state_path = tmp_path / "state.json"
    _seed_alpha_state(state_path)  # ALPHA-204 already committed; ALPHA-205 still available

    responses = [
        "1",  # pick Team Alpha
        "a",  # add a card
        "1",  # ALPHA-205 is the only remaining Sprint Ready card
        "Higher priority now per PO re-prioritization",
        "d",
        "n",
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run_edit_mode(MOCK_DATA_PATH, state_path)

    out = capsys.readouterr().out
    assert "Added ALPHA-205." in out

    reloaded = load_active_sprints(state_path)["team_alpha"]
    assert "ALPHA-205" in [c.card_id for c in reloaded.cards]
    assert reloaded.change_log[-1].action == "add"
    assert reloaded.change_log[-1].card_id == "ALPHA-205"


def test_blank_reason_cancels_without_change(tmp_path, capsys, monkeypatch):
    state_path = tmp_path / "state.json"
    _seed_alpha_state(state_path)

    responses = [
        "1",
        "r",
        "1",  # pick ALPHA-202
        "",  # blank reason -> cancel
        "d",
        "n",
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run_edit_mode(MOCK_DATA_PATH, state_path)

    out = capsys.readouterr().out
    assert "Cancelled: a reason is required." in out

    reloaded = load_active_sprints(state_path)["team_alpha"]
    assert len(reloaded.cards) == 2  # unchanged
    assert reloaded.change_log == []


def test_change_log_displayed_on_reentry(tmp_path, capsys, monkeypatch):
    state_path = tmp_path / "state.json"
    _seed_alpha_state(state_path)

    responses = [
        "1",
        "r",
        "1",
        "Swapped for higher priority work",
        "d",
        "y",  # edit another team -- loop back to team picker
        "1",  # pick Team Alpha again
        "d",  # nothing more to do, just verify the change log shows
        "n",
    ]
    monkeypatch.setattr("builtins.input", _fake_input(responses))

    run_edit_mode(MOCK_DATA_PATH, state_path)

    out = capsys.readouterr().out
    assert "Change log (1 entries):" in out
    assert "Swapped for higher priority work" in out
