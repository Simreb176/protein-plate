#!/usr/bin/env python3
"""Build data/foods.yml from the UK CoFID 2021 spreadsheet.

    .venv/bin/python tools/build_foods.py /path/to/cofid.xlsx

CoFID is the McCance and Widdowson's Composition of Foods Integrated Dataset,
published by Public Health England (2021) under the Open Government Licence.
Values in data/foods.yml are per 100 g. AOAC fibre is used where CoFID has it,
falling back to NSP. A handful of modern products (0% Greek yoghurt, protein
powders, seitan, chia, etc.) are not in CoFID; those use a clearly-labelled
typical label value instead.

The generated file is committed, so normal builds do not need the spreadsheet.
"""
import sys
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "foods.yml"

SOURCE = {
    "name": "McCance and Widdowson's The Composition of Foods Integrated Dataset 2021 (CoFID)",
    "publisher": "Public Health England",
    "url": "https://www.gov.uk/government/publications/composition-of-foods-integrated-dataset-cofid",
    "licence": "Open Government Licence v3.0",
    "accessed": "2026-10-29",
    "fibre": "AOAC fibre where CoFID provides it, otherwise non-starch polysaccharide (NSP)",
}

# key -> (CoFID food code, display name)
COFID = {
    "chicken-breast": ("18-290", "Chicken breast"),
    "chicken-thigh": ("18-289", "Chicken thigh"),
    "turkey-breast": ("18-349", "Turkey breast"),
    "beef-mince": ("18-508", "Beef mince (5% fat)"),
    "stewing-beef": ("18-076", "Stewing beef"),
    "rump-steak": ("18-043", "Rump steak"),
    "salmon": ("16-356", "Salmon"),
    "smoked-salmon": ("16-412", "Smoked salmon"),
    "cod": ("16-372", "Cod"),
    "prawns": ("16-388", "King prawns"),
    "tuna-water": ("16-416", "Tuna in spring water"),
    "eggs": ("12-937", "Eggs"),
    "egg-whites": ("12-938", "Egg whites"),
    "greek-yoghurt": ("12-555", "Greek yoghurt"),
    "cottage-cheese": ("12-550", "Cottage cheese"),
    "milk-semi": ("12-313", "Semi-skimmed milk"),
    "soy-milk": ("12-524", "Soy milk"),
    "tofu": ("13-570", "Firm tofu"),
    "tempeh": ("13-118", "Tempeh"),
    "halloumi": ("12-496", "Halloumi"),
    "paneer": ("12-495", "Paneer"),
    "feta": ("12-525", "Feta"),
    "parmesan": ("12-526", "Parmesan"),
    "butter": ("17-685", "Butter"),
    "olive-oil": ("17-038", "Olive oil"),
    "sesame-oil": ("17-043", "Sesame oil"),
    "vegetable-oil": ("17-686", "Vegetable oil"),
    "creme-fraiche": ("12-335", "Crème fraîche"),
    "mayonnaise-light": ("17-679", "Light mayonnaise"),
    "tahini": ("14-847", "Tahini"),
    "peanut-butter": ("14-892", "Peanut butter"),
    "hummus": ("13-556", "Hummus"),
    "chickpeas": ("13-670", "Chickpeas (canned, drained)"),
    "butter-beans": ("13-559", "Butter beans (canned, drained)"),
    "green-lentils": ("13-661", "Green lentils (cooked)"),
    "red-lentils": ("13-657", "Red lentils (dry)"),
    "black-beans": ("13-063", "Black beans (canned, drained)"),
    "kidney-beans": ("13-660", "Kidney beans (canned, drained)"),
    "baked-beans": ("13-532", "Baked beans"),
    "edamame": ("13-667", "Edamame beans"),
    "quinoa": ("14-843", "Quinoa (dry)"),
    "brown-rice": ("11-867", "Brown rice (cooked)"),
    "white-rice": ("11-862", "White rice (cooked)"),
    "wholewheat-pasta": ("11-718", "Wholewheat pasta (dry)"),
    "white-pasta": ("11-716", "White pasta (dry)"),
    "pearl-barley": ("11-002", "Pearl barley (dry)"),
    "oats": ("11-788", "Rolled oats"),
    "plain-flour": ("11-886", "Plain flour"),
    "wholemeal-bread": ("11-981", "Wholemeal bread"),
    "tortilla-wrap": ("11-925", "Wholemeal wrap"),
    "flatbread": ("11-974", "Flatbread"),
    "oatcakes": ("11-823", "Oatcakes"),
    "granola": ("11-939", "Granola"),
    "potatoes": ("13-618", "New potatoes"),
    "sweet-potato": ("13-463", "Sweet potato"),
    "broccoli": ("13-502", "Broccoli"),
    "kale": ("13-234", "Kale"),
    "spinach": ("13-521", "Spinach"),
    "rocket": ("13-522", "Rocket"),
    "pak-choi": ("13-516", "Pak choi"),
    "courgette": ("13-627", "Courgette"),
    "red-pepper": ("13-524", "Red pepper"),
    "mushrooms": ("13-505", "Mushrooms"),
    "cherry-tomatoes": ("13-519", "Cherry tomatoes"),
    "chopped-tomatoes": ("13-530", "Chopped tomatoes (canned)"),
    "beetroot": ("13-633", "Beetroot (cooked)"),
    "green-beans": ("13-514", "Green beans"),
    "onion": ("13-499", "Onion"),
    "spring-onion": ("13-352", "Spring onion"),
    "garlic": ("13-244", "Garlic"),
    "celery": ("13-636", "Celery"),
    "carrot": ("13-496", "Carrot"),
    "cucumber": ("13-523", "Cucumber"),
    "avocado": ("14-386", "Avocado"),
    "lemon-juice": ("14-277", "Lemon juice"),
    "lime-juice": ("14-279", "Lime juice"),
    "apple": ("14-319", "Apple"),
    "banana": ("14-318", "Banana"),
    "blueberries": ("14-325", "Blueberries"),
    "raspberries": ("14-375", "Raspberries"),
    "pineapple": ("14-376", "Pineapple"),
    "mint": ("13-836", "Mint"),
    "parsley": ("13-844", "Parsley"),
    "walnuts": ("14-879", "Walnuts"),
    "pumpkin-seeds": ("14-842", "Pumpkin seeds"),
    "sesame-seeds": ("14-844", "Sesame seeds"),
    "honey": ("17-050", "Honey"),
    "cinnamon": ("13-874", "Cinnamon"),
    "cumin": ("13-889", "Cumin"),
    "coriander-seeds": ("13-875", "Coriander seeds"),
    "paprika": ("13-879", "Paprika"),
    "turmeric": ("13-861", "Turmeric"),
    "garam-masala": ("13-829", "Garam masala"),
    "chilli-powder": ("13-873", "Chilli powder"),
    "curry-powder": ("13-876", "Curry powder"),
    "mustard": ("17-364", "Dijon mustard"),
    "baking-powder": ("17-355", "Baking powder"),
    "soy-sauce": ("17-721", "Soy sauce"),
    "vinegar": ("17-339", "Vinegar"),
    "black-pepper": ("13-880", "Black pepper"),
    "chicken-stock": ("17-681", "Chicken stock"),
}

