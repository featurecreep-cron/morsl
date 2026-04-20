# Menu Curation & Candidate Generation

Status: **design** — Phase 2

## Problem

morsl's current workflow is: generate → browse → act (save meal plan, shopping list). There's no step where the user refines what they're looking at. You get a flat list of N recipes and your options are "regenerate everything" or "accept it." The swap endpoint exists in the API but has no UI, and even if it did, it's one piece of a larger missing interaction.

The second problem: generation produces a single flat menu. There's no way to say "give me 3 mains, 5 sides, and 3 starches — I'll pick from each." The solver always returns exactly N recipes as a single undifferentiated list.

The third problem: before expanding integrations (new recipe sources, shopping list destinations), the provider abstraction needs to cleanly support the curation workflow — not just the generation workflow.

## User workflows this design must support

### Workflow A: "Generate and refine" (today's model, improved)

1. User selects a profile → morsl generates N recipes
2. User browses the results
3. User removes recipes they don't want
4. User swaps individual recipes for alternatives
5. User is satisfied → saves meal plan, generates shopping list, or both

This is the current workflow with a curation step inserted between 2 and 5.

### Workflow B: "Pick from candidates" (new)

1. User selects a meal plan template defining courses (e.g., 3 mains, 5 sides, 3 starches)
2. morsl generates M candidates per course (M > pick count)
3. User sees candidates grouped by course
4. User selects their picks from each group (e.g., pick 1 of 3 mains, 2 of 5 sides, 1 of 3 starches)
5. User can regenerate candidates for a single course
6. User finalizes → saves meal plan, generates shopping list

### Workflow C: "Weekly plan with daily curation" (extension of existing weekly gen)

1. User selects a weekly template (already exists)
2. morsl generates the full week across profiles with dedup (already works)
3. User sees results organized by day and meal
4. User swaps individual recipes within a day/meal slot
5. User finalizes → saves to Tandoor meal plan

## Design

### 1. Course-slot generation model

#### What changes in profiles

Today a profile has `choices: 5` and produces a flat list of 5 recipes. To support Workflow B, we need a way to define **slots** — groups of recipes the solver should fill, each with its own candidate count and pick count.

**Option A: Compose existing profiles via a template** (recommended)

Reuse the weekly generation template concept, but for a single occasion instead of a week:

```json
{
  "name": "family-dinner",
  "description": "Dinner with sides",
  "slots": [
    {
      "profile": "Mains",
      "generate": 3,
      "pick": 1,
      "label": "Main course"
    },
    {
      "profile": "Sides",
      "generate": 5,
      "pick": 2,
      "label": "Side dishes"
    },
    {
      "profile": "Starches",
      "generate": 3,
      "pick": 1,
      "label": "Starch"
    }
  ],
  "deduplicate": true
}
```

Each slot references an existing profile. The solver runs once per slot (like weekly gen) with deduplication across slots. `generate` is how many candidates to show. `pick` is how many the user selects.

**Why Option A over embedding slots in profiles:**
- Profiles stay simple — one concern (constraint definition)
- Templates compose profiles — second concern (meal structure)
- Weekly templates already work this way
- A "Sides" profile is reusable across templates
- No solver changes needed — each slot is a normal solve with `choices = generate`

**Option B: Slots within a single profile** (not recommended)

Would require the solver to understand course grouping, the profile schema gets complicated, and profiles become non-reusable. Rejected.

#### Template storage

Templates stored in `data/templates/` as JSON files, alongside the existing weekly templates. The weekly template format gains an optional `pick` field per slot (defaults to `recipes_per_day` for backward compat). Single-occasion templates omit the `days` field.

#### Solver changes

None required for candidate generation. Each slot is a normal solve with `choices = generate_count`. The solver already handles this. Deduplication across slots already exists in `WeeklyGenerationService`.

The only new requirement: the generation service needs a `generate_candidates(template_name)` endpoint that returns candidates grouped by slot, not flattened into a single menu.

