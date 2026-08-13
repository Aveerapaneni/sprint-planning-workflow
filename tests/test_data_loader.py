from pathlib import Path

import pytest

from sprint_planning_automator.data_loader import DataValidationError, load_data

MOCK_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_jira_data.json"


def test_loads_all_teams_sprints_and_cards():
    data = load_data(MOCK_DATA_PATH)
    assert len(data.teams) == 3
    assert len(data.sprints) == 3
    assert len(data.cards) == 15


def test_team_ids_are_expected():
    data = load_data(MOCK_DATA_PATH)
    team_ids = {t.team_id for t in data.teams}
    assert team_ids == {"team_alpha", "team_bravo", "team_charlie"}


def test_sprint_ready_cards_present_after_data_edit():
    data = load_data(MOCK_DATA_PATH)
    sprint_ready_ids = {c.card_id for c in data.cards if c.status == "sprint_ready"}
    assert sprint_ready_ids == {
        "ALPHA-204",
        "ALPHA-205",
        "BRAVO-104",
        "BRAVO-105",
        "CHAR-303",
    }


def test_raw_backlog_cards_remain_ungroomed():
    data = load_data(MOCK_DATA_PATH)
    backlog_ids = {c.card_id for c in data.cards if c.status == "backlog"}
    assert backlog_ids == {"ALPHA-206", "CHAR-304"}


def test_rejects_card_with_unknown_team_id(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(
        """
        {
          "teams": [{"team_id": "team_alpha", "team_name": "A", "velocity": 10, "product_owner": "X"}],
          "sprints": [],
          "cards": [{"card_id": "C-1", "team_id": "team_unknown", "sprint_id": null,
                      "title": "t", "priority": "high", "story_points": 1, "status": "backlog"}]
        }
        """
    )
    with pytest.raises(DataValidationError):
        load_data(bad_file)


def test_rejects_empty_teams(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text('{"teams": [], "sprints": [], "cards": []}')
    with pytest.raises(DataValidationError):
        load_data(bad_file)
