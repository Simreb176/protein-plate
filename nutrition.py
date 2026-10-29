"""Nutrition maths shared by the site build and the editing page.

Values are per 100 g in data/foods.yml (built from UK CoFID 2021). A recipe's
ingredients are `{food, grams, label}` rows, and this module turns them into
per-serving calories, protein, carbs, fat and fibre.
"""
from pathlib import Path

import yaml

NUTRIENTS = ("kcal", "protein", "carbs", "fat", "fibre")


class NutritionError(ValueError):
    """A recipe's ingredients can't be costed — explain it in plain language."""


def load_foods(path):
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    foods = doc.get("foods") or {}
    if not foods:
        raise NutritionError(f"{path} has no foods in it.")
    for key, food in foods.items():
        per = food.get("per_100g") or {}
        missing = [name for name in NUTRIENTS if not isinstance(per.get(name), (int, float))]
        if missing:
            raise NutritionError(f"Food “{key}” is missing {', '.join(missing)} in {path}.")
    return foods, doc.get("source") or {}


def compute(recipe, foods):
    """Return the per-serving nutrition for one structured recipe."""
    ingredients = recipe.get("ingredients")
    if not isinstance(ingredients, list) or not ingredients:
        raise NutritionError(f"“{recipe.get('title', 'A recipe')}” has no ingredients.")

    totals = {name: 0.0 for name in NUTRIENTS}
    for row in ingredients:
        if not isinstance(row, dict):
            raise NutritionError(
                f"“{recipe.get('title', 'A recipe')}” has an ingredient that isn't a food + grams row."
            )
        key = row.get("food")
        grams = row.get("grams")
        if key not in foods:
            raise NutritionError(
                f"“{recipe.get('title', 'A recipe')}” uses the food “{key}”, which isn't in data/foods.yml."
            )
        if not isinstance(grams, (int, float)) or grams <= 0:
            raise NutritionError(
                f"“{recipe.get('title', 'A recipe')}” needs a positive number of grams for “{row.get('label') or key}”."
            )
        per = foods[key]["per_100g"]
        for name in NUTRIENTS:
            totals[name] += per[name] * grams / 100.0

    servings = recipe.get("servings", 1)
    if not isinstance(servings, (int, float)) or servings <= 0:
        raise NutritionError(f"“{recipe.get('title', 'A recipe')}” needs a positive number of servings.")

    per_serving = {name: totals[name] / servings for name in NUTRIENTS}
    return {
        "calories": round(per_serving["kcal"], 1),
        "protein": round(per_serving["protein"], 1),
        "carbs": round(per_serving["carbs"], 1),
        "fat": round(per_serving["fat"], 1),
        "fibre": round(per_serving["fibre"], 1),
    }


def display_label(row, foods):
    """The nice ingredient text: the hand-written label, or grams + food name."""
    if row.get("label"):
        return row["label"]
    food = foods.get(row.get("food")) or {}
    grams = row.get("grams", 0)
    grams_text = f"{grams:g}"
    return f"{grams_text} g {str(food.get('name', row.get('food', 'food'))).lower()}"
