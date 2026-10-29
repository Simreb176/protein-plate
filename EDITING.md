# Editing Protein Plate — the plain-English guide

This is your site: **Protein Plate**, a high-protein meal planner. You don't
have to touch any code — describe what you want and it gets done. This guide is
for when you're curious, or want to change a recipe by hand.

## The easiest way: the editing page

There's a page for changing everything yourself, at:

**http://simon-dev.rebecchi.uk:9003**

No password — it's only reachable from your own devices. It has four screens:

- **Recipes** — the whole shelf: add a recipe, edit one, delete one. Adding a
  recipe puts it on the site straight away; the counts and the planner pick it
  up by themselves.
- **Planner** — the starting calorie/protein/meal targets, the slider ranges,
  which meals make up a day, and the words used for meals, diets and allergens.
- **How it works** — every word on the How it works page: the title, the intro,
  the body and the closing note.
- **Site** — the site's name, description, contact details and social links.

Press **Save** and the copy on this machine at **:9002** is rebuilt immediately,
and the change is committed so it can be undone. When you're happy, press
**Publish to live** at the top right: that sends the changes to GitHub, and
**proteinplate.co.uk** updates in about a minute.

## The other way: just ask

Open the assistant in this folder and say what you'd like:

> "Add a recipe for a chicken and chorizo traybake."
> "The default protein target should be 160 g."
> "Try a warmer colour for the accent."
> "Add a 'no shellfish' filter."

The assistant edits the files, rebuilds the site and gives you a link to look
at.

## The content files

Everything the site says comes from `data/`:

| File | What it holds |
|------|---------------|
| `data/recipes.yml` | The recipe shelf — every meal the planner can choose |
| `data/planner.yml` | Defaults, slider ranges, meal patterns, diets and allergens |
| `data/about.yml` | The words on the How it works page |
| `data/site.yml` | Site name, description, email and social links |
| `data/foods.yml` | The nutrition table — generated, don't edit by hand |

YAML is just lists of `key: value` pairs. Indentation matters: items that line
up belong together. Copy the block above when in doubt.

## Adding a recipe

The easiest way is the **Recipes** screen: pick a food for each ingredient and
type the weight in grams. The nutrition is calculated for you — there are no
calorie boxes.

By hand, add a block to `data/recipes.yml` in the same shape as the others:

```yaml
- slug: chicken-traybake            # the web address, lowercase with hyphens
  title: Chicken Traybake
  slot: dinner                      # breakfast | lunch | dinner | snack
  diet: omnivore                    # omnivore | pescatarian | vegetarian | vegan
  minutes: 35
  servings: 2                       # how many servings the ingredients make
  allergens: [dairy]                # dairy, gluten, eggs, fish, shellfish, soy, nuts, sesame
  tags: [one-pan, batch-cook]
  ingredients:
  - food: chicken-breast            # a food from data/foods.yml
    grams: 300
    label: 300 g chicken breast     # optional display text
  - food: potatoes
    grams: 500
  steps:
  - Heat the oven to 200°C.
  - Roast everything for 30 minutes.
  note: Optional serving suggestion.
```

Then rebuild and look at the preview. The planner picks it up automatically.
Use a food key that exists in `data/foods.yml`; the build will tell you if it
doesn't.

## Where the nutrition comes from

Calories, protein, carbs, fat and fibre are calculated from the ingredient
weights using the UK **CoFID 2021** dataset (McCance and Widdowson's
Composition of Foods Integrated Dataset). Fibre is AOAC fibre where CoFID has
it. A few products CoFID doesn't cover — 0% Greek yoghurt, protein powders,
seitan and chia — use a typical label value, and the recipe page says so.

It is an estimate, not a lab analysis. Check labels if you need exact numbers,
especially for allergies.

## Changing the planner's defaults

Open `data/planner.yml`:

- **`defaults`** — what the sliders start at (calories, protein, meals, diet).
- **`limits`** — the smallest and largest value each slider offers.
- **`meal_counts`** — which meals make up a day for 2, 3, 4, 5 or 6 meals.
- **`diets`** and **`allergens`** — the vocabulary used by the filter and by
  every recipe. If you add one here, recipes can start using it.
- **`featured`** — the recipes shown on the home page (use their slugs).

## Changing the How it works page

Open the **How it works** screen in the editing page, or edit `data/about.yml`.
The top fields are the small line above the title, the title and the line under
it. The body is ordinary text with a little **Markdown**:

- leave a blank line between paragraphs;
- `## A heading` starts a new section;
- `- ` makes a bullet and `1. ` makes a numbered list;
- `**bold**` and `[links](https://example.com)` work;
- `{recipes}` is swapped for the number of recipes on the shelf, so leave it in
  if you mention the count.

The closing note's email address comes from the **Site** screen, not this one.

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
