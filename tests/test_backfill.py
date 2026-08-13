from pathlib import Path

import pytest

from sprint_planning_automator.backfill import backfill_sprint
from sprint_planning_automator.data_loader import load_data
from sprint_planning_automator.models import Card
from sprint_planning_automator.sprint_close import close_sprint_and_get_rollover

MOCK_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_jira_data.json"


@pytest.fixture
def data():
    return load_data(MOCK_DATA_PATH)


def _plan_for(data, team_id):
    team = next(t for t in data.teams if t.team_id == team_id)
    _, rollover = close_sprint_and_get_rollover(team, data.sprints, data.cards)
    pool = [c for c in data.cards if c.team_id == team_id]
    return team, backfill_sprint(rollover, pool, team.velocity)


def test_alpha_never_pulls_raw_backlog_despite_remaining_capacity(data):
    _, result = _plan_for(data, "team_alpha")
    added_ids = {c.card_id for c in result.added_cards}
    assert added_ids == {"ALPHA-204", "ALPHA-205"}
    assert "ALPHA-206" not in added_ids  # raw backlog, never groomed
    assert result.total_points == 26
    assert result.capacity_unfilled is True
    assert result.remaining_capacity == 6


def test_bravo_exact_velocity_fit(data):
    _, result = _plan_for(data, "team_bravo")
    assert result.total_points == result.velocity == 24
    assert result.capacity_unfilled is False


def test_charlie_sprint_ready_pile_exhausted(data):
    _, result = _plan_for(data, "team_charlie")
    added_ids = {c.card_id for c in result.added_cards}
    assert added_ids == {"CHAR-303"}
    assert "CHAR-304" not in added_ids  # raw backlog, never groomed
    assert result.capacity_unfilled is True
    assert result.remaining_capacity == 5


def test_never_exceeds_velocity(data):
    for team_id in ("team_alpha", "team_bravo", "team_charlie"):
        _, result = _plan_for(data, team_id)
        assert result.total_points <= result.velocity


def test_tie_breaking_first_listed_wins_within_same_priority():
    pool = [
        Card("C-1", "t1", None, "First high", "high", 5, "sprint_ready"),
        Card("C-2", "t1", None, "Second high", "high", 5, "sprint_ready"),
    ]
    result = backfill_sprint(rollover_cards=[], sprint_ready_pool=pool, velocity=5)
    assert [c.card_id for c in result.added_cards] == ["C-1"]


def test_priority_order_high_before_medium_before_low():
    pool = [
        Card("C-1", "t1", None, "Low", "low", 3, "sprint_ready"),
        Card("C-2", "t1", None, "High", "high", 3, "sprint_ready"),
        Card("C-3", "t1", None, "Medium", "medium", 3, "sprint_ready"),
    ]
    result = backfill_sprint(rollover_cards=[], sprint_ready_pool=pool, velocity=9)
    assert [c.card_id for c in result.added_cards] == ["C-2", "C-3", "C-1"]


def test_ungroomed_or_unpointed_cards_never_added():
    pool = [
        Card("C-1", "t1", None, "No points", "high", None, "sprint_ready"),
        Card("C-2", "t1", None, "Wrong status", "high", 5, "backlog"),
    ]
    result = backfill_sprint(rollover_cards=[], sprint_ready_pool=pool, velocity=100)
    assert result.added_cards == []
    assert result.remaining_capacity == 100


def test_rollover_exceeding_velocity_is_flagged_and_blocks_additions():
    rollover = [Card("R-1", "t1", None, "Big rollover", "high", 40, "in_progress")]
    pool = [Card("C-1", "t1", None, "Extra", "high", 1, "sprint_ready")]
    result = backfill_sprint(rollover_cards=rollover, sprint_ready_pool=pool, velocity=20)
    assert result.rollover_exceeds_velocity is True
    assert result.added_cards == []
