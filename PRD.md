# Recipe App

This is a product requirements document for a recipe management application. This application is intended to help me better manage my pantry inventory and plan meals for my family.

> **Branch applicability**
> - `main` — backend API + CLI only (no UI)
> - `first-ui` — all of `main`, plus the web UI described in this document

# Goal

A user can collect recipes and send them to the tool. The tool can extract the ingredients and instructions. The tool can plan a week's meals for the user. The tool can adapt to user requests. The tool can manage a user's pantry inventory.


# Non-negotiables

The tool must be usable by a lay person. The tool must be adaptive. The tool must not omit important recipe information.

# Tech Stack & Existing Patterns

I am a Python developer. However, use the appropriate tech stack.

# Scope Boundaries

## In Scope (all branches)

A tool that can receive recipes, extracts the ingredients and the instructions, populates an internal database, serves recommendations to the user, and can take user feedback. Accessible via a REST API and a CLI client.

## In Scope (first-ui branch only)

A simple browser-based web UI served directly by the FastAPI backend. The UI must cover:

- **Recipes** — ingest by URL, list all recipes, view ingredients and instructions, rate and add notes, delete
- **Pantry** — add/edit/delete items, mark items as unlimited (always-available staples)
- **Meal Plan** — generate a weekly dinner plan via Claude (with optional preferences and number of meals), view the plan for any week

The UI must be usable without any build step — plain HTML, CSS, and vanilla JavaScript only.

## Out of Scope

- A native mobile application
- Multi-user support or authentication
- Nutritional analysis
- Email-based recipe ingestion
