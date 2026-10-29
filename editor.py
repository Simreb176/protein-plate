#!/usr/bin/env python3
"""Protein Plate — the editing page.

Change the site's words and the recipe shelf from a browser, with no YAML:

    .venv/bin/python editor.py
    # then open http://simon-dev.rebecchi.uk:9003

Screens:
    Site           the name, description, contact details and social links
    Planner        defaults, slider ranges, meal patterns, diets, allergens, featured
    How it works   the words on the about page
    Recipes        the shelf: add, edit and remove recipes

Everything is written back to `data/*.yml`, the site is rebuilt, and the change
is committed locally — so the page at :9002 is up to date straight away and
every version can be undone.

Recipes are written in exactly the shape the hand-written file uses (there is a
byte-for-byte check for that), and site.yml / planner.yml are edited with a
comment-preserving round-trip, so saving without changes produces no diff.

Dependencies: `requirements-editor.txt` (Flask + ruamel.yaml). The site build
itself only needs `requirements.txt`.
"""
from __future__ import annotations

import os
import re
import secrets
import subprocess
import sys
import time
from io import StringIO
from itertools import zip_longest
from pathlib import Path

import yaml
from flask import Flask, flash, redirect, render_template, request, url_for
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import LiteralScalarString

from nutrition import NutritionError, compute, display_label, load_foods

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "editor_templates"
SITE_PORT = 9002  # the always-on copy of the site
PORT = int(os.environ.get("EDITOR_PORT", "9003"))

SECRET_FILE = ROOT / ".editor-secret"
COMMIT_MESSAGE = "Edit from the editing page"

RECIPE_FIELDS = ["slug", "title", "slot", "diet", "minutes", "calories", "protein", "carbs", "fat",
                 "allergens", "tags", "ingredients", "steps", "note"]


class EditorError(Exception):
    """Something to explain to the person typing, rather than a traceback."""


# --------------------------------------------------------------------------
# Reading and writing YAML
# --------------------------------------------------------------------------
def yaml_io():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def load_map(path):
    data = yaml_io().load(path.read_text(encoding="utf-8"))
    return {} if data is None else data


def dump(path, data):
    buf = StringIO()
    yaml_io().dump(data, buf)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    os.replace(tmp, path)


def load_recipes():
    """Plain dicts: the recipes file is written by hand-rolled code, not ruamel."""
    return yaml.safe_load((DATA / "recipes.yml").read_text(encoding="utf-8")) or []


def load_food_data():
    return load_foods(DATA / "foods.yml")[0]


def decorated(recipe):
    """A recipe with its calculated per-serving nutrition attached."""
    foods = load_food_data()
    result = dict(recipe)
    result.update(compute(recipe, foods))
    result["ingredient_lines"] = [display_label(row, foods) for row in recipe.get("ingredients") or []]
    return result


def normalise(text):
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def same(current, value):
    if current is None or value is None:
        return current is None and value is None
    return normalise(current).strip() == normalise(value).strip()


def set_value(mapping, key, value):
    """Leave a value alone when it hasn't changed, so formatting survives."""
    if key in mapping and same(mapping[key], value):
        return
    mapping[key] = value


def slugify(raw):
    return re.sub(r"[^a-z0-9]+", "-", normalise(raw).strip().lower()).strip("-")


# --- recipes: a writer that matches the hand-written file exactly ----------
TIME_RE = re.compile(r"^\d{1,3}:\d{2}$")
NUMBER_RE = re.compile(r"[-+]?\d+(\.\d+)?$")
YAML_WORDS = {"true", "false", "yes", "no", "on", "off", "null", "~"}


def needs_quotes(text):
    if not text or text != text.strip():
        return True
    if text[0] in "-?:,[]{}#&*!|>'\"%@`":
        return True
    if ": " in text or text.endswith(":") or " #" in text:
        return True
    return text.lower() in YAML_WORDS or bool(NUMBER_RE.match(text)) or bool(TIME_RE.match(text))


