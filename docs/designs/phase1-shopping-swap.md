# Shopping List Generation & Recipe Swap

Status: **implemented** — Phase 1 (F2, F4)

## Context

After generating a menu, users need two things: a shopping list aggregating all ingredients, and the ability to replace a single recipe without regenerating the entire menu.

## Shopping List (F2)

### Service (`shopping_service`)

`generate_shopping_list(recipes, exclude_onhand=None)` aggregates ingredients from menu recipe dicts:

- Groups by `(food_name_lower, canonical_unit)` — deduplicates across recipes
- Unit normalization: maps aliases (grams→g, cups→cup, tablespoons→tbsp, etc.) to canonical form, converts within measurement systems (g↔kg at 1000, ml↔l at 1000)
- Display upscaling: 1500g renders as 1.5kg
- Source tracking: each item records which recipes need it
- On-hand exclusion: optional list of food names to skip (case-insensitive)

`get_onhand_names(provider)` fetches on-hand food names via provider interface (capability-gated).

Returns `ShoppingList` with `to_dict()` and `to_text()` for API and clipboard respectively.

### API (`shopping` route)

- `POST /api/shopping-list` — JSON response with aggregated items, `?exclude_onhand=true` to filter
- `POST /api/shopping-list/text` — plain text for clipboard copy

Uses `get_provider` dependency (not direct TandoorAPI instantiation — architecture constraint).

## Recipe Swap (F4)

### Solver (`solver`)

`RecipePicker` accepts optional `locked` parameter — a list of Recipe objects whose selection variables are fixed to 1 in `_build_problem()`. The solver fills remaining slots from the pool while respecting all constraints.

### Generation Service (`generation_service`)

`swap_recipe(old_recipe_id, config, url, token, logger)`:

1. Validates recipe exists in current menu
2. Loads full recipe pool via MenuService
3. Locks all current recipes except the swapped one
4. Removes old recipe from pool (can't be re-selected)
5. Applies profile constraints to the solver
6. Solves for locked + 1 slot
7. Fetches full details for the new recipe
8. Replaces in menu and saves atomically

Raises `RuntimeError` with descriptive messages for: no menu, recipe not found, no replacement available, constraint infeasibility.

### API (`menu` route)

`PATCH /api/menu/swap` with `{old_recipe_id, profile}` — returns the new `RecipeResponse`. Uses profile config to apply constraints during re-solve.

## Affected Modules

- `shopping_service` — new service for aggregation + on-hand lookup
- `shopping` — new API route
- `solver` — `locked` parameter on RecipePicker constructor
- `generation_service` — `swap_recipe()` method
- `menu_service` — used by swap for constraint preparation (no changes needed)
- `dependencies` — `get_provider()` for shopping route
- `app/api/models` — ShoppingItemResponse, ShoppingListResponse, SwapRequest
