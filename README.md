# Recipes

A personal recipe manager for the family. Ingest recipes from URLs, track pantry inventory, and generate weekly meal plans — all from the terminal. Powered by [Claude](https://anthropic.com).

## Features

- **Recipe ingestion** — paste a URL, Claude extracts the name, ingredients, and instructions
- **Pantry tracking** — maintain an inventory of what you have on hand, including unlimited staples (water, salt, etc.)
- **Meal planning** — Claude generates a 7-day breakfast/lunch/dinner plan based on your recipes, pantry, ratings, and preferences
- **Shopping list** — auto-generated markdown file with aggregated quantities, unit conversion, and pantry cross-reference

## Setup

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), an [Anthropic API key](https://console.anthropic.com/)

```bash
git clone https://github.com/mbcalli/recipes.git
cd recipes
uv sync
```

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Running the server

```bash
uv run uvicorn recipes.api.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `/docs`.

## CLI usage

All commands go through the `recipes` CLI, which talks to the running server.

### Recipes

```bash
# Ingest a recipe from a URL
recipes ingest https://example.com/chocolate-chip-cookies

# List all saved recipes
recipes list

# Rate a recipe (0–5) with an optional note
recipes rate 3 4.5 --note "Kids loved it, use less salt next time"
```

### Pantry

```bash
# Add a finite item
recipes pantry add butter 2 sticks
recipes pantry add "chicken broth" 32 oz

# Add an unlimited staple (never appears on the shopping list)
recipes pantry add water --unlimited
recipes pantry add salt --unlimited
recipes pantry add "olive oil" --unlimited

# List pantry contents
recipes pantry list

# Remove an item by ID
recipes pantry remove 4
```

### Meal planning

```bash
# Generate a meal plan for the current week
recipes plan generate

# Generate with dietary preferences
recipes plan generate --prefs "no red meat, kid-friendly"

# Generate for a specific week
recipes plan generate --week 2026-03-16

# View a saved plan
recipes plan show
recipes plan show --week 2026-03-16
```

Each `plan generate` call writes a markdown file to `plans/week-YYYY-MM-DD.md` containing:

1. **Shopping list** — checklist of ingredients to buy, with quantities aggregated across recipes and pantry items crossed off
2. **Schedule** — 7-day table of meals
3. **Recipes** — instructions for every recipe in the plan

### Viewing plan files

```bash
# Render in the terminal
brew install glow
glow plans/week-2026-03-16.md
```

## Shopping list details

Ingredients are aggregated intelligently across recipes:

- **Same unit system** — `1 cup + 2 tbsp butter` → `1 cup 2 tbsp`
- **Cross-system** — `1 cup water` and `250 ml water` stay as separate line items
- **Count units** — `2 chicken breasts + 3 chicken breasts` → `5 breasts`
- **Unlimited pantry items** — always shown as checked off (`∞ unlimited`), never in the buy list

## Running tests

```bash
uv run pytest
```

## Project structure

```
src/recipes/
├── api/
│   ├── main.py           # FastAPI app + DB init
│   └── routes/
│       ├── recipes.py    # Recipe CRUD + URL ingestion
│       ├── pantry.py     # Pantry CRUD
│       └── planner.py    # Meal plan generation + markdown output
├── core/
│   ├── database.py       # SQLite engine + session
│   ├── models.py         # SQLAlchemy ORM models
│   ├── extractor.py      # URL fetch + Claude recipe extraction
│   ├── planner.py        # Claude meal planning logic
│   └── units.py          # Unit conversion + ingredient aggregation
└── cli/
    └── main.py           # Click CLI (thin HTTP client)
```
