# Sprint Planning Automator

A CLI tool that automates the mechanical parts of sprint planning across
multiple teams — closing the old sprint, flagging rollover work, backfilling
the new sprint from a groomed backlog up to team velocity, and getting
explicit Product Owner sign-off — using a mock JIRA dataset instead of a real
integration.

Full requirements: [`sprint-automator-PRD.md`](sprint-automator-PRD.md).

## Status

This build covers **User Stories 1–4** of the PRD's 8. AI-generated sprint
goals (US-6), OOO-adjusted velocity (US-7), PO re-prioritization before
confirmation (US-5), and post-finalization edits (US-8) are not implemented
yet — the sprint goal shown in the confirmation summary is a labeled
placeholder, and velocity shown is each team's baseline velocity.

| Story | Description | Status |
|---|---|---|
| US-1 | PM provides sprint start/end date, validated | Done |
| US-2 | Old sprint closed per team; incomplete cards tagged rollover | Done |
| US-3 | New sprint backfilled from Sprint Ready pile by priority, up to velocity | Done |
| US-4 | Per-team summary + explicit PO yes/no confirmation | Done |
| US-5–8 | PO re-prioritization, AI sprint goal, OOO velocity adjustment, mid-sprint edits | Not yet built |

## How it works

1. **Load** `data/mock_jira_data.json` — 3 teams, their active sprints, and a
   card pool per team.
2. **Close** each team's active sprint; any card not `status: "done"` in that
   sprint is tagged `is_rollover` and carried into the new sprint.
3. **Backfill** the new sprint from that team's **Sprint Ready** cards only
   (never raw, ungroomed `Backlog` cards), ordered high → medium → low
   priority, stopping once velocity is reached. Ties within the same
   priority go to whichever card is listed first. Cards missing a priority
   or point estimate are never selected, regardless of status.
4. **Summarize & confirm** — prints each team's proposed cards, draft goal,
   and points-vs-velocity, then requires an explicit `y`/`n` from the PO
   before that team's sprint is finalized. A "no" halts finalization for
   that team only; the run continues for the others.

Edge cases handled without crashing (PRD Section 7):
- Sprint Ready pile too small to fill velocity → reported as unfilled
  capacity, not an error.
- Rollover alone exceeds velocity → flagged explicitly; no Sprint Ready
  cards are added that cycle.
- A team with no active sprint to close → that team is skipped with a
  message instead of stopping the whole run.

## Project structure

```
sprint-planning-automator/
├── main.py                        # entry point: python main.py
├── conftest.py                    # lets tests import the src/ package
├── data/
│   └── mock_jira_data.json
├── src/sprint_planning_automator/
│   ├── models.py                  # Team, Card, Sprint dataclasses
│   ├── data_loader.py             # load + validate the JSON dataset
│   ├── sprint_close.py            # US-2
│   ├── backfill.py                # US-3
│   ├── summary.py                 # US-4 (summary text)
│   ├── prompts.py                 # US-1 & US-4 (terminal I/O)
│   └── cli.py                     # orchestrates the end-to-end run
└── tests/
    ├── test_data_loader.py
    ├── test_sprint_close.py
    ├── test_backfill.py
    ├── test_summary.py
    └── test_cli.py                # end-to-end smoke tests
```

## Running it

Requires Python 3.9+, standard library only.

```bash
python3 main.py
```

You'll be prompted for the new sprint's start/end dates, then shown each
team's proposed sprint one at a time with a `y`/`n` confirmation.

## Running the tests

```bash
python3 -m pip install pytest
python3 -m pytest -q
```

28 tests cover data validation, rollover tagging, backfill priority/tie-break/
edge-case logic, summary content, and a full end-to-end CLI run (including
input re-prompting on bad dates).

## Performance

The PRD's non-functional requirement is a full 3-team sprint transition in
under 10 seconds of processing time, excluding time spent waiting on PO
input. Measured on this dataset: **~0.002s** for load + close + backfill
across all 3 teams (printed at the end of each run as `Processing time
(excluding PO input)`).

## Token / cost efficiency

No Claude API calls are made in this build — sprint-goal generation (US-6) is
the only step in the PRD that calls out to an LLM, and it isn't implemented
yet. Token usage for this phase is therefore 0; a real measurement will be
added here once US-6 is built, per the PRD's requirement to report it as a
measured result rather than a claim.