### 2. Curation state model

#### What the frontend needs to track

Today the frontend has `shelves` — named stacks of flat recipe lists. Curation needs richer state:

```
CurationSession {
  template: string | null        // null for simple single-profile generation
  slots: [
    {
      label: string              // "Main course", "Side dishes", etc.
      profile: string            // which profile generated these
      candidates: Recipe[]       // all generated candidates
      selected: Set<recipe_id>   // user's picks (initially empty or auto-filled)
      pickCount: number          // how many to pick
    }
  ]
  finalized: boolean             // user has confirmed selections
}
```

For Workflow A (simple generate-and-refine), this degrades to a single slot where `candidates == selected` initially (all recipes are pre-selected) and the user removes/swaps within that slot.

#### State transitions

```
generate
  → candidates loaded, auto-select (pick first N or all)

remove(slot, recipe_id)
  → deselect recipe from slot
  → slot.selected.size may drop below pickCount (show warning)

swap(slot, recipe_id)
  → call swap API for this slot's profile
  → replace recipe in candidates, update selected

regenerate_slot(slot)
  → re-solve this slot only (with other slots' selections as exclude_ids)
  → replace candidates, clear selected

finalize
  → lock selections
  → enable "Save Meal Plan" and "Shopping List" actions
  → shopping list uses only selected recipes, not all candidates
```

#### Where curation state lives

Client-side (localStorage), same as shelves. The backend is stateless — it generates and swaps on demand. The frontend tracks what's selected.

### 3. Frontend UX

#### Layout for candidate selection (Workflow B)

The carousel model doesn't work for multi-slot selection. Candidates grouped by course need a different layout:

```
┌─────────────────────────────────────┐
│  Family Dinner                      │
├─────────────────────────────────────┤
│                                     │
│  Main course (pick 1 of 3)          │
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │ ✓    │  │      │  │      │      │
│  │ img  │  │ img  │  │ img  │      │
│  │ name │  │ name │  │ name │      │
│  └──────┘  └──────┘  └──────┘      │
│                          ↻ More     │
│                                     │
│  Side dishes (pick 2 of 5)          │
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │ ✓    │  │ ✓    │  │      │  →   │
│  │ img  │  │ img  │  │ img  │      │
│  │ name │  │ name │  │ name │      │
│  └──────┘  └──────┘  └──────┘      │
│                          ↻ More     │
│                                     │
│  Starch (pick 1 of 3)              │
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │      │  │ ✓    │  │      │      │
│  │ img  │  │ img  │  │ img  │      │
│  │ name │  │ name │  │ name │      │
│  └──────┘  └──────┘  └──────┘      │
│                          ↻ More     │
│                                     │
│  ┌────────────────────────────────┐ │
│  │  Finalize (3 of 4 selected)   │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Card interactions in candidate view:**
- **Tap card** → toggle selection (if under pick limit) or open detail
- **Tap selected card** → deselect
- **Long press / right-click** → open recipe detail (ingredients, steps)
- **"More" button per slot** → regenerate candidates for that slot only
- **Finalize button** → confirms selections, transitions to action phase

**Mobile:** Slots stack vertically, cards scroll horizontally within each slot (same snap behavior as current carousel).

**Desktop:** Grid layout per slot, scrollable if more candidates than fit.

#### Layout for simple curation (Workflow A)

When generating from a single profile (no template), the current carousel layout works. Curation adds:

- **Remove action on cards** — deselect/remove a recipe from the menu
- **Swap action on cards** — replace with an alternative
- **Visual state** — removed cards fade or collapse; card count updates
- **Restore** — undo a remove (card returns to its position)

These actions surface on the recipe detail modal or directly on cards. Specific placement TBD after prototyping.

#### Action phase (post-curation)

Once the user is satisfied with their selections:

- **"Shopping List"** in hamburger menu (or persistent bottom bar) — generates list from selected recipes only
- **"Save to Meal Plan"** — existing flow, but scoped to selected recipes
- If using a template with courses, meal plan save can auto-assign meal types from slot definitions

#### Shopping list modal

Bottom sheet (consistent with meal plan save pattern):

```
┌─────────────────────────────────────┐
│  Shopping List              ✕ Close │
├─────────────────────────────────────┤
│  ☐ Hide items on hand              │
│                                     │
│  Produce                            │
│    • 2 Onions (Soup, Stir-fry)     │
│    • 500g Spinach (Salad)          │
│                                     │
│  Dairy                              │
│    • 250ml Cream (Soup)            │
│    • 200g Cheese (Pasta)           │
│                                     │
│  Pantry                             │
│    • 1kg Flour (Bread, Pasta)      │
│    • 2 tbsp Olive oil (Salad,      │
│      Stir-fry)                     │
│                                     │
│  ┌────────────────────────────────┐ │
│  │  📋 Copy to Clipboard          │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

