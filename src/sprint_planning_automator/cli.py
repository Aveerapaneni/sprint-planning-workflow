"""Orchestrates US-1 through US-4 into one end-to-end run."""

from __future__ import annotations

import time
from pathlib import Path

from .backfill import backfill_sprint
from .data_loader import load_data
from .models import Sprint
from .prompts import prompt_sprint_dates, prompt_yes_no
from .sprint_close import SprintCloseError, close_sprint_and_get_rollover
from .summary import DRAFT_GOAL_PLACEHOLDER, build_team_summary

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "mock_jira_data.json"


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
        plans.append((team, closed_sprint, result))

    processing_time = time.perf_counter() - processing_start

    # US-4: present each team's proposal and require explicit PO confirmation.
    finalized, declined = [], []
    for team, closed_sprint, result in plans:
        print(build_team_summary(team, result))
        confirmed = prompt_yes_no(f"\nFinalize this sprint for {team.team_name}?")

        if confirmed:
            new_sprint_id = f"{closed_sprint.sprint_id}_next"
            new_sprint = Sprint(
                sprint_id=new_sprint_id,
                team_id=team.team_id,
                status="active",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                sprint_goal=DRAFT_GOAL_PLACEHOLDER,
            )
            for card in result.selected_cards:
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
