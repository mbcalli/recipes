from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from recipes.core.database import get_db
from recipes.core.models import Recipe, PantryItem, MealPlan, MealPlanEntry
from recipes.core import planner as planner_core

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
