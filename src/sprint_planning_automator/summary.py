"""US-4: build the per-team confirmation summary shown to the Product Owner."""

from __future__ import annotations

from .backfill import BackfillResult
from .models import Card, Team

DRAFT_GOAL_PLACEHOLDER = (
    "[Draft goal placeholder — AI-generated sprint goal is not yet implemented (US-6)]"
)


def _format_card(card: Card, tag: str) -> str:
    return f"  [{tag:8}] {card.card_id:10} ({card.priority:6}, {card.story_points} pts)  {card.title}"


def build_team_summary(
    team: Team, result: BackfillResult, draft_sprint_goal: str = DRAFT_GOAL_PLACEHOLDER
) -> str:
    lines = [
        f"=== {team.team_name} — Proposed New Sprint ===",
        f"Product Owner: {team.product_owner}",
        f"Sprint Goal (draft): {draft_sprint_goal}",
        "",
        f"Rollover cards ({len(result.rollover_cards)}, {result.rollover_points} pts):",
    ]
    if result.rollover_cards:
        lines += [_format_card(c, "ROLLOVER") for c in result.rollover_cards]
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append(f"Newly added cards ({len(result.added_cards)}, {result.added_points} pts):")
    if result.added_cards:
        lines += [_format_card(c, "ADDED") for c in result.added_cards]
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append(f"Total points: {result.total_points} / Velocity: {result.velocity}")

    if result.rollover_exceeds_velocity:
        lines.append(
            "WARNING: rollover cards alone exceed team velocity — "
            "no Sprint Ready cards could be added this cycle."
        )
    if result.capacity_unfilled:
        lines.append(
            f"NOTE: Sprint Ready pile did not have enough groomed cards to fill "
            f"remaining capacity ({result.remaining_capacity} pts unfilled)."
        )

    return "\n".join(lines)
