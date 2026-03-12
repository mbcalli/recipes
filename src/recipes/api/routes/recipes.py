from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from recipes.core.database import get_db
from recipes.core.models import Recipe, Ingredient
from recipes.core.extractor import extract_recipe

router = APIRouter(prefix="/recipes", tags=["recipes"])


# ---- Pydantic schemas ----

class IngredientOut(BaseModel):
    id: int
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None

    model_config = {"from_attributes": True}


class RecipeOut(BaseModel):
    id: int
    name: str
    source_url: Optional[str] = None
    instructions: Optional[str] = None
    rating: Optional[float] = None
    notes: Optional[str] = None
    ingredients: list[IngredientOut] = []

    model_config = {"from_attributes": True}


class IngestRequest(BaseModel):
    url: str


class PatchRecipeRequest(BaseModel):
    rating: Optional[float] = None
    notes: Optional[str] = None


# ---- Endpoints ----

@router.get("", response_model=list[RecipeOut])
def list_recipes(db: Session = Depends(get_db)):
    """List all recipes with their ingredients."""
    return db.query(Recipe).all()


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get a single recipe by ID."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.post("/ingest", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def ingest_recipe(body: IngestRequest, db: Session = Depends(get_db)):
    """Fetch a recipe from a URL using Claude extraction and save it to the database."""
    try:
        data = extract_recipe(body.url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract recipe: {exc}",
        )

    instructions_text = (
        "\n".join(data.get("instructions", []))
        if isinstance(data.get("instructions"), list)
        else data.get("instructions", "")
    )

    recipe = Recipe(
        name=data["name"],
        source_url=body.url,
        instructions=instructions_text,
    )
    db.add(recipe)
    db.flush()  # get recipe.id before adding ingredients

    for ing in data.get("ingredients", []):
        ingredient = Ingredient(
            recipe_id=recipe.id,
            name=ing.get("name", ""),
            quantity=str(ing.get("quantity", "")) if ing.get("quantity") is not None else None,
            unit=ing.get("unit"),
        )
        db.add(ingredient)

    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: int, body: PatchRecipeRequest, db: Session = Depends(get_db)
):
    """Update rating (0-5) and/or notes for a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    if body.rating is not None:
        if not (0 <= body.rating <= 5):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Rating must be between 0 and 5",
            )
        recipe.rating = body.rating

    if body.notes is not None:
        recipe.notes = body.notes

    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Delete a recipe and all its ingredients."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    db.delete(recipe)
    db.commit()
