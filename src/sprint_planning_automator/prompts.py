"""US-1, US-4 & US-5: interactive terminal input for sprint dates, PO review/edit,
and PO confirmation."""

from __future__ import annotations

from datetime import date, datetime

from .models import Card

DATE_FORMAT = "%Y-%m-%d"


def _parse_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw.strip(), DATE_FORMAT).date()
    except ValueError:
        return None


def prompt_sprint_dates() -> tuple[date, date]:
    """Prompt for a sprint start/end date, re-prompting until end date is after
    start date and both are valid YYYY-MM-DD dates."""
    while True:
        start_raw = input("Enter new sprint start date (YYYY-MM-DD): ")
        start = _parse_date(start_raw)
        if start is None:
            print(f"  Could not parse {start_raw!r} as a date. Use format YYYY-MM-DD.")
            continue

        end_raw = input("Enter new sprint end date (YYYY-MM-DD): ")
        end = _parse_date(end_raw)
        if end is None:
            print(f"  Could not parse {end_raw!r} as a date. Use format YYYY-MM-DD.")
            continue

        if end <= start:
            print("  End date must be after start date. Please re-enter both dates.")
            continue

        return start, end


def prompt_yes_no(question: str) -> bool:
    """Prompt until the user answers y/yes or n/no (case-insensitive)."""
    while True:
        raw = input(f"{question} [y/n]: ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


def prompt_review_action() -> str:
    """Top-level PO review menu. Returns 'confirm', 'edit', or 'decline'."""
    while True:
        raw = input(
            "\n[c]onfirm as-is / [e]dit cards or goal / [n] decline this sprint: "
        ).strip().lower()
        if raw in ("c", "confirm"):
            return "confirm"
        if raw in ("e", "edit"):
            return "edit"
        if raw in ("n", "no", "decline"):
            return "decline"
        print("  Please enter 'c', 'e', or 'n'.")


def prompt_edit_action() -> str:
    """Edit sub-menu. Returns 'add', 'remove', 'goal', or 'done'."""
    while True:
        raw = input(
            "  [a]dd a card / [r]emove a card / [g]oal / [d]one editing: "
        ).strip().lower()
        if raw in ("a", "add"):
            return "add"
        if raw in ("r", "remove"):
            return "remove"
        if raw in ("g", "goal"):
            return "goal"
        if raw in ("d", "done"):
            return "done"
        print("  Please enter 'a', 'r', 'g', or 'd'.")


def _prompt_card_choice(cards: list[Card], verb: str) -> str | None:
    if not cards:
        print(f"  No cards available to {verb}.")
        return None

    print(f"  Cards available to {verb}:")
    for i, card in enumerate(cards, start=1):
        print(f"    [{i}] {card.card_id} ({card.priority}, {card.story_points} pts)  {card.title}")

    raw = input(f"  Enter a number to {verb} (blank to cancel): ").strip()
    if not raw:
        return None
    try:
        index = int(raw)
    except ValueError:
        print(f"  {raw!r} is not a number. Cancelled.")
        return None
    if not (1 <= index <= len(cards)):
        print(f"  {index} is out of range. Cancelled.")
        return None
    return cards[index - 1].card_id


def prompt_card_to_add(available_cards: list[Card]) -> str | None:
    return _prompt_card_choice(available_cards, "add")


def prompt_card_to_remove(added_cards: list[Card]) -> str | None:
    return _prompt_card_choice(added_cards, "remove")


def prompt_new_goal(current_goal: str) -> str | None:
    print(f"  Current draft goal: {current_goal}")
    raw = input("  Enter new sprint goal (blank to cancel): ").strip()
    return raw or None
