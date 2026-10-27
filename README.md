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
data/recipes.yml    the recipe shelf (the only file you need to add recipes)
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

## The editing page

`editor.py` is a small Flask app that lets the (non-technical) owner change
everything from a browser, with no YAML:

```bash
.venv/bin/pip install -r requirements-editor.txt   # Flask + ruamel.yaml
make edit                                          # foreground, port 9003
make deploy-editor                                 # install + start the service
```

- **Recipes** — add, edit and delete; the shelf, the counts and the planner all
  follow on the next build.
- **Planner** — defaults, slider ranges, meal patterns, meals, diets, allergens
  and the featured recipes.
- **Site** — the site's own words.
- Saving rebuilds `docs/` and makes a local commit. There is no remote here, so
  there is no push.
- Recipes are re-emitted by a hand-rolled writer that matches the hand-written
  file byte for byte; `site.yml` / `planner.yml` use ruamel in round-trip mode,
  where a no-op save must produce no diff.

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
