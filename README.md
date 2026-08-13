# Sprint Planning Automator

Automating the Sprint Planning ceremony for PO and Program Manager review, without a formal team meeting.

A CLI tool that automates the mechanical parts of sprint planning across
multiple teams — closing the old sprint, flagging rollover work, backfilling
the new sprint from a groomed backlog up to team velocity, and getting
explicit Product Owner sign-off — using a mock JIRA dataset instead of a real
integration.

Full requirements: [`sprint-automator-PRD.md`](sprint-automator-PRD.md).

## Status

This build covers **User Stories 1–5** of the PRD's 8. AI-generated sprint
goals (US-6), OOO-adjusted velocity (US-7), and post-finalization edits
(US-8) are not implemented yet — the sprint goal shown in the confirmation
summary starts as a labeled placeholder (editable by the PO per US-5), and
velocity shown is each team's baseline velocity.

| Story | Description | Status |
|---|---|---|
| US-1 | PM provides sprint start/end date, validated | Done |
| US-2 | Old sprint closed per team; incomplete cards tagged rollover | Done |
| US-3 | New sprint backfilled from Sprint Ready pile by priority, up to velocity | Done |
| US-4 | Per-team summary + explicit PO yes/no confirmation | Done |
| US-5 | PO can add/remove Sprint Ready cards and edit the draft goal before confirming | Done |
| US-6–8 | AI sprint goal, OOO velocity adjustment, mid-sprint edits | Not yet built |

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
4. **Summarize & review** — prints each team's proposed cards, draft goal,
   and points-vs-velocity. The PO can `[c]`onfirm as-is, `[e]`dit — add or
   remove Sprint Ready cards, or rewrite the draft goal, with the summary
   re-shown after every edit — or `[n]` decline. A decline halts
   finalization for that team only; the run continues for the others.
   Manual edits that push a team over velocity are flagged, not blocked —
   the PO retains final judgment.

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
│   ├── backfill.py                # US-3 (initial recommendation)
│   ├── proposal.py                # US-5 (PO-editable proposal: add/remove/goal)
│   ├── summary.py                 # US-4 (summary text)
│   ├── prompts.py                 # US-1, US-4 & US-5 (terminal I/O)
│   └── cli.py                     # orchestrates the end-to-end run
└── tests/
    ├── test_data_loader.py
    ├── test_sprint_close.py
    ├── test_backfill.py
    ├── test_proposal.py
    ├── test_summary.py
    └── test_cli.py                # end-to-end smoke tests
```

## Running it

Requires Python 3.9+, standard library only.

```bash
python3 main.py
```

You'll be prompted for the new sprint's start/end dates, then shown each
team's proposed sprint one at a time with a confirm / edit / decline menu.

## Running the tests

```bash
python3 -m pip install pytest
python3 -m pytest -q
```

41 tests cover data validation, rollover tagging, backfill priority/tie-break/
edge-case logic, proposal add/remove/goal editing, summary content, and full
end-to-end CLI runs (including input re-prompting on bad dates and the PO
edit-then-confirm flow).

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
