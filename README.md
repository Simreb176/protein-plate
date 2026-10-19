# Protein Plate

A high-protein meal planner, built as a static site from YAML data. Pick a
calorie and protein target, choose how you eat, and it builds a day from the
recipe shelf — then lets you swap any meal or shuffle the lot.

## How it works

```
data/site.yml       site title, description, contact details, SEO
data/planner.yml    generator defaults, ranges, meal patterns, diets, allergens
data/recipes.yml    the recipe shelf (the only file you need to add recipes)
templates/*.html    Jinja2 layouts — base, planner, recipes, recipe, about
styles.css          all the styling; section 1 holds every design token
app.js              the planner itself (runs in the browser)
generate.py         reads the YAML, renders templates, writes docs/
docs/               the built site (generated — do not hand-edit)
serve.py            rebuilds and serves the dev preview on port 8090
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

## Adding a recipe

Append a block to `data/recipes.yml`:

```yaml
- slug: my-new-meal              # becomes /recipes/my-new-meal/
  title: My New Meal
  slot: dinner                   # breakfast | lunch | dinner | snack
  diet: omnivore                 # omnivore | pescatarian | vegetarian | vegan
  minutes: 25
  calories: 600
  protein: 45
  carbs: 50
  fat: 20
  allergens: [dairy]             # any of the keys in planner.yml
  tags: [quick, batch-cook]
  ingredients:
    - 150 g chicken breast
    - 100 g rice
  steps:
    - Cook the rice.
    - Griddle the chicken and serve.
  note: Optional serving suggestion.
```

The build checks the recipe's `slot`, `diet` and `allergens` against
`data/planner.yml` and stops with a clear message if one is wrong. The recipe
is picked up by the planner automatically.

## Meal plans

The planner fills each slot in the pattern for the chosen number of meals
(`meal_counts` in `data/planner.yml`), filters by diet and allergens, then
searches for the combination closest to the calorie and protein targets. It
prefers not to repeat a recipe, and snacks are the only slot allowed to repeat.

## Publishing

The site is plain static files, so any static host works. For GitHub Pages,
push `main` — `.github/workflows/pages.yml` rebuilds and publishes `docs/`.
To add a custom domain, put it in a `CNAME` file at the repo root (it is copied
into the build) and point the DNS at GitHub Pages.

The always-on copy on this machine runs under systemd:

```bash
make deploy     # port 9002
make status
make logs
```
