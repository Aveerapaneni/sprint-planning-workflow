import pytest

from sprint_planning_automator.models import Card
from sprint_planning_automator.state_store import (
    ActiveSprintState,
    MidSprintEditError,
    add_card,
    load_active_sprints,
    remove_card,
    save_active_sprints,
)


@pytest.fixture
def state():
    return ActiveSprintState(
        team_id="t1",
        team_name="Team Test",
        sprint_id="sprint_1_next",
        start_date="2026-08-25",
        end_date="2026-09-08",
        sprint_goal="Ship the thing",
        baseline_velocity=20,
        adjusted_velocity=20,
        cards=[
            Card("R-1", "t1", "sprint_1_next", "Rollover card", "high", 8, "in_progress"),
        ],
    )


def test_load_returns_empty_dict_when_file_missing(tmp_path):
    assert load_active_sprints(tmp_path / "does_not_exist.json") == {}


def test_save_then_load_round_trips(tmp_path, state):
    path = tmp_path / "state.json"
    save_active_sprints({"t1": state}, path)

    loaded = load_active_sprints(path)

    assert set(loaded.keys()) == {"t1"}
    reloaded = loaded["t1"]
    assert reloaded.team_name == "Team Test"
    assert reloaded.sprint_id == "sprint_1_next"
    assert reloaded.baseline_velocity == 20
    assert [c.card_id for c in reloaded.cards] == ["R-1"]
    assert reloaded.change_log == []


def test_total_points_sums_cards(state):
    assert state.total_points == 8


def test_remove_card_requires_reason(state):
    with pytest.raises(MidSprintEditError):
        remove_card(state, "R-1", "   ")
    assert len(state.cards) == 1  # unchanged


def test_remove_card_removes_and_logs(state):
    removed = remove_card(state, "R-1", "Deprioritized per stakeholder request")

    assert removed.card_id == "R-1"
    assert state.cards == []
    assert len(state.change_log) == 1
    entry = state.change_log[0]
    assert entry.action == "remove"
    assert entry.card_id == "R-1"
    assert entry.reason == "Deprioritized per stakeholder request"
    assert entry.timestamp  # non-empty


def test_remove_unknown_card_raises(state):
    with pytest.raises(MidSprintEditError):
        remove_card(state, "NOT-A-CARD", "some reason")


def test_add_card_requires_reason(state):
    new_card = Card("C-2", "t1", None, "New card", "medium", 5, "sprint_ready")
    with pytest.raises(MidSprintEditError):
        add_card(state, new_card, "")
    assert len(state.cards) == 1  # unchanged


def test_add_card_adds_and_logs(state):
    new_card = Card("C-2", "t1", None, "New card", "medium", 5, "sprint_ready")

    add_card(state, new_card, "Higher priority now per PO")

    assert [c.card_id for c in state.cards] == ["R-1", "C-2"]
    assert len(state.change_log) == 1
    entry = state.change_log[0]
    assert entry.action == "add"
    assert entry.card_id == "C-2"
    assert entry.reason == "Higher priority now per PO"


def test_add_duplicate_card_raises(state):
    dup = Card("R-1", "t1", None, "Rollover card", "high", 8, "in_progress")
    with pytest.raises(MidSprintEditError):
        add_card(state, dup, "some reason")
