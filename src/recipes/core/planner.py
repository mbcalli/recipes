from __future__ import annotations

import json
from datetime import date

import anthropic


def generate_meal_plan(
    recipes: list[dict],
    pantry: list[dict],
    week_of: date,
    preferences: str = "",
    client: anthropic.Anthropic = None,
) -> dict:
    """Call Claude to generate a 7-day meal plan.

    Returns dict with days mapping to meal assignments.
    """
    if client is None:
        client = anthropic.Anthropic()

    recipes_text = json.dumps(recipes, indent=2, default=str)
    pantry_text = json.dumps(pantry, indent=2, default=str)

    prompt = f"""Generate a 7-day meal plan for the week of {week_of}.

Available recipes:
{recipes_text}

Current pantry items:
{pantry_text}

User preferences: {preferences or "None specified"}

Instructions:
- Assign recipes to days (Monday through Sunday) for breakfast, lunch, and dinner
- Favor recipes that use pantry-available ingredients
- Consider recipe ratings (higher rated = better)
- Take user notes and preferences into account
- You don't need to assign all 3 meals every day; some can be "null"

Return ONLY valid JSON with this structure:
{{
  "Monday": {{"breakfast": <recipe_id or null>, "lunch": <recipe_id or null>, "dinner": <recipe_id or null>}},
  "Tuesday": {{"breakfast": <recipe_id or null>, "lunch": <recipe_id or null>, "dinner": <recipe_id or null>}},
  "Wednesday": {{"breakfast": <recipe_id or null>, "lunch": <recipe_id or null>, "dinner": <recipe_id or null>}},
  "Thursday": {{"breakfast": <recipe_id or null>, "lunch": <recipe_id or null>, "dinner": <recipe_id or null>}},
  "Friday": {{"breakfast": <recipe_id or null>, "lunch": <recipe_id or null>, "dinner": <recipe_id or null>}},
  "Saturday": {{"breakfast": <recipe_id or null>, "lunch": <recipe_id or null>, "dinner": <recipe_id or null>}},
  "Sunday": {{"breakfast": <recipe_id or null>, "lunch": <recipe_id or null>, "dinner": <recipe_id or null>}}
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    content = message.content[0].text
    start = content.find("{")
    end = content.rfind("}") + 1
    return json.loads(content[start:end])
