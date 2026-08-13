"""Load and validate the mock JIRA dataset into model objects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import Card, Sprint, Team
from .velocity import Resource

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "mock_jira_data.json"


class DataValidationError(Exception):
    """Raised when the mock dataset is missing required fields or references."""


@dataclass
class JiraData:
    teams: list[Team]
    sprints: list[Sprint]
    cards: list[Card]
    resources: list[Resource]


def load_data(path: str | Path) -> JiraData:
    raw = json.loads(Path(path).read_text())

    teams = [Team(**t) for t in raw.get("teams", [])]
    sprints = [Sprint(**s) for s in raw.get("sprints", [])]
    cards = [Card(**c) for c in raw.get("cards", [])]
    resources = [Resource(**r) for r in raw.get("resources", [])]

    _validate(teams, sprints, cards, resources)

    return JiraData(teams=teams, sprints=sprints, cards=cards, resources=resources)


def _validate(
    teams: list[Team], sprints: list[Sprint], cards: list[Card], resources: list[Resource]
) -> None:
    if not teams:
        raise DataValidationError("No teams found in dataset.")

    team_ids = {t.team_id for t in teams}

    for s in sprints:
        if s.team_id not in team_ids:
            raise DataValidationError(
                f"Sprint {s.sprint_id!r} references unknown team_id {s.team_id!r}."
            )

    sprint_ids = {s.sprint_id for s in sprints}

    for c in cards:
        if c.team_id not in team_ids:
            raise DataValidationError(
                f"Card {c.card_id!r} references unknown team_id {c.team_id!r}."
            )
        if c.sprint_id is not None and c.sprint_id not in sprint_ids:
            raise DataValidationError(
                f"Card {c.card_id!r} references unknown sprint_id {c.sprint_id!r}."
            )

    for r in resources:
        if r.team_id not in team_ids:
            raise DataValidationError(
                f"Resource {r.engineer_name!r} references unknown team_id {r.team_id!r}."
            )