def scalar(value):
    text = str(value)
    return f'"{text}"' if needs_quotes(text) else text


def write_recipes(recipes):
    path = DATA / "recipes.yml"
    header = path.read_text(encoding="utf-8").split("- slug:")[0]

    blocks = []
    for recipe in recipes:
        lines = [f"- slug: {scalar(recipe['slug'])}"]
        for key in ("title", "slot", "diet"):
            lines.append(f"  {key}: {scalar(recipe.get(key, ''))}")
        for key in ("minutes", "servings"):
            lines.append(f"  {key}: {recipe.get(key, 0)}")
        for key in ("allergens", "tags"):
            values = recipe.get(key) or []
            lines.append(f"  {key}: [{', '.join(scalar(v) for v in values)}]")
        lines.append("  ingredients:")
        for item in recipe.get("ingredients") or []:
            lines.append(f"  - food: {scalar(item['food'])}")
            lines.append(f"    grams: {item['grams']:g}")
            if item.get("label"):
                lines.append(f"    label: {scalar(item['label'])}")
        for key in ("steps",):
            values = recipe.get(key) or []
            if values:
                lines.append(f"  {key}:")
                lines.extend(f"  - {scalar(v)}" for v in values)
            else:
                lines.append(f"  {key}: []")
        if recipe.get("note"):
            lines.append(f"  note: {scalar(recipe['note'])}")
        blocks.append("\n".join(lines))

    text = (header.rstrip() + "\n\n" if header.strip() else "") + "\n\n".join(blocks) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Saving
# --------------------------------------------------------------------------
def save_site(form):
    site = load_map(DATA / "site.yml")
    set_value(site, "title", normalise(form.get("title")).strip())
    set_value(site, "description", normalise(form.get("description")).strip())
    set_value(site, "url", normalise(form.get("url")).strip())

    author = site.get("author") or {}
    for key in ("name", "tagline", "location", "email"):
        set_value(author, key, normalise(form.get(f"author_{key}")).strip())

    social = site.get("social") or {}
    for network in ("github", "instagram", "twitter"):
        set_value(social, network, normalise(form.get(f"social_{network}")).strip() or None)

    seo = site.get("seo") or {}
    set_value(seo, "description", normalise(form.get("seo_description")).strip())

    dump(DATA / "site.yml", site)


