from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    Integer, String, Text, Float, ForeignKey, DateTime, Date, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recipes.core.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    ingredients: Mapped[List[Ingredient]] = relationship(
        "Ingredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    meal_plan_entries: Mapped[List[MealPlanEntry]] = relationship(
        "MealPlanEntry",
        back_populates="recipe",
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="ingredients")


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    week_of: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    entries: Mapped[List[MealPlanEntry]] = relationship(
        "MealPlanEntry",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
    )


class MealPlanEntry(Base):
    __tablename__ = "meal_plan_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meal_plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meal_plans.id"), nullable=False
    )
    recipe_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("recipes.id"), nullable=True
    )
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(10), nullable=False)

    meal_plan: Mapped[MealPlan] = relationship("MealPlan", back_populates="entries")
    recipe: Mapped[Optional[Recipe]] = relationship(
        "Recipe", back_populates="meal_plan_entries"
    )
