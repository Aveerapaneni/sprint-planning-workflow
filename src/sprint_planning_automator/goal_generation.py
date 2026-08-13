"""US-6: generate a sprint goal grounded in the actual selected cards via Claude,
with a deterministic, offline, cost-free template fallback for when that call
isn't available (no API key, network error, refusal, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from .models import PRIORITY_ORDER, Card, Team

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 200


class GoalGenerationError(Exception):
    """Raised when the Claude API call fails or returns no usable text.

    Callers should catch this and fall back to the draft-goal placeholder —
    a failed AI call must never crash a sprint transition (PRD Section 7).
    """


@dataclass
class GoalGenerationResult:
    goal: str
    input_tokens: int
    output_tokens: int


def build_prompt(team: Team, cards: list[Card]) -> str:
    lines = [
        f"Team: {team.team_name}",
        "Cards committed to this sprint (priority, points, title):",
    ]
    for c in cards:
        lines.append(f"- [{c.priority}] {c.story_points} pts: {c.title}")
    lines.append(
        "\nWrite a single sprint goal (1-2 sentences) that captures the intentional "
        "theme connecting these cards, grounded in what they actually are — not a "
        "list recap of the titles and not generic filler. Respond with only the "
        "goal text: no preamble, no quotes, no XML tags."
    )
    return "\n".join(lines)


def generate_sprint_goal(team: Team, cards: list[Card]) -> GoalGenerationResult:
    try:
        import anthropic
    except ImportError as exc:
        raise GoalGenerationError("anthropic package is not installed") from exc

    try:
        client = anthropic.Anthropic()
    except (anthropic.AnthropicError, TypeError) as exc:
        raise GoalGenerationError(f"could not create Claude client: {exc}") from exc

    prompt = build_prompt(team, cards)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
    except (anthropic.AnthropicError, TypeError) as exc:
        # TypeError covers missing-credentials, raised lazily at request time
        # rather than at client construction, by this SDK version.
        raise GoalGenerationError(f"Claude API call failed: {exc}") from exc

    if response.stop_reason == "refusal":
        raise GoalGenerationError("Claude declined to generate a sprint goal")

    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    if not text:
        raise GoalGenerationError("Claude returned no goal text")

    return GoalGenerationResult(
        goal=text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


def generate_template_goal(cards: list[Card]) -> str:
    """Deterministic, no-API fallback: names the top 1-2 highest-priority cards
    (ties broken by original order, same as the backfill priority sort) rather
    than a generic placeholder. Not as natural as the AI-generated goal, but
    free, offline, and still grounded in the actual sprint content."""
    if not cards:
        return "No cards committed to this sprint yet."

    ordered = sorted(cards, key=lambda c: PRIORITY_ORDER[c.priority])
    titles = [c.title for c in ordered]

    if len(titles) == 1:
        return f"This sprint focuses on: {titles[0]}."
    if len(titles) == 2:
        return f"This sprint focuses on: {titles[0]} and {titles[1]}."

    remaining = len(titles) - 2
    card_word = "card" if remaining == 1 else "cards"
    return (
        f"This sprint focuses on: {titles[0]} and {titles[1]} "
        f"(plus {remaining} more {card_word})."
    )
