"""US-5: let the PO re-prioritize cards or edit the sprint goal before confirming."""

from __future__ import annotations

from dataclasses import dataclass, field

from .backfill import BackfillResult
from .models import PRIORITY_ORDER, Card, Team

DRAFT_GOAL_PLACEHOLDER = (
    "[Draft goal placeholder — AI-generated sprint goal is not yet implemented (US-6)]"
)


@dataclass
class SprintProposal:
    """A mutable, PO-editable sprint proposal seeded from a BackfillResult.

    rollover_cards are fixed (they represent mandatory carryover work, not a
    Sprint Ready pick). added_cards and sprint_goal can be edited by the PO
    before final confirmation; eligible_pool is the full set of Sprint Ready
    cards this team could draw from.
    """

    team: Team
    rollover_cards: list[Card]
    eligible_pool: list[Card]
    added_cards: list[Card]
    velocity: int
    sprint_goal: str = field(default=DRAFT_GOAL_PLACEHOLDER)

    @property
    def available_cards(self) -> list[Card]:
        added_ids = {c.card_id for c in self.added_cards}
        return [c for c in self.eligible_pool if c.card_id not in added_ids]

    @property
    def selected_cards(self) -> list[Card]:
        return self.rollover_cards + self.added_cards

    @property
    def rollover_points(self) -> int:
        return sum(c.story_points or 0 for c in self.rollover_cards)

    @property
    def added_points(self) -> int:
        return sum(c.story_points or 0 for c in self.added_cards)

    @property
    def total_points(self) -> int:
        return self.rollover_points + self.added_points

    @property
    def remaining_capacity(self) -> int:
        return max(self.velocity - self.total_points, 0)

    @property
    def rollover_exceeds_velocity(self) -> bool:
        return self.rollover_points > self.velocity

    @property
    def over_velocity(self) -> bool:
        """True when PO edits have pushed the total past velocity (beyond
        whatever rollover alone already accounts for)."""
        return self.total_points > self.velocity and not self.rollover_exceeds_velocity

    @property
    def capacity_unfilled(self) -> bool:
        return self.remaining_capacity > 0 and not self.rollover_exceeds_velocity


def build_initial_proposal(
    team: Team, backfill_result: BackfillResult, sprint_ready_pool: list[Card]
) -> SprintProposal:
    """Seed a PO-editable proposal from a BackfillResult's initial recommendation."""
    eligible_pool = sorted(
        (c for c in sprint_ready_pool if c.is_sprint_ready),
        key=lambda c: PRIORITY_ORDER[c.priority],
    )
    return SprintProposal(
        team=team,
        rollover_cards=backfill_result.rollover_cards,
        eligible_pool=eligible_pool,
        added_cards=list(backfill_result.added_cards),
        velocity=backfill_result.velocity,
    )


class ProposalEditError(Exception):
    """Raised when an add/remove card_id is invalid for this proposal."""


def add_card(proposal: SprintProposal, card_id: str) -> Card:
    for card in proposal.available_cards:
        if card.card_id == card_id:
            proposal.added_cards.append(card)
            return card
    raise ProposalEditError(
        f"{card_id!r} is not an available Sprint Ready card for {proposal.team.team_name}."
    )


def remove_card(proposal: SprintProposal, card_id: str) -> Card:
    for card in proposal.added_cards:
        if card.card_id == card_id:
            proposal.added_cards.remove(card)
            return card
    raise ProposalEditError(
        f"{card_id!r} is not currently in the proposed sprint for {proposal.team.team_name}."
    )


def set_sprint_goal(proposal: SprintProposal, new_goal: str) -> None:
    new_goal = new_goal.strip()
    if not new_goal:
        raise ProposalEditError("Sprint goal cannot be blank.")
    proposal.sprint_goal = new_goal
