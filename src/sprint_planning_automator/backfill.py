"""US-3: backfill the new sprint from the Sprint Ready pile, up to team velocity."""

from __future__ import annotations

from dataclasses import dataclass

from .models import PRIORITY_ORDER, Card


@dataclass
class BackfillResult:
    rollover_cards: list[Card]
    added_cards: list[Card]
    skipped_cards: list[Card]  # eligible Sprint Ready cards that didn't fit
    velocity: int
    rollover_points: int
    added_points: int
    remaining_capacity: int
    rollover_exceeds_velocity: bool
    capacity_unfilled: bool  # True if Sprint Ready pile ran out before reaching velocity

    @property
    def selected_cards(self) -> list[Card]:
        return self.rollover_cards + self.added_cards

    @property
    def total_points(self) -> int:
        return self.rollover_points + self.added_points


def backfill_sprint(
    rollover_cards: list[Card], sprint_ready_pool: list[Card], velocity: int
) -> BackfillResult:
    """Select Sprint Ready cards by priority (high -> medium -> low) until velocity
    is reached. Ties within a priority are broken by the card's original order in
    sprint_ready_pool (first listed wins). Ungroomed/unpointed cards are never
    considered, regardless of status.
    """
    rollover_points = sum(c.story_points or 0 for c in rollover_cards)
    rollover_exceeds_velocity = rollover_points > velocity

    eligible = [c for c in sprint_ready_pool if c.is_sprint_ready]
    eligible = sorted(eligible, key=lambda c: PRIORITY_ORDER[c.priority])

    added: list[Card] = []
    skipped: list[Card] = []
    running_total = rollover_points

    for card in eligible:
        fits = not rollover_exceeds_velocity and running_total + card.story_points <= velocity
        if fits:
            added.append(card)
            running_total += card.story_points
        else:
            skipped.append(card)

    remaining_capacity = max(velocity - running_total, 0)
    capacity_unfilled = remaining_capacity > 0 and not rollover_exceeds_velocity

    return BackfillResult(
        rollover_cards=rollover_cards,
        added_cards=added,
        skipped_cards=skipped,
        velocity=velocity,
        rollover_points=rollover_points,
        added_points=running_total - rollover_points,
        remaining_capacity=remaining_capacity,
        rollover_exceeds_velocity=rollover_exceeds_velocity,
        capacity_unfilled=capacity_unfilled,
    )
