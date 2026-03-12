from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from recipes.core.database import get_db
from recipes.core.models import PantryItem

router = APIRouter(prefix="/pantry", tags=["pantry"])


# ---- Pydantic schemas ----

class PantryItemOut(BaseModel):
    id: int
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    unlimited: bool = False

    model_config = {"from_attributes": True}


class CreatePantryItemRequest(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    unlimited: bool = False


class PatchPantryItemRequest(BaseModel):
    quantity: Optional[str] = None
    unit: Optional[str] = None
    unlimited: Optional[bool] = None


# ---- Endpoints ----

@router.get("", response_model=list[PantryItemOut])
def list_pantry(db: Session = Depends(get_db)):
    """List all pantry items."""
    return db.query(PantryItem).all()


@router.post("", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
def add_pantry_item(body: CreatePantryItemRequest, db: Session = Depends(get_db)):
    """Add a new pantry item."""
    item = PantryItem(
        name=body.name,
        quantity=body.quantity,
        unit=body.unit,
        unlimited=body.unlimited,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=PantryItemOut)
def update_pantry_item(
    item_id: int, body: PatchPantryItemRequest, db: Session = Depends(get_db)
):
    """Update quantity and/or unit of a pantry item."""
    item = db.query(PantryItem).filter(PantryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pantry item not found")

    if body.quantity is not None:
        item.quantity = body.quantity
    if body.unit is not None:
        item.unit = body.unit
    if body.unlimited is not None:
        item.unlimited = body.unlimited

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pantry_item(item_id: int, db: Session = Depends(get_db)):
    """Remove a pantry item."""
    item = db.query(PantryItem).filter(PantryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pantry item not found")
    db.delete(item)
    db.commit()