- Source recipes shown in parentheses (backend already tracks this)
- "Hide items on hand" toggle calls the on-hand endpoint
- "Copy to Clipboard" uses the text export endpoint
- Grouped by food category if available from provider, alphabetical fallback

### 4. Provider abstraction impact

#### What's clean today

- Recipe querying, constraint resolution, on-hand items — fully abstracted
- Shopping list aggregation — provider-agnostic (operates on recipe dicts)
- On-hand exclusion — capability-gated via provider

#### What needs work for Phase 2

**Shopping list push (new capability):**

Some recipe managers have their own shopping list feature (Tandoor does). Users may want "add these ingredients to my Tandoor shopping list" instead of just clipboard copy. This is a new provider capability:

```python
class Capability(Flag):
    ...
    SHOPPING_LIST_WRITE = auto()   # can push items to provider's shopping list

class RecipeProvider(ABC):
    ...
    def add_to_shopping_list(self, items: List[Dict]) -> None:
        """Push shopping list items to the provider's native list."""
        raise NotImplementedError
```

Capability-gated: the UI only shows "Send to Tandoor" if the provider declares `SHOPPING_LIST_WRITE`. Clipboard copy always available.

**Meal type mapping:**

Template slots reference meal types by name ("Breakfast", "Dinner"). When saving to a meal plan, the provider needs to resolve these to its internal IDs. Today this is done via `TandoorAPI.get_meal_type()` directly. Should be on the provider interface:

```python
def get_meal_types(self) -> List[Dict]:
    """List available meal types/categories."""
    ...
```

**Recipe search (for manual add):**

If users can manually add a recipe to their curated menu (not just pick from candidates), they need search. The provider has `SEARCH` capability declared but no `search_recipes()` method. Needed:

```python
def search_recipes(self, query: str, **kwargs) -> List[Dict]:
    """Search recipes by name or keyword."""
    ...
```

#### What stays Tandoor-specific

