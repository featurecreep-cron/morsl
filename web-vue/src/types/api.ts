/** Recipe as returned by /api/menu and generation endpoints. */
export interface Recipe {
  id: number
  name: string
  image: string | null
  rating: number
  keywords: Array<{ name: string } | string>
  servings: number
  new: boolean
  created_at: string
  ingredients?: Ingredient[]
  description?: string
  steps?: Step[]
}

/** Current menu state from /api/menu. */
export interface Menu {
  recipes: Recipe[]
  profile: string
  generated_at: string
  version: number | null
  warnings: string[]
  relaxed_constraints: RelaxedConstraint[]
  clear_others: boolean
}

export interface RelaxedConstraint {
  label: string
  slack_value: number
  operator?: string
  original_count?: number
}

/** Generation status from /api/status. */
export interface GenerationStatus {
  state: 'idle' | 'generating' | 'complete' | 'error'
  error?: string
  message?: string
  progress?: number
}

/** Profile summary from /api/profiles. */
export interface ProfileSummary {
  name: string
  display_name: string
  choices: number
  is_default: boolean
  show_on_menu?: boolean
  icon?: string
  item_noun?: string
  category?: string | number
  default?: boolean
}

/** Category from /api/categories. */
export interface Category {
  id: string | number
  display_name: string
  subtitle: string
  icon: string
}

/** Settings from /api/settings/public. */
export interface AppSettings {
  app_name: string
  theme: string
  kiosk_enabled: boolean
  kiosk_pin_enabled: boolean
  kiosk_gesture: string
  admin_pin_enabled: boolean
  has_pin: boolean
  show_logo: boolean
  logo_url: string
  favicon_url: string
  favicon_use_logo: boolean
  loading_icon_url: string
  loading_icon_use_logo: boolean
  slogan_header: string
  slogan_footer: string
  show_ratings: boolean
  ratings_enabled: boolean
  orders_enabled: boolean
  save_ratings_to_tandoor: boolean
  show_new_badge: boolean
  item_noun: string
  toast_seconds: number
  menu_poll_seconds: number
  max_discover_generations: number
  max_previous_recipes: number
  qr_show_on_menu: boolean
  qr_wifi_string: string
  qr_menu_url: string
  [key: string]: unknown
}

/** SSE event types. */
export type SSEEventType =
  | 'generating'
  | 'menu_updated'
  | 'menu_cleared'
  | 'connected'
  | 'settings_changed'
  | 'status'
  | 'version'

export interface SSEEvent {
  type: SSEEventType
  data: unknown
}

/** Recipe detail from /api/recipe/:id. */
export interface RecipeDetail {
  id: number
  name: string
  image: string | null
  description: string
  servings: number
  working_time: number
  waiting_time: number
  keywords: Array<{ name: string } | string>
  rating: number
  ingredients: Ingredient[]
  steps: Step[]
  source_url: string | null
}

export interface Ingredient {
  amount: number | null
  unit: string | null
  food: string
  note: string | null
  is_header: boolean
  original_text: string | null
}

export interface Step {
  instruction: string
  ingredients: Ingredient[]
  time: number
  order: number
  name?: string
}

/** Shelf generation stored in localStorage */
export interface ShelfGeneration {
  recipes: Recipe[]
  generatedAt: string
  profile?: string
}

/** A shelf entry (one per profile/category) */
export interface Shelf {
  name: string
  generations: ShelfGeneration[]
  currentIndex: number
}

/** Carousel item — either a recipe or a divider */
export interface CarouselDivider {
  _isDivider: true
  _pageNum: number
  _totalPages: number
  _generatedAt: string
  _profile: string
}

export type CarouselItem = (Recipe & { _genIndex: number }) | CarouselDivider

/** Meal plan types */
export interface MealType {
  id: number
  name: string
}

export interface TandoorUser {
  id: number
  username: string
  display_name?: string
}

/** Name prompt state */
export interface NamePromptState {
  show: boolean
  name: string
  recipe: Recipe | null
  action: 'order' | 'rate' | ''
  rating: number
  confirmStep: boolean
}

/** Confirm modal state */
export interface ConfirmModalState {
  show: boolean
  title: string
  message: string
  confirmText: string
  onConfirm: () => void
}

/** Meal plan save state */
export interface MealPlanSaveState {
  show: boolean
  date: string
  mealTypeId: number | null
  mealTypes: MealType[]
  users: TandoorUser[]
  selectedUsers: number[]
  saving: boolean
  profile: string | null
  generations: ShelfGeneration[]
  selectedGen: number
  expandedGen: number | null
}

/** Pending order state */
export interface PendingOrder {
  id: number
  recipe_name: string
  status: string
}

/** Icon mappings from /api/icon-mappings */
export interface IconMappings {
  keyword_icons: Record<string, string>
  food_icons: Record<string, string>
}

/** Setup wizard types */

