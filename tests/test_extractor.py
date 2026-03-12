from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from recipes.core.extractor import extract_recipe, fetch_page_text


# ---- Tests for fetch_page_text ----

def test_fetch_page_text_strips_scripts_and_returns_text():
    html = """<html><body>
    <script>alert('hi')</script>
    <nav>Navigation</nav>
    <p>Hello World</p>
    <footer>Footer</footer>
    </body></html>"""

    mock_response = MagicMock()
    mock_response.text = html

    with patch("recipes.core.extractor.httpx.get", return_value=mock_response):
        result = fetch_page_text("http://example.com")

    assert "Hello World" in result
    assert "alert" not in result
    assert "Navigation" not in result
    assert "Footer" not in result


# ---- Tests for extract_recipe ----

SAMPLE_RECIPE = {
    "name": "Chocolate Chip Cookies",
    "ingredients": [
        {"name": "flour", "quantity": "2", "unit": "cups"},
        {"name": "sugar", "quantity": "1", "unit": "cup"},
        {"name": "chocolate chips", "quantity": "1", "unit": "cup"},
    ],
    "instructions": ["Mix ingredients.", "Bake at 375F for 10 minutes."],
}


def _make_mock_client(response_text: str) -> MagicMock:
    mock_message = MagicMock()
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_message.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


def test_extract_recipe_returns_correct_structure():
    """extract_recipe should return a dict with name, ingredients, and instructions."""
    json_response = json.dumps(SAMPLE_RECIPE)

    html = "<html><body><p>Chocolate Chip Cookies recipe page</p></body></html>"
    mock_response = MagicMock()
    mock_response.text = html

    mock_client = _make_mock_client(json_response)

    with patch("recipes.core.extractor.httpx.get", return_value=mock_response):
        result = extract_recipe("http://example.com/cookies", client=mock_client)

    assert result["name"] == "Chocolate Chip Cookies"
    assert isinstance(result["ingredients"], list)
    assert len(result["ingredients"]) == 3
    assert isinstance(result["instructions"], list)
    assert len(result["instructions"]) == 2


def test_extract_recipe_handles_json_embedded_in_text():
    """extract_recipe should extract JSON even when surrounded by prose."""
    json_str = json.dumps(SAMPLE_RECIPE)
    response_with_prose = f"Here is the extracted recipe:\n\n{json_str}\n\nI hope that helps!"

    html = "<html><body><p>Cookies</p></body></html>"
    mock_response = MagicMock()
    mock_response.text = html

    mock_client = _make_mock_client(response_with_prose)

    with patch("recipes.core.extractor.httpx.get", return_value=mock_response):
        result = extract_recipe("http://example.com/cookies", client=mock_client)

    assert result["name"] == "Chocolate Chip Cookies"


def test_extract_recipe_calls_claude_with_correct_model():
    """extract_recipe should call the anthropic client with claude-sonnet-4-6."""
    json_str = json.dumps(SAMPLE_RECIPE)
    html = "<html><body><p>Recipe</p></body></html>"

    mock_response = MagicMock()
    mock_response.text = html

    mock_client = _make_mock_client(json_str)

    with patch("recipes.core.extractor.httpx.get", return_value=mock_response):
        extract_recipe("http://example.com/recipe", client=mock_client)

    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs.get("model") == "claude-sonnet-4-6" or (
        len(call_kwargs.args) > 0 and "claude-sonnet-4-6" in str(call_kwargs)
    )


def test_extract_recipe_ingredient_fields():
    """Each ingredient should have name, quantity, and unit."""
    json_str = json.dumps(SAMPLE_RECIPE)
    html = "<html><body><p>Recipe</p></body></html>"

    mock_response = MagicMock()
    mock_response.text = html
    mock_client = _make_mock_client(json_str)

    with patch("recipes.core.extractor.httpx.get", return_value=mock_response):
        result = extract_recipe("http://example.com/recipe", client=mock_client)

    first = result["ingredients"][0]
    assert "name" in first
    assert "quantity" in first
    assert "unit" in first