def save_planner(form):
    planner = load_map(DATA / "planner.yml")

    defaults = planner.get("defaults") or {}
    for key in ("calories", "protein", "meals"):
        set_value(defaults, key, int(form.get(f"default_{key}", 0) or 0))
    set_value(defaults, "diet", normalise(form.get("default_diet")).strip())

    limits = planner.get("limits") or {}
    for key in ("calories", "protein", "meals"):
        low = int(form.get(f"limit_{key}_min", 0) or 0)
        high = int(form.get(f"limit_{key}_max", 0) or 0)
        if high < low:
            raise EditorError(f"The {key} range is back to front: minimum {low}, maximum {high}.")
        set_value(limits, key, [low, high])

    slots = planner.get("slots") or {}
    slot_rows = []
    for key, label in zip(form.getlist("slot_key"), form.getlist("slot_label")):
        key, label = slugify(key), normalise(label).strip()
        if key:
            slot_rows.append((key, label or key.title()))
    if not slot_rows:
        raise EditorError("The planner needs at least one meal (breakfast, lunch…).")

    counts = {}
    for line in normalise(form.get("meal_counts")).strip().splitlines():
        line = line.strip()
        if not line:
            continue
        number, _, meals = line.partition(":")
        try:
            key = int(number.strip())
        except ValueError:
            raise EditorError(f"“{line}” doesn't start with a number of meals, e.g. “4: breakfast, snack, lunch, dinner”.")
        chosen = [part.strip() for part in meals.split(",") if part.strip()]
        unknown = [slot for slot in chosen if slot not in dict(slot_rows)]
        if unknown:
            raise EditorError(f"The {key}-meal day uses “{unknown[0]}”, which isn't one of the meals above.")
        counts[key] = chosen
    if not counts:
        raise EditorError("The planner needs at least one meal pattern.")

    diets = _rows(form, "diet", ("key", "label", "description"))
    if not diets:
        raise EditorError("The planner needs at least one way of eating.")
    allergens = _rows(form, "allergen", ("key", "label"))

    recipes = load_recipes()
    for recipe in recipes:
        if recipe.get("slot") not in dict(slot_rows):
            raise EditorError(
                f"The recipe “{recipe['title']}” is a “{recipe.get('slot')}”, which you just removed. "
                "Put the meal back, or change the recipe first."
            )
        if recipe.get("diet") not in [d["key"] for d in diets]:
            raise EditorError(f"The recipe “{recipe['title']}” uses the diet “{recipe.get('diet')}”, which no longer exists.")
        unknown = [a for a in recipe.get("allergens") or [] if a not in [a["key"] for a in allergens]]
        if unknown:
            raise EditorError(f"The recipe “{recipe['title']}” lists “{unknown[0]}”, which is no longer an allergen.")

    # Only touch a section when it has actually changed: that is what keeps the
    # comments in planner.yml intact when someone just presses Save.
    if dict(planner.get("slots") or {}) != dict(slot_rows):
        planner["slots"] = CommentedMap(slot_rows)

    current_counts = {int(k): [str(v) for v in meals]
                      for k, meals in (planner.get("meal_counts") or {}).items()}
    if current_counts != counts:
        planner["meal_counts"] = CommentedMap((n, flow(meals)) for n, meals in counts.items())

    merged_diets = _merge_rows(planner.get("diets") or [], diets, "key")
    if not same_sequence(planner.get("diets"), merged_diets):
        planner["diets"] = merged_diets

    merged_allergens = _merge_rows(planner.get("allergens") or [], allergens, "key")
    if not same_sequence(planner.get("allergens"), merged_allergens):
        planner["allergens"] = merged_allergens

    featured = flow([slug for slug in form.getlist("featured") if slug])
    if not same_sequence(planner.get("featured"), featured, as_rows=False):
        planner["featured"] = featured

    dump(DATA / "planner.yml", planner)


def flow(items):
    """A list written inline, like the hand-written [dairy, gluten]."""
    seq = CommentedSeq(items)
    seq.fa.set_flow_style()
    return seq


def plain_rows(rows):
    return [{k: str(v) for k, v in row.items()} for row in rows]


def same_sequence(existing, wanted, as_rows=True):
    if existing is None:
        return False
    if as_rows:
        return plain_rows(existing) == plain_rows(wanted)
    return [str(x) for x in existing] == [str(x) for x in wanted]


def _rows(form, prefix, fields):
    columns = [form.getlist(f"{prefix}_{field}") for field in fields]
    rows = []
    for values in zip(*columns):
        row = {field: normalise(value).strip() for field, value in zip(fields, values)}
        if not row.get(fields[0]):
            continue
        rows.append(row)
    return rows


def _merge_rows(existing, rows, key):
    """Reuse the loaded row objects so their comments and quoting survive."""
    pool = {}
    for row in existing:
        pool.setdefault(str(row.get(key, "")), []).append(row)
    merged = []
    for row in rows:
        waiting = pool.get(row[key]) or []
        old = waiting.pop(0) if waiting else {}
        for field, value in row.items():
            set_value(old, field, value)
        merged.append(old)
    return merged


def save_about(form):
    """The How it works page. Nothing is written when nothing changed."""
    about = load_map(DATA / "about.yml")

    fields = ("eyebrow", "heading", "subtitle", "contact_heading", "contact_text")
    values = {key: normalise(form.get(key)).strip() for key in fields}
    story = normalise(form.get("story")).strip("\n")

    changed = any(not same(about.get(key), value) for key, value in values.items())
    story_changed = not same(about.get("story"), story)

    if not changed and not story_changed:
        return

    for key, value in values.items():
        set_value(about, key, value)
    if story_changed:
        about["story"] = LiteralScalarString(story + "\n") if story else ""

    dump(DATA / "about.yml", about)


