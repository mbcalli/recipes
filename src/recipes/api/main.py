from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from recipes.core.database import engine, Base
from recipes.api.routes import recipes, pantry, planner


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Recipe Manager",
    description="Manage recipes, pantry inventory, and meal plans",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(recipes.router)
app.include_router(pantry.router)
app.include_router(planner.router)


@app.get("/")
def root():
    return {"message": "Recipe Manager API", "docs": "/docs"}
