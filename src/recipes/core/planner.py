from __future__ import annotations

import json
from datetime import date

import anthropic


def generate_meal_plan(
    recipes: list[dict],
    pantry: list[dict],
    week_of: date,
    preferences: str = "",
    num_meals: int | None = None,
    client: anthropic.Anthropic = None,
) -> dict:
    """Call Claude to generate a 7-day meal plan.

    Returns dict with days mapping to meal assignments.
    """
    if client is None:
        client = anthropic.Anthropic()

    recipes_text = json.dumps(recipes, indent=2, default=str)
    pantry_text = json.dumps(pantry, indent=2, default=str)

    meals_instruction = (
        f"- Plan exactly {num_meals} meals total across the week. Spread them sensibly across days and meal types, leaving the rest as null. This accounts for leftovers — a meal planned one day will be eaten again the next, so fewer unique meals are needed."
        if num_meals is not None
        else "- You don't need to assign all 3 meals every day; some can be null."
    )

    prompt = f"""Generate a 7-day meal plan for the week of {week_of}.

Available recipes:
{recipes_text}

Current pantry items:
{pantry_text}

User preferences: {preferences or "None specified"}

Instructions:
- Assign one recipe per day (dinner only) for Monday through Sunday
- Favor recipes that use pantry-available ingredients
- Consider recipe ratings (higher rated = better)
- Take user notes and preferences into account
{meals_instruction}

Return ONLY valid JSON with this structure:
{{
  "Monday": {{"dinner": <recipe_id or null>}},
  "Tuesday": {{"dinner": <recipe_id or null>}},
  "Wednesday": {{"dinner": <recipe_id or null>}},
  "Thursday": {{"dinner": <recipe_id or null>}},
  "Friday": {{"dinner": <recipe_id or null>}},
  "Saturday": {{"dinner": <recipe_id or null>}},
  "Sunday": {{"dinner": <recipe_id or null>}}
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
