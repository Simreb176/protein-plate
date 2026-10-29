#!/usr/bin/env python3
"""One-off migration: turn the hand-written ingredient lines into structured rows.

    .venv/bin/python tools/structure_recipes.py

Each row becomes `{food, grams, label}`. `label` keeps the original wording for
the website; `food` and `grams` are what the nutrition calculation uses. The
hand-typed calorie/protein/carb/fat fields are removed — they are now derived
from data/foods.yml at build time.
"""
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "data" / "recipes.yml"

# original ingredient line -> (food key in data/foods.yml, grams)
INGREDIENTS = {
    "1 apple": ("apple", 150),
    "1 banana": ("banana", 120),
    "1 carrot": ("carrot", 80),
    "1 carrot, diced": ("carrot", 80),
    "1 carrot, grated": ("carrot", 80),
    "1 clove garlic": ("garlic", 3),
    "1 clove garlic, sliced": ("garlic", 3),
    "1 courgette, chopped": ("courgette", 200),
    "1 courgette, ribboned": ("courgette", 200),
    "1 large sweet potato, diced": ("sweet-potato", 300),
    "1 lemon": ("lemon-juice", 40),
    "1 litre beef stock": ("beef-stock", 1000),
    "1 onion, diced": ("onion", 120),
    "1 pepper, chunks": ("red-pepper", 150),
    "1 red onion, wedges": ("onion", 100),
    "1 red pepper, chopped": ("red-pepper", 150),
    "1 red pepper, sliced": ("red-pepper", 150),
    "1 scoop (30 g) pea or soy protein": ("pea-protein", 30),
    "1 scoop (30 g) pea protein": ("pea-protein", 30),
    "1 scoop (30 g) whey protein": ("whey-protein", 30),
    "1 slice rye bread (optional)": ("rye-bread", 35),
    "1 slice wholemeal toast": ("wholemeal-bread", 40),
    "1 small tin (80 g) tuna in spring water": ("tuna-water", 56),
    "1 spring onion, sliced": ("spring-onion", 15),
    "1 stick celery, diced": ("celery", 40),
    "1 tbsp Greek yoghurt": ("greek-yoghurt", 15),
    "1 tbsp chia seeds": ("chia-seeds", 12),
    "1 tbsp crème fraîche": ("creme-fraiche", 15),
    "1 tbsp honey": ("honey", 21),
    "1 tbsp lemon juice": ("lemon-juice", 15),
    "1 tbsp oats": ("oats", 6),
    "1 tbsp oil": ("vegetable-oil", 14),
    "1 tbsp olive oil": ("olive-oil", 14),
    "1 tbsp pumpkin seeds": ("pumpkin-seeds", 10),
    "1 tbsp red wine vinegar": ("vinegar", 15),
    "1 tbsp soy sauce": ("soy-sauce", 15),
    "1 tbsp tahini": ("tahini", 15),
    "1 tin (145 g) tuna in spring water": ("tuna-water", 112),
    "1 tin (240 g) butter beans, drained": ("butter-beans", 240),
    "1 tin (240 g) chickpeas, drained": ("chickpeas", 240),
    "1 tin (240 g) green lentils, drained": ("green-lentils", 240),
    "1 tin black beans, drained": ("black-beans", 240),
    "1 tin chopped tomatoes": ("chopped-tomatoes", 400),
    "1 tin kidney beans, drained": ("kidney-beans", 240),
    "1 tsp Dijon mustard": ("mustard", 5),
    "1 tsp baking powder": ("baking-powder", 4),
    "1 tsp coriander": ("coriander-seeds", 1.8),
    "1 tsp cumin": ("cumin", 2.1),
    "1 tsp garam masala": ("garam-masala", 2),
    "1 tsp honey": ("honey", 7),
    "1 tsp light mayonnaise": ("mayonnaise-light", 5),
    "1 tsp oil": ("vegetable-oil", 4.5),
    "1 tsp olive oil": ("olive-oil", 4.5),
    "1 tsp paprika": ("paprika", 2.3),
    "1 tsp rice vinegar": ("vinegar", 5),
    "1 tsp sesame oil": ("sesame-oil", 4.5),
    "1 tsp sesame seeds": ("sesame-seeds", 3),
    "1 tsp smoked paprika": ("paprika", 2.3),
    "1 tsp turmeric": ("turmeric", 3),
    "1 whole egg": ("eggs", 50),
    "1 wholemeal flatbread": ("flatbread", 80),
    "1 wholemeal wrap": ("tortilla-wrap", 60),
    "1/2 avocado": ("avocado", 75),
    "1/2 cucumber": ("cucumber", 150),
    "1/2 cucumber, chopped": ("cucumber", 150),
    "1/2 cucumber, diced": ("cucumber", 150),
    "1/2 onion, sliced": ("onion", 60),
    "1/2 red onion, finely sliced": ("onion", 50),
    "1/2 tsp chilli flakes": ("chilli-powder", 0.9),
    "1/2 tsp smoked paprika": ("paprika", 1.2),
    "1/2 tsp turmeric": ("turmeric", 1.5),
    "100 g blueberries": ("blueberries", 100),
    "100 g cherry tomatoes": ("cherry-tomatoes", 100),
    "100 g cherry tomatoes, halved": ("cherry-tomatoes", 100),
    "100 g edamame beans": ("edamame", 100),
    "100 g halloumi, sliced": ("halloumi", 100),
    "100 g mushrooms": ("mushrooms", 100),
    "100 g pak choi": ("pak-choi", 100),
    "100 g paneer, cubed": ("paneer", 100),
    "100 g pineapple chunks": ("pineapple", 100),
    "100 g red lentils (dry)": ("red-lentils", 100),
    "100 g roasted beetroot": ("beetroot", 100),
    "100 g spinach": ("spinach", 100),
    "100 g wholewheat noodles": ("wholewheat-pasta", 100),
    "120 g baked beans": ("baked-beans", 120),
    "120 g cooked turkey breast, sliced": ("turkey-breast", 120),
    "120 g firm tofu, cubed": ("tofu", 120),
    "15 g walnuts": ("walnuts", 15),
    "150 g 5% beef mince": ("beef-mince", 150),
    "150 g chicken breast": ("chicken-breast", 150),
    "150 g cooked brown rice": ("brown-rice", 150),
    "150 g cooked jasmine rice": ("white-rice", 150),
    "150 g cooked rice": ("white-rice", 150),
    "150 g cottage cheese": ("cottage-cheese", 150),
    "150 g edamame beans": ("edamame", 150),
    "150 g king prawns": ("prawns", 150),
    "150 g linguine": ("white-pasta", 150),
    "150 g new potatoes": ("potatoes", 150),
    "150 g paneer, cubed": ("paneer", 150),
    "150 g salmon fillet": ("salmon", 150),
    "150 g stewing beef, diced": ("stewing-beef", 150),
    "150 g tenderstem broccoli": ("broccoli", 150),
    "160 g seitan, sliced": ("seitan", 160),
    "180 g cod fillet": ("cod", 180),
    "180 g firm tofu, crumbled": ("tofu", 180),
    "180 g firm tofu, cubed": ("tofu", 180),
    "180 g tempeh, sliced": ("tempeh", 180),
    "2 boiled eggs": ("eggs", 100),
    "2 cloves garlic": ("garlic", 6),
    "2 cloves garlic, crushed": ("garlic", 6),
    "2 eggs": ("eggs", 100),
    "2 handfuls of rocket": ("rocket", 60),
    "2 slices sourdough": ("sourdough", 80),
    "2 tbsp Greek yoghurt": ("greek-yoghurt", 30),
    "2 tbsp curry powder": ("curry-powder", 12),
    "2 tbsp peanut butter": ("peanut-butter", 32),
    "2 tbsp soy sauce": ("soy-sauce", 30),
    "2 turkey sausages": ("turkey-sausages", 120),
    "20 g butter": ("butter", 20),
    "20 g parmesan": ("parmesan", 20),
    "200 g 0% Greek yoghurt": ("greek-yoghurt-0", 200),
    "200 g broccoli": ("broccoli", 200),
    "200 g chicken breast": ("chicken-breast", 200),
    "200 g chicken thigh, diced": ("chicken-thigh", 200),
    "200 g cottage cheese": ("cottage-cheese", 200),
    "200 g green beans": ("green-beans", 200),
    "200 g kale": ("kale", 200),
    "200 g plain soy yoghurt": ("soy-yoghurt", 200),
    "200 g rump steak": ("rump-steak", 200),
    "200 g tenderstem broccoli": ("broccoli", 200),
    "200 ml semi-skimmed milk": ("milk-semi", 200),
    "25 g butter": ("butter", 25),
    "250 g potatoes, halved": ("potatoes", 250),
    "250 ml soy milk": ("soy-milk", 250),
    "3 eggs": ("eggs", 150),
    "3 oatcakes": ("oatcakes", 30),
    "30 g peanut butter": ("peanut-butter", 30),
    "300 g 0% Greek yoghurt": ("greek-yoghurt-0", 300),
    "300 ml soy milk": ("soy-milk", 300),
    "300 ml water or milk": ("water", 300),
    "40 g feta": ("feta", 40),
    "40 g feta, crumbled": ("feta", 40),
    "40 g granola": ("granola", 40),
    "40 g pearl barley": ("pearl-barley", 40),
    "5 egg whites": ("egg-whites", 165),
    "50 g beef jerky": ("beef-jerky", 50),
    "50 g blueberries": ("blueberries", 50),
    "50 g plain flour": ("plain-flour", 50),
    "60 g feta, crumbled": ("feta", 60),
    "60 g quinoa (dry)": ("quinoa", 60),
    "60 g raspberries": ("raspberries", 60),
    "60 g rolled oats": ("oats", 60),
    "60 g smoked salmon": ("smoked-salmon", 60),
    "80 g hummus": ("hummus", 80),
    "80 g mixed berries": ("mixed-berries", 80),
    "Handful of mint": ("mint", 5),
    "Handful of parsley": ("parsley", 5),
    "Handful of spinach": ("spinach", 30),
    "Pinch of cinnamon": ("cinnamon", 0.5),
    "Pinch of flaky salt": ("salt", 1),
    "Pinch of salt": ("salt", 0.5),
    "Pinch of sea salt": ("salt", 1),
    "Squeeze of lemon": ("lemon-juice", 10),
    "Squeeze of lime": ("lime-juice", 10),
}


def main():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    with open(RECIPES, encoding="utf-8") as f:
        recipes = y.load(f)

    missing = set()
    for recipe in recipes:
        rows = []
        for line in recipe.get("ingredients") or []:
            line = str(line).strip()
            if line not in INGREDIENTS:
                missing.add(line)
                continue
            food, grams = INGREDIENTS[line]
            row = CommentedMap()
            row["food"] = food
            row["grams"] = grams
            row["label"] = line
            rows.append(row)

        recipe["ingredients"] = CommentedSeq(rows)
        for key in ("calories", "protein", "carbs", "fat"):
            recipe.pop(key, None)
        if "servings" not in recipe:
            keys = list(recipe.keys())
            recipe.insert(keys.index("minutes") + 1, "servings", 1)

    if missing:
        print("Unmapped ingredient lines:")
        for line in sorted(missing):
            print(" ", line)
        raise SystemExit(f"{len(missing)} lines still need a food and gram weight.")

    with open(RECIPES, "w", encoding="utf-8") as f:
        y.dump(recipes, f)
    print(f"Structured {len(recipes)} recipes.")


if __name__ == "__main__":
    main()
