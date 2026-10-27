# AGENTS.md — notes for the AI agent working on this site

## 1. What this is

Protein Plate is a static meal-planning site. Pick a calorie and protein target,
choose a diet and any allergens to avoid, and it builds a day from a shelf of
recipes. Everything is generated from YAML by `generate.py`; the planner itself
runs in the browser in `app.js` and reads `docs/data/planner.json`.

There is no database, no account system and no server-side code at runtime.

## 2. Map of the repo

| Path | What it is | You edit it? |
|------|-----------|--------------|
| `data/site.yml` | Site title, description, contact, social links, SEO | Yes — content |
| `data/planner.yml` | Defaults, slider ranges, meal patterns, diets, allergens, featured recipes | Yes — behaviour |
| `data/about.yml` | The words on the How it works page (Markdown) | Yes — content |
| `data/recipes.yml` | The recipe shelf — one block per recipe | Yes — content |
| `templates/*.html` | Jinja2 layouts: `base`, `index` (planner), `recipes`, `recipe`, `about` | Yes — layout |
| `styles.css` | All styling. Section 1 holds every design token | Yes — appearance |
| `app.js` | The planner: filtering, search, rendering, swaps | Yes — behaviour |
| `generate.py` | Reads YAML, validates recipes, renders pages, writes `docs/` | Yes — when adding features |
| `serve.py` | Rebuilds and serves the dev preview on port 8090 | Rarely |
| `editor.py` | The owner's editing page (Flask) on port 9003: recipes, planner, about, site | Yes — part of the product |
| `editor_templates/*.html` | The editing page's screens (`base`, `site_edit`, `planner_edit`, `about_edit`, `recipes`, `recipe_form`) | Yes |
| `editor_static/editor.css` | The editing page's stylesheet (not the site's) | Yes |
| `Makefile` | `build`, `preview`, `deploy`, `status`, `logs`, `edit`, `deploy-editor` | Yes |
| `deploy/proteinplate.service` | systemd unit for the always-on copy on port 9002 | Yes |
| `deploy/proteinplate-editor.service` | systemd unit for the editing page on port 9003 | Yes |
| `docs/` | The **generated** site. Never hand-edit; it is overwritten | No (generated) |
| `.github/workflows/pages.yml` | Builds and publishes on push to `main` | No |

## 3. The loop

```bash
.venv/bin/python generate.py     # rebuild docs/
.venv/bin/python serve.py        # rebuild + serve on 0.0.0.0:8090
```

- Preview: **http://simon-dev.rebecchi.uk:8090** (also LAN at
  `http://192.168.1.127:8090`). Ports on this box: **8090** this repo's preview,
  **9002** this repo's always-on copy, **8080** the sibling run-a-mile preview,
  **9001** the run-a-mile editing page. Don't share a port.
- Always rebuild and check before showing the result.
- `make build`, `make preview` do the same thing.

### Adding or changing a recipe

Append to `data/recipes.yml` in the same shape as the existing blocks. Required
fields: `slug`, `title`, `slot`, `diet`, `minutes`, `calories`, `protein`,
`carbs`, `fat`. Optional: `allergens`, `tags`, `ingredients`, `steps`, `note`.

The build validates:

- `slug` is present and unique;
- `slot` is in `planner.yml` → `slots`;
- `diet` is in `planner.yml` → `diets`;
- every `allergens` entry is in `planner.yml` → `allergens`;
- `minutes`, `calories`, `protein`, `carbs` and `fat` are whole numbers.

If you add a new diet or allergen key, add it to `planner.yml` too — the pages
and the planner both build their vocabularies from there.

### How the planner chooses meals

`app.js` fills one recipe per slot in the pattern for the chosen meal count
(`meal_counts` in `planner.yml`). It filters by diet (a recipe suits every diet
to its right: vegan → vegetarian → pescatarian → omnivore) and by allergens,
then does a hill-climb search over combinations to get closest to the calorie
and protein targets. Protein is weighted higher than calories. Main meals never
repeat; snacks may, at a cost. `rankSwaps` finds alternatives for one slot.

### The editing page (the owner can do it himself)

`make deploy-editor` installs and starts `deploy/proteinplate-editor.service`
on **port 9003**. It writes the same `data/*.yml` files, so anything it does
you can do, and vice versa:

- **Recipes** (`/recipes`): list with a filter, add, edit, delete. Deleting
  removes the recipe *and* its generated page (the build wipes `docs/`).
- **Planner** (`/planner`): defaults, slider ranges, meal patterns, meals,
  diets, allergens, featured recipes. It refuses to save a diet/allergen/meal
  that a recipe still uses rather than breaking the build.
- **How it works** (`/about`): eyebrow, title, subtitle, the Markdown body and
  the closing contact note. `{recipes}` in the body becomes the current count.
- **Site** (`/`): the site's own words.
- Every save rebuilds and makes a local commit ("Edit from the editing page").
  **Publish to live** in the header pushes `main`; GitHub Actions rebuilds the
  public site. The push uses the repo's SSH remote and the service's `HOME`.
- **Recipes are written by a hand-rolled writer** (`write_recipes` in
  `editor.py`) that reproduces the hand-written file byte for byte — the
  nested ingredient/step lists and the inline `[dairy, gluten]` style depend on
  it. `site.yml` / `planner.yml` / `about.yml` go through ruamel in round-trip
  mode, and a no-op save must produce no diff — including the block scalar in
  `about.yml`. Test both after touching the editor.
- After changing `editor.py`, run `make deploy-editor` — the service runs from
  this working tree and keeps the old code until restarted.

## 4. Preview and publish

The site is static. Locally:

```bash
.venv/bin/python serve.py         # port 8090
```

The always-on copy on this machine:

```bash
make deploy                       # installs + starts port 9002
make status
make logs
```

To publish publicly, push `main`; GitHub Actions rebuilds and deploys `docs/`
to **https://proteinplate.co.uk** (repo:
`git@github.com:Simreb176/protein-plate.git`). The custom domain is in `CNAME`
at the repo root and copied into the build.

DNS is proxied through Cloudflare, so GitHub's "Enforce HTTPS" toggle stays
unavailable; HTTPS is terminated by Cloudflare. If `http://` should redirect to
`https://`, use Cloudflare's **SSL/TLS → Edge Certificates → Always Use HTTPS**.

## 5. Definition of done

1. `generate.py` builds with no errors or validation messages.
2. The preview looks right on a wide screen and a narrow one: planner (generate,
   swap, shuffle), recipes list, one recipe page, about.
3. Links resolve from recipe pages (they live at `/recipes/<slug>/`, so every
   link uses the `base` prefix — keep using `{{ base }}`).
4. Any new recipe or config key is valid, and the planner still works for every
   diet and meal count. Quick check:

   ```bash
   node -e '
     const P = require("./app.js");
     const d = require("./docs/data/planner.json");
     for (const diet of ["omnivore","pescatarian","vegetarian","vegan"])
       for (const meals of [2,3,4,5,6]) {
         const r = P.makePlan({...d, recipes:d.recipes, mealCounts:d.mealCounts,
           slots:d.slots, meals, diet, calories:2100, protein:150, avoid:[]});
         console.log(diet, meals, r.error || "ok");
       }'
   ```

5. Committed (and pushed, if there is a remote).
