"""US-2: close the old active sprint per team and tag rollover cards."""

from __future__ import annotations

from .models import Card, Sprint, Team


class SprintCloseError(Exception):
    """Raised when a team has no active sprint to close."""


def find_active_sprint(sprints: list[Sprint], team_id: str) -> Sprint | None:
    for s in sprints:
        if s.team_id == team_id and s.status == "active":
            return s
    return None


def close_sprint_and_get_rollover(
    team: Team, sprints: list[Sprint], cards: list[Card]
) -> tuple[Sprint, list[Card]]:
    """Close the team's active sprint and tag its incomplete cards as rollover.

    Returns the now-closed sprint and the list of rollover cards.
    Raises SprintCloseError if the team has no active sprint.
    """
    active = find_active_sprint(sprints, team.team_id)
    if active is None:
        raise SprintCloseError(
            f"Team {team.team_name!r} has no active sprint to close."
        )

    active.status = "closed"

    rollover = [
        c for c in cards if c.sprint_id == active.sprint_id and not c.is_done
    ]
    for c in rollover:
        c.is_rollover = True

    return active, rollover
