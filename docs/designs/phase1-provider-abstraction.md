# Provider Abstraction & Pantry-Aware Generation

Status: **implemented** — Phase 1 (F1, F3)

## Context

morsl was hard-coupled to Tandoor Recipes via direct `TandoorAPI` calls in every service. This blocks future provider support (Mealie, Paprika, etc.) and makes testing require mocking the HTTP client. The provider abstraction decouples the service layer from any specific recipe app.

## Design

### Provider Interface (`base`)

`morsl/providers/base.py` defines:
- `Capability` flag enum: `ONHAND`, `SHOPPING_LIST`, `MEAL_PLAN`, `NUTRITION`, `SEARCH`, `SUBSTITUTES`
- `RecipeProvider` ABC with core methods (required) and optional methods (default no-op)

Core methods use generic terminology:
- `get_tag_tree` / `get_tag` (Tandoor: keywords)
- `get_ingredient` (Tandoor: foods)
- `get_collection` / `get_collection_recipes` (Tandoor: books)
- `get_recipes`, `get_recipe_details`

Optional methods declared via `capabilities()`:
- `get_onhand_items()` — on-hand ingredient list (ONHAND)
- `get_ingredient_substitutes()` — substitute lookup (SUBSTITUTES)
- `get_mealplan_recipes()` — meal plan queries (MEAL_PLAN)
- `get_custom_filters()` — saved filters

### Tandoor Provider (`tandoor`)

`morsl/providers/tandoor.py` wraps `TandoorAPI`, mapping generic names to Tandoor-specific calls. Exposes `.api` property for Tandoor-only operations (meal plan CRUD, orders) that don't belong on the generic interface.

### Pantry Constraint (`menu_service`)

Profile-level `pantry: true` flag auto-injects a soft `makenow` constraint during `prepare_constraints()`. Only activates if provider declares `ONHAND` capability. Skips injection if user already has a manual `makenow` constraint. Weight configurable via `pantry_weight` (default 5).

## Affected Modules

- `base` — new ABC + Capability enum
- `tandoor` — new provider wrapping TandoorAPI
- `menu_service` — constructor takes `RecipeProvider`, pantry constraint injection
- `generation_service` — creates TandoorProvider, passes to MenuService
- `recipe_detail_service` — parameter renamed api→provider, method names genericized
- `weekly_generation_service` — same pattern as generation_service
- `solver` — unchanged (operates on Recipe objects, not provider)
- `dependencies` — `get_provider()` dependency for routes needing a provider instance
- `tandoor_api` — added `get_onhand_foods()` method
