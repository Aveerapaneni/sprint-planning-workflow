import pytest

from sprint_planning_automator.models import Card, Team
from sprint_planning_automator.proposal import (
    DRAFT_GOAL_PLACEHOLDER,
    ProposalEditError,
    SprintProposal,
    add_card,
    remove_card,
    set_sprint_goal,
)


@pytest.fixture
def proposal():
    team = Team("t1", "Team Test", 20, "Jamie PO")
    rollover = [Card("R-1", "t1", None, "Rollover", "high", 8, "in_progress")]
    added = [Card("C-1", "t1", None, "Added", "high", 5, "sprint_ready")]
    skipped = [Card("C-2", "t1", None, "Skipped", "medium", 10, "sprint_ready")]
    return SprintProposal(
        team=team,
        rollover_cards=rollover,
        eligible_pool=added + skipped,
        added_cards=list(added),
        velocity=20,
    )


def test_default_goal_is_placeholder(proposal):
    assert proposal.sprint_goal == DRAFT_GOAL_PLACEHOLDER


def test_available_cards_excludes_added(proposal):
    assert [c.card_id for c in proposal.available_cards] == ["C-2"]


def test_totals_reflect_rollover_and_added(proposal):
    assert proposal.rollover_points == 8
    assert proposal.added_points == 5
    assert proposal.total_points == 13
    assert proposal.remaining_capacity == 7


def test_remove_card_moves_it_back_to_available(proposal):
    removed = remove_card(proposal, "C-1")
    assert removed.card_id == "C-1"
    assert proposal.added_cards == []
    assert {c.card_id for c in proposal.available_cards} == {"C-1", "C-2"}
    assert proposal.total_points == 8


def test_add_card_moves_it_out_of_available(proposal):
    added = add_card(proposal, "C-2")
    assert added.card_id == "C-2"
    assert {c.card_id for c in proposal.added_cards} == {"C-1", "C-2"}
    assert proposal.available_cards == []
    assert proposal.total_points == 23


def test_add_card_can_push_over_velocity(proposal):
    add_card(proposal, "C-2")  # 8 + 5 + 10 = 23 > velocity 20
    assert proposal.total_points == 23
    assert proposal.over_velocity is True


def test_remove_unknown_card_raises(proposal):
    with pytest.raises(ProposalEditError):
        remove_card(proposal, "NOT-A-CARD")


def test_add_unknown_card_raises(proposal):
    with pytest.raises(ProposalEditError):
        add_card(proposal, "NOT-A-CARD")


def test_add_already_added_card_raises(proposal):
    with pytest.raises(ProposalEditError):
        add_card(proposal, "C-1")


def test_set_sprint_goal_updates_text(proposal):
    set_sprint_goal(proposal, "Ship the new onboarding flow")
    assert proposal.sprint_goal == "Ship the new onboarding flow"


def test_set_sprint_goal_rejects_blank(proposal):
    with pytest.raises(ProposalEditError):
        set_sprint_goal(proposal, "   ")
    assert proposal.sprint_goal == DRAFT_GOAL_PLACEHOLDER  # unchanged
