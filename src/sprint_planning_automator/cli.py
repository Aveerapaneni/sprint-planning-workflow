"""Orchestrates US-1 through US-7 into one end-to-end "new sprint" run, plus
the top-level menu that also offers the US-8 mid-sprint edit mode."""

from __future__ import annotations

import time
from pathlib import Path

from .backfill import backfill_sprint
from .data_loader import DEFAULT_DATA_PATH, load_data
from .goal_generation import GoalGenerationError, generate_sprint_goal, generate_template_goal
from .mid_sprint_edit import run_edit_mode
from .models import Sprint, Team
from .prompts import (
    prompt_card_to_add,
    prompt_card_to_remove,
    prompt_edit_action,
    prompt_new_goal,
    prompt_review_action,
    prompt_sprint_dates,
    prompt_top_level_menu,
)
from .proposal import (
    DRAFT_GOAL_PLACEHOLDER,
    ProposalEditError,
    SprintProposal,
    add_card,
    build_initial_proposal,
    remove_card,
    set_sprint_goal,
)
from .sprint_close import SprintCloseError, close_sprint_and_get_rollover
from .state_store import DEFAULT_STATE_PATH, ActiveSprintState, load_active_sprints, save_active_sprints
from .summary import build_team_summary
from .velocity import VelocityAdjustment, compute_adjusted_velocity


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


def _review_and_confirm(
    team: Team, proposal: SprintProposal, velocity_adjustment: VelocityAdjustment
) -> bool:
    """US-4 + US-5: show the proposal, let the PO edit it, then confirm or decline."""
    while True:
        print(build_team_summary(team, proposal, proposal.sprint_goal, velocity_adjustment))
        action = prompt_review_action()
        if action == "confirm":
            return True
        if action == "decline":
            return False
        _run_edit_loop(proposal)


def run(
    data_path: Path | str = DEFAULT_DATA_PATH,
    state_path: Path | str = DEFAULT_STATE_PATH,
) -> None:
    print("Sprint Planning Automator\n" + "=" * 40)

    # US-1: sprint window for the new sprint (not timed against the NFR budget,
    # since it's PO/PM input, not processing).
    start_date, end_date = prompt_sprint_dates()
    print(f"\nNew sprint window: {start_date.isoformat()} -> {end_date.isoformat()}\n")

    processing_start = time.perf_counter()
    data = load_data(data_path)
    active_states = load_active_sprints(state_path)

    plans = []
    for team in data.teams:
        try:
            closed_sprint, rollover_cards = close_sprint_and_get_rollover(
                team, data.sprints, data.cards
            )
        except SprintCloseError as exc:
            print(f"Skipping {team.team_name}: {exc}")
            continue

        # US-7: adjust velocity for OOO engineers before backfilling.
        velocity_adjustment = compute_adjusted_velocity(
            team.team_id, team.velocity, data.resources, start_date, end_date
        )

        pool = [c for c in data.cards if c.team_id == team.team_id]
        result = backfill_sprint(rollover_cards, pool, velocity_adjustment.adjusted_velocity)
        plans.append((team, closed_sprint, result, pool, velocity_adjustment))

    processing_time = time.perf_counter() - processing_start

    # US-6: generate an AI sprint goal per team, grounded in its selected cards.
    # Timed separately from processing_time -- it's the only step that calls out
    # to the Claude API, and the PRD calls it out as the main token-cost lever.
    ai_start = time.perf_counter()
    total_input_tokens = 0
    total_output_tokens = 0
    draft_goals: dict[str, str] = {}
    for team, closed_sprint, result, pool, velocity_adjustment in plans:
        try:
            gen = generate_sprint_goal(team, result.selected_cards)
            draft_goals[team.team_id] = gen.goal
            total_input_tokens += gen.input_tokens
            total_output_tokens += gen.output_tokens
        except GoalGenerationError as exc:
            fallback_goal = generate_template_goal(result.selected_cards)
            print(f"Could not generate AI sprint goal for {team.team_name}: {exc}")
            print(f"  Falling back to a template-based goal: {fallback_goal}\n")
            draft_goals[team.team_id] = fallback_goal
    ai_generation_time = time.perf_counter() - ai_start

    # US-4 & US-5: present each team's proposal, allow PO edits, require confirmation.
    finalized, declined = [], []
    for team, closed_sprint, result, pool, velocity_adjustment in plans:
        proposal = build_initial_proposal(team, result, pool)
        proposal.sprint_goal = draft_goals.get(team.team_id, DRAFT_GOAL_PLACEHOLDER)
        confirmed = _review_and_confirm(team, proposal, velocity_adjustment)

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

            # US-8: persist this as the team's active sprint so it can be
            # edited mid-cycle in a later run via the "edit" menu option.
            active_states[team.team_id] = ActiveSprintState(
                team_id=team.team_id,
                team_name=team.team_name,
                sprint_id=new_sprint_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                sprint_goal=proposal.sprint_goal,
                baseline_velocity=velocity_adjustment.baseline_velocity,
                adjusted_velocity=velocity_adjustment.adjusted_velocity,
                cards=list(proposal.selected_cards),
            )
            save_active_sprints(active_states, state_path)

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
    print(
        f"AI sprint-goal generation time: {ai_generation_time:.3f}s "
        f"({total_input_tokens} input / {total_output_tokens} output tokens)"
    )


def main() -> None:
    action = prompt_top_level_menu()
    if action == "new":
        run()
    else:
        run_edit_mode()
