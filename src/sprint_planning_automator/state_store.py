"""US-8: persist finalized (active) sprints so cards can be edited mid-cycle.

Kept separate from mock_jira_data.json so that file stays a stable, reusable
fixture (and test data source) while active-sprint state accumulates across
separate runs of the tool.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .models import Card

DEFAULT_STATE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "active_sprints_state.json"
)


class MidSprintEditError(Exception):
    """Raised when a mid-sprint add/remove request is invalid."""


@dataclass
class ChangeLogEntry:
    timestamp: str
    action: str  # "add" | "remove"
    card_id: str
    reason: str


@dataclass
class ActiveSprintState:
    team_id: str
    team_name: str
    sprint_id: str
    start_date: str
    end_date: str
    sprint_goal: str
    baseline_velocity: int
    adjusted_velocity: int
    cards: list[Card]
    change_log: list[ChangeLogEntry] = field(default_factory=list)

    @property
    def total_points(self) -> int:
        return sum(c.story_points or 0 for c in self.cards)


def load_active_sprints(path: str | Path = DEFAULT_STATE_PATH) -> dict[str, ActiveSprintState]:
    p = Path(path)
    if not p.exists():
        return {}

    raw = json.loads(p.read_text())
    states: dict[str, ActiveSprintState] = {}
    for team_id, entry in raw.items():
        states[team_id] = ActiveSprintState(
            team_id=entry["team_id"],
            team_name=entry["team_name"],
            sprint_id=entry["sprint_id"],
            start_date=entry["start_date"],
            end_date=entry["end_date"],
            sprint_goal=entry["sprint_goal"],
            baseline_velocity=entry["baseline_velocity"],
            adjusted_velocity=entry["adjusted_velocity"],
            cards=[Card(**c) for c in entry["cards"]],
            change_log=[ChangeLogEntry(**e) for e in entry.get("change_log", [])],
        )
    return states


def save_active_sprints(
    states: dict[str, ActiveSprintState], path: str | Path = DEFAULT_STATE_PATH
) -> None:
    raw = {
        team_id: {
            "team_id": s.team_id,
            "team_name": s.team_name,
            "sprint_id": s.sprint_id,
            "start_date": s.start_date,
            "end_date": s.end_date,
            "sprint_goal": s.sprint_goal,
            "baseline_velocity": s.baseline_velocity,
            "adjusted_velocity": s.adjusted_velocity,
            "cards": [asdict(c) for c in s.cards],
            "change_log": [asdict(e) for e in s.change_log],
        }
        for team_id, s in states.items()
    }
    Path(path).write_text(json.dumps(raw, indent=2) + "\n")


def remove_card(state: ActiveSprintState, card_id: str, reason: str) -> Card:
    reason = reason.strip()
    if not reason:
        raise MidSprintEditError("A reason is required to remove a card.")

    for card in state.cards:
        if card.card_id == card_id:
            state.cards.remove(card)
            state.change_log.append(
                ChangeLogEntry(
                    timestamp=datetime.now().isoformat(timespec="seconds"),
                    action="remove",
                    card_id=card_id,
                    reason=reason,
                )
            )
            return card

    raise MidSprintEditError(f"{card_id!r} is not in this active sprint.")


def add_card(state: ActiveSprintState, card: Card, reason: str) -> None:
    reason = reason.strip()
    if not reason:
        raise MidSprintEditError("A reason is required to add a card.")
    if any(c.card_id == card.card_id for c in state.cards):
        raise MidSprintEditError(f"{card.card_id!r} is already in this active sprint.")

    state.cards.append(card)
    state.change_log.append(
        ChangeLogEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            action="add",
            card_id=card.card_id,
            reason=reason,
        )
    )
