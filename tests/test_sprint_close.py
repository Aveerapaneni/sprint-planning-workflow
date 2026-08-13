from pathlib import Path

import pytest

from sprint_planning_automator.data_loader import load_data
from sprint_planning_automator.sprint_close import (
    SprintCloseError,
    close_sprint_and_get_rollover,
)

MOCK_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_jira_data.json"


@pytest.fixture
def data():
    return load_data(MOCK_DATA_PATH)


EXPECTED_ROLLOVER = {
    "team_alpha": {"ALPHA-202"},
    "team_bravo": {"BRAVO-102", "BRAVO-103"},
    "team_charlie": {"CHAR-301"},
}


@pytest.mark.parametrize("team_id", ["team_alpha", "team_bravo", "team_charlie"])
def test_rollover_cards_match_known_incomplete_cards(data, team_id):
    team = next(t for t in data.teams if t.team_id == team_id)
    _, rollover = close_sprint_and_get_rollover(team, data.sprints, data.cards)
    assert {c.card_id for c in rollover} == EXPECTED_ROLLOVER[team_id]


def test_done_cards_are_never_marked_rollover(data):
    team = next(t for t in data.teams if t.team_id == "team_alpha")
    _, rollover = close_sprint_and_get_rollover(team, data.sprints, data.cards)
    assert "ALPHA-201" not in {c.card_id for c in rollover}  # status: done
    assert "ALPHA-203" not in {c.card_id for c in rollover}  # status: done


def test_closing_sprint_sets_status_closed(data):
    team = next(t for t in data.teams if t.team_id == "team_alpha")
    closed_sprint, _ = close_sprint_and_get_rollover(team, data.sprints, data.cards)
    assert closed_sprint.status == "closed"


def test_rollover_cards_are_flagged(data):
    team = next(t for t in data.teams if t.team_id == "team_alpha")
    _, rollover = close_sprint_and_get_rollover(team, data.sprints, data.cards)
    assert all(c.is_rollover for c in rollover)


def test_raises_when_no_active_sprint(data):
    team = next(t for t in data.teams if t.team_id == "team_alpha")
    active = next(s for s in data.sprints if s.team_id == "team_alpha")
    active.status = "closed"  # simulate already-closed sprint
    with pytest.raises(SprintCloseError):
        close_sprint_and_get_rollover(team, data.sprints, data.cards)
