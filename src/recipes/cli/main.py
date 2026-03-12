from __future__ import annotations

import json
from datetime import date, timedelta

import click
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"


def _print_json(data):
    click.echo(json.dumps(data, indent=2, default=str))


def _handle_response(response: httpx.Response):
    if response.status_code >= 400:
        click.echo(f"Error {response.status_code}: {response.text}", err=True)
        raise SystemExit(1)
    if response.status_code == 204:
        click.echo("Done.")
        return None
    return response.json()


@click.group()
def cli():
    """Recipe Manager - manage recipes, pantry, and meal plans."""


# ---- recipe commands ----

@cli.command("ingest")
@click.argument("url")
def recipes_ingest(url: str):
    """Ingest a recipe from a URL."""
    click.echo(f"Fetching and extracting recipe from {url} ...")
    with httpx.Client(timeout=60) as client:
        response = client.post(f"{BASE_URL}/recipes/ingest", json={"url": url})
    data = _handle_response(response)
    if data:
        click.echo(f"\nRecipe saved: [{data['id']}] {data['name']}")
        if data.get("ingredients"):
            click.echo(f"  Ingredients: {len(data['ingredients'])}")
        _print_json(data)


@cli.command("list")
def recipes_list():
    """List all saved recipes."""
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{BASE_URL}/recipes")
    data = _handle_response(response)
    if data is not None:
        if not data:
            click.echo("No recipes found.")
            return
        for r in data:
            rating_str = f"  rating={r['rating']}" if r.get("rating") is not None else ""
            click.echo(f"[{r['id']}] {r['name']}{rating_str}")


@cli.command("rate")
@click.argument("recipe_id", type=int)
@click.argument("rating", type=float)
@click.option("--note", default=None, help="Optional note to attach to the recipe")
def recipes_rate(recipe_id: int, rating: float, note: str):
    """Rate a recipe (0-5) and optionally add a note."""
    payload = {"rating": rating}
    if note:
        payload["notes"] = note
    with httpx.Client(timeout=30) as client:
        response = client.patch(f"{BASE_URL}/recipes/{recipe_id}", json=payload)
    data = _handle_response(response)
    if data:
        click.echo(f"Updated recipe [{data['id']}] {data['name']} — rating: {data['rating']}")


# ---- pantry commands ----

@cli.group()
def pantry():
    """Pantry inventory commands."""


@pantry.command("add")
@click.argument("name")
@click.argument("qty", required=False, default=None)
@click.argument("unit", required=False, default=None)
@click.option("--unlimited", is_flag=True, default=False, help="Mark as always available (never appears on shopping list).")
def pantry_add(name: str, qty: str, unit: str, unlimited: bool):
    """Add an item to the pantry.

    Use --unlimited for staples you always have (water, salt, etc.).
    QTY and UNIT are optional for unlimited items.
    """
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{BASE_URL}/pantry",
            json={"name": name, "quantity": qty, "unit": unit, "unlimited": unlimited},
        )
    data = _handle_response(response)
    if data:
        if data.get("unlimited"):
            click.echo(f"Added pantry item [{data['id']}]: {data['name']} (unlimited)")
        else:
            click.echo(f"Added pantry item [{data['id']}]: {data['quantity']} {data['unit']} of {data['name']}")


@pantry.command("list")
def pantry_list():
    """List all pantry items."""
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{BASE_URL}/pantry")
    data = _handle_response(response)
    if data is not None:
        if not data:
            click.echo("Pantry is empty.")
            return
        for item in data:
            if item.get("unlimited"):
                click.echo(f"[{item['id']}] {item['name']}  (∞ unlimited)")
            else:
                qty = f"{item['quantity']} {item['unit']}" if item.get("quantity") else "—"
                click.echo(f"[{item['id']}] {item['name']}  ({qty})")


@pantry.command("remove")
@click.argument("item_id", type=int)
def pantry_remove(item_id: int):
    """Remove a pantry item by ID."""
    with httpx.Client(timeout=30) as client:
        response = client.delete(f"{BASE_URL}/pantry/{item_id}")
    _handle_response(response)


# ---- plan commands ----

@cli.group()
def plan():
    """Meal planning commands."""


def _current_monday() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


@plan.command("generate")
@click.option("--week", default=None, help="Week start date (YYYY-MM-DD). Defaults to current Monday.")
@click.option("--prefs", default=None, help="Meal plan preferences or dietary notes.")
@click.option("--num-meals", default=None, type=int, help="Total number of meals to plan (rest are leftovers).")
def plan_generate(week: str, prefs: str, num_meals: int):
    """Generate a meal plan for the given week using Claude."""
    week_of = week or _current_monday()
    click.echo(f"Generating meal plan for week of {week_of} ...")
    payload = {"week_of": week_of}
    if prefs:
        payload["preferences"] = prefs
    if num_meals is not None:
        payload["num_meals"] = num_meals
    with httpx.Client(timeout=120) as client:
        response = client.post(f"{BASE_URL}/planner/generate", json=payload)
    data = _handle_response(response)
    if data:
        click.echo(f"\nMeal Plan (week of {data['week_of']}):")
        _display_plan(data)


@plan.command("show")
@click.option("--week", default=None, help="Week start date (YYYY-MM-DD). Defaults to current Monday.")
def plan_show(week: str):
    """Show the meal plan for a given week."""
    week_of = week or _current_monday()
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{BASE_URL}/planner/{week_of}")
    data = _handle_response(response)
    if data:
        click.echo(f"Meal Plan (week of {data['week_of']}):")
        _display_plan(data)


def _display_plan(data: dict):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    dinner_by_day: dict[str, str] = {}
    for entry in data.get("entries", []):
        if entry["meal_type"] == "dinner":
            dinner_by_day[entry["day_of_week"]] = entry.get("recipe_name") or "—"

    for day in days:
        recipe_name = dinner_by_day.get(day, "—")
        click.echo(f"  {day:10s} {recipe_name}")


@cli.command("reset")
@click.option("--all", "reset_all", is_flag=True, required=True, help="Required flag to confirm full database reset.")
def reset(reset_all: bool):
    """Drop all tables and re-ingest every recipe from its original URL."""
    click.echo("Collecting URLs, wiping database, and re-ingesting all recipes ...")
    with httpx.Client(timeout=300) as client:
        response = client.post(f"{BASE_URL}/admin/reset")
    data = _handle_response(response)
    if data:
        click.echo(f"\nDone. {data['succeeded']}/{data['urls_found']} recipes re-ingested successfully.")
        for r in data["results"]:
            if r["status"] == "ok":
                click.echo(f"  [ok]    {r['name']}  ({r['url']})")
            else:
                click.echo(f"  [fail]  {r['url']}\n          {r['error']}")


if __name__ == "__main__":
    cli()
