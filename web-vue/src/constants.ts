/**
 * Shared frontend constants — ported from web/js/constants.js.
 * All magic numbers and localStorage keys live here.
 */
export const CONST = {
  // Timers & polling
  STATUS_POLL_MS: 2000,
  GENERATING_TICK_MS: 1000,
  SCROLL_ARROW_DELAY_MS: 200,
  SCROLL_ARROW_SETTLE_MS: 600,

  // SSE reconnect
  SSE_INITIAL_RETRY_MS: 1000,
  SSE_MAX_RETRY_MS: 30000,

  // Data limits
  MAX_SHELF_GENERATIONS: 5,
  MAX_RECENT_NAMES: 10,

  // Layout
  CAROUSEL_GAP_PX: 16,
  SCROLL_THRESHOLD_PX: 10,
  SWIPE_ZONE_PX: 100,
  SWIPE_DISTANCE_PX: 150,

  // localStorage keys
  LS_MENU_HISTORY: 'menu-history',
  LS_MENU_SHELVES: 'menu-shelves',
  LS_ACTIVE_DECK: 'menu-active-deck',
  LS_RECENT_NAMES: 'recentNames',
  LS_DISCOVER_GENS: 'menu-discover-generations',

  // sessionStorage keys
  SS_ADMIN_TOKEN: 'admin-token',
  SS_ADMIN_TOKEN_TS: 'admin-token-ts',

  // Setup wizard search debounce
  KEYWORD_DEBOUNCE_MS: 150,
  FOOD_DEBOUNCE_MS: 300,
  BOOK_DEBOUNCE_MS: 300,

  // Admin search limits
  MAX_KEYWORD_RESULTS: 20,
  MIN_KEYWORD_SEARCH_LEN: 2,
  DEFAULT_CUSTOM_CHOICES: 5,
  HISTORY_PAGE_SIZE: 20,

  // localStorage keys (admin)
  LS_ADMIN_TIER: 'admin-tier',

  // Defaults for settings-backed values
  DEFAULT_MENU_POLL_SECONDS: 60,
  DEFAULT_TOAST_SECONDS: 2,
  DEFAULT_MAX_DISCOVER_GENS: 10,
  DEFAULT_MAX_PREVIOUS_RECIPES: 50,
} as const
