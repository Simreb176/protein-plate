# Editing Protein Plate — the plain-English guide

This is your site: **Protein Plate**, a high-protein meal planner. You don't
have to touch any code — describe what you want and it gets done. This guide is
for when you're curious, or want to change a recipe by hand.

## The easy way: just ask

Open the assistant in this folder and say what you'd like:

> "Add a recipe for a chicken and chorizo traybake."
> "The default protein target should be 160 g."
> "Try a warmer colour for the accent."
> "Add a 'no shellfish' filter."

The assistant edits the files, rebuilds the site and gives you a link to look
at. Nothing goes live until it's published.

## The three content files

Everything the site says comes from `data/`:

| File | What it holds |
|------|---------------|
| `data/recipes.yml` | The recipe shelf — every meal the planner can choose |
| `data/planner.yml` | Defaults, slider ranges, meal patterns, diets and allergens |
| `data/site.yml` | Site name, description, email and social links |

YAML is just lists of `key: value` pairs. Indentation matters: items that line
up belong together. Copy the block above when in doubt.

## Adding a recipe

Add a block to `data/recipes.yml` in the same shape as the others:

```yaml
- slug: chicken-chorizo-traybake     # the web address, lowercase with hyphens
  title: Chicken & Chorizo Traybake
  slot: dinner                      # breakfast | lunch | dinner | snack
  diet: omnivore                    # omnivore | pescatarian | vegetarian | vegan
  minutes: 35
  calories: 640
  protein: 48
  carbs: 45
  fat: 26
  allergens: [dairy]                # dairy, gluten, eggs, fish, shellfish, soy, nuts, sesame
  tags: [one-pan, batch-cook]
  ingredients:
    - 150 g chicken breast
    - 60 g chorizo
    - 250 g potatoes
  steps:
    - Heat the oven to 200°C.
    - Roast everything for 30 minutes.
  note: Optional serving suggestion.
```

Then rebuild and look at the preview. The planner picks it up automatically.
Keep `calories`, `protein`, `carbs`, `fat` and `minutes` as plain numbers.

## Changing the planner's defaults

Open `data/planner.yml`:

- **`defaults`** — what the sliders start at (calories, protein, meals, diet).
- **`limits`** — the smallest and largest value each slider offers.
- **`meal_counts`** — which meals make up a day for 2, 3, 4, 5 or 6 meals.
- **`diets`** and **`allergens`** — the vocabulary used by the filter and by
  every recipe. If you add one here, recipes can start using it.
- **`featured`** — the recipes shown on the home page (use their slugs).

## Changing how it looks

- **`styles.css`** — section 1 at the top holds every colour, font and spacing
  token. Changing `--accent` restyles the whole site.
- **`templates/`** — the page layouts. `base.html` is the header, footer and
  page frame; `index.html` is the planner; `recipes.html` is the shelf;
  `recipe.html` is a single recipe; `about.html` is the guide page.

The site follows the visitor's light/dark setting automatically and adapts to
phones.

## Looking before publishing

The development version is rebuilt every time you save:

**http://simon-dev.rebecchi.uk:8090**

Nothing there is public. When you're happy, publish — the live site updates a
minute or so later.

## If something breaks

Nothing is lost; every version is saved. The usual culprit is a typo in YAML —
a missing slug, an allergen key that isn't in `planner.yml`, or a non-number in
a calorie field. The build stops and names the recipe and the field. Ask the
assistant to fix it and rebuild.
