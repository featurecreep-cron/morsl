/**
 * Shared frontend constants — loaded before app.js and admin.js.
 * All magic numbers and localStorage keys live here.
 */
const CONST = {
    // Timers & polling
    STATUS_POLL_MS: 2000,
    GENERATING_TICK_MS: 1000,
    SCROLL_ARROW_DELAY_MS: 200,
    SCROLL_ARROW_SETTLE_MS: 600,

    // Debounce
    KEYWORD_DEBOUNCE_MS: 150,
    FOOD_DEBOUNCE_MS: 300,
    BOOK_DEBOUNCE_MS: 300,

    // SSE reconnect
    SSE_INITIAL_RETRY_MS: 1000,
    SSE_MAX_RETRY_MS: 30000,

    // Data limits (non-configurable)
    MAX_SHELF_GENERATIONS: 5,
    MAX_RECENT_NAMES: 10,
    MAX_KEYWORD_RESULTS: 20,
    MIN_KEYWORD_SEARCH_LEN: 2,
    DEFAULT_CUSTOM_CHOICES: 5,

    // Layout
    CAROUSEL_GAP_PX: 16,
    SCROLL_THRESHOLD_PX: 10,
    SWIPE_ZONE_PX: 100,
    SWIPE_DISTANCE_PX: 150,

    // localStorage keys
    LS_MENU_HISTORY: 'menu-history',
    LS_MENU_SHELVES: 'menu-shelves',
    LS_ACTIVE_DECK: 'menu-active-deck',
    LS_DISCOVER_GENS: 'menu-discover-generations',
    LS_RECENT_NAMES: 'recentNames',
    LS_ADMIN_TIER: 'admin-tier',

    // sessionStorage keys
    SS_ADMIN_TOKEN: 'admin-token',

    // Defaults for settings-backed values (before settings load)
    DEFAULT_MENU_POLL_SECONDS: 60,
    DEFAULT_TOAST_SECONDS: 2,
    DEFAULT_MAX_DISCOVER_GENS: 10,
    DEFAULT_MAX_PREVIOUS_RECIPES: 50,
};

Object.freeze(CONST);
