#!/usr/bin/env python3
"""Protein Plate — static site generator.

Reads the YAML in `data/`, renders the Jinja templates in `templates/`, and
writes the finished site to `docs/`.

    .venv/bin/python generate.py        # or: python3 generate.py

`docs/` is the built site: it is what you serve or publish. The meal generator
itself runs in the visitor's browser (see `app.js`), fed by a JSON file this
script writes from `data/recipes.yml` and `data/planner.yml`, so the recipe
shelf and the planner rules both stay editable in one place.
"""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

try:
    import markdown
except ImportError:  # markdown is optional — see requirements.txt
    markdown = None

ROOT = Path(__file__).parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "docs"

# Static files copied verbatim into the built site.
ASSETS = ["styles.css", "app.js", "favicon.svg"]

# Files that must survive a rebuild.
PRESERVE = {"CNAME", ".nojekyll"}

# Where each top-level page lives in the generated site.
# template -> (output file, page id used to highlight the active nav link)
PAGES = {
    "index.html": ("index.html", "planner"),
    "recipes.html": ("recipes.html", "recipes"),
    "about.html": ("about.html", "about"),
}

# Strictest-first. A recipe fits every diet to its right.
DIET_ORDER = ["vegan", "vegetarian", "pescatarian", "omnivore"]

SLOT_ORDER = ["breakfast", "lunch", "dinner", "snack"]


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def render_markdown(text):
    if not text:
        return ""
    if markdown is not None:
        return Markup(markdown.markdown(text.strip()))
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return Markup("\n".join(f"<p>{p}</p>" for p in parts))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def asset_version(names):
    """A short fingerprint of the static assets.

    The site's CSS and JS are served with a long browser cache. Putting this
    in the URL (styles.css?v=…) means a change is picked up immediately instead
    of visitors seeing yesterday's stylesheet for hours.
    """
    digest = hashlib.sha256()
    for name in names:
        src = ROOT / name
        if src.exists():
            digest.update(src.read_bytes())
    return digest.hexdigest()[:10]


def load_recipes(planner):
    """Read the recipe shelf and check it against the planner's vocabulary.

    A typo in `diet:` or `allergens:` would quietly make a recipe unfindable in
    the planner, so the build stops and says which recipe is wrong.
    """
    diets = [d["key"] for d in planner["diets"]]
    allergens = [a["key"] for a in planner["allergens"]]
    slots = list(planner["slots"].keys())

    recipes = []
    seen = set()
    for raw in load_yaml(DATA / "recipes.yml"):
        recipe = dict(raw)
        slug = str(recipe.get("slug") or "").strip()
        where = f"recipe “{recipe.get('title') or slug or '?'}”"
        if not slug:
            raise SystemExit(f"{where} has no slug — it needs one to get a page.")
        if slug in seen:
            raise SystemExit(f"{where} reuses the slug “{slug}” — slugs must be unique.")
        seen.add(slug)

        if recipe.get("slot") not in slots:
            raise SystemExit(f"{where} has slot “{recipe.get('slot')}” — use one of {', '.join(slots)}.")
        if recipe.get("diet") not in diets:
            raise SystemExit(f"{where} has diet “{recipe.get('diet')}” — use one of {', '.join(diets)}.")

        unknown = [a for a in recipe.get("allergens") or [] if a not in allergens]
        if unknown:
            raise SystemExit(
                f"{where} lists unknown allergen(s) {', '.join(unknown)} — "
                f"use {', '.join(allergens)}."
            )

        for field in ("calories", "protein", "carbs", "fat", "minutes"):
            value = recipe.get(field)
            if not isinstance(value, int) or value < 0:
                raise SystemExit(f"{where} needs a whole number for “{field}”.")

        recipe.setdefault("allergens", [])
        recipe.setdefault("tags", [])
        recipe.setdefault("ingredients", [])
        recipe.setdefault("steps", [])
        recipe["diet_label"] = next(d["label"] for d in planner["diets"] if d["key"] == recipe["diet"])
        recipe["slot_label"] = planner["slots"][recipe["slot"]]
        recipe["allergen_labels"] = [
            next(a["label"] for a in planner["allergens"] if a["key"] == key)
            for key in recipe["allergens"]
        ]
        recipes.append(recipe)

    order = {slot: i for i, slot in enumerate(SLOT_ORDER)}
    recipes.sort(key=lambda r: (order.get(r["slot"], 99), r["title"].lower()))
    return recipes


def main():
    site = load_yaml(DATA / "site.yml")
    planner = load_yaml(DATA / "planner.yml")
    about = load_yaml(DATA / "about.yml")
    recipes = load_recipes(planner)

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    env.filters["markdown"] = render_markdown

    featured = [r for slug in planner.get("featured", []) for r in recipes if r["slug"] == slug]

    context = {
        "site": site,
        "planner": planner,
        "about": about,
        "recipes": recipes,
        "featured": featured,
        "asset_version": asset_version(["styles.css", "app.js"]),
        "year": datetime.now().year,
    }

    # Start each build from a clean slate, keeping only the files we must keep.
    if OUTPUT.exists():
        for child in OUTPUT.iterdir():
            if child.name in PRESERVE:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for template_name, (out_name, page_id) in PAGES.items():
        template = env.get_template(template_name)
        write(OUTPUT / out_name, template.render(base="", page=page_id, **context))
        print(f"  {out_name}")

    # One page per recipe: docs/recipes/<slug>/index.html
    for recipe in recipes:
        template = env.get_template("recipe.html")
        html = template.render(recipe=recipe, base="../../", page="recipes", **context)
        write(OUTPUT / "recipes" / recipe["slug"] / "index.html", html)
        print(f"  recipes/{recipe['slug']}/index.html")

    # The data the browser-side planner runs on. Everything the generator needs
    # to know about meals, diets and allergens lives in planner.yml, so this is
    # the single source of truth for both the pages and the JavaScript.
    planner_data = {
        "defaults": planner["defaults"],
        "limits": planner["limits"],
        "mealCounts": {str(k): v for k, v in planner["meal_counts"].items()},
        "slots": planner["slots"],
        "diets": planner["diets"],
        "allergens": planner["allergens"],
        "recipes": [
            {
                "slug": r["slug"],
                "title": r["title"],
                "slot": r["slot"],
                "diet": r["diet"],
                "minutes": r["minutes"],
                "calories": r["calories"],
                "protein": r["protein"],
                "carbs": r["carbs"],
                "fat": r["fat"],
                "allergens": r["allergens"],
                "tags": r["tags"],
            }
            for r in recipes
        ],
    }
    write(OUTPUT / "data" / "planner.json", json.dumps(planner_data, indent=2))
    print("  data/planner.json")

    write(OUTPUT / ".nojekyll", "")

    for asset in ASSETS:
        src = ROOT / asset
        if src.exists():
            write(OUTPUT / asset, src.read_text(encoding="utf-8"))
            print(f"  {asset}")

    cname = ROOT / "CNAME"
    if cname.exists():
        write(OUTPUT / "CNAME", cname.read_text(encoding="utf-8"))
        print("  CNAME")

    print(f"\nDone — {len(PAGES)} pages + {len(recipes)} recipes written to {OUTPUT}/")


if __name__ == "__main__":
    main()
