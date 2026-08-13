"""US-1 & US-4: interactive terminal input for sprint dates and PO confirmation."""

from __future__ import annotations

from datetime import date, datetime

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
