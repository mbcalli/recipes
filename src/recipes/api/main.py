from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

from sqlalchemy import text
from recipes.core.database import engine, Base
from recipes.api.routes import recipes, pantry, planner, admin

_WEB_DIR = Path(__file__).parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Add columns introduced after initial schema (safe to run on every start)
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE pantry_items ADD COLUMN unlimited BOOLEAN NOT NULL DEFAULT 0"
            ))
            conn.commit()
        except Exception:
            pass  # Column already exists
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
app.include_router(admin.router)

app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")


@app.get("/")
def root():
    return FileResponse(_WEB_DIR / "index.html")