def save_recipe(form, original_slug):
    planner = load_map(DATA / "planner.yml")
    recipes = load_recipes()
    foods = load_food_data()

    slot_keys = list((planner.get("slots") or {}).keys())
    diet_keys = [d["key"] for d in planner.get("diets") or []]
    allergen_keys = [a["key"] for a in planner.get("allergens") or []]

    title = normalise(form.get("title")).strip()
    slug = slugify(form.get("slug")) or slugify(title)
    problems = []
    if not title:
        problems.append("A recipe needs a title.")
    if not slug:
        problems.append("A recipe needs a web address (the slug).")

    numbers = {}
    for field in ("minutes", "servings"):
        raw = normalise(form.get(field)).strip()
        if not re.fullmatch(r"\d+", raw or "") or int(raw) < 1:
            problems.append(f"“{field}” needs a whole number of at least 1, and “{raw}” isn't one.")
        else:
            numbers[field] = int(raw)

    slot = normalise(form.get("slot")).strip()
    diet = normalise(form.get("diet")).strip()
    if slot not in slot_keys:
        problems.append("Pick one of the meals for this recipe.")
    if diet not in diet_keys:
        problems.append("Pick one of the ways of eating for this recipe.")

    ticks = [a for a in form.getlist("allergens") if a]
    unknown = [a for a in ticks if a not in allergen_keys]
    if unknown:
        problems.append(f"“{unknown[0]}” isn't in the allergen list.")

    ingredients = []
    rows = list(zip_longest(
        form.getlist("ingredient_food"),
        form.getlist("ingredient_grams"),
        form.getlist("ingredient_label"),
        fillvalue="",
    ))
    saw_row = any(food.strip() or grams.strip() for food, grams, _ in rows)
    for food, grams_raw, label in rows:
        food = normalise(food).strip()
        grams_raw = normalise(grams_raw).strip()
        label = normalise(label).strip()
        if not food and not grams_raw:
            continue
        if food not in foods:
            problems.append(f"“{food or '(blank)'}” isn't one of the foods in the nutrition table.")
            continue
        if not re.fullmatch(r"\d+(\.\d+)?", grams_raw):
            problems.append(f"The grams for “{label or foods[food]['name']}” need to be a number.")
            continue
        grams = float(grams_raw) if "." in grams_raw else int(grams_raw)
        if grams <= 0:
            problems.append(f"The grams for “{label or foods[food]['name']}” need to be more than zero.")
            continue
        row = {"food": food, "grams": grams}
        if label:
            row["label"] = label
        ingredients.append(row)
    if not ingredients and not saw_row:
        problems.append("Add at least one ingredient.")

    others = [r for r in recipes if r["slug"] != original_slug]
    if any(r["slug"] == slug for r in others):
        problems.append(f"There's already a recipe at “{slug}” — give this one a different address.")

    recipe = {
        "slug": slug,
        "title": title,
        "slot": slot,
        "diet": diet,
        "minutes": numbers.get("minutes", 1),
        "servings": numbers.get("servings", 1),
        "allergens": ticks,
        "tags": [tag.strip() for tag in normalise(form.get("tags")).split(",") if tag.strip()],
        "ingredients": ingredients,
        "steps": [line.strip() for line in normalise(form.get("steps")).splitlines() if line.strip()],
    }
    note = normalise(form.get("note")).strip()
    if note:
        recipe["note"] = note

    if not problems:
        try:
            compute(recipe, foods)
        except NutritionError as error:
            problems.append(str(error))

    if problems:
        raise EditorError("Nothing was saved, because of this:\n\n" + "\n".join(f"• {p}" for p in problems))

    if original_slug:
        recipes = [recipe if r["slug"] == original_slug else r for r in recipes]
    else:
        recipes.append(recipe)

    write_recipes(recipes)
    return title


