function menuApp() {
    // INTERNAL_PROFILES removed — visibility is now controlled by show_on_menu field

    return {
        // Application state
        state: 'loading',  // loading | ready | generating | error
        errorMessage: '',

        // Menu data
        recipes: [],
        currentRecipes: [],
        previousRecipes: [],
        warnings: [],
        relaxedConstraints: [],
        menuVersion: null,
        generatedAt: '',

        // Profiles
        profiles: [],
        activeProfile: null,

        // Categories (loaded from API)
        categories: [],
        categoryPanelOpen: null,  // id of open category panel, or null

        // Theming
        currentTheme: localStorage.getItem('morsl-theme') || 'cast-iron',

        // Navigation
        navOpen: false,
        appVersion: '',

        // Recipe modal
        selectedRecipe: null,
        orderConfirm: null,  // recipe id that was just ordered

        // Name prompt (reusable for orders and ratings)
        namePrompt: { show: false, name: '', callback: null, recipe: null, action: '', rating: 0, confirmStep: false },
        recentNames: [],

        // Settings (loaded from /api/settings/public)
        settings: {},
        settingsLoaded: false,

        // Carousel scroll state
        canScrollLeft: false,
        canScrollRight: false,
        canPageLeft: false,
        canPageRight: false,

        // Icon mappings (keyword/food → icon, loaded from API)
        iconMappings: {},

        // Bumped when custom icons finish loading, to trigger Alpine re-renders
        _iconGen: 0,

        // Memoization for mainCarouselRecipes
        _carouselCache: null,
        _carouselCacheKey: null,

        // Menu SSE
        _menuSSE: null,
        _sseRetryDelay: 1000,
        _loadMenuInFlight: false,
        _loadMenuPending: false,
        _pendingClearOthers: false,

        // Category shelves (persistent per-category rows)
        shelves: [],          // [{name, generations: [{recipes, generatedAt}], currentIndex: 0}, ...]
        activeDeckName: null, // which shelf is in the main carousel
        _targetShelf: null,      // shelf name for current generation

        // Meal plan save
        mealPlanSave: {
            show: false,
            date: new Date().toISOString().slice(0, 10),
            mealTypeId: null,
            mealTypes: [],
            users: [],
            selectedUsers: [],
            saving: false,
            profile: null,
            generations: [],
            selectedGen: 0,
            expandedGen: null,
        },
        mealPlanToast: false,

        // Kiosk
        showKioskPin: false,
        showKioskPinText: false,
        kioskPinValue: '',
        kioskPinError: '',

        _kioskLongPressTimer: null,
        _kioskGestureCleanup: null,

        // Confirmation modal
        confirmModal: {
            show: false,
            title: '',
            message: '',
            confirmText: '',
            onConfirm: () => {},
        },

        // Inline SVG abort controller
        _svgAbort: null,

        // Polling handles
        _menuPollId: null,
        _statusPollId: null,

        // ---- Computed ----

        get visibleProfiles() {
            return this.profiles.filter(p => p.show_on_menu !== false);
        },

        get displayCategories() {
            if (this.categories.length > 0) return this.categories;
            if (this.profiles.length === 0) return [];
            return [{ id: '_all', display_name: '', subtitle: '', icon: '' }];
        },

        get categorizedProfiles() {
            const result = {};
            const categoryIds = new Set();
            const visible = this.visibleProfiles;
            for (const cat of this.displayCategories) {
                if (cat.id === '_all') {
                    result['_all'] = visible;
                } else {
                    categoryIds.add(cat.id);
                    result[cat.id] = visible.filter(p => p.category === cat.id);
                }
            }
            // Profiles not assigned to any defined category
            if (categoryIds.size > 0) {
                const uncategorized = visible.filter(p => !p.category || !categoryIds.has(p.category));
                if (uncategorized.length > 0) result['_uncategorized'] = uncategorized;
            }
            return result;
        },

        get mainCarouselRecipes() {
            let gens;
            if (this.activeDeckName) {
                gens = (this.shelves.find(s => s.name === this.activeDeckName) || {}).generations || [];
            } else if (this.shelves.length > 0) {
                gens = this.shelves[0].generations || [];
            } else {
                return [];
            }
            const cacheKey = (this.activeDeckName || '_first') + ':' + gens.length + ':' +
                gens.reduce((s, g) => s + (g.recipes ? g.recipes.length : 0), 0);
            if (this._carouselCacheKey === cacheKey && this._carouselCache) {
                return this._carouselCache;
            }
            const profile = this.activeDeckName || (this.shelves[0]?.name) || 'mixed';
            this._carouselCache = this.flattenGenerations(gens, profile);
            this._carouselCacheKey = cacheKey;
            return this._carouselCache;
        },

        flattenGenerations(generations, defaultProfile) {
            const items = [];
            for (let i = 0; i < generations.length; i++) {
                const gen = generations[i];
                if (!gen || !Array.isArray(gen.recipes)) continue;
                if (i > 0) {
                    items.push({
                        _isDivider: true,
                        _pageNum: i + 1,
                        _totalPages: generations.length,
                        _generatedAt: gen.generatedAt,
                        _profile: gen.profile || defaultProfile,
                    });
                }
                for (const recipe of gen.recipes) {
                    if (recipe && recipe.id) {
                        items.push({ ...recipe, _genIndex: i });
                    }
                }
            }
            return items;
        },


        // ---- Lifecycle ----

        async init() {
            this.applyTheme(this.currentTheme);
            this.registerServiceWorker();
            // Fetch version (no auth required)
            try {
                const h = await fetch('/health');
                if (h.ok) this.appVersion = (await h.json()).version || '';
            } catch (_) { /* ignore */ }
            // Restore history from localStorage
            try {
                const saved = localStorage.getItem(CONST.LS_MENU_HISTORY);
                if (saved) this.previousRecipes = JSON.parse(saved);
            } catch (e) { /* ignore corrupt data */ }
            this._loadRecentNames();
            this.loadShelves();
            // Tier 1: fast UI chrome — settings, profiles, categories
            await Promise.all([
                this.loadCategories(),
                this.loadProfiles(),
                this.loadSettings(),
            ]);
            this.state = 'ready';
            // Tier 2: heavier data — menu and icon mappings load in background
            Promise.all([
                this.loadMenu(),
                this.loadIconMappings(),
            ]).catch(e => console.warn('Background load failed:', e));
            // If shelves exist but no active deck, set to first shelf
            if (this.shelves.length > 0 && !this.activeDeckName) {
                this.activeDeckName = this.shelves[0].name;
            }
            // Prefetch brand logo and loading icon SVGs for theme-aware inline rendering
            if (this.settings.logo_url) {
                prefetchBrandSvg(this.settings.logo_url).then(ok => { if (ok) this._iconGen++; });
            }
            const loadingUrl = this.loadingIconUrl;
            if (loadingUrl && loadingUrl !== DEFAULT_FAVICON_PATH) {
                prefetchBrandSvg(loadingUrl).then(ok => {
                    if (ok) {
                        this._iconGen++;
                        // Cache the resolved loading icon for instant display on next page load
                        try { localStorage.setItem('morsl-loading-icon', getBrandIcon(loadingUrl)); } catch (e) { /* */ }
                    }
                });
            }
            // Inline SVG logos (inherit theme color via currentColor)
            this._svgAbort = new AbortController();
            this._updateInlineSvgs();
            this.$watch(() => this.logoUrl, () => this._updateInlineSvgs());
            // Re-render icons once custom SVGs finish loading
            this._iconHandler = () => this._iconGen++;
            window.addEventListener('custom-icons-loaded', this._iconHandler);
            this.setupKioskGesture();
            this.connectMenuSSE();
            this.startMenuPolling();
            this.scheduleScrollArrowUpdate();
            this._resizeHandler = () => this.updateScrollArrows();
            window.addEventListener('resize', this._resizeHandler);
        },

        destroy() {
            if (this._svgAbort) { this._svgAbort.abort(); this._svgAbort = null; }
            if (this._menuSSE) { this._menuSSE.close(); this._menuSSE = null; }
            if (this._visibilityHandler) { document.removeEventListener('visibilitychange', this._visibilityHandler); this._visibilityHandler = null; }
            if (this._statusPollId) { clearInterval(this._statusPollId); this._statusPollId = null; }
            if (this._resizeHandler) { window.removeEventListener('resize', this._resizeHandler); this._resizeHandler = null; }
            if (this._kioskGestureCleanup) { this._kioskGestureCleanup(); this._kioskGestureCleanup = null; }
            if (this._iconHandler) { window.removeEventListener('custom-icons-loaded', this._iconHandler); this._iconHandler = null; }
        },

        _updateInlineSvgs() {
            const signal = this._svgAbort?.signal;
            if (this.logoUrl && this.$refs.menuLogo) {
                inlineSvg(this.logoUrl, this.$refs.menuLogo, signal);
            }
        },

        // ---- Data Loading ----

        async loadSettings() {
            try {
                const res = await fetch('/api/settings/public');
                if (res.ok) {
                    this.settings = await res.json();
                    this.settingsLoaded = true;
                    if (this.settings.theme) {
                        this.applyTheme(this.settings.theme);
                    }
                    document.title = this.settings.app_name || 'Morsl';
                    this._updateFaviconLinks();
                    this._renderFooterQr();
                }
            } catch (e) {
                console.warn('Failed to load settings:', e);
            }
        },

        _updateFaviconLinks() {
            const url = (this.settings.favicon_use_logo && this.settings.logo_url)
                ? this.settings.logo_url
                : this.settings.favicon_url;
            if (!url) return;
            document.querySelectorAll('link[rel="icon"]').forEach(link => {
                link.href = url;
            });
        },

        _renderFooterQr() {
            if (!this.settings.qr_show_on_menu || typeof qrcode === 'undefined') return;
            this.$nextTick(() => {
                const render = (ref, data) => {
                    if (!ref || !data) return;
                    const container = ref.querySelector('.qr-corner-code');
                    if (!container) return;
                    try {
                        const qr = qrcode(0, 'M');
                        qr.addData(data);
                        qr.make();
                        container.innerHTML = qr.createSvgTag({ cellSize: 2, margin: 1 });
                    } catch (e) { /* skip */ }
                };
                render(this.$refs.cornerQrWifi, this.settings.qr_wifi_string);
                render(this.$refs.cornerQrMenu, this.settings.qr_menu_url);
            });
        },

        get appName() { return this.settings.app_name || 'Morsl'; },
        get sloganHeader() { return this.settings.slogan_header || ''; },
        get sloganFooter() { return this.settings.slogan_footer || ''; },
        get logoUrl() { return this.settings.show_logo !== false ? (this.settings.logo_url || '') : ''; },
        get loadingIconUrl() {
            if (this.settings.loading_icon_use_logo && this.settings.logo_url) return this.settings.logo_url;
            return this.settings.loading_icon_url || DEFAULT_FAVICON_PATH;
        },
        get loadingIconHtml() {
            void this._iconGen;
            const url = this.loadingIconUrl;
            if (url === DEFAULT_FAVICON_PATH && !this.settingsLoaded) {
                // Before settings load, use cached loading icon from previous session
                try { const c = localStorage.getItem('morsl-loading-icon'); if (c) return c; } catch (e) { /* */ }
                return '';  // Don't flash stock icon while settings are loading
            }
            return getBrandIcon(url !== DEFAULT_FAVICON_PATH ? url : '');
        },

        async loadCategories() {
            try {
                const res = await fetch('/api/categories');
                if (res.ok) this.categories = await res.json();
            } catch (e) {
                console.warn('Failed to load categories:', e);
            }
        },

        async loadProfiles() {
            try {
                const res = await fetch('/api/profiles');
                if (res.ok) {
                    this.profiles = await res.json();
                }
            } catch (e) {
                console.warn('Failed to load profiles:', e);
            }
        },

        async loadIconMappings() {
            try {
                const res = await fetch('/api/icon-mappings');
                if (res.ok) {
                    this.iconMappings = await res.json();
                    this._iconGen++;
                }
            } catch (e) {
                console.warn('Failed to load icon mappings:', e);
            }
        },

        async loadMenu({ clearOthers = false } = {}) {
            try {
                const res = await fetch('/api/menu');
                if (res.ok) {
                    const data = await res.json();
                    // clear_others may be persisted in the menu JSON (schedule flag)
                    const effectiveClear = clearOthers || !!data.clear_others;
                    this.applyMenuData(data, { clearOthers: effectiveClear });
                    this.state = 'ready';
                } else if (res.status === 404) {
                    // No server menu — check if generation failed
                    this.shelves = [];
                    this.activeDeckName = null;
                    this.recipes = [];
                    this.currentRecipes = [];
                    this.saveShelves();
                    await this._checkGenerationStatus();
                } else {
                    this.state = 'error';
                    this.errorMessage = 'Failed to load menu';
                }
            } catch (e) {
                this.state = 'error';
                this.errorMessage = 'Cannot reach server';
            }
        },

        async _checkGenerationStatus() {
            try {
                const res = await fetch('/api/status');
                if (res.ok) {
                    const status = await res.json();
                    if (status.state === 'error') {
                        this.state = 'error';
                        this.errorMessage = status.error || 'Generation failed';
                        return;
                    } else if (status.state === 'generating') {
                        this.state = 'generating';
                        this.startStatusPolling();
                        return;
                    }
                }
            } catch (e) {
                // Fall through to ready state
            }
            this.state = 'ready';
        },

        applyMenuData(data, { clearOthers = false } = {}) {
            const newRecipes = data.recipes || [];
            this.warnings = data.warnings || [];
            this.relaxedConstraints = data.relaxed_constraints || [];
            this.generatedAt = data.generated_at || '';

            const versionChanged = data.version !== this.menuVersion;

            if (newRecipes.length > 0) {
                this.currentRecipes = newRecipes;

                // Scheduled generation with clear_others — fresh start
                if (clearOthers && versionChanged) {
                    this.shelves = [];
                    this.activeDeckName = null;
                    this._carouselCache = null;
                    this._carouselCacheKey = null;
                }

                if (this.shelves.length === 0) {
                    // First load or cleared — seed shelf
                    const name = data.profile || this.activeProfile || 'Menu';
                    this.addShelf(name, newRecipes);
                    this.activeDeckName = name;
                } else if (versionChanged) {
                    // Server has a newer menu than what shelves hold — update active shelf
                    const target = data.profile || this.activeDeckName || this.activeProfile || 'Menu';
                    this.addShelf(target, newRecipes);
                    this.activeDeckName = target;
                    this.saveShelves();
                }

                // Keep previousRecipes for backward compatibility
                const newIdSet = new Set(newRecipes.map(r => r.id));
                const merged = [
                    ...this.currentRecipes.filter(r => !newIdSet.has(r.id)),
                    ...this.previousRecipes.filter(r => !newIdSet.has(r.id)),
                ];
                const seen = new Set();
                this.previousRecipes = merged.filter(r => {
                    if (seen.has(r.id)) return false;
                    seen.add(r.id);
                    return true;
                }).slice(0, this.settings.max_previous_recipes ?? CONST.DEFAULT_MAX_PREVIOUS_RECIPES);

                try {
                    localStorage.setItem(CONST.LS_MENU_HISTORY, JSON.stringify(this.previousRecipes));
                } catch (e) { /* storage full */ }
            }

            // Set menuVersion AFTER shelf comparison so staleness is detected
            this.menuVersion = data.version;

            // Combined list for carousel
            this.recipes = [...this.currentRecipes, ...this.previousRecipes];

            // Scroll carousel to start only when content changed
            if (versionChanged) {
                this.$nextTick(() => this.scrollCarouselToStart());
            }
        },

        // ---- Menu SSE (real-time updates) ----

        connectMenuSSE() {
            if (this._menuSSE) this._menuSSE.close();
            this._sseRetryDelay = CONST.SSE_INITIAL_RETRY_MS;
            this._menuSSE = new EventSource('/api/menu/stream');

            this._menuSSE.addEventListener('generating', () => {
                // Only show spinner on kiosk displays — customers don't need to see it
                if (this.settings.kiosk_enabled && this.state !== 'generating') {
                    this.state = 'generating';
                }
            });

            this._menuSSE.addEventListener('menu_updated', (e) => {
                let clearOthers = false;
                try {
                    const data = JSON.parse(e.data);
                    clearOthers = !!data.clear_others;
                } catch (_) { /* ignore parse errors */ }
                this._pendingClearOthers = clearOthers;
                this._debouncedLoadMenu();
            });

            this._menuSSE.addEventListener('menu_cleared', () => {
                // On kiosk, clear immediately. On phones, keep current view with stale indicator.
                if (this.settings.kiosk_enabled) {
                    this.shelves = [];
                    this.activeDeckName = null;
                    this.menuVersion = null;
                    this.recipes = [];
                    this.currentRecipes = [];
                    this.generatedAt = '';
                    this.saveShelves();
                    this.state = 'ready';
                }
            });

            this._menuSSE.addEventListener('connected', (e) => {
                this._sseRetryDelay = CONST.SSE_INITIAL_RETRY_MS;
                // Reload page if server version changed (new deployment)
                try {
                    const data = JSON.parse(e.data);
                    if (this.appVersion && data.version && data.version !== this.appVersion) {
                        location.reload();
                        return;
                    }
                } catch (_) { /* ignore */ }
                // Sync state on reconnect — may have missed events while disconnected
                this._debouncedLoadMenu();
            });

            this._menuSSE.onerror = () => {
                this._menuSSE.close();
                setTimeout(() => this.connectMenuSSE(), this._sseRetryDelay);
                this._sseRetryDelay = Math.min(this._sseRetryDelay * 2, CONST.SSE_MAX_RETRY_MS);
            };
        },

        // Debounced menu load — prevents concurrent fetches from rapid SSE events
        _debouncedLoadMenu() {
            if (this._loadMenuInFlight) {
                this._loadMenuPending = true;
                return;
            }
            this._loadMenuInFlight = true;
            const clearOthers = this._pendingClearOthers || false;
            this._pendingClearOthers = false;
            this.loadMenu({ clearOthers }).finally(() => {
                this._loadMenuInFlight = false;
                if (this._loadMenuPending) {
                    this._loadMenuPending = false;
                    this._debouncedLoadMenu();
                }
            });
        },

        // Fallback: sync on tab visibility (SSE may have disconnected while backgrounded)
        startMenuPolling() {
            this._visibilityHandler = () => {
                if (document.visibilityState === 'visible') {
                    this._checkAppVersion();
                    // Only fetch if SSE is disconnected or version might be stale
                    if (!this._menuSSE || this._menuSSE.readyState !== EventSource.OPEN) {
                        this._debouncedLoadMenu();
                    }
                }
            };
            document.addEventListener('visibilitychange', this._visibilityHandler);
        },

        // ---- Generation ----

        async switchProfile(profileName) {
            if (this.state === 'generating') return;
            this.activeProfile = profileName;
            this.state = 'generating';
            this.errorMessage = '';

            try {
                const res = await fetch(
                    `/api/generate/${encodeURIComponent(profileName)}`,
                    { method: 'POST' }
                );
                if (res.status === 202) {
                    this.startStatusPolling();
                } else if (res.status === 409) {
                    this.startStatusPolling();
                } else {
                    this.state = 'error';
                    this.errorMessage = 'Failed to start generation';
                }
            } catch (e) {
                this.state = 'error';
                this.errorMessage = 'Cannot reach server';
            }
        },

        retryGeneration() {
            if (this.activeProfile) {
                this.switchProfile(this.activeProfile);
            } else if (this.visibleProfiles.length > 0) {
                this.switchProfile(this.visibleProfiles[0].name);
            } else {
                this.loadMenu();
            }
        },

        startStatusPolling() {
            if (this._statusPollId) clearInterval(this._statusPollId);
            this._statusPollId = setInterval(async () => {
                try {
                    const res = await fetch('/api/status');
                    if (!res.ok) return;
                    const status = await res.json();

                    if (status.state === 'complete' || status.state === 'idle') {
                        clearInterval(this._statusPollId);
                        this._statusPollId = null;
                        await this.loadMenuResult();
                    } else if (status.state === 'error') {
                        clearInterval(this._statusPollId);
                        this._statusPollId = null;
                        this.state = 'error';
                        this.errorMessage = status.error || 'Generation failed';
                    }
                } catch (e) {
                    // Keep polling
                }
            }, CONST.STATUS_POLL_MS);
        },

        // ---- Category / Carousel Actions ----

        discoverCocktails() {
            const available = this.visibleProfiles;
            if (available.length === 0) return;
            const pick = available.find(p => p.default)
                || available[Math.floor(Math.random() * available.length)];
            this._targetShelf = pick.name;
            this.switchProfile(pick.name);
        },

        selectCategory(name) {
            this._targetShelf = name;
            this.categoryPanelOpen = null;
            this.switchProfile(name);
        },

        toggleCategoryPanel(id) {
            this.categoryPanelOpen = this.categoryPanelOpen === id ? null : id;
        },

        // Category/profile icons (using custom SVG icons from icons.js)
        // Reading _iconGen creates an Alpine dependency so x-html re-evaluates
        // once custom icons finish loading asynchronously.
        getCategoryIcon(category) {
            void this._iconGen;
            const brandUrl = this.settings.logo_url || '';
            if (category.icon === 'logo') return getBrandIcon(brandUrl);
            if (category.icon) return getIconByKey(category.icon);
            // Fallback: first profile's icon in this category, or brand icon
            const profiles = this.categorizedProfiles[category.id] || [];
            if (profiles.length > 0) {
                const match = getIconIfExists(profiles[0].name);
                if (match) return match;
            }
            return getBrandIcon(brandUrl);
        },

        getProfileIcon(profileOrName) {
            void this._iconGen;
            // Accept profile object (with .icon) or string name
            if (typeof profileOrName === 'object' && profileOrName !== null) {
                if (profileOrName.icon) return getIconByKey(profileOrName.icon);
                // No explicit icon: try name-based match, fall back to brand icon
                const nameMatch = getIconIfExists(profileOrName.name || '');
                return nameMatch || getBrandIcon(this.settings.logo_url || '');
            }
            return getIconByKey(profileOrName);
        },

        getHeadingIcon() {
            void this._iconGen;
            return getBrandIcon(this.settings.logo_url || '');
        },

        // Resolve item noun: profile-level → global setting → "recipe"
        resolveNoun(profileName) {
            const p = this.profiles.find(x => x.name === profileName);
            return (p && p.item_noun) || this.settings.item_noun || 'recipe';
        },

        // Display name formatting (e.g., "oldfashioned" → "Old Fashioned")
        formatDisplayName(name) {
            const displayNames = {
                'oldfashioned': 'Old Fashioned',
            };
            return displayNames[name.toLowerCase()] || name.charAt(0).toUpperCase() + name.slice(1);
        },

        timeAgo(isoString) {
            if (!isoString) return '';
            return dayjs(isoString).fromNow();
        },

        formatMenuDate(isoString) {
            if (!isoString) return '';
            return dayjs(isoString).format('dddd, MMMM D');
        },

        scrollCarouselToStart() {
            const track = this.$refs.carouselTrack;
            if (track) track.scrollTo({ left: 0, behavior: 'smooth' });
            this.scheduleScrollArrowUpdate();
        },

        scrollCarousel(direction) {
            const track = this.$refs.carouselTrack;
            if (!track) return;
            const slide = track.children[0];
            const slideWidth = slide ? slide.offsetWidth + CONST.CAROUSEL_GAP_PX : 300; // gap
            track.scrollBy({ left: direction * slideWidth, behavior: 'smooth' });
        },

        getPageBoundaries() {
            const track = this.$refs.carouselTrack;
            if (!track) return [];
            const boundaries = [0];
            const dividers = track.querySelectorAll('.carousel-slide--divider');
            for (const div of dividers) {
                boundaries.push(div.offsetLeft);
            }
            return boundaries;
        },

        // Find the index of the boundary closest to the current scroll position
        getCurrentPageIndex(boundaries) {
            const track = this.$refs.carouselTrack;
            if (!track || boundaries.length === 0) return 0;
            const scrollLeft = track.scrollLeft;
            let closestIdx = 0;
            let closestDist = Math.abs(scrollLeft - boundaries[0]);
            for (let i = 1; i < boundaries.length; i++) {
                const dist = Math.abs(scrollLeft - boundaries[i]);
                if (dist < closestDist) {
                    closestIdx = i;
                    closestDist = dist;
                }
            }
            return closestIdx;
        },

        scrollToPrevPage() {
            const track = this.$refs.carouselTrack;
            if (!track) return;
            const boundaries = this.getPageBoundaries();
            const idx = this.getCurrentPageIndex(boundaries);
            if (idx > 0) {
                track.scrollTo({ left: boundaries[idx - 1], behavior: 'smooth' });
                this.scheduleScrollArrowUpdate();
            }
        },

        scrollToNextPage() {
            const track = this.$refs.carouselTrack;
            if (!track) return;
            const boundaries = this.getPageBoundaries();
            const idx = this.getCurrentPageIndex(boundaries);
            if (idx < boundaries.length - 1) {
                track.scrollTo({ left: boundaries[idx + 1], behavior: 'smooth' });
                this.scheduleScrollArrowUpdate();
            }
        },

        updateScrollArrows() {
            const track = this.$refs.carouselTrack;
            if (!track) {
                this.canScrollLeft = false;
                this.canScrollRight = false;
                this.canPageLeft = false;
                this.canPageRight = false;
                return;
            }
            const scrollLeft = track.scrollLeft;
            const scrollRight = track.scrollWidth - track.clientWidth - scrollLeft;
            this.canScrollLeft = scrollLeft > CONST.SCROLL_THRESHOLD_PX;
            this.canScrollRight = scrollRight > CONST.SCROLL_THRESHOLD_PX;

            const boundaries = this.getPageBoundaries();
            const idx = this.getCurrentPageIndex(boundaries);
            this.canPageLeft = idx > 0;
            this.canPageRight = idx < boundaries.length - 1;
        },

        // Debounced version for resize/load events
        scheduleScrollArrowUpdate() {
            this.$nextTick(() => this.updateScrollArrows());
            // Also check after images load and layout settles
            setTimeout(() => this.updateScrollArrows(), CONST.SCROLL_ARROW_DELAY_MS);
            setTimeout(() => this.updateScrollArrows(), CONST.SCROLL_ARROW_SETTLE_MS);
        },

        // ---- Category Shelves ----

        async loadMenuResult() {
            try {
                const res = await fetch('/api/menu');
                if (res.ok) {
                    const data = await res.json();
                    // SSE may have already delivered this menu — skip duplicate shelf add
                    if (data.version && data.version === this.menuVersion) {
                        this._targetShelf = null;
                        this.state = 'ready';
                        return;
                    }
                    const target = this._targetShelf || data.profile || this.activeProfile || 'Menu';
                    this._targetShelf = null;
                    this.addShelf(target, data.recipes || []);
                    this.activeDeckName = target;
                    this.generatedAt = data.generated_at || '';
                    this.menuVersion = data.version;
                    this.currentRecipes = data.recipes || [];
                    this.recipes = [...this.currentRecipes, ...this.previousRecipes];
                    this.saveShelves();
                    this.state = 'ready';
                    this.$nextTick(() => this.scrollCarouselToStart());
                } else if (res.status === 404) {
                    this.state = 'ready';
                } else {
                    this.state = 'error';
                    this.errorMessage = 'Failed to load menu';
                }
            } catch (e) {
                this.state = 'error';
                this.errorMessage = 'Cannot reach server';
            }
        },

        addShelf(name, recipes) {
            this._carouselCache = null;
            this._carouselCacheKey = null;
            const existing = this.shelves.find(s => s.name === name);
            const generation = { recipes, generatedAt: new Date().toISOString() };
            if (existing) {
                // Prepend new generation, cap at max
                existing.generations.unshift(generation);
                if (existing.generations.length > CONST.MAX_SHELF_GENERATIONS) {
                    existing.generations = existing.generations.slice(0, CONST.MAX_SHELF_GENERATIONS);
                }
                existing.currentIndex = 0;
                // Move to front (newest from left)
                const idx = this.shelves.indexOf(existing);
                if (idx > 0) {
                    this.shelves.splice(idx, 1);
                    this.shelves.unshift(existing);
                }
            } else {
                // Insert at front
                this.shelves.unshift({ name, generations: [generation], currentIndex: 0 });
            }
            this.saveShelves();
        },

        removeShelf(name) {
            this.confirmModal = {
                show: true,
                title: 'Remove Shelf?',
                message: `Remove the ${name} shelf? This will clear its recipe history.`,
                confirmText: 'Remove',
                onConfirm: () => {
                    if (this.activeDeckName === name) {
                        const remaining = this.shelves.filter(s => s.name !== name);
                        this.activeDeckName = remaining.length > 0 ? remaining[0].name : null;
                    }
                    this.shelves = this.shelves.filter(s => s.name !== name);
                    this.saveShelves();
                },
            };
        },

        currentGeneration(shelf) {
            if (!shelf.generations || shelf.generations.length === 0) return [];
            const idx = shelf.currentIndex || 0;
            return shelf.generations[idx].recipes;
        },

        prevGeneration(name) {
            const shelf = this.shelves.find(s => s.name === name);
            if (!shelf || shelf.currentIndex >= shelf.generations.length - 1) return;
            shelf.currentIndex++;
            this.saveShelves();
            this.$nextTick(() => this.scrollCarouselToStart());
        },

        nextGeneration(name) {
            const shelf = this.shelves.find(s => s.name === name);
            if (!shelf || shelf.currentIndex <= 0) return;
            shelf.currentIndex--;
            this.saveShelves();
            this.$nextTick(() => this.scrollCarouselToStart());
        },

        goToGeneration(name, index) {
            const shelf = this.shelves.find(s => s.name === name);
            if (!shelf || index < 0 || index >= shelf.generations.length) return;
            shelf.currentIndex = index;
            this.saveShelves();
            this.$nextTick(() => this.scrollCarouselToStart());
        },

        saveShelves() {
            try {
                localStorage.setItem(CONST.LS_MENU_SHELVES, JSON.stringify(this.shelves));
                localStorage.setItem(CONST.LS_ACTIVE_DECK, JSON.stringify(this.activeDeckName));
            } catch (e) { /* storage full */ }
        },

        loadShelves() {
            try {
                const saved = localStorage.getItem(CONST.LS_MENU_SHELVES);
                if (!saved) return;
                const parsed = JSON.parse(saved);
                if (!Array.isArray(parsed)) return;
                // Validate structure
                this.shelves = parsed.filter(s =>
                    s.name && Array.isArray(s.generations) && s.generations.length > 0
                ).map(s => ({
                    name: s.name,
                    generations: s.generations.slice(0, CONST.MAX_SHELF_GENERATIONS),
                    currentIndex: Math.min(s.currentIndex || 0, s.generations.length - 1),
                }));
            } catch (e) { /* ignore corrupt data */ }
            try {
                const savedDeck = localStorage.getItem(CONST.LS_ACTIVE_DECK);
                if (savedDeck) {
                    const deckName = JSON.parse(savedDeck);
                    // Only restore if the shelf still exists (or null for discover)
                    if (deckName === null || this.shelves.find(s => s.name === deckName)) {
                        this.activeDeckName = deckName;
                    }
                }
            } catch (e) { /* ignore corrupt data */ }
        },

        activateDeck(name) {
            this.activeDeckName = name;
            this.saveShelves();
            this.$nextTick(() => this.scrollCarouselToStart());
        },

        activeShelf() {
            if (this.activeDeckName === null) return null;
            return this.shelves.find(s => s.name === this.activeDeckName) || null;
        },

        getShelfGenerations() {
            const shelf = this.activeShelf() || (this.shelves.length > 0 ? this.shelves[0] : null);
            if (!shelf || !shelf.generations || shelf.generations.length === 0) return null;
            return {
                profile: shelf.name,
                generations: shelf.generations.map((g, i) => {
                    const valid = (g.recipes || []).filter(r => r && r.id);
                    return {
                        recipes: valid,
                        recipeCount: valid.length,
                        preview: valid.slice(0, 3),
                    };
                }),
            };
        },

        deckPreview(shelf) {
            // Return first recipe from a shelf's current generation (for card preview)
            const recipes = this.currentGeneration(shelf);
            return recipes.length > 0 ? recipes[0] : null;
        },

        // ---- Recipe Modal ----

        openRecipe(recipe) {
            this.selectedRecipe = recipe;
        },

        closeRecipe() {
            this.selectedRecipe = null;
        },

        formatIngredient,

        // ---- Ratings ----

        rateDrink(recipe, rating) {
            if (!recipe) return;
            if (this.settings.ratings_enabled === false) return;
            this.showNamePrompt(recipe, 'rate', (userName) => {
                this.setRating(recipe.id, rating, userName);
            }, rating);
        },

        rateDrinkFromCard(recipe) {
            if (!recipe) return;
            if (this.settings.ratings_enabled === false) return;
            this.showNamePrompt(recipe, 'rate', (userName, rating) => {
                if (rating > 0) {
                    this.setRating(recipe.id, rating, userName);
                }
            });
        },

        async setRating(recipeId, rating, userName) {
            if (!recipeId) return;
            if (this.settings.ratings_enabled === false) return;
            try {
                const res = await fetch(`/api/recipe/${recipeId}/rating`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rating, customer_name: userName }),
                });
                if (res.ok) {
                    // Update local state everywhere
                    for (const r of this.currentRecipes) {
                        if (r.id === recipeId) r.rating = rating;
                    }
                    for (const r of this.previousRecipes) {
                        if (r.id === recipeId) r.rating = rating;
                    }
                    for (const r of this.recipes) {
                        if (r.id === recipeId) r.rating = rating;
                    }
                    if (this.selectedRecipe && this.selectedRecipe.id === recipeId) {
                        this.selectedRecipe.rating = rating;
                    }
                }
            } catch (e) {
                console.warn('Failed to set rating:', e);
            }
        },

        // ---- Name Prompt (reusable for orders and ratings) ----

        _loadRecentNames() {
            try { this.recentNames = JSON.parse(localStorage.getItem(CONST.LS_RECENT_NAMES) || '[]'); }
            catch (e) { this.recentNames = []; }
        },

        showNamePrompt(recipe, action, callback, rating) {
            this.namePrompt = { show: true, name: '', callback, recipe, action, rating: rating || 0, confirmStep: false };
            this.$nextTick(() => {
                if (this.$refs.namePromptInput) this.$refs.namePromptInput.focus();
            });
        },

        selectNameChip(rn) {
            this.namePrompt.name = rn;
            this._saveRecentName(rn);
            if (this.namePrompt.action === 'rate' && this.namePrompt.rating) {
                this.submitNamePrompt(rn);
            } else if (this.namePrompt.action !== 'rate') {
                this.submitNamePrompt(rn);
            }
        },

        selectRating(i) {
            this.namePrompt.rating = i;
            if (this.namePrompt.name.trim()) {
                this.submitNamePrompt(this.namePrompt.name);
            }
        },

        submitNamePrompt(name) {
            const trimmed = (name || '').trim();
            if (trimmed) this._saveRecentName(trimmed);

            // Rating + Tandoor save → show confirmation first
            if (this.namePrompt.action === 'rate'
                && this.settings.save_ratings_to_tandoor !== false
                && !this.namePrompt.confirmStep) {
                this.namePrompt.name = trimmed || '';
                this.namePrompt.confirmStep = true;
                return;
            }

            const cb = this.namePrompt.callback;
            const rating = this.namePrompt.rating || 0;
            this.namePrompt = { show: false, name: '', callback: null, recipe: null, action: '', rating: 0, confirmStep: false };
            if (cb) cb(trimmed || null, rating);
        },

        skipNamePrompt() {
            this.namePrompt = { show: false, name: '', callback: null, recipe: null, action: '', rating: 0, confirmStep: false };
        },

        confirmRating() {
            const cb = this.namePrompt.callback;
            const rating = this.namePrompt.rating || 0;
            const name = this.namePrompt.name || null;
            this.namePrompt = { show: false, name: '', callback: null, recipe: null, action: '', rating: 0, confirmStep: false };
            if (cb) cb(name, rating);
        },

        cancelConfirmation() {
            this.namePrompt.confirmStep = false;
        },

        _saveRecentName(name) {
            try {
                let names = JSON.parse(localStorage.getItem(CONST.LS_RECENT_NAMES) || '[]');
                names = names.filter(n => n.toLowerCase() !== name.toLowerCase());
                names.unshift(name);
                if (names.length > CONST.MAX_RECENT_NAMES) names = names.slice(0, CONST.MAX_RECENT_NAMES);
                localStorage.setItem(CONST.LS_RECENT_NAMES, JSON.stringify(names));
                this.recentNames = names;
            } catch (e) { /* storage full */ }
        },

        // ---- Ordering ----

        orderDrink(recipe) {
            if (!recipe) return;
            if (this.settings.orders_enabled === false) return;
            this.showNamePrompt(recipe, 'order', async (userName) => {
                try {
                    const res = await fetch('/api/orders', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            recipe_id: recipe.id,
                            recipe_name: recipe.name,
                            customer_name: userName,
                        }),
                    });
                    if (res.ok) {
                        this.orderConfirm = recipe.id;
                        const toastMs = (this.settings.toast_seconds ?? CONST.DEFAULT_TOAST_SECONDS) * 1000;
                        setTimeout(() => { this.orderConfirm = null; }, toastMs);
                    }
                } catch (e) {
                    console.warn('Failed to place order:', e);
                }
            });
        },

        // ---- Meal Plan Save ----

        async openMealPlanSave() {
            this.navOpen = false;
            const info = this.getShelfGenerations();
            this.mealPlanSave.profile = info?.profile || null;
            this.mealPlanSave.generations = info?.generations || [];
            this.mealPlanSave.selectedGen = 0;
            this.mealPlanSave.expandedGen = null;
            this.mealPlanSave.date = new Date().toISOString().slice(0, 10);
            this.mealPlanSave.saving = false;
            this.mealPlanSave.selectedUsers = [];
            this.mealPlanSave.show = true;
            try {
                const [mtRes, uRes] = await Promise.all([
                    fetch('/api/meal-types'),
                    fetch('/api/users'),
                ]);
                if (mtRes.ok) {
                    const mtData = await mtRes.json();
                    this.mealPlanSave.mealTypes = Array.isArray(mtData) ? mtData : (mtData.results || []);
                    if (!this.mealPlanSave.mealTypeId && this.mealPlanSave.mealTypes.length) {
                        this.mealPlanSave.mealTypeId = this.mealPlanSave.mealTypes[0].id;
                    }
                }
                if (uRes.ok) {
                    const uData = await uRes.json();
                    this.mealPlanSave.users = Array.isArray(uData) ? uData : (uData.results || []);
                }
            } catch (e) {
                console.warn('Failed to load meal plan options:', e);
            }
        },

        toggleMealPlanUser(userId) {
            const idx = this.mealPlanSave.selectedUsers.indexOf(userId);
            if (idx >= 0) {
                this.mealPlanSave.selectedUsers.splice(idx, 1);
            } else {
                this.mealPlanSave.selectedUsers.push(userId);
            }
        },

        async submitMealPlanSave() {
            if (this.mealPlanSave.saving) return;
            this.mealPlanSave.saving = true;
            try {
                const payload = {
                    date: this.mealPlanSave.date,
                    meal_type_id: this.mealPlanSave.mealTypeId,
                    shared: this.mealPlanSave.selectedUsers,
                };
                const gen = this.mealPlanSave.generations[this.mealPlanSave.selectedGen];
                if (gen?.recipes) {
                    payload.recipes = gen.recipes.map(r => ({ id: r.id, name: r.name }));
                }
                const res = await fetch('/api/meal-plan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (res.ok) {
                    this.mealPlanSave.show = false;
                    this.mealPlanToast = true;
                    const toastMs = (this.settings.toast_seconds ?? CONST.DEFAULT_TOAST_SECONDS) * 1000;
                    setTimeout(() => { this.mealPlanToast = false; }, toastMs);
                } else {
                    const data = await res.json().catch(() => ({}));
                    alert(data.detail || 'Failed to save meal plan');
                }
            } catch (e) {
                alert('Failed to save meal plan');
            } finally {
                this.mealPlanSave.saving = false;
            }
        },

        // ---- Kiosk Mode ----

        setupKioskGesture() {
            if (!this.settings.kiosk_enabled) return;
            const gesture = this.settings.kiosk_gesture || 'menu';
            if (gesture === 'menu') return; // hamburger handles it

            const header = this.$refs.menuHeader;
            if (!header) return;

            const cleanupFns = [];

            if (gesture === 'double-tap') {
                const handler = (e) => {
                    // Use browser's native click counter (detail: 1=single, 2=double, 3=triple)
                    if (e.detail === 2) {
                        this.kioskAdminAccess();
                    }
                };
                header.addEventListener('click', handler);
                cleanupFns.push(() => header.removeEventListener('click', handler));
            } else if (gesture === 'long-press') {
                const startHandler = (e) => {
                    this._kioskLongPressTimer = setTimeout(() => {
                        this.kioskAdminAccess();
                    }, 2000);
                };
                const cancelHandler = () => {
                    if (this._kioskLongPressTimer) {
                        clearTimeout(this._kioskLongPressTimer);
                        this._kioskLongPressTimer = null;
                    }
                };
                header.addEventListener('pointerdown', startHandler);
                header.addEventListener('pointerup', cancelHandler);
                header.addEventListener('pointercancel', cancelHandler);
                header.addEventListener('pointerleave', cancelHandler);
                cleanupFns.push(() => {
                    header.removeEventListener('pointerdown', startHandler);
                    header.removeEventListener('pointerup', cancelHandler);
                    header.removeEventListener('pointercancel', cancelHandler);
                    header.removeEventListener('pointerleave', cancelHandler);
                });
            } else if (gesture === 'swipe-up') {
                let startY = 0;
                const touchStart = (e) => {
                    const touch = e.touches[0];
                    // Only activate from bottom zone of screen
                    if (touch.clientY > window.innerHeight - CONST.SWIPE_ZONE_PX) {
                        startY = touch.clientY;
                    } else {
                        startY = 0;
                    }
                };
                const touchEnd = (e) => {
                    if (!startY) return;
                    const touch = e.changedTouches[0];
                    const deltaY = startY - touch.clientY;
                    if (deltaY > CONST.SWIPE_DISTANCE_PX) {
                        this.kioskAdminAccess();
                    }
                    startY = 0;
                };
                document.addEventListener('touchstart', touchStart, { passive: true });
                document.addEventListener('touchend', touchEnd, { passive: true });
                cleanupFns.push(() => {
                    document.removeEventListener('touchstart', touchStart);
                    document.removeEventListener('touchend', touchEnd);
                });
            }

            this._kioskGestureCleanup = () => cleanupFns.forEach(fn => fn());
        },

        kioskAdminAccess() {
            const pinFeatureOn = this.settings.admin_pin_enabled ||
                (this.settings.kiosk_enabled && this.settings.kiosk_pin_enabled);
            if (pinFeatureOn && this.settings.has_pin) {
                this.showKioskPin = true;
                this.showKioskPinText = false;
                this.kioskPinValue = '';
                this.kioskPinError = '';
                this.$nextTick(() => {
                    if (this.$refs.kioskPinInput) this.$refs.kioskPinInput.focus();
                });
            } else {
                window.location.href = '/admin';
            }
        },

        async submitKioskPin() {
            this.kioskPinError = '';
            try {
                const res = await fetch('/api/settings/verify-pin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pin: this.kioskPinValue }),
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.valid) {
                        if (data.token) {
                            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN, data.token);
                            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN_TS, String(Date.now()));
                        }
                        this.showKioskPin = false;
                        window.location.href = '/admin';
                    } else {
                        this.kioskPinError = 'Incorrect PIN';
                        this.kioskPinValue = '';
                    }
                } else {
                    this.kioskPinError = 'Failed to verify PIN';
                }
            } catch (e) {
                this.kioskPinError = 'Cannot reach server';
            }
        },

        // ---- Theming ----

        applyTheme(name) {
            this.currentTheme = applyThemeGlobal(name);
        },

        // ---- Helpers ----

        placeholderSvg(recipe) {
            void this._iconGen;
            return getPlaceholderSvg(recipe, this.activeProfile, this.iconMappings, this.settings.logo_url || this.loadingIconUrl || '');
        },

        ratingStars,

        registerServiceWorker() {
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/service-worker.js').catch(() => {});
            }
        },
    };
}