export interface SetupStatus {
  has_credentials: boolean
  has_profiles: boolean
  has_categories: boolean
}

export interface ConnectionTestResult {
  success: boolean
  error?: string
}

export interface ProfilePreset {
  key: string
  name: string
  subtitle: string
  icon: string
  selected: boolean
  choices: number
}

export interface TagItem {
  id: number
  name: string
}

export interface BalanceItem extends TagItem {
  count: number
}

export interface ProfileRules {
  tagsInclude: { active: boolean; theme: TagItem[]; balance: BalanceItem[] }
  foodsInclude: { active: boolean; items: TagItem[]; except: TagItem[]; count: number }
  booksInclude: { active: boolean; items: TagItem[]; count: number }
  tagsExclude: { active: boolean; items: TagItem[] }
  foodsExclude: { active: boolean; items: TagItem[] }
  rating: { active: boolean; min: number }
  avoidRecent: { active: boolean; days: number }
  includeNew: { active: boolean; count: number; days: number }
}

export interface ProfileEntry {
  name: string
  description: string
  icon: string
  category: string
  choices: number
  min_choices: number | null
  default: boolean
  rules: ProfileRules
}

export interface CategoryPreset {
  key: string
  display_name: string
  subtitle: string
  icon: string
  selected: boolean
}

export interface ProfileAssignment {
  name: string
  category: string
}

export interface RuleSummaryLine {
  text: string
  page: string
}

/** Admin types */

export type ConstraintOperator = '>=' | '<=' | '=='
export type AdminConstraintType =
  | 'keyword'
  | 'food'
  | 'book'
  | 'rating'
  | 'cookedon'
  | 'createdon'
  | 'makenow'

export interface AdminConstraint {
  type: AdminConstraintType
  operator: ConstraintOperator
  count: number
  items?: Array<{ id: number; name: string; path?: string }>
  except?: Array<{ id: number; name: string }>
  label?: string
  weight?: number
  min?: number
  max?: number
  date_direction?: 'within' | 'older'
  date_days?: number
  date_before?: string
  date_after?: string
  include_children?: boolean
}

export interface ConstraintTypeInfo {
  label: string
  icon: string
  description: string
  help?: string
}

export interface ProfileEditorState {
  name: string
  originalName: string
  description: string
  choices: number
  min_choices: number | null
  default: boolean
  show_on_menu: boolean
  icon: string
  item_noun: string
  category: string | number
  constraints: AdminConstraint[]
  filters: number[]
}

export interface AdminProfileSummary extends ProfileSummary {
  constraint_count: number
  description?: string
}

export interface TemplateSlot {
  days: string[]
  meal_type_id: number
  meal_type_name: string
  profile: string
  recipes_per_day: number
}

export interface Template {
  name: string
  description: string
  deduplicate: boolean
  slots: TemplateSlot[]
  slot_count: number
}

export interface TemplateEditorState {
  name: string
  originalName: string
  description: string
  deduplicate: boolean
  slots: TemplateSlot[]
}

export interface Schedule {
  id: number
  profile: string | null
  template: string | null
  day_of_week: string
  hour: number
  minute: number
  enabled: boolean
  clear_before_generate: boolean
  create_meal_plan: boolean
  meal_plan_type: number | null
  cleanup_uncooked_days: number
  last_run: string | null
}

export interface ScheduleForm {
  mode: 'profile' | 'template'
  template: string
  profile: string
  day_of_week: string
  hour: number
  minute: number
  enabled: boolean
  clear_before_generate: boolean
  create_meal_plan: boolean
  meal_plan_type: number | null
  cleanup_uncooked_days: number
  _selectedDays: string[]
}

export interface Order {
  id: number
  recipe_id: number
  recipe_name: string
  customer_name?: string
  timestamp: string
  status: string
}

export interface OrderCount {
  recipe_id: number
  recipe_name: string
  count: number
}

export interface HistoryEntry {
  id: number
  generated_at: string
  profile: string
  recipe_count: number
  status: string
  duration_ms: number
  error?: string
  recipes: Array<{ id: number; name: string }>
  constraint_count: number
  relaxed_constraints: RelaxedConstraint[]
  warnings: string[]
}

export interface AnalyticsData {
  total_generations: number
  avg_duration_ms: number
  status_counts: Record<string, number>
  profile_counts: Record<string, number>
  most_relaxed: Array<{ label: string; relaxation_rate: number }>
  avg_recipes_per_generation: number
}

export interface WeeklyStatus {
  state: 'idle' | 'generating' | 'complete' | 'error'
  error?: string
  warnings?: string[]
  profile_progress: Record<string, string>
}

export interface WeeklyPlanDay {
  date: string
  data: {
    meals: Record<
      string,
      {
        meal_type_name: string
        recipes: Recipe[]
      }
    >
  }
}

export interface CustomFilter {
  id: number
  name: string
}