def delete_recipe(slug):
    recipes = load_recipes()
    doomed = next((r for r in recipes if r["slug"] == slug), None)
    if not doomed:
        return None, False
    write_recipes([r for r in recipes if r["slug"] != slug])

    planner = load_map(DATA / "planner.yml")
    featured = [s for s in planner.get("featured") or [] if s != slug]
    if featured != list(planner.get("featured") or []):
        planner["featured"] = featured
        dump(DATA / "planner.yml", planner)
    return doomed["title"], True


# --------------------------------------------------------------------------
# Build, commit, links
# --------------------------------------------------------------------------
def python():
    venv = ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


def run(*args):
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )


def rebuild():
    done = run(python(), "generate.py")
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def commit(message):
    run("git", "add", "-A")
    run("git", "commit", "-m", message)


def publish():
    """Push what's committed (and commit anything left over) to GitHub.

    The site itself is built by GitHub Actions, so a successful push here is
    what makes proteinplate.co.uk update.
    """
    if run("git", "status", "--porcelain").stdout.strip():
        run("git", "add", "-A")
        saved = run("git", "commit", "-m", COMMIT_MESSAGE)
        if saved.returncode != 0:
            return False, (
                "Your changes are safe on this machine, but couldn't be saved as a "
                f"commit, so nothing was published.\n\n{(saved.stderr or saved.stdout).strip()}"
            )

    ahead = run("git", "rev-list", "--count", "@{upstream}..HEAD")
    if ahead.returncode == 0 and ahead.stdout.strip() in ("", "0"):
        return True, "Nothing new to publish — the live site is already up to date."

    pushed = run("git", "push", "origin", "main")
    if pushed.returncode != 0:
        return False, (
            "Your changes are safe on this machine, but GitHub didn't accept the push, "
            "so the live site hasn't changed.\n\n"
            f"{(pushed.stderr or pushed.stdout).strip()}"
        )
    return True, "Published. proteinplate.co.uk updates in about a minute."


def after_save(message):
    """Rebuild and remember — used by every save."""
    ok, output = rebuild()
    if not ok:
        flash(f"Saved, but the site didn't rebuild:\n\n{output}", "bad")
        return
    commit(message)
    flash(f"{message} The site is updated.", "good")


def site_url():
    host = request.host.split(":")[0]
    return f"http://{host}:{SITE_PORT}/"


def read_or_create(path, factory):
    if not path.exists():
        path.write_text(factory(), encoding="utf-8")
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


app = Flask(__name__, template_folder=str(TEMPLATES),
            static_folder=str(ROOT / "editor_static"), static_url_path="/static")
app.secret_key = read_or_create(SECRET_FILE, lambda: secrets.token_hex(32))


@app.context_processor
def chrome():
    return {"site_link": site_url(), "recipe_count": len(load_recipes())}


# --------------------------------------------------------------------------
# Site settings
# --------------------------------------------------------------------------
@app.get("/")
def home():
    return render_template("site_edit.html", site=load_map(DATA / "site.yml"), page="site")


@app.post("/site/save")
def site_save():
    save_site(request.form)
    after_save("Saved the site settings.")
    return redirect(url_for("home"))


# --------------------------------------------------------------------------
# Planner
# --------------------------------------------------------------------------
@app.get("/planner")
def planner_page():
    return render_template(
        "planner_edit.html",
        planner=load_map(DATA / "planner.yml"),
        recipes=load_recipes(),
        page="planner",
    )


@app.post("/planner/save")
def planner_save():
    try:
        save_planner(request.form)
    except EditorError as error:
        flash(str(error), "bad")
        return redirect(url_for("planner_page"))
    after_save("Saved the planner settings.")
    return redirect(url_for("planner_page"))


# --------------------------------------------------------------------------
# How it works
# --------------------------------------------------------------------------
@app.get("/about")
def about_page():
    return render_template(
        "about_edit.html",
        about=load_map(DATA / "about.yml"),
        page="about",
    )


@app.post("/about/save")
def about_save():
    try:
        save_about(request.form)
    except EditorError as error:
        flash(str(error), "bad")
        return redirect(url_for("about_page"))
    after_save("Saved the How it works page.")
    return redirect(url_for("about_page"))


# --------------------------------------------------------------------------
# Recipes
# --------------------------------------------------------------------------
@app.get("/recipes")
def recipes_page():
    return render_template("recipes.html", recipes=[decorated(r) for r in load_recipes()], page="recipes")


@app.get("/recipes/new")
def recipe_new():
    return render_template(
        "recipe_form.html",
        recipe={"slug": "", "title": "", "slot": "", "diet": "",
                "minutes": "", "servings": 1,
                "allergens": [], "tags": [], "ingredients": [], "steps": [], "note": ""},
        foods=load_food_data(),
        planner=load_map(DATA / "planner.yml"),
        editing=False,
        page="recipes",
    )


@app.get("/recipes/<slug>/edit")
def recipe_edit(slug):
    found = next((r for r in load_recipes() if r["slug"] == slug), None)
    if not found:
        flash("That recipe isn't there any more.", "warn")
        return redirect(url_for("recipes_page"))
    return render_template("recipe_form.html", recipe=decorated(found), foods=load_food_data(),
                           planner=load_map(DATA / "planner.yml"), editing=True, page="recipes")


@app.post("/recipes/save")
def recipe_save():
    original = normalise(request.form.get("original_slug")).strip()
    try:
        title = save_recipe(request.form, original)
    except EditorError as error:
        flash(str(error), "bad")
        # Hand back what was typed rather than losing it.
        return (
            render_template(
                "recipe_form.html",
                recipe=_recipe_from_form(request.form),
                foods=load_food_data(),
                planner=load_map(DATA / "planner.yml"),
                editing=bool(original),
                page="recipes",
            ),
            400,
        )
    after_save(f"Saved “{title}”." if original else f"Added “{title}”.")
    return redirect(url_for("recipes_page"))


def _recipe_from_form(form):
    ingredients = []
    for food, grams, label in zip_longest(
        form.getlist("ingredient_food"),
        form.getlist("ingredient_grams"),
        form.getlist("ingredient_label"),
        fillvalue="",
    ):
        food = normalise(food).strip()
        grams = normalise(grams).strip()
        label = normalise(label).strip()
        if not food and not grams:
            continue
        row = {"food": food, "grams": grams}
        if label:
            row["label"] = label
        ingredients.append(row)
    return {
        "slug": normalise(form.get("slug")),
        "title": normalise(form.get("title")),
        "slot": normalise(form.get("slot")),
        "diet": normalise(form.get("diet")),
        "minutes": normalise(form.get("minutes")),
        "servings": normalise(form.get("servings")),
        "allergens": form.getlist("allergens"),
        "tags": [t.strip() for t in normalise(form.get("tags")).split(",") if t.strip()],
        "ingredients": ingredients,
        "steps": normalise(form.get("steps")).strip().splitlines(),
        "note": normalise(form.get("note")),
    }


@app.post("/recipes/delete")
def recipe_delete():
    title, gone = delete_recipe(normalise(request.form.get("slug")).strip())
    if not gone:
        flash("That recipe was already gone.", "warn")
    else:
        after_save(f"Deleted “{title}”.")
    return redirect(url_for("recipes_page"))


# --------------------------------------------------------------------------
# Publishing
# --------------------------------------------------------------------------
@app.post("/publish")
def publish_page():
    ok, message = publish()
    flash(message, "good" if ok else "bad")
    target = normalise(request.form.get("next")).strip() or url_for("home")
    if not target.startswith("/"):
        target = url_for("home")
    return redirect(target)


if __name__ == "__main__":
    print(f"\n  Editing page:  http://simon-dev.rebecchi.uk:{PORT}/")
    print(f"  The site:      http://simon-dev.rebecchi.uk:{SITE_PORT}/\n")
    app.run(host="0.0.0.0", port=PORT, debug=False)