# key -> label-per-100g values for foods CoFID does not cover. `note` explains
# the substitution, and is carried through to the page so the source is clear.
FALLBACK = {
    "greek-yoghurt-0": dict(name="Greek yoghurt (0% fat)", kcal=57, protein=10.0, carbs=3.5,
                            fat=0.4, fibre=0.0, note="Typical 0% Greek yoghurt label; CoFID has no 0% Greek entry."),
    "whey-protein": dict(name="Whey protein powder", kcal=380, protein=80.0, carbs=6.0,
                         fat=5.0, fibre=0.0, note="Typical whey protein label; not in CoFID."),
    "pea-protein": dict(name="Pea protein powder", kcal=375, protein=80.0, carbs=3.0,
                        fat=6.0, fibre=2.0, note="Typical pea protein label; not in CoFID."),
    "seitan": dict(name="Seitan", kcal=145, protein=25.0, carbs=6.0,
                   fat=2.0, fibre=1.0, note="Typical seitan; not in CoFID."),
    "chia-seeds": dict(name="Chia seeds", kcal=486, protein=16.5, carbs=42.0,
                       fat=30.7, fibre=34.4, note="USDA FoodData Central; CoFID has no chia entry."),
    "soy-yoghurt": dict(name="Soy yoghurt", kcal=50, protein=3.5, carbs=4.0,
                        fat=2.0, fibre=1.0, note="Typical plain soy yoghurt; CoFID only lists a fruit version."),
    "sourdough": dict(name="Sourdough bread", kcal=250, protein=8.5, carbs=48.0,
                      fat=2.0, fibre=3.0, note="Typical sourdough; not in CoFID."),
    "rye-bread": dict(name="Rye bread", kcal=250, protein=9.0, carbs=48.0,
                      fat=3.0, fibre=6.0, note="Typical rye bread; not in CoFID."),
    "mixed-berries": dict(name="Mixed berries", kcal=40, protein=1.0, carbs=8.0,
                          fat=0.3, fibre=3.0, note="Typical frozen mixed berries; not in CoFID."),
    "turkey-sausages": dict(name="Turkey sausages", kcal=200, protein=17.0, carbs=5.0,
                            fat=13.0, fibre=1.0, note="Typical turkey sausage label; not in CoFID."),
    "beef-jerky": dict(name="Beef jerky", kcal=410, protein=33.0, carbs=11.0,
                       fat=26.0, fibre=0.0, note="Typical beef jerky label; not in CoFID."),
    "beef-stock": dict(name="Beef stock", kcal=5, protein=0.5, carbs=0.5,
                       fat=0.2, fibre=0.0, note="Typical made-up stock; CoFID only lists a chicken ready-made stock."),
    "salt": dict(name="Salt", kcal=0, protein=0.0, carbs=0.0, fat=0.0, fibre=0.0),
    "water": dict(name="Water", kcal=0, protein=0.0, carbs=0.0, fat=0.0, fibre=0.0),
}