- Order creation (bartender workflow — not relevant to meal planning)
- Cook log creation
- Meal plan CRUD (the act of saving a meal plan to Tandoor — this uses TandoorAPI directly and that's correct)

### 5. API changes

#### New endpoints

```
POST /api/generate/template/{template_name}
  → Generates candidates for all slots in a template
  → Returns: { slots: [{ label, profile, candidates: Recipe[], pickCount }] }

POST /api/generate/template/{template_name}/slot/{slot_index}
  → Regenerate candidates for one slot (with exclude_ids from other slots' selections)
  → Body: { exclude_ids: [int] }
  → Returns: { candidates: Recipe[] }

GET /api/templates
  → List available templates

GET /api/templates/{name}
  → Get template definition
```

#### Modified endpoints

```
PATCH /api/menu/swap
  → No changes needed — already takes old_recipe_id and profile
  → Frontend sends the slot's profile name

POST /api/shopping-list
POST /api/shopping-list/text
  → Add optional body parameter: { recipe_ids: [int] }
  → If provided, generate list from only those recipes (selected subset)
  → If omitted, use full current menu (backward compat)
```

#### Unchanged

- `POST /api/generate/{profile}` — single-profile generation stays as-is
- `GET /api/menu` — returns current menu as before
- `POST /api/meal-plan` — receives recipe list from frontend (already flexible)

### 6. Data flow summary

```
Template
  → WeeklyGenerationService (extended for single-occasion templates)
    → MenuService.select_recipes() per slot (existing)
      → Solver per slot (existing, choices = generate count)
    → Dedup across slots (existing)
  → Response: candidates grouped by slot

Frontend
  → CurationSession state (new, client-side)
    → User selects/deselects/swaps within slots
    → Swap calls PATCH /api/menu/swap (existing)
    → Regenerate calls POST /api/.../slot/{index} (new)
  → Finalize
    → Shopping list from selected recipes
    → Meal plan save from selected recipes
```

## Implementation sequence

### Phase 2a: Simple curation (Workflow A)

Smallest useful increment. No templates, no slots, no new generation model.

1. **Swap UI** — surface the existing swap endpoint on recipe cards/detail modal
2. **Remove/restore** — client-side only, toggle recipes in/out of the active set
3. **Shopping list integration** — `SHOPPING_LIST_WRITE` provider capability + Tandoor implementation. Push selected recipes' ingredients to Tandoor's native shopping list. Minimal local UI fallback for providers without the capability.
4. **Selection-aware meal plan save** — existing save flow, but only includes non-removed recipes

This makes the existing workflow immediately better. Backend changes limited to the new provider capability for shopping list push.

### Phase 2b: Candidate generation (Workflow B)

New generation model. Requires template system, admin UI, and new frontend layout.

1. Template schema and storage
2. **Admin panel template builder** — create/edit templates, pick profiles per slot, set generate/pick counts
3. Template generation endpoint (extend WeeklyGenerationService)
4. Candidate selection UI (new layout, slot-based, pre-selection with visual parity)
5. Per-slot regeneration
6. Running prep/cook time tally
7. Finalize → shopping list / meal plan save

### Phase 2c: Provider expansion

After curation is working against Tandoor:

1. `get_meal_types()` on provider interface
2. `search_recipes()` on provider interface (for manual add)
3. Second provider implementation (Mealie or Paprika) to validate the abstraction

## Decisions needed

### 1. Template creation: Admin panel UI

**Decided.** Users create templates through the admin panel — pick profiles, set generate/pick counts per slot, name it, save. Never count on users manually creating JSON files. This means the admin panel template builder is part of Phase 2b scope, not a follow-up.

### 2. Candidate pre-selection: Pre-select with visual parity

**Decided.** Top N candidates are pre-selected with a subtle "suggested" badge. Unselected candidates are equally prominent — not grayed out, not visually diminished. Pre-selection saves time for users who trust the solver; equal visual weight invites users who want to browse.

### 3. Candidate count: Default multiplier, overridable

**Decided.** Default `generate = pick * 3`, capped at pool size. Template author can override with an explicit `generate` value in the admin panel. Cap at pool size prevents asking for 15 candidates from a 6-recipe pool.

### 4. Cross-slot constraints: Show info, don't enforce

**Decided.** Display total prep/cook time for selected recipes as a running tally in the UI. No enforcement, no warnings — just visibility. Users self-regulate. Revisit enforcement if users ask for it.

### 5. Shopping list: Integration-first

**Decided.** Shopping list output is always a provider integration — push to the provider's native shopping list (Tandoor shopping list, Mealie shopping list, etc.) via `SHOPPING_LIST_WRITE` capability. Clipboard-only is never the right answer. Minimal local/UI support as a fallback when the provider doesn't support shopping list write, but the primary path is integration.

This moves `SHOPPING_LIST_WRITE` from Phase 2c into Phase 2a — it's part of the shopping list feature, not a later expansion.
