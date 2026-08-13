from sprint_planning_automator.backfill import backfill_sprint
from sprint_planning_automator.models import Card, Team
from sprint_planning_automator.summary import build_team_summary


def test_summary_includes_team_and_card_details():
    team = Team("t1", "Team Test", 20, "Jamie PO")
    rollover = [Card("R-1", "t1", None, "Rollover card", "high", 8, "in_progress")]
    pool = [Card("C-1", "t1", None, "Added card", "high", 5, "sprint_ready")]
    result = backfill_sprint(rollover, pool, team.velocity)

    text = build_team_summary(team, result)

    assert "Team Test" in text
    assert "Jamie PO" in text
    assert "R-1" in text and "Rollover card" in text
    assert "C-1" in text and "Added card" in text
    assert "Total points: 13 / Velocity: 20" in text


def test_summary_flags_capacity_unfilled():
    team = Team("t1", "Team Test", 100, "Jamie PO")
    result = backfill_sprint(rollover_cards=[], sprint_ready_pool=[], velocity=team.velocity)
    text = build_team_summary(team, result)
    assert "NOTE:" in text


def test_summary_flags_rollover_exceeding_velocity():
    team = Team("t1", "Team Test", 5, "Jamie PO")
    rollover = [Card("R-1", "t1", None, "Too big", "high", 40, "in_progress")]
    result = backfill_sprint(rollover, [], team.velocity)
    text = build_team_summary(team, result)
    assert "WARNING:" in text
