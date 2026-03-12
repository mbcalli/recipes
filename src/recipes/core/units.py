"""Unit conversion and ingredient aggregation for shopping lists."""
from __future__ import annotations

from fractions import Fraction


# ---------------------------------------------------------------------------
# Quantity parsing
# ---------------------------------------------------------------------------

def parse_qty(s: str) -> Fraction | None:
    """Parse '1', '1/2', or '1 1/2' into a Fraction. Returns None on failure."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        parts = s.split()
        if len(parts) == 2:
            return Fraction(int(parts[0])) + Fraction(parts[1])
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


# ---------------------------------------------------------------------------
# Unit tables
# ---------------------------------------------------------------------------

# US volume — base unit: tsp (all relationships are exact rationals)
_US_VOL: dict[str, Fraction] = {
    "tsp": Fraction(1), "teaspoon": Fraction(1), "teaspoons": Fraction(1),
    "tbsp": Fraction(3), "tablespoon": Fraction(3), "tablespoons": Fraction(3),
    "fl oz": Fraction(6), "fluid oz": Fraction(6),
    "fluid ounce": Fraction(6), "fluid ounces": Fraction(6),
    "cup": Fraction(48), "cups": Fraction(48),
    "pint": Fraction(96), "pints": Fraction(96), "pt": Fraction(96),
    "quart": Fraction(192), "quarts": Fraction(192), "qt": Fraction(192),
    "gallon": Fraction(768), "gallons": Fraction(768), "gal": Fraction(768),
}
_US_VOL_THRESHOLDS = [
    (Fraction(768), "gallon", "gallons"),
    (Fraction(192), "quart",  "quarts"),
    (Fraction(96),  "pint",   "pints"),
    (Fraction(48),  "cup",    "cups"),
    (Fraction(3),   "tbsp",   "tbsp"),
    (Fraction(1),   "tsp",    "tsp"),
]

# Metric volume — base unit: ml
_METRIC_VOL: dict[str, Fraction] = {
    "ml": Fraction(1), "milliliter": Fraction(1), "milliliters": Fraction(1),
    "l": Fraction(1000), "liter": Fraction(1000), "liters": Fraction(1000),
}
_METRIC_VOL_THRESHOLDS = [
    (Fraction(1000), "l",  "l"),
    (Fraction(1),    "ml", "ml"),
]

# US weight — base unit: oz (16 oz = 1 lb, exact)
_US_WEIGHT: dict[str, Fraction] = {
    "oz": Fraction(1), "ounce": Fraction(1), "ounces": Fraction(1),
    "lb": Fraction(16), "lbs": Fraction(16), "pound": Fraction(16), "pounds": Fraction(16),
}
_US_WEIGHT_THRESHOLDS = [
    (Fraction(16), "lb",  "lbs"),
    (Fraction(1),  "oz",  "oz"),
]

# Metric weight — base unit: g
_METRIC_WEIGHT: dict[str, Fraction] = {
    "g": Fraction(1), "gram": Fraction(1), "grams": Fraction(1),
    "kg": Fraction(1000), "kilogram": Fraction(1000), "kilograms": Fraction(1000),
}
_METRIC_WEIGHT_THRESHOLDS = [
    (Fraction(1000), "kg", "kg"),
    (Fraction(1),    "g",  "g"),
]

# Count units — maps any variant to (singular, plural) for display
_COUNT: dict[str, tuple[str, str]] = {
    "piece": ("piece", "pieces"),       "pieces": ("piece", "pieces"),
    "breast": ("breast", "breasts"),    "breasts": ("breast", "breasts"),
    "thigh": ("thigh", "thighs"),       "thighs": ("thigh", "thighs"),
    "leg": ("leg", "legs"),             "legs": ("leg", "legs"),
    "wing": ("wing", "wings"),          "wings": ("wing", "wings"),
    "fillet": ("fillet", "fillets"),    "fillets": ("fillet", "fillets"),
    "clove": ("clove", "cloves"),       "cloves": ("clove", "cloves"),
    "head": ("head", "heads"),          "heads": ("head", "heads"),
    "whole": ("whole", "whole"),
    "each": ("each", "each"),
    "can": ("can", "cans"),             "cans": ("can", "cans"),
    "bunch": ("bunch", "bunches"),      "bunches": ("bunch", "bunches"),
    "stalk": ("stalk", "stalks"),       "stalks": ("stalk", "stalks"),
    "slice": ("slice", "slices"),       "slices": ("slice", "slices"),
    "sprig": ("sprig", "sprigs"),       "sprigs": ("sprig", "sprigs"),
    "leaf": ("leaf", "leaves"),         "leaves": ("leaf", "leaves"),
    "strip": ("strip", "strips"),       "strips": ("strip", "strips"),
    "egg": ("egg", "eggs"),             "eggs": ("egg", "eggs"),
    "sheet": ("sheet", "sheets"),       "sheets": ("sheet", "sheets"),
    "link": ("link", "links"),          "links": ("link", "links"),
    "package": ("package", "packages"), "packages": ("package", "packages"),
    "pkg": ("package", "packages"),
    "bag": ("bag", "bags"),             "bags": ("bag", "bags"),
    "jar": ("jar", "jars"),             "jars": ("jar", "jars"),
    "bottle": ("bottle", "bottles"),    "bottles": ("bottle", "bottles"),
    "box": ("box", "boxes"),            "boxes": ("box", "boxes"),
    "container": ("container", "containers"), "containers": ("container", "containers"),
    "stick": ("stick", "sticks"),       "sticks": ("stick", "sticks"),
    "rack": ("rack", "racks"),          "racks": ("rack", "racks"),
    "skewer": ("skewer", "skewers"),    "skewers": ("skewer", "skewers"),
}


# ---------------------------------------------------------------------------
# Unit lookup
# ---------------------------------------------------------------------------

def _lookup(unit: str) -> tuple[str, Fraction | None, tuple[str, str] | None]:
    """Return (system, factor_to_base, count_forms).

    system: 'us_volume' | 'metric_volume' | 'us_weight' | 'metric_weight' | 'count' | 'unknown'
    factor_to_base: multiply parsed qty by this to reach the base unit (None for count/unknown)
    count_forms: (singular, plural) for count units, else None
    """
    u = unit.lower().strip()
    if u in _US_VOL:
        return "us_volume", _US_VOL[u], None
    if u in _METRIC_VOL:
        return "metric_volume", _METRIC_VOL[u], None
    if u in _US_WEIGHT:
        return "us_weight", _US_WEIGHT[u], None
    if u in _METRIC_WEIGHT:
        return "metric_weight", _METRIC_WEIGHT[u], None
    if u in _COUNT:
        return "count", Fraction(1), _COUNT[u]
    return "unknown", None, None


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_SNAP_FRACTIONS = [
    Fraction(1, 8), Fraction(1, 4), Fraction(1, 3),
    Fraction(3, 8), Fraction(1, 2), Fraction(5, 8),
    Fraction(2, 3), Fraction(3, 4), Fraction(7, 8),
]


def _snap(f: Fraction) -> Fraction:
    """Snap a fractional remainder to the nearest common cooking fraction (within 2%)."""
    for cf in _SNAP_FRACTIONS:
        if abs(float(f - cf)) < 0.02:
            return cf
    return f


def fmt_qty(f: Fraction) -> str:
    """Format a Fraction as a human-readable quantity string (e.g. Fraction(3,2) → '1 1/2')."""
    if f <= 0:
        return "0"
    whole = int(f)
    rem = _snap(f - whole)
    if rem == 0:
        return str(whole)
    frac_str = f"{rem.numerator}/{rem.denominator}"
    return f"{whole} {frac_str}" if whole else frac_str


def _display_total(total: Fraction, system: str) -> str:
    """Convert a base-unit total back to a human-readable string."""
    if system == "us_volume":
        thresholds = _US_VOL_THRESHOLDS
    elif system == "metric_volume":
        thresholds = _METRIC_VOL_THRESHOLDS
    elif system == "us_weight":
        thresholds = _US_WEIGHT_THRESHOLDS
    elif system == "metric_weight":
        thresholds = _METRIC_WEIGHT_THRESHOLDS
    else:
        return fmt_qty(total)

    for threshold, singular, plural in thresholds:
        if total >= threshold:
            val = _snap(total / threshold)
            label = plural if val != 1 else singular
            return f"{fmt_qty(val)} {label}"

    # Below smallest threshold — use smallest unit
    _, singular, plural = thresholds[-1]
    label = plural if total != 1 else singular
    return f"{fmt_qty(total)} {label}"


# ---------------------------------------------------------------------------
# Public aggregation API
# ---------------------------------------------------------------------------

def aggregate_ingredients(planned_recipe_ids: set, recipe_lookup: dict) -> list[dict]:
    """Aggregate ingredients across planned recipes, normalising and summing quantities.

    Ingredients with the same name are combined when they share the same unit
    system (e.g. all US volume units are summed together; a recipe with 1 cup
    and another with 2 tbsp of the same ingredient becomes 1 cup 2 tbsp).
    Cross-system combinations (e.g. cups + ml, or oz + g) are kept as separate
    line items since no lossless conversion exists.

    Count units (breasts, cloves, cans, …) are summed by normalised unit so
    "2 breasts + 3 breasts = 5 breasts" works, but "2 breasts" and "500 g
    chicken" remain separate entries.

    Returns a list sorted by ingredient name, each entry::

        {
            "name":       str,   # title-cased display name
            "total":      str,   # e.g. "1 1/2 cups" or "5 breasts"
            "detail":     str,   # per-recipe breakdown
            "aggregated": bool,  # True when >1 usage was summed
        }
    """
    groups: dict[tuple, dict] = {}

    for recipe_id in planned_recipe_ids:
        recipe = recipe_lookup.get(recipe_id)
        if not recipe:
            continue
        for ing in recipe.ingredients:
            name_key = ing.name.lower().strip()
            unit_raw = (ing.unit or "").strip()

            if unit_raw:
                system, factor, count_forms = _lookup(unit_raw)
            else:
                system, factor, count_forms = "unknown", None, None

            # Sub-key keeps different count units (breasts vs cloves) separate,
            # and keeps unknown units separate by their literal string.
            if system == "count":
                sub_key = count_forms[0]          # canonical singular
            elif system == "unknown":
                sub_key = unit_raw.lower()
            else:
                sub_key = ""                       # all same-system units merge

            group_key = (name_key, system, sub_key)

            qty_str = (ing.quantity or "").strip()
            usage_label = f"{qty_str} {unit_raw}".strip() if (qty_str or unit_raw) else "some"

            if group_key not in groups:
                groups[group_key] = {
                    "name": ing.name.strip(),
                    "system": system,
                    "count_forms": count_forms,
                    "total": Fraction(0),
                    "can_sum": True,
                    "usages": [],
                }

            g = groups[group_key]
            g["usages"].append((usage_label, recipe.name))

            qty_frac = parse_qty(qty_str) if qty_str else None
            if qty_frac is not None and factor is not None:
                g["total"] += qty_frac * factor
            elif qty_str:
                # Has a quantity string but couldn't parse it — disable summing
                g["can_sum"] = False

    result = []
    for (name_key, system, sub_key), g in sorted(groups.items(), key=lambda x: x[0][0]):
        usages = g["usages"]
        detail = ", ".join(f"{qty} {rname}" if qty else rname for qty, rname in usages)

        if g["can_sum"] and g["total"] > 0:
            if system in ("us_volume", "metric_volume", "us_weight", "metric_weight"):
                total_str = _display_total(g["total"], system)
            elif system == "count":
                singular, plural = g["count_forms"]
                label = singular if g["total"] == 1 else plural
                total_str = f"{fmt_qty(g['total'])} {label}"
            else:
                # Unknown unit but parseable qty — show raw sum with unit
                total_str = f"{fmt_qty(g['total'])} {sub_key}".strip()
        else:
            total_str = " + ".join(qty for qty, _ in usages if qty) or "some"

        result.append({
            "name": g["name"].title(),
            "total": total_str,
            "detail": detail,
            "aggregated": len(usages) > 1,
        })

    return result
