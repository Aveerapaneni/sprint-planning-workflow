import sys
import types

import pytest

from sprint_planning_automator.goal_generation import (
    GoalGenerationError,
    build_prompt,
    generate_sprint_goal,
)
from sprint_planning_automator.models import Card, Team


@pytest.fixture
def team_and_cards():
    team = Team("t1", "Team Test", 20, "Jamie PO")
    cards = [
        Card("C-1", "t1", None, "Add SSO login", "high", 8, "in_progress"),
        Card("C-2", "t1", None, "Refactor settings API", "medium", 5, "sprint_ready"),
    ]
    return team, cards


def test_build_prompt_includes_cards_and_team(team_and_cards):
    team, cards = team_and_cards
    prompt = build_prompt(team, cards)
    assert "Team Test" in prompt
    assert "Add SSO login" in prompt
    assert "Refactor settings API" in prompt
    assert "high" in prompt and "medium" in prompt
    assert "1-2 sentences" in prompt


def test_missing_credentials_raises_goal_generation_error(monkeypatch, team_and_cards):
    team, cards = team_and_cards
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(GoalGenerationError):
        generate_sprint_goal(team, cards)


class _FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeResponse:
    def __init__(self, text, stop_reason="end_turn", input_tokens=42, output_tokens=17):
        self.content = [_FakeTextBlock(text)]
        self.stop_reason = stop_reason
        self.usage = _FakeUsage(input_tokens, output_tokens)


def _install_fake_anthropic(monkeypatch, response=None, raise_on_create=None):
    fake_module = types.ModuleType("anthropic")

    class AnthropicError(Exception):
        pass

    class APIError(AnthropicError):
        pass

    class _FakeMessages:
        def create(self, **kwargs):
            if raise_on_create is not None:
                raise raise_on_create
            return response

    class _FakeClient:
        def __init__(self, *a, **kw):
            self.messages = _FakeMessages()

    fake_module.Anthropic = _FakeClient
    fake_module.AnthropicError = AnthropicError
    fake_module.APIError = APIError
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return fake_module


def test_successful_generation_returns_goal_and_token_usage(monkeypatch, team_and_cards):
    team, cards = team_and_cards
    _install_fake_anthropic(
        monkeypatch, response=_FakeResponse("Ship SSO and refactor the settings API.")
    )

    result = generate_sprint_goal(team, cards)

    assert result.goal == "Ship SSO and refactor the settings API."
    assert result.input_tokens == 42
    assert result.output_tokens == 17


def test_refusal_stop_reason_raises_goal_generation_error(monkeypatch, team_and_cards):
    team, cards = team_and_cards
    _install_fake_anthropic(
        monkeypatch, response=_FakeResponse("", stop_reason="refusal")
    )

    with pytest.raises(GoalGenerationError):
        generate_sprint_goal(team, cards)


def test_empty_text_response_raises_goal_generation_error(monkeypatch, team_and_cards):
    team, cards = team_and_cards
    _install_fake_anthropic(monkeypatch, response=_FakeResponse("   "))

    with pytest.raises(GoalGenerationError):
        generate_sprint_goal(team, cards)


def test_api_error_during_create_raises_goal_generation_error(monkeypatch, team_and_cards):
    team, cards = team_and_cards

    class _BoomError(Exception):
        pass

    fake_module = _install_fake_anthropic(monkeypatch, raise_on_create=_BoomError("boom"))
    fake_module.APIError = _BoomError
    fake_module.AnthropicError = _BoomError

    with pytest.raises(GoalGenerationError):
        generate_sprint_goal(team, cards)
