"""US-8: PO edits an already-finalized (active) sprint's cards mid-cycle."""

from __future__ import annotations

from pathlib import Path

from .data_loader import DEFAULT_DATA_PATH, load_data
from .models import PRIORITY_ORDER, Card
from .prompts import (
    prompt_card_to_add,
    prompt_card_to_remove,
    prompt_edit_reason,
    prompt_mid_sprint_edit_action,
    prompt_team_choice,
    prompt_yes_no,
)
from .state_store import (
    DEFAULT_STATE_PATH,
    ActiveSprintState,
    MidSprintEditError,
    add_card,
    load_active_sprints,
    remove_card,
    save_active_sprints,
)


def _available_cards_for_team(state: ActiveSprintState, all_cards: list[Card]) -> list[Card]:
    committed_ids = {c.card_id for c in state.cards}
    eligible = [
        c
        for c in all_cards
        if c.team_id == state.team_id and c.is_sprint_ready and c.card_id not in committed_ids
    ]
    return sorted(eligible, key=lambda c: PRIORITY_ORDER[c.priority])


def _print_active_sprint_summary(state: ActiveSprintState) -> None:
    print(f"\n=== {state.team_name} — Active Sprint {state.sprint_id} ===")
    print(f"Sprint Goal: {state.sprint_goal}")
    print(f"Window: {state.start_date} -> {state.end_date}")
    print(f"Velocity: {state.baseline_velocity} baseline / {state.adjusted_velocity} adjusted")

    print(f"Committed cards ({len(state.cards)}, {state.total_points} pts):")
    if state.cards:
        for c in state.cards:
            tag = "ROLLOVER" if c.is_rollover else "ADDED"
            print(f"  [{tag:8}] {c.card_id:10} ({c.priority:6}, {c.story_points} pts)  {c.title}")
    else:
        print("  (none)")

    print(f"Total points: {state.total_points} / Adjusted velocity: {state.adjusted_velocity}")

    if state.change_log:
        print(f"Change log ({len(state.change_log)} entries):")
        for e in state.change_log:
            print(f"  [{e.timestamp}] {e.action.upper():6} {e.card_id} — {e.reason}")


def _edit_one_team(state: ActiveSprintState, all_cards: list[Card]) -> None:
    while True:
        _print_active_sprint_summary(state)
        action = prompt_mid_sprint_edit_action()
        if action == "done":
            return

        try:
            if action == "add":
                available = _available_cards_for_team(state, all_cards)
                card_id = prompt_card_to_add(available)
                if card_id is None:
                    continue
                reason = prompt_edit_reason("add", card_id)
                if reason is None:
                    print("  Cancelled: a reason is required.")
                    continue
                card = next(c for c in available if c.card_id == card_id)
                add_card(state, card, reason)
                print(f"  Added {card_id}.")
            elif action == "remove":
                card_id = prompt_card_to_remove(state.cards)
                if card_id is None:
                    continue
                reason = prompt_edit_reason("remove", card_id)
                if reason is None:
                    print("  Cancelled: a reason is required.")
                    continue
                remove_card(state, card_id, reason)
                print(f"  Removed {card_id}.")
        except MidSprintEditError as exc:
            print(f"  {exc}")


def run_edit_mode(
    data_path: Path | str = DEFAULT_DATA_PATH,
    state_path: Path | str = DEFAULT_STATE_PATH,
) -> None:
    states = load_active_sprints(state_path)
    if not states:
        print("No active sprints found. Start a new sprint cycle first.")
        return

    data = load_data(data_path)

    while True:
        team_ids = list(states.keys())
        team_names = [states[tid].team_name for tid in team_ids]
        choice = prompt_team_choice(team_names)
        if choice is None:
            break

        team_id = team_ids[choice]
        _edit_one_team(states[team_id], data.cards)
        save_active_sprints(states, state_path)
        print(f"Changes saved for {states[team_id].team_name}.\n")

        if not prompt_yes_no("Edit another team's active sprint?"):
            break
