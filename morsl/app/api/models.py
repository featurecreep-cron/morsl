from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field

from morsl.constants import API_CACHE_TTL_MINUTES


class IngredientResponse(BaseModel):
    amount: Optional[float] = None
    unit: Optional[str] = None
    food: str


class StepResponse(BaseModel):
    name: str = ""
    instruction: str
    time: int = 0
    order: int = 0


class KeywordRef(BaseModel):
    id: int
    name: str = ""


class RecipeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    rating: Optional[float] = None
    image: Optional[str] = None
    ingredients: List[IngredientResponse] = []
    keywords: List[KeywordRef] = []
    steps: List[StepResponse] = []
    working_time: Optional[int] = None
    cooking_time: Optional[int] = None


class RelaxedConstraintResponse(BaseModel):
    label: str
    slack_value: float
    weight: float


class SolverResultResponse(BaseModel):
    recipes: List[RecipeResponse]
    requested_count: int
    constraint_count: int
    status: str
    warnings: List[str] = []
    relaxed_constraints: List[RelaxedConstraintResponse] = []


class MenuResponse(BaseModel):
    recipes: List[RecipeResponse]
    generated_at: str
    requested_count: int
    constraint_count: int
    status: str
    profile: str = ""
    warnings: List[str] = []
    relaxed_constraints: List[RelaxedConstraintResponse] = []

    @computed_field
    @property
    def version(self) -> str:
        content = json.dumps(
            {"recipes": [r.model_dump() for r in self.recipes], "generated_at": self.generated_at},
            sort_keys=True,
        )
        return hashlib.md5(content.encode()).hexdigest()[:12]  # noqa: S324


class GenerationStatusResponse(BaseModel):
    state: str
    request_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    recipe_count: Optional[int] = None
    warnings: List[str] = []


class GenerateRequest(BaseModel):
    """Custom generation request with inline constraints (v2 format)."""

    choices: int = 5
    min_choices: Optional[int] = None
    cache: int = API_CACHE_TTL_MINUTES
    recipes: Optional[Dict[str, Any]] = None
    filters: List[int] = []
    plan_type: List[int] = []
    constraints: List[Dict[str, Any]] = []


class GenerateResponse(BaseModel):
    request_id: str
    status: str


class ProfileResponse(BaseModel):
    name: str
    choices: int
    constraint_count: int
    description: str = ""
    icon: str = ""
    category: str = ""
    default: bool = False
    show_on_menu: bool = True
    item_noun: str = ""


class ProfileCreateRequest(BaseModel):
    """Full profile shape for create/update (v2 format)."""

    name: str
    description: str = ""
    icon: str = ""
    category: str = ""
    choices: int = 5
    min_choices: Optional[int] = None
    cache: int = API_CACHE_TTL_MINUTES
    filters: List[int] = []
    plan_type: List[int] = []
    constraints: List[Dict[str, Any]] = []
    default: bool = False
    show_on_menu: bool = True
    item_noun: str = ""

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert to the dict format expected by ConfigService."""
        data = self.model_dump(exclude={"name", "default"})
        # Remove empty lists to keep files clean
        if not data.get("constraints"):
            data.pop("constraints", None)
        if not data.get("filters"):
            data.pop("filters", None)
        if not data.get("plan_type"):
            data.pop("plan_type", None)
        return data


class ProfileDetailResponse(BaseModel):
    name: str
    config: Dict[str, Any]


class RatingRequest(BaseModel):
    rating: float
    customer_name: Optional[str] = None


class OrderRequest(BaseModel):
    recipe_id: int
    recipe_name: str
    servings: int = 1
    customer_name: Optional[str] = None


class MealTypeCreateRequest(BaseModel):
    name: str
    color: Optional[str] = "#FF5722"


class RecipeRef(BaseModel):
    id: int
    name: str


class MealPlanSaveRequest(BaseModel):
    date: str  # YYYY-MM-DD
    meal_type_id: int
    shared: List[int] = []
    recipes: Optional[List[RecipeRef]] = None


# ---- History ----


class HistoryRecipeSummary(BaseModel):
    id: int
    name: str


class HistoryEntryResponse(BaseModel):
    id: str
    generated_at: str
    duration_ms: int
    profile: str
    request_id: str
    recipe_count: int
    requested_count: int
    constraint_count: int
    status: str
    recipes: List[HistoryRecipeSummary] = []
    relaxed_constraints: List[RelaxedConstraintResponse] = []
    warnings: List[str] = []
    error: Optional[str] = None


class HistoryListResponse(BaseModel):
    entries: List[HistoryEntryResponse]
    total: int


class ConstraintAnalyticsItem(BaseModel):
    label: str
    times_relaxed: int
    avg_slack: float
    total_generations: int
    relaxation_rate: float


class AnalyticsResponse(BaseModel):
    total_generations: int
    avg_duration_ms: float
    status_counts: Dict[str, int] = {}
    profile_counts: Dict[str, int] = {}
    most_relaxed: List[ConstraintAnalyticsItem] = []
    avg_recipes_per_generation: float = 0


class CategoryRequest(BaseModel):
    id: str = ""
    display_name: str
    subtitle: str = ""
    icon: str = ""
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: str
    display_name: str
    subtitle: str = ""
    icon: str = ""
    sort_order: int = 0


class IconMappingRequest(BaseModel):
    keyword_icons: Dict[str, str] = {}
    food_icons: Dict[str, str] = {}


class ScheduleRequest(BaseModel):
    profile: Optional[str] = None
    template: Optional[str] = None
    day_of_week: str = "mon-fri"
    hour: int = 16
    minute: int = 0
    enabled: bool = True
    clear_before_generate: bool = False
    create_meal_plan: bool = False
    meal_plan_type: Optional[int] = None
    cleanup_uncooked_days: int = 0


class ScheduleResponse(BaseModel):
    id: str
    profile: Optional[str] = None
    template: Optional[str] = None
    day_of_week: str
    hour: int
    minute: int
    enabled: bool
    clear_before_generate: bool = False
    create_meal_plan: bool = False
    meal_plan_type: Optional[int] = None
    cleanup_uncooked_days: int = 0
    last_run: Optional[str] = None


# ---- Templates ----


class TemplateSlot(BaseModel):
    days: List[str]
    meal_type_id: int
    meal_type_name: str = ""
    profile: str
    recipes_per_day: int = 1


class TemplateCreateRequest(BaseModel):
    name: str
    description: str = ""
    slots: List[TemplateSlot]
    deduplicate: bool = True


class TemplateUpdateRequest(BaseModel):
    description: str = ""
    slots: List[TemplateSlot]
    deduplicate: bool = True


class TemplateSummaryResponse(BaseModel):
    name: str
    description: str = ""
    slot_count: int = 0
    deduplicate: bool = True


class TemplateDetailResponse(BaseModel):
    name: str
    description: str = ""
    slots: List[TemplateSlot] = []
    deduplicate: bool = True


# ---- Weekly Generation ----


class WeeklyGenerateRequest(BaseModel):
    week_start: Optional[str] = None  # YYYY-MM-DD, defaults to current week's Monday


class WeeklyRegenerateSlotRequest(BaseModel):
    template: str
    date: str  # YYYY-MM-DD
    meal_type_id: int


class WeeklySaveRequest(BaseModel):
    template: str
    shared: List[int] = []


class WeeklyGenerationStatusResponse(BaseModel):
    state: str
    request_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    template: Optional[str] = None
    profile_progress: Dict[str, str] = {}
    warnings: List[str] = []


class WeeklySaveResponse(BaseModel):
    created: int
    errors: List[str] = []
    total: int
