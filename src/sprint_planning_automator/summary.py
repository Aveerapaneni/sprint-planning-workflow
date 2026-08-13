"""US-4: build the per-team confirmation summary shown to the Product Owner."""

from __future__ import annotations

from .backfill import BackfillResult
from .models import Card, Team
from .proposal import DRAFT_GOAL_PLACEHOLDER
from .velocity import VelocityAdjustment


def _format_card(card: Card, tag: str) -> str:
    return f"  [{tag:8}] {card.card_id:10} ({card.priority:6}, {card.story_points} pts)  {card.title}"


def _format_velocity_line(va: VelocityAdjustment) -> str:
    if va.data_missing:
        return (
            f"Velocity: {va.baseline_velocity} (baseline) — resource/OOO data missing "
            f"for this team; using full baseline velocity, flagged for follow-up."
        )
    if va.ooo_engineers:
        names = ", ".join(va.ooo_engineers)
        return (
            f"Velocity: {va.baseline_velocity} baseline -> {va.adjusted_velocity} adjusted "
            f"({len(va.ooo_engineers)} of {va.total_engineers} engineers OOO: {names})"
        )
    return f"Velocity: {va.baseline_velocity} (no engineers OOO this sprint window)"


def build_team_summary(
    team: Team,
    result: BackfillResult,
    draft_sprint_goal: str = DRAFT_GOAL_PLACEHOLDER,
    velocity_adjustment: VelocityAdjustment | None = None,
) -> str:
    lines = [
        f"=== {team.team_name} — Proposed New Sprint ===",
        f"Product Owner: {team.product_owner}",
    ]
    if velocity_adjustment is not None:
        lines.append(_format_velocity_line(velocity_adjustment))
    lines += [
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
    elif getattr(result, "over_velocity", False):
        lines.append(
            "WARNING: manual edits have pushed this proposal over team velocity — "
            "review before confirming."
        )
    if result.capacity_unfilled:
        lines.append(
            f"NOTE: Sprint Ready pile did not have enough groomed cards to fill "
            f"remaining capacity ({result.remaining_capacity} pts unfilled)."
        )

    return "\n".join(lines)
