from __future__ import annotations

import json

import httpx
from bs4 import BeautifulSoup
import anthropic


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page_text(url: str) -> str:
    """Fetch URL and return visible text via BeautifulSoup."""
    response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def extract_recipe(url: str, client: anthropic.Anthropic = None) -> dict:
    """Fetch page + call Claude to extract structured recipe.

    Returns dict with name, ingredients[], instructions.
    """
    if client is None:
        client = anthropic.Anthropic()
    text = fetch_page_text(url)
    prompt = f"""Extract the recipe from the following webpage text. Return ONLY valid JSON with this exact structure:
{{
  "name": "Recipe Name",
  "ingredients": [
    {{"name": "ingredient name", "quantity": "1", "unit": "cup"}}
  ],
  "instructions": ["Step 1...", "Step 2..."]
}}

Rules for ingredients:
- Each entry must be a single ingredient — never combine two into one (e.g. "salt and pepper" must become two separate entries: "salt" and "pepper")
- Use null for quantity or unit when not specified
- Normalise ingredient names to lowercase

Webpage text:
{text[:8000]}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    content = message.content[0].text
    # Strip markdown code fences if present
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in Claude response: {content[:200]}")
    return json.loads(content[start:end])
