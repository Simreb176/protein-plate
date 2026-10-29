/* ==========================================================================
   Protein Plate — the meal planner
   --------------------------------------------------------------------------
   The first half of this file is the planner itself: plain functions with no
   page attached, so they can be reasoned about (and tested) on their own.
   The second half wires it to the form and draws the results.

   Recipes and the planner's vocabulary are read from data/planner.json, which
   is generated from data/recipes.yml and data/planner.yml at build time.
   ========================================================================== */

const ProteinPlate = (() => {
  const DIET_ORDER = ["vegan", "vegetarian", "pescatarian", "omnivore"];

  /** A vegan recipe suits everyone; an omnivore recipe only suits omnivores. */
  function dietAllows(recipeDiet, chosen) {
    return DIET_ORDER.indexOf(recipeDiet) <= DIET_ORDER.indexOf(chosen);
  }

  function candidatesFor(recipes, slot, diet, avoid) {
    return recipes.filter(
      (recipe) =>
        recipe.slot === slot &&
        dietAllows(recipe.diet, diet) &&
        !recipe.allergens.some((allergen) => avoid.includes(allergen))
    );
  }

  function totals(picks) {
    return picks.reduce(
      (sum, recipe) => ({
        calories: sum.calories + recipe.calories,
        protein: sum.protein + recipe.protein,
        carbs: sum.carbs + recipe.carbs,
        fat: sum.fat + recipe.fat,
        fibre: sum.fibre + recipe.fibre,
      }),
      { calories: 0, protein: 0, carbs: 0, fat: 0, fibre: 0 }
    );
  }

  function score(picks, targets) {
    const total = totals(picks);
    const calorieError = (total.calories - targets.calories) / targets.calories;
    const proteinError = (total.protein - targets.protein) / targets.protein;

    // Protein matters a little more than calories: undershooting it is the
    // whole reason someone is here.
    let value = Math.abs(calorieError) + Math.abs(proteinError) * 1.6;
    if (total.protein < targets.protein) {
      value += ((targets.protein - total.protein) / targets.protein) * 0.6;
    }

    // Prefer not to serve the same recipe twice in a day.
    const seen = new Set();
    let repeats = 0;
    for (const recipe of picks) {
      if (seen.has(recipe.slug)) repeats += 1;
      seen.add(recipe.slug);
    }
    return value + repeats * 0.35;
  }

  function allowedInSlot(candidate, picks, slots, index) {
    // Main meals must all be different. Snacks may repeat, at a scoring cost.
    if (slots[index] === "snack") return true;
    return !picks.some(
      (pick, other) => other !== index && slots[other] !== "snack" && pick.slug === candidate.slug
    );
  }

  /** Search for the combination of one recipe per slot closest to the targets. */
  function pickPlan(slots, pools, targets) {
    let best = null;
    let bestScore = Infinity;

    // A handful of random starts, each improved by swapping one meal at a time.
    for (let restart = 0; restart < 8; restart += 1) {
      const picks = slots.map((slot) => {
        const pool = pools[slot];
        return pool[Math.floor(Math.random() * pool.length)];
      });

      let current = score(picks, targets);

      for (let pass = 0; pass < 40; pass += 1) {
        let improved = false;

        for (let index = 0; index < slots.length; index += 1) {
          const slot = slots[index];
          const pool = pools[slot];
          const original = picks[index];
          let localBest = current;
          let localPick = original;

          for (const candidate of pool) {
            if (candidate.slug === original.slug) continue;
            if (!allowedInSlot(candidate, picks, slots, index)) continue;
            picks[index] = candidate;
            const candidateScore = score(picks, targets);
            if (candidateScore < localBest) {
              localBest = candidateScore;
              localPick = candidate;
            }
          }

          picks[index] = localPick;
          if (localPick !== original) {
            current = localBest;
            improved = true;
          }
        }

        if (!improved) break;
      }

      if (current < bestScore) {
        bestScore = current;
        best = picks.slice();
      }
    }

    return best;
  }

  /**
   * Build a plan. Returns `{ slots, picks }`, or `{ error }` with a message
   * explaining which slot couldn't be filled.
   */
  function makePlan(options) {
    const { recipes, mealCounts, slots: slotLabels, meals, calories, protein, diet, avoid } = options;
    const slots = mealCounts[String(meals)];
    const targets = { calories, protein };

    const pools = {};
    for (const slot of new Set(slots)) {
      pools[slot] = candidatesFor(recipes, slot, diet, avoid);
      if (pools[slot].length === 0) {
        return {
          error:
            `Nothing on the shelf fits that. There are no ${slotLabels[slot].toLowerCase()} ` +
            `recipes for this diet with those ingredients left out — try allowing one back, ` +
            `or choosing a less restrictive diet.`,
        };
      }
    }

    return { slots, picks: pickPlan(slots, pools, targets) };
  }

  /** Alternatives for one slot, best fit first, with a little randomness. */
  function rankSwaps(options) {
    const { recipes, slots, picks, index, diet, avoid, targets } = options;
    const slot = slots[index];
    const others = picks.filter((_, other) => other !== index);
    return candidatesFor(recipes, slot, diet, avoid)
      .filter((recipe) => recipe.slug !== picks[index].slug)
      .filter((recipe) => slot === "snack" || !others.some((other) => other.slug === recipe.slug))
      .map((recipe) => {
        const next = totals([...others, recipe]);
        const value =
          Math.abs((next.calories - targets.calories) / targets.calories) +
          Math.abs((next.protein - targets.protein) / targets.protein) * 1.6 +
          Math.random() * 0.12;
        return { recipe, value };
      })
      .sort((a, b) => a.value - b.value);
  }

  return { dietAllows, candidatesFor, totals, score, pickPlan, makePlan, rankSwaps };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = ProteinPlate;
}

/* ==========================================================================
   The page
   ========================================================================== */
if (typeof document !== "undefined") {
  const form = document.getElementById("planner-form");

  if (form) {
    const results = document.getElementById("results");
    const planEl = document.getElementById("plan");
    const totalsEl = document.getElementById("totals");
    const summaryEl = document.getElementById("results-summary");
    const footEl = document.getElementById("plan-foot");
    const shuffleBtn = document.getElementById("shuffle");
    const printBtn = document.getElementById("print");

    const el = (id) => document.getElementById(id);
    const caloriesInput = el("calories");
    const proteinInput = el("protein");

    let data = null;
    let plan = null; // { slots, picks }

    /* ---------------------------------------------------------------- setup */
    const chosenMeals = () => Number(form.querySelector('input[name="meals"]:checked').value);
    const chosenDiet = () => form.querySelector('input[name="diet"]:checked').value;
    const chosenAvoid = () =>
      [...form.querySelectorAll('input[name="avoid"]:checked')].map((input) => input.value);
    const targets = () => ({
      calories: Number(caloriesInput.value),
      protein: Number(proteinInput.value),
    });

    function refreshOutputs() {
      el("calories-out").textContent = `${caloriesInput.value} kcal`;
      el("protein-out").textContent = `${proteinInput.value} g`;
      el("hero-protein").textContent = proteinInput.value;
      for (const input of [caloriesInput, proteinInput]) {
        const percent = ((input.value - input.min) / (input.max - input.min)) * 100;
        input.style.setProperty("--fill", `${percent}%`);
      }
      updateMealHint();
    }

    function updateMealHint() {
      if (!data) return;
      const slots = data.mealCounts[String(chosenMeals())] || [];
      el("meal-count-hint").textContent = slots.map((slot) => data.slots[slot]).join(" · ");
    }

    function planOptions() {
      const target = targets();
      return {
        recipes: data.recipes,
        mealCounts: data.mealCounts,
        slots: data.slots,
        meals: chosenMeals(),
        calories: target.calories,
        protein: target.protein,
        diet: chosenDiet(),
        avoid: chosenAvoid(),
      };
    }

    /* -------------------------------------------------------------- rendering */
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char]);
    }

    function prettyAllergen(key) {
      const found = data.allergens.find((allergen) => allergen.key === key);
      return found ? found.label.toLowerCase() : key;
    }

    function renderTotals(target, total) {
      const rows = [
        { key: "calories", label: "Calories", unit: "kcal", target: target.calories, value: total.calories },
        { key: "protein", label: "Protein", unit: "g", target: target.protein, value: total.protein },
        { key: "carbs", label: "Carbs", unit: "g", target: null, value: total.carbs },
        { key: "fat", label: "Fat", unit: "g", target: null, value: total.fat },
      ];

      totalsEl.innerHTML = rows
        .map((row) => {
          const percent = row.target ? Math.min(100, Math.round((row.value / row.target) * 100)) : null;
          const difference = row.target ? Math.round(row.value - row.target) : null;
          const note = difference === null
            ? "planned"
            : `${difference > 0 ? "+" : ""}${difference} vs target`;
          return `
            <div class="total total-${row.key}">
              <span class="total-label">${row.label}</span>
              <span class="total-value">${Math.round(row.value)}<span>${row.unit}</span></span>
              <span class="total-note">${note}</span>
              ${percent !== null ? `
                <span class="total-meter" role="img" aria-label="${percent}% of target">
                  <span style="width: ${percent}%"></span>
                </span>` : ""}
            </div>`;
        })
        .join("");
    }

    function renderPlan() {
      const target = targets();
      const total = ProteinPlate.totals(plan.picks);
      const diffProtein = Math.round(total.protein - target.protein);

      renderTotals(target, total);

      summaryEl.textContent =
        `${plan.picks.length} meals, ${Math.round(total.calories)} kcal, ` +
        `${Math.round(total.protein)} g protein and ${Math.round(total.fibre)} g fibre` +
        (diffProtein >= 0
          ? ` — ${diffProtein} g above your protein target.`
          : ` — ${Math.abs(diffProtein)} g short of your protein target.`);

      planEl.innerHTML = plan.picks
        .map((recipe, index) => `
          <article class="meal">
            <div class="meal-slot">${escapeHtml(data.slots[plan.slots[index]])}</div>
            <div class="meal-body">
              <div class="meal-head">
                <h3><a href="recipes/${recipe.slug}/index.html">${escapeHtml(recipe.title)}</a></h3>
                <span class="meal-time">${recipe.minutes} min</span>
              </div>
              <p class="meal-macros">
                <span class="meal-protein">${Math.round(recipe.protein)} g protein</span>
                <span>${Math.round(recipe.calories)} kcal</span>
                <span>${Math.round(recipe.carbs)} g carbs</span>
                <span>${Math.round(recipe.fat)} g fat</span>
                <span>${recipe.fibre.toFixed(1)} g fibre</span>
              </p>
              <p class="meal-meta">
                ${escapeHtml(recipe.tags.join(" · "))}
                <span>Serves ${recipe.servings}</span>
                ${recipe.allergens.length
                  ? `<span class="meal-allergens">Contains ${escapeHtml(recipe.allergens.map(prettyAllergen).join(", "))}</span>`
                  : ""}
              </p>
            </div>
            <div class="meal-actions">
              <button type="button" class="btn btn-swap" data-swap="${index}">Swap</button>
            </div>
          </article>`)
        .join("");

      const shortfall = target.protein - total.protein;
      footEl.textContent = shortfall > 15
        ? "A little short on protein — add a yoghurt or a shake, or raise the calorie target and generate again."
        : "Portion sizes are per serving. Numbers are estimates; check your labels.";

      results.hidden = false;
      shuffleBtn.hidden = false;
      printBtn.hidden = false;
    }

    function showProblem(message) {
      results.hidden = false;
      planEl.innerHTML = `<div class="notice notice-bad">${escapeHtml(message)}</div>`;
      totalsEl.innerHTML = "";
      summaryEl.textContent = "";
      footEl.textContent = "";
      shuffleBtn.hidden = true;
      printBtn.hidden = true;
    }

    /* ----------------------------------------------------------------- events */
    function buildAndRender(avoidCurrent) {
      let next = ProteinPlate.makePlan(planOptions());
      if (next.error) {
        showProblem(next.error);
        return;
      }

      // "Shuffle" should feel different: try again if it handed back the same day.
      if (avoidCurrent && plan) {
        const before = plan.picks.map((recipe) => recipe.slug).join("|");
        for (let attempt = 0; attempt < 6; attempt += 1) {
          if (next.picks.map((recipe) => recipe.slug).join("|") !== before) break;
          next = ProteinPlate.makePlan(planOptions());
        }
      }

      plan = next;
      renderPlan();
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      buildAndRender(false);
    });

    shuffleBtn.addEventListener("click", () => {
      const before = planEl.innerHTML;
      buildAndRender(true);
      if (planEl.innerHTML === before) return; // the problem notice is already showing
      planEl.classList.remove("is-fresh");
      void planEl.offsetWidth; // restart the entrance animation
      planEl.classList.add("is-fresh");
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    printBtn.addEventListener("click", () => window.print());

    planEl.addEventListener("click", (event) => {
      const button = event.target.closest("[data-swap]");
      if (button) swapMeal(Number(button.dataset.swap));
    });

    function swapMeal(index) {
      const target = targets();
      const ranked = ProteinPlate.rankSwaps({
        recipes: data.recipes,
        slots: plan.slots,
        picks: plan.picks,
        index,
        diet: chosenDiet(),
        avoid: chosenAvoid(),
        targets: target,
      });

      if (ranked.length === 0) {
        footEl.textContent = "There's nothing else on the shelf that fits this meal — try relaxing a filter.";
        return;
      }

      // Choose from the best few so a swap feels like a swap.
      const shortlist = ranked.slice(0, Math.min(3, ranked.length));
      plan.picks[index] = shortlist[Math.floor(Math.random() * shortlist.length)].recipe;
      renderPlan();
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    caloriesInput.addEventListener("input", refreshOutputs);
    proteinInput.addEventListener("input", refreshOutputs);
    form.addEventListener("change", (event) => {
      if (event.target.name === "meals") updateMealHint();
    });

    refreshOutputs();

    fetch("data/planner.json")
      .then((response) => {
        if (!response.ok) throw new Error("Could not load the recipe shelf.");
        return response.json();
      })
      .then((loaded) => {
        data = loaded;
        refreshOutputs();
      })
      .catch(() => {
        showProblem("The recipe shelf couldn't be loaded. Refresh the page and try again.");
      });
  }
}
