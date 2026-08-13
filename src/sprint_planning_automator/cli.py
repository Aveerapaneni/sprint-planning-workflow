"""Orchestrates US-1 through US-5 into one end-to-end run."""

from __future__ import annotations

import time
from pathlib import Path

from .backfill import backfill_sprint
from .data_loader import load_data
from .models import Sprint, Team
from .prompts import (
    prompt_card_to_add,
    prompt_card_to_remove,
    prompt_edit_action,
    prompt_new_goal,
    prompt_review_action,
    prompt_sprint_dates,
)
from .proposal import (
    ProposalEditError,
    SprintProposal,
    add_card,
    build_initial_proposal,
    remove_card,
    set_sprint_goal,
)
from .sprint_close import SprintCloseError, close_sprint_and_get_rollover
from .summary import build_team_summary

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "mock_jira_data.json"


def _run_edit_loop(proposal: SprintProposal) -> None:
    while True:
        action = prompt_edit_action()
        if action == "done":
            return

        try:
            if action == "goal":
                new_goal = prompt_new_goal(proposal.sprint_goal)
                if new_goal is not None:
                    set_sprint_goal(proposal, new_goal)
                    print("  Sprint goal updated.")
            elif action == "add":
                card_id = prompt_card_to_add(proposal.available_cards)
                if card_id is not None:
                    card = add_card(proposal, card_id)
                    print(f"  Added {card.card_id}.")
            elif action == "remove":
                card_id = prompt_card_to_remove(proposal.added_cards)
                if card_id is not None:
                    card = remove_card(proposal, card_id)
                    print(f"  Removed {card.card_id}.")
        except ProposalEditError as exc:
            print(f"  {exc}")


def _review_and_confirm(team: Team, proposal: SprintProposal) -> bool:
    """US-4 + US-5: show the proposal, let the PO edit it, then confirm or decline."""
    while True:
        print(build_team_summary(team, proposal, proposal.sprint_goal))
        action = prompt_review_action()
        if action == "confirm":
            return True
        if action == "decline":
            return False
        _run_edit_loop(proposal)


def run(data_path: Path | str = DEFAULT_DATA_PATH) -> None:
    print("Sprint Planning Automator\n" + "=" * 40)

    # US-1: sprint window for the new sprint (not timed against the NFR budget,
    # since it's PO/PM input, not processing).
    start_date, end_date = prompt_sprint_dates()
    print(f"\nNew sprint window: {start_date.isoformat()} -> {end_date.isoformat()}\n")

    processing_start = time.perf_counter()
    data = load_data(data_path)

    plans = []
    for team in data.teams:
        try:
            closed_sprint, rollover_cards = close_sprint_and_get_rollover(
                team, data.sprints, data.cards
            )
        except SprintCloseError as exc:
            print(f"Skipping {team.team_name}: {exc}")
            continue

        pool = [c for c in data.cards if c.team_id == team.team_id]
        result = backfill_sprint(rollover_cards, pool, team.velocity)
        plans.append((team, closed_sprint, result, pool))

    processing_time = time.perf_counter() - processing_start

    # US-4 & US-5: present each team's proposal, allow PO edits, require confirmation.
    finalized, declined = [], []
    for team, closed_sprint, result, pool in plans:
        proposal = build_initial_proposal(team, result, pool)
        confirmed = _review_and_confirm(team, proposal)

        if confirmed:
            new_sprint_id = f"{closed_sprint.sprint_id}_next"
            new_sprint = Sprint(
                sprint_id=new_sprint_id,
                team_id=team.team_id,
                status="active",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                sprint_goal=proposal.sprint_goal,
            )
            for card in proposal.selected_cards:
                card.sprint_id = new_sprint_id
            data.sprints.append(new_sprint)
            finalized.append(team.team_name)
            print(f"-> {team.team_name}: sprint finalized as {new_sprint_id}.\n")
        else:
            declined.append(team.team_name)
            print(
                f"-> {team.team_name}: PO declined. Program Manager notified; "
                f"new sprint not finalized for this team.\n"
            )

    print("=" * 40)
    print(f"Finalized: {finalized or 'none'}")
    print(f"Declined:  {declined or 'none'}")
    print(f"Processing time (excluding PO input): {processing_time:.3f}s")


def main() -> None:
    run()
