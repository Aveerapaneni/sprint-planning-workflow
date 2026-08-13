"""Data models for teams, cards, and sprints."""

from dataclasses import dataclass, field
from typing import Optional

# Lower value = higher priority. Used for sorting the Sprint Ready pile.
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Card statuses that count as complete when a sprint is closed.
DONE_STATUS = "done"

# Statuses eligible to be pulled into a new sprint during backfill.
SPRINT_READY_STATUS = "sprint_ready"


@dataclass
class Team:
    team_id: str
    team_name: str
    velocity: int
    product_owner: str


@dataclass
class Sprint:
    sprint_id: str
    team_id: str
    status: str  # "active" | "closed"
    start_date: str
    end_date: str
    sprint_goal: str


@dataclass
class Card:
    card_id: str
    team_id: str
    sprint_id: Optional[str]
    title: str
    priority: str  # "high" | "medium" | "low"
    story_points: Optional[int]
    status: str  # "done" | "in_progress" | "backlog" | "sprint_ready"
    is_rollover: bool = field(default=False)

    @property
    def is_done(self) -> bool:
        return self.status == DONE_STATUS

    @property
    def is_sprint_ready(self) -> bool:
        return (
            self.status == SPRINT_READY_STATUS
            and self.priority in PRIORITY_ORDER
            and self.story_points is not None
        )
