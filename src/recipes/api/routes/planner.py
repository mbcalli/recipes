from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from recipes.core.database import get_db
from recipes.core.models import Recipe, PantryItem, MealPlan, MealPlanEntry
from recipes.core import planner as planner_core
from recipes.core.units import aggregate_ingredients

router = APIRouter(prefix="/planner", tags=["planner"])

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEAL_TYPES = ["breakfast", "lunch", "dinner"]


# ---- Pydantic schemas ----

class GeneratePlanRequest(BaseModel):
    week_of: date
    preferences: Optional[str] = None


class MealPlanEntryOut(BaseModel):
    id: int
    day_of_week: str
    meal_type: str
    recipe_id: Optional[int] = None
    recipe_name: Optional[str] = None

    model_config = {"from_attributes": True}


class MealPlanOut(BaseModel):
    id: int
    week_of: date
    entries: list[MealPlanEntryOut] = []

    model_config = {"from_attributes": True}


def _serialize_recipe(recipe: Recipe) -> dict:
    return {
        "id": recipe.id,
        "name": recipe.name,
        "rating": recipe.rating,
        "notes": recipe.notes,
        "ingredients": [
            {"name": ing.name, "quantity": ing.quantity, "unit": ing.unit}
            for ing in recipe.ingredients
        ],
    }


def _serialize_pantry_item(item: PantryItem) -> dict:
    return {"id": item.id, "name": item.name, "quantity": item.quantity, "unit": item.unit}


def _meal_plan_to_out(meal_plan: MealPlan) -> MealPlanOut:
    entries_out = []
    for entry in meal_plan.entries:
        recipe_name = entry.recipe.name if entry.recipe else None
        entries_out.append(
            MealPlanEntryOut(
                id=entry.id,
                day_of_week=entry.day_of_week,
                meal_type=entry.meal_type,
                recipe_id=entry.recipe_id,
                recipe_name=recipe_name,
            )
        )
    return MealPlanOut(id=meal_plan.id, week_of=meal_plan.week_of, entries=entries_out)


def _write_plan_markdown(meal_plan: MealPlan, recipe_lookup: dict, pantry_items: list) -> None:
    """Write a markdown meal plan file to the plans/ directory."""
    week_of = meal_plan.week_of

    # Collect planned recipe IDs and build schedule lookup
    entries_by_day: dict[str, dict[str, str]] = {day: {} for day in DAYS_OF_WEEK}
    planned_recipe_ids: set[int] = set()
    for entry in meal_plan.entries:
        if entry.recipe_id is not None:
            recipe = recipe_lookup.get(entry.recipe_id)
            entries_by_day[entry.day_of_week][entry.meal_type] = recipe.name if recipe else "Unknown"
            planned_recipe_ids.add(entry.recipe_id)
        else:
            entries_by_day[entry.day_of_week][entry.meal_type] = "—"

    # Aggregate ingredients with unit conversion
    pantry_names = {item.name.lower() for item in pantry_items}
    items = aggregate_ingredients(planned_recipe_ids, recipe_lookup)

    buy = [i for i in items if i["name"].lower() not in pantry_names]
    have = [i for i in items if i["name"].lower() in pantry_names]

    lines: list[str] = [f"# Meal Plan – Week of {week_of}\n"]

    # --- Shopping List (top) ---
    lines.append("## Shopping List\n")
    lines.append("### Need to Buy\n")
    if buy:
        for i in buy:
            if i["aggregated"]:
                lines.append(f"- [ ] **{i['name']}** — {i['total']} ({i['detail']})")
            else:
                lines.append(f"- [ ] **{i['name']}** — {i['total']}")
    else:
        lines.append("- *(nothing — everything is in the pantry!)*")

    lines.append("\n### Already in Pantry\n")
    if have:
        for i in have:
            if i["aggregated"]:
                lines.append(f"- [x] {i['name']} — {i['total']} ({i['detail']})")
            else:
                lines.append(f"- [x] {i['name']} — {i['total']}")
    else:
        lines.append("- *(no overlap with pantry)*")

    # --- Schedule ---
    lines.append("\n## Schedule\n")
    lines.append("| Day | Breakfast | Lunch | Dinner |")
    lines.append("|-----|-----------|-------|--------|")
    for day in DAYS_OF_WEEK:
        meals = entries_by_day[day]
        b = meals.get("breakfast", "—")
        lu = meals.get("lunch", "—")
        d = meals.get("dinner", "—")
        lines.append(f"| {day} | {b} | {lu} | {d} |")

    # --- Recipes & Instructions ---
    lines.append("\n## Recipes\n")
    for recipe_id in planned_recipe_ids:
        recipe = recipe_lookup.get(recipe_id)
        if not recipe:
            continue
        lines.append(f"### {recipe.name}\n")
        if recipe.source_url:
            lines.append(f"Source: {recipe.source_url}\n")
        if recipe.instructions:
            lines.append("**Instructions:**\n")
            for idx, step in enumerate(recipe.instructions.splitlines(), start=1):
                step = step.strip()
                if step:
                    lines.append(f"{idx}. {step}")
            lines.append("")

    # Write file
    plans_dir = Path("plans")
    plans_dir.mkdir(exist_ok=True)
    output_path = plans_dir / f"week-{week_of}.md"
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---- Endpoints ----

@router.post("/generate", response_model=MealPlanOut, status_code=status.HTTP_201_CREATED)
def generate_plan(body: GeneratePlanRequest, db: Session = Depends(get_db)):
    """Generate a 7-day meal plan using Claude and save it to the database."""
    recipes = db.query(Recipe).all()
    pantry_items = db.query(PantryItem).all()

    recipes_data = [_serialize_recipe(r) for r in recipes]
    pantry_data = [_serialize_pantry_item(p) for p in pantry_items]

    try:
        plan_data = planner_core.generate_meal_plan(
            recipes=recipes_data,
            pantry=pantry_data,
            week_of=body.week_of,
            preferences=body.preferences or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate meal plan: {exc}",
        )

    # Remove existing plan for that week if present
    existing = db.query(MealPlan).filter(MealPlan.week_of == body.week_of).first()
    if existing:
        db.delete(existing)
        db.flush()

    meal_plan = MealPlan(week_of=body.week_of)
    db.add(meal_plan)
    db.flush()

    for day in DAYS_OF_WEEK:
        day_data = plan_data.get(day, {})
        for meal_type in MEAL_TYPES:
            recipe_id = day_data.get(meal_type)
            # Validate recipe_id exists
            if recipe_id is not None:
                recipe_exists = db.query(Recipe).filter(Recipe.id == recipe_id).first()
                if not recipe_exists:
                    recipe_id = None
            entry = MealPlanEntry(
                meal_plan_id=meal_plan.id,
                recipe_id=recipe_id,
                day_of_week=day,
                meal_type=meal_type,
            )
            db.add(entry)

    db.commit()
    db.refresh(meal_plan)

    # Build a recipe lookup from the full ORM objects (ingredients included)
    recipe_lookup = {r.id: r for r in recipes}
    _write_plan_markdown(meal_plan, recipe_lookup, pantry_items)

    return _meal_plan_to_out(meal_plan)


@router.get("/{week_of}", response_model=MealPlanOut)
def get_plan(week_of: date, db: Session = Depends(get_db)):
    """Retrieve an existing meal plan for a given week."""
    meal_plan = db.query(MealPlan).filter(MealPlan.week_of == week_of).first()
    if not meal_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No meal plan found for week of {week_of}",
        )
    return _meal_plan_to_out(meal_plan)