# Substitutions worth surfacing next to the value.
SUBSTITUTIONS = {
    "black-beans": "CoFID has no black beans; the closest entry, blackeye beans, is used.",
    "granola": "CoFID has no granola; a nutty crunchy muesli is used.",
    "wholemeal-bread": "Wholemeal bread is used for the toast.",
    "tortilla-wrap": "A soft wheat tortilla is used for the wrap.",
    "chicken-breast": "CoFID's raw light chicken meat is used.",
    "chicken-thigh": "CoFID's raw dark chicken meat is used.",
}


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    workbook = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
    sheet = workbook["1.3 Proximates"]
    rows = {}
    for row in sheet.iter_rows(min_row=4, values_only=True):
        if row[0]:
            rows[str(row[0]).strip()] = row

    foods = {}
    for key, (code, name) in COFID.items():
        row = rows.get(code)
        if not row:
            sys.exit(f"CoFID code {code} for {key} not found.")
        aoac = number(row[25])
        nsp = number(row[24])
        foods[key] = {
            "name": name,
            "cofid": code,
            "per_100g": {
                "kcal": round(number(row[12]), 1),
                "protein": round(number(row[9]), 1),
                "carbs": round(number(row[11]), 1),
                "fat": round(number(row[10]), 1),
                "fibre": round(aoac if aoac else nsp, 1),
            },
        }
        if key in SUBSTITUTIONS:
            foods[key]["note"] = SUBSTITUTIONS[key]

    for key, values in FALLBACK.items():
        foods[key] = {
            "name": values["name"],
            "per_100g": {
                "kcal": values["kcal"],
                "protein": values["protein"],
                "carbs": values["carbs"],
                "fat": values["fat"],
                "fibre": values["fibre"],
            },
        }
        if values.get("note"):
            foods[key]["note"] = values["note"]

    doc = {
        "source": SOURCE,
        "foods": dict(sorted(foods.items())),
    }
    OUT.write_text(
        "# Generated by tools/build_foods.py from CoFID 2021 — edit that, not this.\n"
        + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"Wrote {OUT} with {len(foods)} foods.")


if __name__ == "__main__":
    main()
