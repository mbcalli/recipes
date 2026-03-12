from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from recipes.core.database import engine, SessionLocal, Base
from recipes.core.models import Recipe, Ingredient
from recipes.core.extractor import extract_recipe

router = APIRouter(prefix="/admin", tags=["admin"])


class ResetResult(BaseModel):
    url: str
    name: str | None = None
    status: str
    error: str | None = None


class ResetResponse(BaseModel):
    urls_found: int
    succeeded: int
    failed: int
    results: list[ResetResult]


@router.post("/reset", response_model=ResetResponse)
def reset_and_reingest():
    """Drop all tables, recreate schema, and re-ingest every recipe URL."""
    # 1. Collect URLs before destroying data
    with SessionLocal() as db:
        urls = [
            r.source_url
            for r in db.query(Recipe).filter(Recipe.source_url.isnot(None)).all()
        ]

    # 2. Wipe and recreate schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 3. Re-ingest each URL
    results: list[ResetResult] = []
    for url in urls:
        try:
            data = extract_recipe(url)

            instructions_text = (
                "\n".join(data.get("instructions", []))
                if isinstance(data.get("instructions"), list)
                else data.get("instructions", "")
            )

            with SessionLocal() as db:
                recipe = Recipe(
                    name=data["name"],
                    source_url=url,
                    instructions=instructions_text,
                )
                db.add(recipe)
                db.flush()

                for ing in data.get("ingredients", []):
                    db.add(Ingredient(
                        recipe_id=recipe.id,
                        name=ing.get("name", ""),
                        quantity=str(ing["quantity"]) if ing.get("quantity") is not None else None,
                        unit=ing.get("unit"),
                    ))

                db.commit()

            results.append(ResetResult(url=url, name=data["name"], status="ok"))
        except Exception as exc:
            results.append(ResetResult(url=url, status="error", error=str(exc)))

    succeeded = sum(1 for r in results if r.status == "ok")
    return ResetResponse(
        urls_found=len(urls),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )
