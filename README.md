# Protein Plate

A high-protein meal planner, live at
**[proteinplate.co.uk](https://proteinplate.co.uk)**, built as a static site
from YAML data. Pick a calorie and protein target, choose how you eat, and it
builds a day from the recipe shelf — then lets you swap any meal or shuffle the
lot.

## How it works

```
data/site.yml       site title, description, contact details, SEO
data/planner.yml    generator defaults, ranges, meal patterns, diets, allergens
data/about.yml      the words on the How it works page
data/recipes.yml    the recipe shelf (the only file you need to add recipes)
data/foods.yml      per-100g nutrition table (built from CoFID 2021)
nutrition.py        ingredient -> calories/protein/carbs/fat/fibre maths
tools/              scripts that build foods.yml and migrated the recipes
templates/*.html    Jinja2 layouts — base, planner, recipes, recipe, about
styles.css          all the styling; section 1 holds every design token
app.js              the planner itself (runs in the browser)
generate.py         reads the YAML, renders templates, writes docs/
docs/               the built site (generated — do not hand-edit)
serve.py            rebuilds and serves the dev preview on port 8090
editor.py           the editing page (Flask) on port 9003 — see below
Makefile            build / preview / deploy
deploy/             systemd unit for the always-on copy on port 9002
```

The generator runs client-side so it is instant and works on GitHub Pages. At
build time `generate.py` writes `docs/data/planner.json` from the YAML, which
is the single source of truth for the recipes and the planner's rules.

## Building locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python generate.py
.venv/bin/python serve.py        # http://simon-dev.rebecchi.uk:8090
```

`make build` and `make preview` do the same thing.

To regenerate the nutrition table from a fresh CoFID spreadsheet:

```bash
.venv/bin/pip install -r requirements-tools.txt
.venv/bin/python tools/build_foods.py /path/to/cofid.xlsx
```

CoFID 2021 is published by Public Health England under the Open Government
Licence v3.0. The generated `data/foods.yml` is committed, so normal builds do
not need the spreadsheet.

## Adding a recipe

Append a block to `data/recipes.yml`:

```yaml
- slug: my-new-meal              # becomes /recipes/my-new-meal/
  title: My New Meal
  slot: dinner                   # breakfast | lunch | dinner | snack
  diet: omnivore                 # omnivore | pescatarian | vegetarian | vegan
  minutes: 25
  servings: 1                    # how many servings the ingredients make
  allergens: [dairy]             # any of the keys in planner.yml
  tags: [quick, batch-cook]
  ingredients:
  - food: chicken-breast         # a key in data/foods.yml
    grams: 150
    label: 150 g chicken breast  # optional display text
  - food: brown-rice
    grams: 150
    label: 150 g cooked brown rice
  steps:
  - Cook the rice.
  - Griddle the chicken and serve.
  note: Optional serving suggestion.
```

Calories, protein, carbs, fat and fibre are **calculated at build time** from
the ingredient weights — do not type them in. The calculation uses
`data/foods.yml`, a per-100g table built from the UK
[CoFID 2021](https://www.gov.uk/government/publications/composition-of-foods-integrated-dataset-cofid)
dataset. Fibre is AOAC fibre where CoFID has it, falling back to NSP; a few
products CoFID doesn't cover use a labelled typical value (see the note on the
food entry).

The build checks the recipe's `slug`, `slot`, `diet`, `allergens`, servings and
ingredient foods, and stops with a clear message if one is wrong. The recipe is
picked up by the planner automatically.

## Meal plans

The planner fills each slot in the pattern for the chosen number of meals
(`meal_counts` in `data/planner.yml`), filters by diet and allergens, then
searches for the combination closest to the calorie and protein targets. It
prefers not to repeat a recipe, and snacks are the only slot allowed to repeat.

## The editing page

`editor.py` is a small Flask app that lets the (non-technical) owner change
everything from a browser, with no YAML:

```bash
.venv/bin/pip install -r requirements-editor.txt   # Flask + ruamel.yaml
make edit                                          # foreground, port 9003
make deploy-editor                                 # install + start the service
```

- **Recipes** — add, edit and delete. Ingredients are picked from the food
  table with a weight in grams; nutrition is calculated for you. The shelf, the
  counts and the planner all follow on the next build.
- **Planner** — defaults, slider ranges, meal patterns, meals, diets, allergens
  and the featured recipes.
- **How it works** — the title, intro, body and closing note on the about page.
- **Site** — the site's own words.
- Saving rebuilds `docs/` and makes a local commit. **Publish to live** in the
  header pushes `main`; GitHub Actions then rebuilds proteinplate.co.uk.
- Recipes are re-emitted by a hand-rolled writer that matches the hand-written
  file byte for byte; `site.yml` / `planner.yml` / `about.yml` use ruamel in
  round-trip mode, where a no-op save must produce no diff.

## Publishing

The live site is **https://proteinplate.co.uk**, published by GitHub Actions
from `main` in
[Simreb176/protein-plate](https://github.com/Simreb176/protein-plate). The
workflow rebuilds `docs/` and deploys it; the custom domain comes from the
`CNAME` file at the repo root.

DNS is proxied through Cloudflare, which also terminates TLS. That means
GitHub's **Enforce HTTPS** toggle stays unavailable — use Cloudflare's
**SSL/TLS → Edge Certificates → Always Use HTTPS** if you want `http://` to
redirect to `https://`.

The always-on copy on this machine runs under systemd:

```bash
make deploy     # port 9002
make status
make logs
```
