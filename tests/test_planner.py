from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from recipes.core.planner import generate_meal_plan

SAMPLE_RECIPES = [
    {"id": 1, "name": "Oatmeal", "rating": 4, "notes": None, "ingredients": []},
    {"id": 2, "name": "Pasta Carbonara", "rating": 5, "notes": "Family favourite", "ingredients": []},
    {"id": 3, "name": "Caesar Salad", "rating": 3, "notes": None, "ingredients": []},
]

SAMPLE_PANTRY = [
    {"id": 1, "name": "oats", "quantity": "2", "unit": "cups"},
    {"id": 2, "name": "eggs", "quantity": "12", "unit": ""},
]

SAMPLE_PLAN = {
    "Monday": {"breakfast": 1, "lunch": 3, "dinner": 2},
    "Tuesday": {"breakfast": 1, "lunch": None, "dinner": 2},
    "Wednesday": {"breakfast": None, "lunch": 3, "dinner": 2},
    "Thursday": {"breakfast": 1, "lunch": None, "dinner": None},
    "Friday": {"breakfast": None, "lunch": 3, "dinner": 2},
    "Saturday": {"breakfast": 1, "lunch": 3, "dinner": None},
    "Sunday": {"breakfast": None, "lunch": None, "dinner": 2},
}


def _make_mock_client(plan_dict: dict) -> MagicMock:
    mock_message = MagicMock()
    mock_content = MagicMock()
    mock_content.text = json.dumps(plan_dict)
    mock_message.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


def test_generate_meal_plan_returns_all_seven_days():
    """generate_meal_plan should return a dict with all 7 days."""
    week = date(2026, 3, 9)
    mock_client = _make_mock_client(SAMPLE_PLAN)

    result = generate_meal_plan(
        recipes=SAMPLE_RECIPES,
        pantry=SAMPLE_PANTRY,
        week_of=week,
        client=mock_client,
    )

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        assert day in result, f"Missing day: {day}"


def test_generate_meal_plan_has_meal_types():
    """Each day in the plan should have breakfast, lunch, and dinner keys."""
    week = date(2026, 3, 9)
    mock_client = _make_mock_client(SAMPLE_PLAN)

    result = generate_meal_plan(
        recipes=SAMPLE_RECIPES,
        pantry=SAMPLE_PANTRY,
        week_of=week,
        client=mock_client,
    )

    for day, meals in result.items():
        assert "breakfast" in meals, f"Missing breakfast in {day}"
        assert "lunch" in meals, f"Missing lunch in {day}"
        assert "dinner" in meals, f"Missing dinner in {day}"


def test_generate_meal_plan_allows_null_meals():
    """Meals can be null (None) when not assigned."""
    week = date(2026, 3, 9)
    mock_client = _make_mock_client(SAMPLE_PLAN)

    result = generate_meal_plan(
        recipes=SAMPLE_RECIPES,
        pantry=SAMPLE_PANTRY,
        week_of=week,
        client=mock_client,
    )

    # SAMPLE_PLAN has several null values
    assert result["Tuesday"]["lunch"] is None
    assert result["Sunday"]["breakfast"] is None


def test_generate_meal_plan_uses_recipe_ids():
    """Non-null meal assignments should be integer recipe IDs."""
    week = date(2026, 3, 9)
    mock_client = _make_mock_client(SAMPLE_PLAN)

    result = generate_meal_plan(
        recipes=SAMPLE_RECIPES,
        pantry=SAMPLE_PANTRY,
        week_of=week,
        client=mock_client,
    )

    assert result["Monday"]["breakfast"] == 1
    assert result["Monday"]["dinner"] == 2


def test_generate_meal_plan_calls_claude_with_week_info():
    """generate_meal_plan should include week_of in the prompt sent to Claude."""
    week = date(2026, 3, 9)
    mock_client = _make_mock_client(SAMPLE_PLAN)

    generate_meal_plan(
        recipes=SAMPLE_RECIPES,
        pantry=SAMPLE_PANTRY,
        week_of=week,
        preferences="vegetarian",
        client=mock_client,
    )

    call_kwargs = mock_client.messages.create.call_args
    prompt_content = str(call_kwargs)
    assert "2026-03-09" in prompt_content
    assert "vegetarian" in prompt_content


def test_generate_meal_plan_handles_json_with_surrounding_text():
    """generate_meal_plan should parse JSON even if Claude includes extra prose."""
    week = date(2026, 3, 9)
    json_str = json.dumps(SAMPLE_PLAN)
    wrapped_response = f"Sure! Here's your meal plan:\n\n{json_str}\n\nEnjoy!"

    mock_message = MagicMock()
    mock_content = MagicMock()
    mock_content.text = wrapped_response
    mock_message.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    result = generate_meal_plan(
        recipes=SAMPLE_RECIPES,
        pantry=SAMPLE_PANTRY,
        week_of=week,
        client=mock_client,
    )

    assert "Monday" in result
