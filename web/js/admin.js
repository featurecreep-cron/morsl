function adminApp() {
    return {
        // Navigation
        navOpen: false,
        appVersion: '',

        // Bumped when custom icons finish loading, to trigger Alpine re-renders
        _iconGen: 0,

        // Bumped every second during generation to drive elapsed display
        _generatingTick: 0,
        _generatingTickId: null,

        // Status
        status: { state: 'idle' },

        // Profiles & generation
        profiles: [],
        selectedProfile: '',

        // Menu data
        recipes: [],
        warnings: [],
        relaxedConstraints: [],
        menuVersion: null,
        menuMeta: {},

        // Tab navigation
        activeTab: 'generate',

        // Tier progressive disclosure
        adminTier: localStorage.getItem(CONST.LS_ADMIN_TIER) || 'essential',
        _tierLevels: { essential: 0, standard: 1, advanced: 2 },

        // Constraint builder
        showConstraints: false,
        keywords: [],
        keywordMap: {},        // {id: {id, name, ...}} for constraint label lookups
        keywordFilter: '',
        keywordSearch: '',
        keywordResults: [],
        selectedKeywords: [],  // { id, name, count, operator }
        foodSearch: '',
        foodResults: [],
        foodMap: {},           // {id: {id, name, ...}} for constraint label lookups
        selectedFoods: [],     // { id, name, count, operator }
        customChoices: CONST.DEFAULT_CUSTOM_CHOICES,
        _foodDebounceId: null,
        _keywordDebounceId: null,
        customFilters: [],       // Available Tandoor custom filters

        // Recipe modal
        selectedRecipe: null,

        // Theming
        currentTheme: localStorage.getItem('morsl-theme') || 'cast-iron',
        themeRegistry: THEME_REGISTRY,

        // Settings
        settings: {},
        settingsLoaded: false,

        // Credential editing
        credEditing: false,
        credEnvLocked: false,
        credUrl: '',
        credToken: '',
        credTesting: false,
        credSaving: false,
        credTestResult: null,
        credError: '',

        // Icon mappings
        iconMappings: { keyword_icons: {}, food_icons: {} },
        newKwName: '',
        newKwIcon: '',
        newFoodName: '',
        newFoodIcon: '',
        mappingKwSearch: '',
        mappingKwResults: [],
        _mappingKwDebounceId: null,
        mappingFoodSearch: '',
        mappingFoodResults: [],
        mappingFoodSearched: false,
        _mappingFoodDebounceId: null,

        // Polling
        _statusPollId: null,

        // Profile Manager (v2 format)
        editingProfile: false,
        isNewProfile: false,
        profileSaving: false,
        profilePreviewing: false,
        previewResult: null,
        expandedConstraint: null,  // Index of currently expanded constraint
        profileEditor: {
            name: '', originalName: '', description: '', icon: '', category: '',
            choices: 5, min_choices: null,
            cache: 240,
            default: false, show_on_menu: true, item_noun: '',
            filters: [],
            constraints: [],
        },
        // Constraint type metadata for UI — icons from CONSTRAINT_ICONS registry
        constraintTypes: {
            keyword: {
                label: 'Keyword',
                icon: CONSTRAINT_ICONS.keyword,
                description: 'Require recipes with specific tags like "Italian", "Quick", or "Vegetarian"',
                help: 'Keywords are tags assigned to recipes in Tandoor. Use this to filter by cuisine, meal type, or any custom tags you\'ve created.'
            },
            food: {
                label: 'Ingredient',
                icon: CONSTRAINT_ICONS.food,
                description: 'Require recipes containing specific ingredients like bourbon or lime juice',
                help: 'Filter recipes by their ingredients. Great for using up specific bottles or avoiding ingredients you don\'t have.'
            },
            book: {
                label: 'Book',
                icon: CONSTRAINT_ICONS.book,
                description: 'Require recipes from specific recipe books or collections',
                help: 'If your recipes are organized into books in Tandoor, use this to pull from specific collections.'
            },
            rating: {
                label: 'Rating',
                icon: CONSTRAINT_ICONS.rating,
                description: 'Require recipes with a minimum star rating',
                help: 'Filter by how you\'ve rated recipes. Great for ensuring quality picks or finding underrated gems to try again.'
            },
            cookedon: {
                label: 'Last Made',
                icon: CONSTRAINT_ICONS.cookedon,
                description: 'Filter by when you last made a recipe',
                help: 'Avoid recipes you\'ve had recently, or specifically include recent favorites. Based on Tandoor\'s meal plan history.'
            },
            createdon: {
                label: 'Date Added',
                icon: CONSTRAINT_ICONS.createdon,
                description: 'Filter by when recipes were added to your collection',
                help: 'Find new additions you haven\'t tried yet, or stick to tried-and-true classics.'
            },
            makenow: {
                label: 'Make Now',
                icon: CONSTRAINT_ICONS.makenow,
                description: 'Prefer recipes you can make with ingredients on hand',
                help: 'Uses Tandoor\'s on-hand tracking. Mark ingredients as "on hand" in Tandoor, then use this to prefer recipes you can make right now.'
            },
        },
        showAddConstraintMenu: false,  // For the add constraint dropdown
        collapsedGroups: {},  // {type: true/false} for constraint group collapse
        operatorLabels: {
            '>=': 'At least',
            '<=': 'At most',
            '==': 'Exactly',
        },

        // Order Queue
        orders: [],
        orderCounts: [],
        _orderSSE: null,

        // Categories
        categories: [],
        showCategoryForm: false,
        editingCategoryId: null,
        categoryForm: { display_name: '', subtitle: '', icon: '' },
        _sortableInstance: null,

        // Templates (weekly meal plan)
        templates: [],
        editingTemplate: false,
        isNewTemplate: false,
        templateSaving: false,
        templateEditor: { name: '', originalName: '', description: '', deduplicate: true, slots: [] },
        _expandedSlot: null,

        // Weekly generation
        weeklyStatus: { state: 'idle', profile_progress: {} },
        weeklyPlan: null,
        weeklyPlanTemplate: '',
        selectedWeeklyTemplate: '',
        weeklyWeekStart: '',
        weeklyGenerating: false,
        weeklyPlanSaving: false,
        weeklyPlanSaved: false,
        weeklyRegenSlot: null,
        _weeklyPollId: null,

        // Schedules
        schedules: [],
        showScheduleForm: false,
        editingScheduleId: null,
        scheduleDays: [
            { key: 'mon', label: 'Mon' },
            { key: 'tue', label: 'Tue' },
            { key: 'wed', label: 'Wed' },
            { key: 'thu', label: 'Thu' },
            { key: 'fri', label: 'Fri' },
            { key: 'sat', label: 'Sat' },
            { key: 'sun', label: 'Sun' },
        ],
        scheduleForm: {
            mode: 'profile', template: '',
            profile: '', day_of_week: 'mon-fri', hour: 16, minute: 0,
            enabled: true, clear_before_generate: false,
            create_meal_plan: false, meal_plan_type: null, cleanup_uncooked_days: 0,
            _selectedDays: ['mon', 'tue', 'wed', 'thu', 'fri'],
        },
        mealTypes: [],
        showNewMealType: false,
        newMealTypeName: '',

        // Confirmation Modal
        confirmModal: {
            show: false,
            title: '',
            message: '',
            confirmText: '',
            onConfirm: () => {},
        },

        // Kiosk PIN gate
        adminReady: false,
        showPinGate: false,
        showPinText: false,
        pinInput: '',
        pinError: '',

        // ---- History ----
        history: [],
        historyTotal: 0,
        historyPage: 0,
        historyPageSize: 20,
        historyLoading: false,
        expandedHistoryId: null,
        analytics: { total_generations: 0, avg_duration_ms: 0, status_counts: {}, profile_counts: {}, most_relaxed: [], avg_recipes_per_generation: 0 },

        // ---- Icons ----

        formatSolverStatus(s) {
            return ({
                optimal: 'Generated successfully',
                infeasible: 'Could not generate \u2014 rules too strict',
                error: 'Failed',
            })[s] || s || '';
        },

        resolveIcon(key) {
            void this._iconGen;
            return getIconByKey(key);
        },

        getHeadingIcon() {
            void this._iconGen;
            return getBrandIcon(this.settings.logo_url || '');
        },

        resolveNoun(profileName) {
            const p = this.profiles.find(x => x.name === profileName);
            return (p && p.item_noun) || this.settings.item_noun || 'recipe';
        },

        // ---- Auth ----

        _isPinRequired(settings) {
            const featureOn = settings.admin_pin_enabled || (settings.kiosk_enabled && settings.kiosk_pin_enabled);
            return featureOn && settings.has_pin;
        },

        async adminFetch(url, opts = {}) {
            const token = sessionStorage.getItem(CONST.SS_ADMIN_TOKEN);
            if (token) {
                opts.headers = { ...opts.headers, 'X-Admin-Token': token };
            }
            if (!opts._skipAbort && this._adminAbort) {
                opts.signal = this._adminAbort.signal;
            }
            const res = await fetch(url, opts);
            if (res.status === 401 && !opts._silent) {
                if (!this.showPinGate) {
                    sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN);
                    this.adminReady = false;
                    this.showPinGate = true;
                    // Abort remaining parallel requests
                    if (this._adminAbort) this._adminAbort.abort();
                    this.$nextTick(() => {
                        if (this.$refs.pinGateInput) this.$refs.pinGateInput.focus();
                    });
                }
            }
            return res;
        },

        // ---- Lifecycle ----

        async init() {
            this.applyTheme(this.currentTheme);
            this._iconHandler = () => this._iconGen++;
            window.addEventListener('custom-icons-loaded', this._iconHandler);
            this._svgAbort = new AbortController();

            // Fetch version (no auth required)
            try {
                const h = await fetch('/health');
                if (h.ok) this.appVersion = (await h.json()).version || '';
            } catch (_) { /* ignore */ }

            // Check if PIN is required before loading admin data
            if (await this._checkPinGate()) return;

            await this._loadAdminData();
            // Prefetch brand logo SVG for theme-aware inline rendering
            if (this.settings.logo_url) {
                prefetchBrandSvg(this.settings.logo_url).then(ok => { if (ok) this._iconGen++; });
            }
            this._updateBrandingPreviews();
            this.$watch(() => this.settings.logo_url, () => this.$nextTick(() => this._updateBrandingPreviews()));
            this.$watch(() => this.settings.favicon_url, () => this.$nextTick(() => this._updateBrandingPreviews()));
            this.$watch(() => this.settings.loading_icon_url, () => this.$nextTick(() => this._updateBrandingPreviews()));
            this.$watch(() => this.settings.favicon_use_logo, () => this.$nextTick(() => this._updateBrandingPreviews()));
            this.$watch(() => this.settings.loading_icon_use_logo, () => this.$nextTick(() => this._updateBrandingPreviews()));
        },

        async _checkPinGate() {
            try {
                const pubRes = await fetch('/api/settings/public');
                if (pubRes.ok) {
                    const pub = await pubRes.json();
                    if (!this._isPinRequired(pub)) return false;
                    const token = sessionStorage.getItem(CONST.SS_ADMIN_TOKEN);
                    const tokenTs = parseInt(sessionStorage.getItem(CONST.SS_ADMIN_TOKEN_TS) || '0', 10);
                    const pinTimeout = pub.pin_timeout ?? 0;

                    let needsPin = !token;
                    if (token && pinTimeout === 0) {
                        // Immediate mode — always require re-entry on page load
                        sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN);
                        sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN_TS);
                        needsPin = true;
                    } else if (token && pinTimeout > 0 && tokenTs) {
                        // Timed mode — check if token has expired client-side
                        if (Date.now() - tokenTs > pinTimeout * 1000) {
                            sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN);
                            sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN_TS);
                            needsPin = true;
                        }
                    }

                    if (needsPin) {
                        this.showPinGate = true;
                        this.$nextTick(() => {
                            if (this.$refs.pinGateInput) this.$refs.pinGateInput.focus();
                        });
                        return true;
                    }
                }
            } catch (e) { /* proceed without gate — don't lock users out if server unreachable */ }
            return false;
        },

        async _loadAdminData() {
            this._adminAbort = new AbortController();
            try {
                await Promise.all([
                    this.loadProfiles(),
                    this.loadTemplates(),
                    this.loadStatus(),
                    this.loadMenu(),
                    this.loadKeywords(),
                    this.loadOrders(),
                    this.loadSchedules(),
                    this.loadCategories(),
                    this.loadSettings(),
                    this.loadMealTypes(),
                    this.loadHistory(),
                    this.loadAnalytics(),
                    this.loadIconMappings(),
                    this.loadCustomFilters(),
                ]);
                this.adminReady = true;
                // Hash-based tab activation (e.g., /admin#weekly)
                const tabTiers = { generate: 'essential', profiles: 'essential', weekly: 'essential', settings: 'essential', orders: 'advanced', branding: 'advanced' };
                const hash = window.location.hash.replace('#', '');
                if (hash && tabTiers[hash] && this.tierVisible(tabTiers[hash])) {
                    this.activeTab = hash;
                }
            } catch (e) {
                if (e.name === 'AbortError') return; // 401 triggered abort
                throw e;
            } finally {
                this._adminAbort = null;
            }
            const dflt = this.profiles.find(p => p.default);
            if (dflt) {
                this.selectedProfile = dflt.name;
            }
            if (this.templates.length && !this.selectedWeeklyTemplate) {
                this.selectedWeeklyTemplate = this.templates[0].name;
            }
            this.connectOrderSSE();
        },

        destroy() {
            if (this._svgAbort) { this._svgAbort.abort(); this._svgAbort = null; }
            if (this._statusPollId) clearInterval(this._statusPollId);
            if (this._weeklyPollId) { clearInterval(this._weeklyPollId); this._weeklyPollId = null; }
            if (this._foodDebounceId) clearTimeout(this._foodDebounceId);
            if (this._keywordDebounceId) clearTimeout(this._keywordDebounceId);
            if (this._sseReconnectId) clearTimeout(this._sseReconnectId);
            if (this._orderSSE) this._orderSSE.close();
            if (this._iconHandler) { window.removeEventListener('custom-icons-loaded', this._iconHandler); this._iconHandler = null; }
            if (this._sortableInstance) { this._sortableInstance.destroy(); this._sortableInstance = null; }
            this._stopGeneratingTick();
        },

        _updateBrandingPreviews() {
            const signal = this._svgAbort?.signal;
            const defaultSvg = DEFAULT_FAVICON_PATH;
            const logoUrl = this.settings.logo_url;
            // Logo previews
            if (this.$refs.logoDefaultPreview) inlineSvg(defaultSvg, this.$refs.logoDefaultPreview, signal);
            if (logoUrl && this.$refs.logoPreview) inlineSvg(logoUrl, this.$refs.logoPreview, signal);
            // Favicon previews
            if (this.$refs.faviconDefaultPreview) inlineSvg(defaultSvg, this.$refs.faviconDefaultPreview, signal);
            if (this.settings.favicon_url && this.$refs.faviconPreview) inlineSvg(this.settings.favicon_url, this.$refs.faviconPreview, signal);
            if (logoUrl && this.$refs.faviconLogoPreview) inlineSvg(logoUrl, this.$refs.faviconLogoPreview, signal);
            // Loading icon previews
            if (this.$refs.loadingDefaultPreview) inlineSvg(defaultSvg, this.$refs.loadingDefaultPreview, signal);
            if (this.settings.loading_icon_url && this.$refs.loadingPreview) inlineSvg(this.settings.loading_icon_url, this.$refs.loadingPreview, signal);
            if (logoUrl && this.$refs.loadingLogoPreview) inlineSvg(logoUrl, this.$refs.loadingLogoPreview, signal);
        },

        // ---- Tier Progressive Disclosure ----

        tierVisible(tier) {
            return this._tierLevels[this.adminTier] >= this._tierLevels[tier];
        },

        setTier(tier) {
            this.adminTier = tier;
            localStorage.setItem(CONST.LS_ADMIN_TIER, tier);
            // If active tab is now hidden, redirect to generate
            const tabTiers = { generate: 'essential', profiles: 'essential', weekly: 'essential', settings: 'essential', orders: 'advanced', branding: 'advanced' };
            if (!this.tierVisible(tabTiers[this.activeTab] || 'essential')) {
                this.activeTab = 'generate';
            }
        },

        _getVisibleTabs() {
            return Array.from(document.querySelectorAll('[role="tablist"] [role="tab"]'))
                .filter(btn => btn.offsetParent !== null);
        },

        focusNextTab(e) {
            const tabs = this._getVisibleTabs();
            const idx = tabs.indexOf(e.target);
            if (idx < 0) return;
            const next = tabs[(idx + 1) % tabs.length];
            next.click();
            next.focus();
        },

        focusPrevTab(e) {
            const tabs = this._getVisibleTabs();
            const idx = tabs.indexOf(e.target);
            if (idx < 0) return;
            const prev = tabs[(idx - 1 + tabs.length) % tabs.length];
            prev.click();
            prev.focus();
        },

        // ---- Data Loading ----

        async loadProfiles() {
            try {
                const res = await fetch('/api/profiles');
                if (res.ok) {
                    this.profiles = await res.json();
                    if (this.profiles.length > 0 && !this.selectedProfile) {
                        this.selectedProfile = this.profiles[0].name;
                    }
                }
            } catch (e) {
                console.warn('Failed to load profiles:', e);
            }
        },

        async loadStatus() {
            try {
                const res = await fetch('/api/status');
                if (res.ok) {
                    this.status = await res.json();
                }
            } catch (e) {
                this.status = { state: 'error' };
            }
        },

        async loadMenu() {
            try {
                const res = await fetch('/api/menu');
                if (res.ok) {
                    const data = await res.json();
                    this.recipes = data.recipes || [];
                    this.warnings = data.warnings || [];
                    this.relaxedConstraints = data.relaxed_constraints || [];
                    this.menuVersion = data.version;
                    this.menuMeta = {
                        generated_at: data.generated_at,
                        requested_count: data.requested_count,
                        constraint_count: data.constraint_count,
                        status: data.status,
                    };
                }
            } catch (e) {
                // silent
            }
        },

        clearMenu() {
            this.confirmModal = {
                show: true,
                title: 'Clear Menu?',
                message: 'This will remove the current menu.',
                confirmText: 'Clear',
                onConfirm: async () => {
                    try {
                        const res = await this.adminFetch('/api/menu', { method: 'DELETE' });
                        if (res.ok || res.status === 204) {
                            this.recipes = [];
                            this.warnings = [];
                            this.relaxedConstraints = [];
                            this.menuMeta = {};
                        }
                    } catch (e) {
                        this.showError('Failed to clear menu: ' + e.message);
                    }
                },
            };
        },

        async loadKeywords() {
            try {
                const res = await fetch('/api/keywords');
                if (res.ok) {
                    const data = await res.json();
                    this.keywords = data.results || data || [];
                    // Build keywordMap for constraint label lookups
                    this.keywordMap = {};
                    for (const kw of this.keywords) {
                        this.keywordMap[kw.id] = kw;
                    }
                }
            } catch (e) {
                console.warn('Failed to load keywords:', e);
            }
        },

        async loadCustomFilters() {
            try {
                const res = await fetch('/api/custom-filters');
                if (res.ok) {
                    const data = await res.json();
                    this.customFilters = data.results || data || [];
                }
            } catch (e) {
                // Not fatal — custom filters are optional
            }
        },

        // Get hierarchical path for a keyword (e.g., "Spirits > Gin")
        getKeywordPath(kw) {
            if (!kw) return '?';
            const parts = [kw.name];
            let current = kw;
            while (current.parent && this.keywordMap[current.parent]) {
                current = this.keywordMap[current.parent];
                parts.unshift(current.name);
            }
            return parts.length > 1 ? parts.join(' › ') : kw.name;
        },

        // Get hierarchical path for a food (e.g., "Spirits > Whiskey > Bourbon")
        getFoodPath(food) {
            if (!food) return '?';
            const parts = [food.name];
            let current = food;
            // Foods in Tandoor may have supermarket_category or parent
            while (current.supermarket_category && this.foodMap[current.supermarket_category]) {
                current = this.foodMap[current.supermarket_category];
                parts.unshift(current.name);
            }
            return parts.length > 1 ? parts.join(' › ') : food.name;
        },

        // Search keywords (similar to food search)
        searchKeywords() {
            if (this._keywordDebounceId) clearTimeout(this._keywordDebounceId);
            this._keywordDebounceId = setTimeout(() => {
                if (!this.keywordSearch || this.keywordSearch.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
                    this.keywordResults = [];
                    return;
                }
                const query = this.keywordSearch.toLowerCase();
                // Search and add path info for display
                this.keywordResults = this.keywords
                    .filter(k => k.name.toLowerCase().includes(query))
                    .map(k => ({ ...k, path: this.getKeywordPath(k) }))
                    .slice(0, CONST.MAX_KEYWORD_RESULTS);
            }, CONST.KEYWORD_DEBOUNCE_MS);
        },

        addKeyword(kw) {
            if (this.selectedKeywords.some(k => k.id === kw.id)) return;
            this.selectedKeywords.push({
                id: kw.id,
                name: kw.name,
                count: 1,
                operator: '>=',
            });
            this.keywordSearch = '';
            this.keywordResults = [];
        },

        // Resolve constraint condition IDs to human-readable names
        getConstraintLabel(type, condition) {
            if (!Array.isArray(condition) || condition.length === 0) return 'Any';

            if (type === 'keyword') {
                return condition.map(id => this.keywordMap[id]?.name || `#${id}`).join(', ');
            } else if (type === 'food') {
                return condition.map(id => this.foodMap[id]?.name || `#${id}`).join(', ');
            } else if (type === 'rating') {
                return condition.join(' - ');
            } else if (type === 'cookedon' || type === 'createdon') {
                return condition.join(' to ');
            }
            return JSON.stringify(condition);
        },

        // Cache food lookups for constraint labels
        async cacheFood(id) {
            if (this.foodMap[id]) return;
            try {
                const res = await fetch(`/api/foods/${id}`);
                if (res.ok) {
                    const food = await res.json();
                    this.foodMap[id] = food;
                }
            } catch (e) { /* silent */ }
        },

        // ---- Generation ----

        async generateProfile() {
            if (this.status.state === 'generating' || !this.selectedProfile) return;
            this.status = { state: 'generating', started_at: new Date().toISOString() };
            this._startGeneratingTick();

            try {
                const url = `/api/generate/${encodeURIComponent(this.selectedProfile)}`;
                const res = await this.adminFetch(url, { method: 'POST' });
                if (res.status === 202 || res.status === 409) {
                    this.startStatusPolling();
                } else {
                    this.status = { state: 'error', error: 'Failed to start generation' };
                }
            } catch (e) {
                this.status = { state: 'error', error: 'Cannot reach server' };
            }
        },

        async generateCustom() {
            if (this.status.state === 'generating') return;
            this.status = { state: 'generating', started_at: new Date().toISOString() };
            this._startGeneratingTick();

            const body = {
                choices: this.customChoices,
                keyword: this.selectedKeywords.map(k => ({
                    condition: Array.isArray(k.id) ? k.id : [k.id],
                    count: String(k.count),
                    operator: k.operator,
                })),
                food: this.selectedFoods.map(f => ({
                    condition: [f.id],
                    count: String(f.count),
                    operator: f.operator,
                })),
            };

            try {
                const res = await this.adminFetch('/api/generate/custom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (res.status === 202 || res.status === 409) {
                    this.startStatusPolling();
                } else {
                    this.status = { state: 'error', error: 'Failed to start custom generation' };
                }
            } catch (e) {
                this.status = { state: 'error', error: 'Cannot reach server' };
            }
        },

        generatingElapsed() {
            void this._generatingTick;
            const start = this.status.started_at ? new Date(this.status.started_at) : null;
            if (!start) return 'generating';
            const secs = Math.max(0, Math.round((Date.now() - start.getTime()) / 1000));
            return 'generating \u00b7 ' + secs + 's';
        },

        _startGeneratingTick() {
            this._stopGeneratingTick();
            this._generatingTickId = setInterval(() => this._generatingTick++, CONST.GENERATING_TICK_MS);
        },

        _stopGeneratingTick() {
            if (this._generatingTickId) { clearInterval(this._generatingTickId); this._generatingTickId = null; }
        },

        startStatusPolling() {
            if (this._statusPollId) clearInterval(this._statusPollId);
            this._statusPollId = setInterval(async () => {
                try {
                    const res = await fetch('/api/status');
                    if (!res.ok) return;
                    this.status = await res.json();

                    if (this.status.state === 'complete' || this.status.state === 'idle') {
                        clearInterval(this._statusPollId);
                        this._statusPollId = null;
                        this._stopGeneratingTick();
                        await this.loadMenu();
                        this.loadHistory({ _silent: true, _skipAbort: true });
                        this.loadAnalytics({ _silent: true, _skipAbort: true });
                    } else if (this.status.state === 'error') {
                        clearInterval(this._statusPollId);
                        this._statusPollId = null;
                        this._stopGeneratingTick();
                    }
                } catch (e) {
                    // keep polling
                }
            }, CONST.STATUS_POLL_MS);
        },

        // ---- Constraint Builder ----

        get filteredKeywords() {
            if (!this.keywordFilter) return this.keywords;
            const q = this.keywordFilter.toLowerCase();
            return this.keywords.filter(k => k.name.toLowerCase().includes(q));
        },

        toggleKeyword(kw) {
            const idx = this.selectedKeywords.findIndex(s => s.id === kw.id);
            if (idx >= 0) {
                this.selectedKeywords.splice(idx, 1);
            } else {
                this.selectedKeywords.push({
                    id: kw.id,
                    name: kw.name,
                    count: 1,
                    operator: '>=',
                });
            }
        },

        isKeywordSelected(kw) {
            return this.selectedKeywords.some(s => s.id === kw.id);
        },

        getKeywordConstraint(kw) {
            return this.selectedKeywords.find(s => s.id === kw.id);
        },

        searchFoods() {
            if (this._foodDebounceId) clearTimeout(this._foodDebounceId);
            this._foodDebounceId = setTimeout(async () => {
                if (!this.foodSearch || this.foodSearch.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
                    this.foodResults = [];
                    return;
                }
                try {
                    const res = await fetch(`/api/foods?search=${encodeURIComponent(this.foodSearch)}`);
                    if (res.ok) {
                        const data = await res.json();
                        const results = data.results || data || [];
                        // Add path for display (Tandoor foods have supermarket_category with name)
                        this.foodResults = results.map(f => ({
                            ...f,
                            path: f.supermarket_category?.name
                                ? `${f.supermarket_category.name} › ${f.name}`
                                : f.name
                        }));
                    }
                } catch (e) {
                    this.foodResults = [];
                }
            }, CONST.FOOD_DEBOUNCE_MS);
        },

        addFood(food) {
            if (this.selectedFoods.some(f => f.id === food.id)) return;
            this.selectedFoods.push({
                id: food.id,
                name: food.name,
                count: 1,
                operator: '>=',
            });
            this.foodSearch = '';
            this.foodResults = [];
        },

        removeFood(idx) {
            this.selectedFoods.splice(idx, 1);
        },

        removeKeyword(idx) {
            this.selectedKeywords.splice(idx, 1);
        },

        // ---- Profile Manager ----

        async loadProfileDetail(name) {
            try {
                const res = await fetch(`/api/profiles/${encodeURIComponent(name)}`);
                if (res.ok) {
                    const data = await res.json();
                    return data.config;
                }
            } catch (e) {
                console.warn('Failed to load profile detail:', e);
            }
            return null;
        },

        startNewProfile() {
            if (this.adminTier === 'essential') {
                window.location.href = '/setup?mode=add-profile';
                return;
            }
            this.isNewProfile = true;
            this.editingProfile = true;
            this.expandedConstraint = null;
            this.collapsedGroups = {};
            this.profileEditor = {
                name: '', originalName: '', description: '', icon: '', category: '',
                choices: 5, min_choices: null,
                default: false, show_on_menu: true, item_noun: '',
                filters: [],
                constraints: [],
            };
        },

        async startEditProfile(name) {
            const config = await this.loadProfileDetail(name);
            if (!config) return;
            const profileInfo = this.profiles.find(p => p.name === name);
            this.isNewProfile = false;
            this.editingProfile = true;
            this.expandedConstraint = null;
            this.profileEditor = {
                name: name,
                originalName: name,
                description: config.description || '',
                icon: config.icon || '',
                category: config.category || '',
                choices: config.choices || 5,
                min_choices: config.min_choices || null,
                default: profileInfo?.default || false,
                show_on_menu: config.show_on_menu !== false,
                item_noun: config.item_noun || '',
                filters: config.filters || [],
                constraints: config.constraints || [],
            };
            // Sort by type for grouped display, then resolve names
            this.sortConstraintsByType();
            // Start all constraint groups collapsed
            const types = new Set((this.profileEditor.constraints || []).map(c => c.type));
            this.collapsedGroups = {};
            for (const t of types) this.collapsedGroups[t] = true;
            await this.resolveConstraintItemNames();
        },

        // Resolve "#id" format names to real names from API
        async resolveConstraintItemNames() {
            const foodIdsToFetch = new Set();

            // First pass: resolve keywords from already-loaded keywordMap
            // and collect food IDs that need fetching
            for (const c of this.profileEditor.constraints) {
                // Initialize UI date fields for cookedon/createdon constraints
                if (c.type === 'cookedon' || c.type === 'createdon') {
                    this.initDateFields(c);
                }

                if (c.type === 'keyword' && c.items) {
                    for (const item of c.items) {
                        if (this.keywordMap[item.id]?.name && !this.keywordMap[item.id].name.match(/^#\d+$/)) {
                            item.name = this.keywordMap[item.id].name;
                        }
                    }
                } else if (c.type === 'food') {
                    if (c.items) {
                        for (const item of c.items) {
                            if (!this.foodMap[item.id] || this.foodMap[item.id].name?.match(/^#\d+$/)) {
                                foodIdsToFetch.add(item.id);
                            }
                        }
                    }
                    if (c.except) {
                        for (const item of c.except) {
                            if (!this.foodMap[item.id] || this.foodMap[item.id].name?.match(/^#\d+$/)) {
                                foodIdsToFetch.add(item.id);
                            }
                        }
                    }
                }
            }

            // Fetch food names in parallel
            const foodPromises = [...foodIdsToFetch].map(async (id) => {
                try {
                    const res = await fetch(`/api/foods/${id}`);
                    if (res.ok) {
                        const food = await res.json();
                        this.foodMap[id] = food;
                    }
                } catch (e) { /* silent */ }
            });
            await Promise.all(foodPromises);

            // Second pass: update food item names
            for (const c of this.profileEditor.constraints) {
                if (c.type === 'food') {
                    if (c.items) {
                        for (const item of c.items) {
                            if (this.foodMap[item.id]?.name) {
                                item.name = this.foodMap[item.id].name;
                            }
                        }
                    }
                    if (c.except) {
                        for (const item of c.except) {
                            if (this.foodMap[item.id]?.name) {
                                item.name = this.foodMap[item.id].name;
                            }
                        }
                    }
                }
            }
        },

        cancelEditProfile() {
            this.editingProfile = false;
            this.isNewProfile = false;
        },

        async saveProfile() {
            if (!this.profileEditor.name) return;
            this.profileSaving = true;

            // Clean up constraints before saving - remove UI-only fields and apply goals
            const cleanConstraints = (this.profileEditor.constraints || []).map(c => {
                const cleaned = { ...c };
                delete cleaned.label;      // Labels are auto-generated from data
                delete cleaned.date_mode;  // Legacy UI-only field

                // Sync date fields before saving for date constraints
                if (c.type === 'cookedon' || c.type === 'createdon') {
                    this.syncDateFields(cleaned);
                }
                // Remove UI-only fields
                delete cleaned.goal;
                delete cleaned.date_direction;
                delete cleaned.date_days;

                return cleaned;
            });

            const body = {
                name: this.profileEditor.name,
                description: this.profileEditor.description,
                icon: this.profileEditor.icon,
                category: this.profileEditor.category,
                choices: this.profileEditor.choices,
                min_choices: this.profileEditor.min_choices,
                default: this.profileEditor.default,
                show_on_menu: this.profileEditor.show_on_menu,
                item_noun: this.profileEditor.item_noun,
                filters: this.profileEditor.filters.length > 0 ? this.profileEditor.filters : undefined,
                constraints: cleanConstraints,
            };

            try {
                const isRename = !this.isNewProfile && this.profileEditor.name !== this.profileEditor.originalName;
                let res;

                if (this.isNewProfile) {
                    // Create new profile
                    res = await this.adminFetch('/api/profiles', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });
                } else if (isRename) {
                    // Rename: create new profile with new name, then delete old one
                    res = await this.adminFetch('/api/profiles', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });
                    if (res.ok) {
                        // Delete the old profile
                        await this.adminFetch(`/api/profiles/${encodeURIComponent(this.profileEditor.originalName)}`, {
                            method: 'DELETE',
                        });
                    }
                } else {
                    // Update existing profile
                    res = await this.adminFetch(`/api/profiles/${encodeURIComponent(this.profileEditor.name)}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });
                }

                if (res.ok) {
                    this.editingProfile = false;
                    this.isNewProfile = false;
                    await this.loadProfiles();
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showError('Save failed: ' + (err.detail || res.statusText));
                }
            } catch (e) {
                this.showError('Save failed: ' + e.message);
            } finally {
                this.profileSaving = false;
            }
        },

        deleteProfile(name) {
            this.confirmModal = {
                show: true,
                title: 'Delete Profile?',
                message: `Are you sure you want to delete the profile "${name}"? This cannot be undone.`,
                confirmText: 'Delete',
                onConfirm: async () => {
                    try {
                        const res = await this.adminFetch(`/api/profiles/${encodeURIComponent(name)}`, { method: 'DELETE' });
                        if (res.ok || res.status === 204) {
                            await this.loadProfiles();
                        }
                    } catch (e) {
                        this.showError('Delete failed: ' + e.message);
                    }
                },
            };
        },

        addConstraint(type) {
            // Create a new constraint with v2 format
            const newConstraint = {
                type: type,
                operator: '>=',
                count: 1,
                label: '',
            };

            // Add type-specific defaults
            if (type === 'keyword' || type === 'food' || type === 'book') {
                newConstraint.items = [];
            } else if (type === 'rating') {
                newConstraint.min_rating = 3;
            } else if (type === 'cookedon' || type === 'createdon') {
                newConstraint.date_direction = 'within';
                newConstraint.date_days = 30;
                newConstraint.within_days = 30;
            }

            // Insert after the last constraint of the same type (keeps groups contiguous)
            const lastOfType = this.profileEditor.constraints.reduce((last, c, i) => c.type === type ? i : last, -1);
            if (lastOfType >= 0) {
                this.profileEditor.constraints.splice(lastOfType + 1, 0, newConstraint);
                this.expandedConstraint = lastOfType + 1;
            } else {
                this.profileEditor.constraints.push(newConstraint);
                this.expandedConstraint = this.profileEditor.constraints.length - 1;
            }
            // Ensure group is expanded when adding a constraint
            this.collapsedGroups[type] = false;
        },

        async previewProfile() {
            if (this.profilePreviewing) return;
            this.profilePreviewing = true;
            this.previewResult = null;

            const body = {
                name: this.profileEditor.name || 'preview',
                description: this.profileEditor.description,
                choices: this.profileEditor.choices,
                min_choices: this.profileEditor.min_choices,
                constraints: this.profileEditor.constraints || [],
            };

            try {
                const res = await this.adminFetch('/api/profiles/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (res.ok) {
                    const data = await res.json();
                    this.previewResult = data.matching_count;
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.previewResult = `Error: ${err.detail || res.statusText}`;
                }
            } catch (e) {
                this.previewResult = `Error: ${e.message}`;
            } finally {
                this.profilePreviewing = false;
            }
        },

        // Check if a constraint is "soft" (soft: true)
        isConstraintSoft(c) {
            return c.soft === true;
        },

        // Toggle between soft and hard constraint
        toggleConstraintSoft(c) {
            c.soft = !c.soft;
            if (c.soft) {
                c.weight = c.weight || 10;
            } else {
                delete c.soft;
                delete c.weight;
            }
        },

        // Sync UI date fields (date_direction, date_days) to backend fields (within_days, older_than_days)
        syncDateFields(c) {
            if (c.date_direction === 'within') {
                c.within_days = c.date_days || 30;
                delete c.older_than_days;
            } else {
                c.older_than_days = c.date_days || 30;
                delete c.within_days;
            }
        },

        // Initialize UI date fields from backend fields when loading a constraint
        initDateFields(c) {
            if (c.older_than_days !== undefined) {
                c.date_direction = 'older';
                c.date_days = c.older_than_days;
            } else {
                c.date_direction = 'within';
                c.date_days = c.within_days || 30;
            }
        },

        removeConstraint(idx) {
            this.profileEditor.constraints.splice(idx, 1);
            // Close expanded view if we removed the expanded constraint
            if (this.expandedConstraint === idx) {
                this.expandedConstraint = null;
            } else if (this.expandedConstraint > idx) {
                this.expandedConstraint--;
            }
        },

        // Toggle constraint expansion for editing
        toggleConstraintExpand(idx) {
            this.expandedConstraint = this.expandedConstraint === idx ? null : idx;
        },

        // Count constraints of a given type
        countConstraintsByType(type) {
            return (this.profileEditor.constraints || []).filter(c => c.type === type).length;
        },

        // Toggle collapse state for a constraint group
        toggleGroupCollapse(type) {
            this.collapsedGroups[type] = !this.collapsedGroups[type];
        },

        // Check if all constraint groups are collapsed
        areAllGroupsCollapsed() {
            const types = new Set((this.profileEditor.constraints || []).map(c => c.type));
            if (types.size === 0) return false;
            for (const t of types) {
                if (!this.collapsedGroups[t]) return false;
            }
            return true;
        },

        // Toggle all constraint groups collapsed/expanded
        toggleAllGroups() {
            const types = new Set((this.profileEditor.constraints || []).map(c => c.type));
            const allCollapsed = this.areAllGroupsCollapsed();
            for (const t of types) {
                this.collapsedGroups[t] = !allCollapsed;
            }
        },

        // Sort constraints by type so groups are contiguous
        sortConstraintsByType() {
            const typeOrder = ['keyword', 'food', 'book', 'rating', 'cookedon', 'createdon'];
            this.profileEditor.constraints.sort((a, b) => {
                const ai = typeOrder.indexOf(a.type);
                const bi = typeOrder.indexOf(b.type);
                return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
            });
            this.expandedConstraint = null;
        },

        // Get display name for an item, looking up from cache if it's just "#id"
        getItemDisplayName(item, type) {
            if (!item) return '?';
            // If name is just "#id" format, try to look up the real name
            if (item.name && item.name.match(/^#\d+$/)) {
                if (type === 'keyword' && this.keywordMap[item.id]?.name) {
                    return this.keywordMap[item.id].name;
                } else if (type === 'food' && this.foodMap[item.id]?.name) {
                    return this.foodMap[item.id].name;
                }
            }
            return item.name || `#${item.id}`;
        },

        // Get a human-readable summary of a constraint (auto-generated)
        getConstraintSummary(c) {
            const opLabel = this.operatorLabels[c.operator] || c.operator;

            if (c.type === 'keyword' || c.type === 'food' || c.type === 'book') {
                const items = c.items || [];
                if (items.length === 0) {
                    return `${opLabel} ${c.count} (no items selected)`;
                }
                const names = items.slice(0, 3).map(i => this.getItemDisplayName(i, c.type));
                let itemStr = names.join(', ');
                if (items.length > 3) itemStr += ` +${items.length - 3} more`;
                return `${opLabel} ${c.count} with ${itemStr}`;
            } else if (c.type === 'rating') {
                const min = c.min !== undefined ? c.min : 0;
                const max = c.max !== undefined ? c.max : 5;
                if (min > 0 && max < 5) {
                    return `${opLabel} ${c.count} rated ${min}-${max} stars`;
                } else if (min > 0) {
                    return `${opLabel} ${c.count} rated ${min}+ stars`;
                } else if (max < 5) {
                    return `${opLabel} ${c.count} rated up to ${max} stars`;
                }
                return `${opLabel} ${c.count} (any rating)`;
            } else if (c.type === 'cookedon') {
                const days = c.date_days ?? c.within_days ?? c.older_than_days ?? 30;
                const direction = c.date_direction ?? (c.older_than_days !== undefined ? 'older' : 'within');
                if (direction === 'older') {
                    return `${opLabel} ${c.count} made more than ${days} days ago`;
                }
                return `${opLabel} ${c.count} made within last ${days} days`;
            } else if (c.type === 'createdon') {
                const days = c.date_days ?? c.within_days ?? c.older_than_days ?? 30;
                const direction = c.date_direction ?? (c.older_than_days !== undefined ? 'older' : 'within');
                if (direction === 'older') {
                    return `${opLabel} ${c.count} added more than ${days} days ago`;
                }
                return `${opLabel} ${c.count} added within last ${days} days`;
            } else if (c.type === 'makenow') {
                return `${opLabel} ${c.count} with on-hand ingredients`;
            }
            return `${opLabel} ${c.count}`;
        },

        // Auto-generate a label for a constraint based on its settings
        autoGenerateLabel(c) {
            return this.getConstraintSummary(c);
        },

        // Human-readable description of a constraint (friendlier than getConstraintSummary)
        describeConstraint(c) {
            if (!c) return '';
            const type = c.type;
            const items = c.items || [];
            const names = items.slice(0, 4).map(i => this.getItemDisplayName(i, type));
            const nameStr = names.join(', ') + (items.length > 4 ? ` +${items.length - 4} more` : '');
            const count = c.count || 0;
            const op = c.operator || '>=';

            if (type === 'keyword' || type === 'food' || type === 'book') {
                const typeLabel = type === 'keyword' ? 'keywords' : type === 'food' ? 'foods' : 'books';
                if (c.exclude) {
                    return items.length ? `Exclude ${typeLabel}: ${nameStr}` : `Exclude ${typeLabel}`;
                }
                if (op === '==' && count === 0) {
                    return items.length ? `Exclude ${typeLabel}: ${nameStr}` : `Exclude ${typeLabel}`;
                }
                if (op === '>=') return items.length ? `At least ${count} from: ${nameStr}` : `At least ${count} ${typeLabel}`;
                if (op === '<=') return items.length ? `At most ${count} from: ${nameStr}` : `At most ${count} ${typeLabel}`;
                if (op === '==') return items.length ? `Exactly ${count} from: ${nameStr}` : `Exactly ${count} ${typeLabel}`;
            }
            if (type === 'rating') {
                const min = c.min !== undefined ? c.min : 0;
                if (min > 0) return `Rating ${min}+ stars`;
                return `Rating filter`;
            }
            if (type === 'cookedon') {
                const days = c.date_days ?? c.within_days ?? c.older_than_days ?? 30;
                const dir = c.date_direction ?? (c.older_than_days !== undefined ? 'older' : 'within');
                if (c.exclude || (op === '==' && count === 0)) return `Avoid recipes cooked in last ${days} days`;
                if (dir === 'older') return `${count}+ not cooked in ${days} days`;
                return `${count}+ cooked within last ${days} days`;
            }
            if (type === 'createdon') {
                const days = c.date_days ?? c.within_days ?? c.older_than_days ?? 30;
                const dir = c.date_direction ?? (c.older_than_days !== undefined ? 'older' : 'within');
                if (dir === 'within') return `Include ${count}+ recipes added in last ${days} days`;
                return `${count}+ recipes added over ${days} days ago`;
            }
            if (type === 'makenow') return `At least ${count} with on-hand ingredients`;
            return this.getConstraintSummary(c);
        },

        // Quick-add constraint presets matching wizard page concepts
        quickAddConstraint(preset) {
            const presets = {
                'theme-keywords':    { type: 'keyword', operator: '>=', count: 1, items: [], label: 'Theme' },
                'avoid-keywords':    { type: 'keyword', operator: '==', count: 0, exclude: true, items: [], label: 'Avoid' },
                'include-foods':     { type: 'food', operator: '>=', count: 1, items: [], label: 'Include Foods' },
                'avoid-foods':       { type: 'food', operator: '==', count: 0, exclude: true, items: [], label: 'Avoid Foods' },
                'from-books':        { type: 'book', operator: '>=', count: 1, items: [], label: 'From Books' },
                'min-rating':        { type: 'rating', operator: '>=', count: 1, min: 4, label: 'Min Rating' },
                'avoid-recent':      { type: 'cookedon', operator: '==', count: 0, exclude: true, within_days: 14, date_direction: 'within', date_days: 14, label: 'Avoid Recent' },
                'include-new':       { type: 'createdon', operator: '>=', count: 1, within_days: 30, date_direction: 'within', date_days: 30, label: 'Include New' },
            };
            const c = presets[preset];
            if (!c) return;
            const newConstraint = { ...c };

            // Insert in type-grouped position
            const lastOfType = this.profileEditor.constraints.reduce((last, x, i) => x.type === c.type ? i : last, -1);
            if (lastOfType >= 0) {
                this.profileEditor.constraints.splice(lastOfType + 1, 0, newConstraint);
                this.expandedConstraint = lastOfType + 1;
            } else {
                this.profileEditor.constraints.push(newConstraint);
                this.expandedConstraint = this.profileEditor.constraints.length - 1;
            }
            this.collapsedGroups[c.type] = false;
            this.showAddConstraintMenu = false;
        },

        // Add an item (keyword/food/book) to a constraint's items array
        addItemToConstraint(constraint, item) {
            if (!Array.isArray(constraint.items)) constraint.items = [];
            if (constraint.items.some(i => i.id === item.id)) return;
            constraint.items.push({ id: item.id, name: item.name });
            // Cache for lookups
            if (constraint.type === 'keyword') {
                this.keywordMap[item.id] = item;
            } else if (constraint.type === 'food') {
                this.foodMap[item.id] = item;
            }
        },

        // Remove an item from a constraint's items array
        removeItemFromConstraint(constraint, itemId) {
            if (!Array.isArray(constraint.items)) return;
            const idx = constraint.items.findIndex(i => i.id === itemId);
            if (idx >= 0) constraint.items.splice(idx, 1);
        },

        // Duplicate a constraint
        duplicateConstraint(idx) {
            const original = this.profileEditor.constraints[idx];
            const copy = JSON.parse(JSON.stringify(original));
            copy.label = (copy.label || '') + ' (copy)';
            this.profileEditor.constraints.splice(idx + 1, 0, copy);
            this.expandedConstraint = idx + 1;
        },

        // Move constraint up in the list
        moveConstraintUp(idx) {
            if (idx <= 0) return;
            const constraints = this.profileEditor.constraints;
            [constraints[idx - 1], constraints[idx]] = [constraints[idx], constraints[idx - 1]];
            if (this.expandedConstraint === idx) this.expandedConstraint = idx - 1;
            else if (this.expandedConstraint === idx - 1) this.expandedConstraint = idx;
        },

        // Move constraint down in the list
        moveConstraintDown(idx) {
            const constraints = this.profileEditor.constraints;
            if (idx >= constraints.length - 1) return;
            [constraints[idx], constraints[idx + 1]] = [constraints[idx + 1], constraints[idx]];
            if (this.expandedConstraint === idx) this.expandedConstraint = idx + 1;
            else if (this.expandedConstraint === idx + 1) this.expandedConstraint = idx;
        },

        tryParseJSON(str) {
            try { return JSON.parse(str); }
            catch (e) { return str; }
        },

        // ---- Templates ----

        async loadTemplates() {
            try {
                const res = await this.adminFetch('/api/templates');
                if (res.ok) this.templates = await res.json();
            } catch (e) { /* silent */ }
        },

        startNewTemplate() {
            this.isNewTemplate = true;
            this.templateEditor = { name: '', originalName: '', description: '', deduplicate: true, slots: [] };
            this._expandedSlot = null;
            this.editingTemplate = true;
        },

        async startEditTemplate(name) {
            try {
                const res = await this.adminFetch(`/api/templates/${encodeURIComponent(name)}`);
                if (!res.ok) return;
                const data = await res.json();
                this.isNewTemplate = false;
                this.templateEditor = {
                    name: data.name,
                    originalName: data.name,
                    description: data.description || '',
                    deduplicate: data.deduplicate !== false,
                    slots: data.slots || [],
                };
                this._expandedSlot = null;
                this.editingTemplate = true;
            } catch (e) {
                this.showError('Failed to load template: ' + e.message);
            }
        },

        cancelEditTemplate() {
            this.editingTemplate = false;
        },

        async saveTemplate() {
            if (!this.templateEditor.name) return;
            this.templateSaving = true;
            try {
                let res;
                if (this.isNewTemplate) {
                    res = await this.adminFetch('/api/templates', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: this.templateEditor.name,
                            description: this.templateEditor.description,
                            deduplicate: this.templateEditor.deduplicate,
                            slots: this.templateEditor.slots,
                        }),
                    });
                } else {
                    res = await this.adminFetch(`/api/templates/${encodeURIComponent(this.templateEditor.originalName)}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            description: this.templateEditor.description,
                            deduplicate: this.templateEditor.deduplicate,
                            slots: this.templateEditor.slots,
                        }),
                    });
                }
                if (res.ok) {
                    this.editingTemplate = false;
                    await this.loadTemplates();
                    if (!this.selectedWeeklyTemplate && this.templates.length) {
                        this.selectedWeeklyTemplate = this.templates[0].name;
                    }
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showError('Save failed: ' + (err.detail || res.statusText));
                }
            } catch (e) {
                this.showError('Save failed: ' + e.message);
            } finally {
                this.templateSaving = false;
            }
        },

        deleteTemplate(name) {
            this.confirmModal = {
                show: true,
                title: 'Delete Template?',
                message: `Are you sure you want to delete the template "${name}"? This cannot be undone.`,
                confirmText: 'Delete',
                onConfirm: async () => {
                    try {
                        await this.adminFetch(`/api/templates/${encodeURIComponent(name)}`, { method: 'DELETE' });
                        await this.loadTemplates();
                    } catch (e) {
                        this.showError('Delete failed: ' + e.message);
                    }
                },
            };
        },

        addSlot() {
            this.templateEditor.slots.push({
                days: ['mon', 'tue', 'wed', 'thu', 'fri'],
                meal_type_id: this.mealTypes[0]?.id || 0,
                meal_type_name: this.mealTypes[0]?.name || '',
                profile: this.profiles[0]?.name || '',
                recipes_per_day: 1,
            });
            this._expandedSlot = this.templateEditor.slots.length - 1;
        },

        removeSlot(idx) {
            this.templateEditor.slots.splice(idx, 1);
            if (this._expandedSlot === idx) this._expandedSlot = null;
            else if (this._expandedSlot > idx) this._expandedSlot--;
        },

        toggleSlotExpand(idx) {
            this._expandedSlot = this._expandedSlot === idx ? null : idx;
        },

        toggleSlotDay(slotIdx, day) {
            const days = this.templateEditor.slots[slotIdx].days;
            const i = days.indexOf(day);
            if (i >= 0) {
                if (days.length <= 1) return;
                days.splice(i, 1);
            } else {
                days.push(day);
            }
        },

        // ---- Weekly Generation ----

        async generateWeekly() {
            if (this.weeklyGenerating || !this.selectedWeeklyTemplate) return;
            this.weeklyGenerating = true;
            this.weeklyPlanSaved = false;
            this.weeklyPlanTemplate = this.selectedWeeklyTemplate;
            this.weeklyStatus = { state: 'generating', profile_progress: {} };

            try {
                const body = {};
                if (this.weeklyWeekStart) body.week_start = this.weeklyWeekStart;
                const res = await this.adminFetch(`/api/weekly/generate/${encodeURIComponent(this.selectedWeeklyTemplate)}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (res.status === 202) {
                    this.startWeeklyPolling();
                } else if (res.status === 409) {
                    const err = await res.json().catch(() => ({}));
                    this.showError(err.detail || 'Generation already in progress');
                    this.startWeeklyPolling();
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showError(err.detail || 'Failed to start generation');
                    this.weeklyGenerating = false;
                    this.weeklyStatus = { state: 'error', error: err.detail || 'Failed', profile_progress: {} };
                }
            } catch (e) {
                this.showError('Cannot reach server');
                this.weeklyGenerating = false;
                this.weeklyStatus = { state: 'error', error: e.message, profile_progress: {} };
            }
        },

        startWeeklyPolling() {
            this.stopWeeklyPolling(true);
            this._weeklyPollId = setInterval(async () => {
                try {
                    const res = await fetch('/api/weekly/status');
                    if (!res.ok) return;
                    const data = await res.json();
                    this.weeklyStatus = data;

                    if (data.state === 'complete' || data.state === 'idle') {
                        this.stopWeeklyPolling();
                        if (data.state === 'complete') await this.loadWeeklyPlan();
                    } else if (data.state === 'error') {
                        this.stopWeeklyPolling();
                    }
                } catch (e) { /* keep polling */ }
            }, CONST.STATUS_POLL_MS);
        },

        stopWeeklyPolling(keepGenerating) {
            if (this._weeklyPollId) { clearInterval(this._weeklyPollId); this._weeklyPollId = null; }
            if (!keepGenerating) this.weeklyGenerating = false;
        },

        async loadWeeklyPlan() {
            if (!this.weeklyPlanTemplate) return;
            try {
                const res = await this.adminFetch(`/api/weekly/plan/${encodeURIComponent(this.weeklyPlanTemplate)}`);
                if (res.ok) {
                    this.weeklyPlan = await res.json();
                } else if (res.status === 404) {
                    this.weeklyPlan = null;
                }
            } catch (e) { /* silent */ }
        },

        discardWeeklyPlan() {
            this.confirmModal = {
                show: true,
                title: 'Discard Weekly Plan?',
                message: 'This will remove the generated weekly plan. This cannot be undone.',
                confirmText: 'Discard',
                onConfirm: async () => {
                    try {
                        await this.adminFetch(`/api/weekly/plan/${encodeURIComponent(this.weeklyPlanTemplate)}`, { method: 'DELETE' });
                    } catch (e) { /* ignore 404 */ }
                    this.weeklyPlan = null;
                    this.weeklyPlanSaved = false;
                },
            };
        },

        async regenerateSlot(date, mealTypeId) {
            this.weeklyRegenSlot = { date, mealTypeId };
            try {
                const res = await this.adminFetch('/api/weekly/regenerate-slot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ template: this.weeklyPlanTemplate, date, meal_type_id: mealTypeId }),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    this.showError(err.detail || 'Regeneration failed');
                }
            } catch (e) {
                this.showError('Regeneration failed: ' + e.message);
            } finally {
                this.weeklyRegenSlot = null;
                await this.loadWeeklyPlan();
            }
        },

        async saveWeeklyPlan() {
            if (this.weeklyPlanSaving || !this.weeklyPlanTemplate) return;
            this.weeklyPlanSaving = true;
            try {
                const res = await this.adminFetch('/api/weekly/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ template: this.weeklyPlanTemplate, shared: [] }),
                });
                if (res.ok) {
                    const data = await res.json();
                    this.weeklyPlanSaved = true;
                    const msg = `Saved ${data.created}/${data.total} meals to Tandoor`;
                    if (data.errors?.length) {
                        this.showError(msg + '. Errors: ' + data.errors.join(', '));
                    } else {
                        this.reloadPrompt(msg);
                    }
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showError('Save failed: ' + (err.detail || res.statusText));
                }
            } catch (e) {
                this.showError('Save failed: ' + e.message);
            } finally {
                this.weeklyPlanSaving = false;
            }
        },

        get weeklyPlanDays() {
            if (!this.weeklyPlan?.days) return [];
            return Object.entries(this.weeklyPlan.days).sort().map(([date, data]) => ({ date, data }));
        },

        weeklyPlanDayLabel(dateStr) {
            return dayjs(dateStr + 'T12:00:00').format('ddd, MMM D');
        },

        // ---- Ratings ----

        async setRating(recipeId, rating) {
            if (!recipeId) return;
            try {
                const res = await fetch(`/api/recipe/${recipeId}/rating`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rating }),
                });
                if (res.ok) {
                    // Update local state
                    const recipe = this.recipes.find(r => r.id === recipeId);
                    if (recipe) recipe.rating = rating;
                    if (this.selectedRecipe && this.selectedRecipe.id === recipeId) {
                        this.selectedRecipe.rating = rating;
                    }
                }
            } catch (e) {
                console.warn('Failed to set rating:', e);
            }
        },

        // ---- Order Queue ----

        async loadOrders() {
            try {
                const res = await this.adminFetch('/api/orders');
                if (res.ok) this.orders = await res.json();
            } catch (e) { /* silent */ }
            try {
                const res = await this.adminFetch('/api/orders/counts');
                if (res.ok) {
                    const data = await res.json();
                    this.orderCounts = data.counts || [];
                }
            } catch (e) { /* silent */ }
        },

        async connectOrderSSE() {
            if (this._orderSSE) this._orderSSE.close();
            this._sseRetryDelay = CONST.SSE_INITIAL_RETRY_MS;

            // EventSource can't send X-Admin-Token headers, so SSE only
            // works when PIN auth is disabled (no auth required on admin endpoints).
            // Skip connection entirely when PIN is active to avoid 401 reconnect loops.
            const pub = this.settings;
            const pinActive = pub.admin_pin_enabled || (pub.kiosk_enabled && pub.kiosk_pin_enabled);
            if (pinActive && pub.has_pin) return;

            this._orderSSE = new EventSource('/api/orders/stream');
            this._orderSSE.addEventListener('order', (e) => {
                try {
                    const order = JSON.parse(e.data);
                    this.orders.unshift(order);
                    // Update counts
                    const existing = this.orderCounts.find(c => c.recipe_id === order.recipe_id);
                    if (existing) {
                        existing.count += order.count;
                    } else {
                        this.orderCounts.push({
                            recipe_id: order.recipe_id,
                            recipe_name: order.recipe_name,
                            count: order.count,
                        });
                    }
                } catch (err) { /* ignore parse errors */ }
            });
            this._orderSSE.addEventListener('connected', () => {
                this._sseRetryDelay = CONST.SSE_INITIAL_RETRY_MS;
            });
            this._orderSSE.onerror = () => {
                this._orderSSE.close();
                this._sseReconnectId = setTimeout(() => {
                    this.connectOrderSSE();
                }, this._sseRetryDelay);
                this._sseRetryDelay = Math.min(this._sseRetryDelay * 2, CONST.SSE_MAX_RETRY_MS);
            };
        },

        clearOrders() {
            this.confirmModal = {
                show: true,
                title: 'Clear All Requests?',
                message: 'This will remove all requests from the queue. This cannot be undone.',
                confirmText: 'Clear All',
                onConfirm: async () => {
                    try {
                        await this.adminFetch('/api/orders', { method: 'DELETE' });
                        this.orders = [];
                        this.orderCounts = [];
                    } catch (e) { /* silent */ }
                },
            };
        },

        async markOrderReady(order) {
            try {
                await this.adminFetch(`/api/orders/${order.id}/status`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'ready' }),
                });
            } catch (e) {
                console.warn('Failed to mark order ready:', e);
            }
        },

        async deleteOrder(order) {
            try {
                const res = await this.adminFetch(`/api/orders/${order.id}`, { method: 'DELETE' });
                if (res.ok || res.status === 204 || res.status === 404) {
                    this.orders = this.orders.filter(o => o.id !== order.id);
                    // Recompute order counts from remaining orders
                    const counts = {};
                    for (const o of this.orders) {
                        if (!counts[o.recipe_id]) {
                            counts[o.recipe_id] = { recipe_id: o.recipe_id, recipe_name: o.recipe_name, count: 0 };
                        }
                        counts[o.recipe_id].count += o.count || 1;
                    }
                    this.orderCounts = Object.values(counts);
                }
            } catch (e) { /* silent */ }
        },

        async viewOrderRecipe(order) {
            if (!order.recipe_id) return;
            try {
                const res = await fetch(`/api/recipe/${order.recipe_id}`);
                if (res.ok) {
                    const data = await res.json();
                    this.openRecipe({
                        id: data.id,
                        name: data.name,
                        image: data.image,
                        rating: data.rating,
                        description: data.description || '',
                        ingredients: (data.steps || []).flatMap(s =>
                            (s.ingredients || []).map(i => ({
                                amount: i.amount,
                                unit: i.unit?.name || '',
                                food: i.food?.name || '',
                            }))
                        ),
                        steps: (data.steps || []).filter(s => s.instruction).map(s => ({
                            name: s.name || '',
                            instruction: s.instruction,
                            order: s.order,
                            time: s.time || 0,
                        })),
                    });
                }
            } catch (e) {
                console.warn('Failed to load recipe for order:', e);
            }
        },

        // ---- Categories ----

        async loadCategories() {
            try {
                const res = await fetch('/api/categories');
                if (res.ok) {
                    this.categories = await res.json();
                    this.$nextTick(() => this._initCategorySortable());
                }
            } catch (e) { /* silent */ }
        },

        startNewCategory() {
            this.editingCategoryId = null;
            this.categoryForm = { display_name: '', subtitle: '', icon: '' };
            this.showCategoryForm = true;
        },

        editCategory(cat) {
            this.editingCategoryId = cat.id;
            this.categoryForm = {
                display_name: cat.display_name,
                subtitle: cat.subtitle || '',
                icon: cat.icon || '',
            };
            this.showCategoryForm = true;
        },

        async saveCategory() {
            const body = { display_name: this.categoryForm.display_name, subtitle: this.categoryForm.subtitle, icon: this.categoryForm.icon };
            try {
                let res;
                if (this.editingCategoryId) {
                    res = await this.adminFetch(`/api/categories/${encodeURIComponent(this.editingCategoryId)}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });
                } else {
                    res = await this.adminFetch('/api/categories', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });
                }
                if (res.ok) {
                    this.showCategoryForm = false;
                    this.editingCategoryId = null;
                    await this.loadCategories();
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showError('Failed to save category: ' + (err.detail || res.statusText));
                }
            } catch (e) {
                this.showError('Failed to save category: ' + e.message);
            }
        },

        deleteCategory(id) {
            this.confirmModal = {
                show: true,
                title: 'Delete Category?',
                message: 'Are you sure you want to delete this category? Profiles using it will have their category cleared.',
                confirmText: 'Delete',
                onConfirm: async () => {
                    try {
                        await this.adminFetch(`/api/categories/${encodeURIComponent(id)}`, { method: 'DELETE' });
                        await this.loadCategories();
                    } catch (e) { /* silent */ }
                },
            };
        },

        // SortableJS category reordering
        _initCategorySortable() {
            if (this._sortableInstance) this._sortableInstance.destroy();
            const el = this.$refs.categoryList;
            if (!el) return;
            this._sortableInstance = Sortable.create(el, {
                handle: '.drag-handle',
                animation: 150,
                onEnd: async (evt) => {
                    if (evt.oldIndex === evt.newIndex) return;
                    const item = this.categories.splice(evt.oldIndex, 1)[0];
                    this.categories.splice(evt.newIndex, 0, item);
                    const orderedIds = this.categories.map(c => c.id);
                    try {
                        const res = await this.adminFetch('/api/categories/reorder', {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(orderedIds),
                        });
                        if (res.ok) this.categories = await res.json();
                    } catch (e) { console.debug('Category reorder failed:', e); }
                },
            });
        },

        // ---- Schedules ----

        async loadSchedules() {
            try {
                const res = await this.adminFetch('/api/schedules');
                if (res.ok) this.schedules = await res.json();
            } catch (e) { /* silent */ }
        },

        async loadMealTypes() {
            try {
                const res = await fetch('/api/meal-types');
                if (res.ok) {
                    const data = await res.json();
                    this.mealTypes = Array.isArray(data) ? data : (data.results || []);
                    // Auto-select first meal type if none configured
                    if (!this.settings.order_meal_type_id && this.mealTypes.length) {
                        this.settings.order_meal_type_id = this.mealTypes[0].id;
                        await this.saveSettings({ order_meal_type_id: this.mealTypes[0].id });
                    }
                }
            } catch (e) { /* silent */ }
        },

        async createMealType() {
            const name = (this.newMealTypeName || '').trim();
            if (!name) return;
            try {
                const res = await this.adminFetch('/api/meal-types', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, color: '#FF5722' }),
                });
                if (res.ok) {
                    const created = await res.json();
                    await this.loadMealTypes();
                    // Auto-select the newly created type
                    this.settings.order_meal_type_id = created.id;
                    await this.saveSettings({ order_meal_type_id: created.id });
                    this.showNewMealType = false;
                    this.newMealTypeName = '';
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showError('Failed to create meal type: ' + (err.detail || res.statusText));
                }
            } catch (e) {
                this.showError('Failed to create meal type: ' + e.message);
            }
        },

        async saveSchedule() {
            const body = { ...this.scheduleForm };
            delete body._selectedDays;
            delete body.mode;
            if (this.scheduleForm.mode === 'template') {
                body.profile = null;
                body.day_of_week = '*';
            } else {
                body.template = null;
            }
            try {
                let res;
                if (this.editingScheduleId) {
                    res = await this.adminFetch(`/api/schedules/${this.editingScheduleId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });
                } else {
                    res = await this.adminFetch('/api/schedules', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body),
                    });
                }
                if (res.ok) {
                    this.showScheduleForm = false;
                    this.editingScheduleId = null;
                    await this.loadSchedules();
                }
            } catch (e) {
                this.showError('Failed to save schedule: ' + e.message);
            }
        },

        // ---- Schedule Day Helpers ----

        parseCronDays(cronStr) {
            const dayOrder = ['mon','tue','wed','thu','fri','sat','sun'];
            if (!cronStr || cronStr === '*') return [...dayOrder];
            const result = new Set();
            const parts = cronStr.toLowerCase().split(',');
            for (const part of parts) {
                if (part.includes('-')) {
                    const [start, end] = part.split('-');
                    const si = dayOrder.indexOf(start.trim());
                    const ei = dayOrder.indexOf(end.trim());
                    if (si >= 0 && ei >= 0) {
                        for (let i = si; i <= ei; i++) result.add(dayOrder[i]);
                    }
                } else {
                    const d = part.trim();
                    if (dayOrder.includes(d)) result.add(d);
                }
            }
            return dayOrder.filter(d => result.has(d));
        },

        buildCronDays(selected) {
            const dayOrder = ['mon','tue','wed','thu','fri','sat','sun'];
            const sorted = dayOrder.filter(d => selected.includes(d));
            if (sorted.length === 7) return '*';
            if (sorted.length === 0) return 'mon';
            const ranges = [];
            let rangeStart = null;
            let prev = -1;
            for (const d of sorted) {
                const idx = dayOrder.indexOf(d);
                if (rangeStart === null) {
                    rangeStart = d;
                    prev = idx;
                } else if (idx === prev + 1) {
                    prev = idx;
                } else {
                    ranges.push(dayOrder.indexOf(rangeStart) === prev
                        ? rangeStart
                        : rangeStart + '-' + dayOrder[prev]);
                    rangeStart = d;
                    prev = idx;
                }
            }
            if (rangeStart !== null) {
                ranges.push(dayOrder.indexOf(rangeStart) === prev
                    ? rangeStart
                    : rangeStart + '-' + dayOrder[prev]);
            }
            return ranges.join(',');
        },

        toggleScheduleDay(day) {
            const idx = this.scheduleForm._selectedDays.indexOf(day);
            if (idx >= 0) {
                if (this.scheduleForm._selectedDays.length <= 1) return;
                this.scheduleForm._selectedDays.splice(idx, 1);
            } else {
                this.scheduleForm._selectedDays.push(day);
            }
            this.scheduleForm.day_of_week = this.buildCronDays(this.scheduleForm._selectedDays);
        },

        formatScheduleDays(cronStr) {
            const dayLabels = { mon:'Mon', tue:'Tue', wed:'Wed', thu:'Thu', fri:'Fri', sat:'Sat', sun:'Sun' };
            const days = this.parseCronDays(cronStr);
            if (days.length === 7) return 'Every day';
            if (days.length === 5 && !days.includes('sat') && !days.includes('sun')) return 'Weekdays';
            if (days.length === 2 && days.includes('sat') && days.includes('sun')) return 'Weekends';
            return days.map(d => dayLabels[d]).join(', ');
        },

        startNewSchedule() {
            this.editingScheduleId = null;
            this.scheduleForm = {
                mode: 'profile',
                template: this.templates[0]?.name || '',
                profile: this.profiles[0]?.name || '',
                day_of_week: 'mon-fri',
                hour: 16,
                minute: 0,
                enabled: true,
                clear_before_generate: false,
                create_meal_plan: false,
                meal_plan_type: null,
                cleanup_uncooked_days: 0,
                _selectedDays: this.parseCronDays('mon-fri'),
            };
            this.showScheduleForm = true;
        },

        editSchedule(s) {
            this.editingScheduleId = s.id;
            this.scheduleForm = {
                mode: s.template ? 'template' : 'profile',
                template: s.template || this.templates[0]?.name || '',
                profile: s.profile || this.profiles[0]?.name || '',
                day_of_week: s.day_of_week,
                hour: s.hour,
                minute: s.minute,
                enabled: s.enabled,
                clear_before_generate: s.clear_before_generate || false,
                create_meal_plan: s.create_meal_plan || false,
                meal_plan_type: s.meal_plan_type || null,
                cleanup_uncooked_days: s.cleanup_uncooked_days || 0,
                _selectedDays: this.parseCronDays(s.day_of_week),
            };
            this.showScheduleForm = true;
        },

        async toggleScheduleEnabled(s) {
            const body = {
                profile: s.profile,
                day_of_week: s.day_of_week,
                hour: s.hour,
                minute: s.minute,
                enabled: !s.enabled,
                create_meal_plan: s.create_meal_plan || false,
                meal_plan_type: s.meal_plan_type || null,
                cleanup_uncooked_days: s.cleanup_uncooked_days || 0,
            };
            try {
                const res = await this.adminFetch(`/api/schedules/${s.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (res.ok) await this.loadSchedules();
            } catch (e) { /* silent */ }
        },

        deleteSchedule(id) {
            this.confirmModal = {
                show: true,
                title: 'Delete Schedule?',
                message: 'Are you sure you want to delete this schedule? This cannot be undone.',
                confirmText: 'Delete',
                onConfirm: async () => {
                    try {
                        await this.adminFetch(`/api/schedules/${id}`, { method: 'DELETE' });
                        await this.loadSchedules();
                    } catch (e) { /* silent */ }
                },
            };
        },

        // ---- Settings ----

        async loadSettings() {
            try {
                const res = await this.adminFetch('/api/settings');
                if (res.ok) {
                    this.settings = await res.json();
                    this.settingsLoaded = true;
                    if (this.settings.theme) {
                        this.currentTheme = this.settings.theme;
                        this.applyTheme(this.settings.theme);
                    }
                    document.title = (this.settings.app_name || 'Morsl') + ' - Admin';
                    this._updateFaviconLinks();
                    this.renderQrPreviews();
                }
                // Check if credentials are locked by env vars
                const statusRes = await fetch('/api/settings/setup-status');
                if (statusRes.ok) {
                    const status = await statusRes.json();
                    this.credEnvLocked = status.has_env_credentials;
                }
            } catch (e) {
                console.warn('Failed to load settings:', e);
            }
        },

        async testCredentials() {
            if (!this.credUrl) return;
            // If no new token, we can't test (need the token for the API call)
            if (!this.credToken) {
                this.credError = 'Enter a token to test the connection.';
                return;
            }
            this.credTesting = true;
            this.credTestResult = null;
            this.credError = '';
            try {
                const res = await this.adminFetch('/api/settings/test-connection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: this.credUrl, token: this.credToken }),
                });
                this.credTestResult = res.ok
                    ? await res.json()
                    : { success: false, error: 'Server error' };
            } catch {
                this.credTestResult = { success: false, error: 'Cannot reach server' };
            } finally {
                this.credTesting = false;
            }
        },

        async saveCredentials() {
            if (!this.credTestResult?.success) return;
            this.credSaving = true;
            this.credError = '';
            try {
                const res = await this.adminFetch('/api/settings/credentials', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: this.credUrl, token: this.credToken }),
                });
                if (res.ok) {
                    this.credEditing = false;
                    await this.loadSettings();
                    this.reloadPrompt('Tandoor credentials updated — reload to apply');
                } else {
                    this.credError = 'Failed to save credentials.';
                }
            } catch {
                this.credError = 'Failed to save credentials. Please try again.';
            } finally {
                this.credSaving = false;
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

        async saveSettings(updates) {
            try {
                const res = await this.adminFetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates),
                });
                if (res.ok) {
                    this.settings = await res.json();
                }
            } catch (e) {
                console.warn('Failed to save settings:', e);
            }
        },

        async toggleSetting(key, value) {
            this.settings[key] = value;
            await this.saveSettings({ [key]: value });
            if (key === 'orders_enabled' && !value && this.activeTab === 'orders') {
                this.activeTab = 'generate';
            }
        },

        // ---- Branding ----

        async saveBranding(key, value) {
            this.settings[key] = value;
            await this.saveSettings({ [key]: value });
            document.title = (this.settings.app_name || 'Morsl') + ' - Admin';
        },

        async uploadBranding(type, event) {
            const file = event.target.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await this.adminFetch(`/api/settings/upload/${type}`, {
                    method: 'POST',
                    body: formData,
                });
                if (res.ok) {
                    this.settings = await res.json();
                    if (type === 'favicon') {
                        this.reloadPrompt('Icons regenerated. Reload to see favicon changes.');
                    }
                } else {
                    const err = await res.text();
                    this.showError(`Upload failed: ${err}`);
                }
            } catch (e) {
                this.showError(`Upload failed: ${e.message}`);
            }
            event.target.value = '';
        },

        async removeBranding(type) {
            try {
                const res = await this.adminFetch(`/api/settings/upload/${type}`, { method: 'DELETE' });
                if (res.ok) {
                    this.settings = await res.json();
                    if (type === 'favicon') {
                        this.reloadPrompt('Favicon reset to default. Reload to see changes.');
                    }
                }
            } catch (e) {
                this.showError(`Remove failed: ${e.message}`);
            }
        },

        async syncIconToLogo(type, checked) {
            const settingKey = type === 'favicon' ? 'favicon_use_logo' : 'loading_icon_use_logo';
            this.settings[settingKey] = checked;
            await this.saveSettings({ [settingKey]: checked });

            if (checked && this.settings.logo_url) {
                // Upload the logo file as the favicon/loading-icon source
                try {
                    const blob = await (await fetch(this.settings.logo_url)).blob();
                    const ext = this.settings.logo_url.split('.').pop().split('?')[0] || 'png';
                    const formData = new FormData();
                    formData.append('file', blob, `logo.${ext}`);
                    const res = await this.adminFetch(`/api/settings/upload/${type}`, {
                        method: 'POST',
                        body: formData,
                    });
                    if (res.ok) {
                        this.settings = await res.json();
                        if (type === 'favicon') {
                            this.reloadPrompt('Favicon updated from logo. Reload to see changes.');
                        }
                    }
                } catch (e) {
                    this.showError(`Sync failed: ${e.message}`);
                }
            }
        },

        resetBranding() {
            this.confirmModal = {
                show: true,
                title: 'Reset Branding?',
                message: 'This will clear your app name, taglines, logo, favicon, and loading icon. This cannot be undone.',
                confirmText: 'Reset All',
                onConfirm: async () => {
                    try {
                        const res = await this.adminFetch('/api/settings/reset-branding', { method: 'POST' });
                        if (res.ok) {
                            this.settings = await res.json();
                            document.title = (this.settings.app_name || 'Morsl') + ' - Admin';
                            this.reloadPrompt('Branding reset! Reload to see all changes.');
                        }
                    } catch (e) {
                        this.showError(`Reset failed: ${e.message}`);
                    }
                },
            };
        },

        // ---- QR Codes ----

        _renderQr(ref, data) {
            if (!ref || !data) { if (ref) ref.innerHTML = ''; return; }
            try {
                const qr = qrcode(0, 'M');
                qr.addData(data);
                qr.make();
                ref.innerHTML = qr.createSvgTag({ cellSize: 3, margin: 2 });
            } catch (e) {
                console.warn('QR generation failed:', e);
                ref.innerHTML = '';
            }
        },

        renderQrPreviews() {
            this.$nextTick(() => {
                this._renderQr(this.$refs.qrMenuPreview, this.settings.qr_menu_url);
                this._renderQr(this.$refs.qrWifiPreview, this.settings.qr_wifi_string);
            });
        },

        async saveQrSetting(key, value) {
            this.settings[key] = value;
            await this.saveSettings({ [key]: value });
            this.renderQrPreviews();
        },

        async saveWifiQr() {
            const ssid = this.$refs.wifiSsid?.value || '';
            const password = this.$refs.wifiPassword?.value || '';
            const encryption = this.$refs.wifiEncryption?.value || 'WPA';
            // Build WiFi QR string (standard format)
            let wifiString = '';
            if (ssid) {
                const esc = s => s.replace(/([\\;,":])/, '\\$1');
                wifiString = `WIFI:T:${encryption};S:${esc(ssid)};`;
                if (encryption !== 'nopass' && password) {
                    wifiString += `P:${esc(password)};`;
                }
                wifiString += ';';
            }
            this.settings.qr_wifi_ssid = ssid;
            this.settings.qr_wifi_password = password;
            this.settings.qr_wifi_encryption = encryption;
            this.settings.qr_wifi_string = wifiString;
            await this.saveSettings({
                qr_wifi_ssid: ssid,
                qr_wifi_password: password,
                qr_wifi_encryption: encryption,
                qr_wifi_string: wifiString,
            });
            this.renderQrPreviews();
        },

        // ---- Icon Mappings ----

        async loadIconMappings() {
            try {
                const res = await fetch('/api/icon-mappings');
                if (res.ok) this.iconMappings = await res.json();
            } catch (e) {
                console.warn('Failed to load icon mappings:', e);
            }
        },

        async saveIconMappings() {
            try {
                await this.adminFetch('/api/icon-mappings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.iconMappings),
                });
            } catch (e) {
                this.showError(`Failed to save icon mappings: ${e.message}`);
            }
        },

        addMapping(type) {
            const nameKey = type === 'keyword' ? 'newKwName' : 'newFoodName';
            const iconKey = type === 'keyword' ? 'newKwIcon' : 'newFoodIcon';
            const mapKey = type === 'keyword' ? 'keyword_icons' : 'food_icons';
            const searchKey = type === 'keyword' ? 'mappingKwSearch' : 'mappingFoodSearch';
            // Fall back to search text if no dropdown selection was made
            const name = (this[nameKey] || this[searchKey] || '').trim();
            const icon = this[iconKey];
            if (!name || !icon) return;
            this.iconMappings[mapKey][name.toLowerCase()] = icon;
            this[nameKey] = '';
            this[iconKey] = '';
            if (type === 'keyword') {
                this.mappingKwSearch = '';
                this.mappingKwResults = [];
            } else {
                this.mappingFoodSearch = '';
                this.mappingFoodResults = [];
            }
            this.saveIconMappings();
        },

        searchMappingKeywords() {
            if (this._mappingKwDebounceId) clearTimeout(this._mappingKwDebounceId);
            this._mappingKwDebounceId = setTimeout(() => {
                if (!this.mappingKwSearch || this.mappingKwSearch.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
                    this.mappingKwResults = [];
                    return;
                }
                const query = this.mappingKwSearch.toLowerCase();
                this.mappingKwResults = this.keywords
                    .filter(k => k.name.toLowerCase().includes(query))
                    .slice(0, CONST.MAX_KEYWORD_RESULTS);
            }, CONST.KEYWORD_DEBOUNCE_MS);
        },

        selectMappingKeyword(kw) {
            this.newKwName = kw.name;
            this.mappingKwSearch = '';
            this.mappingKwResults = [];
        },

        searchMappingFoods() {
            if (this._mappingFoodDebounceId) clearTimeout(this._mappingFoodDebounceId);
            this._mappingFoodDebounceId = setTimeout(async () => {
                if (!this.mappingFoodSearch || this.mappingFoodSearch.length < CONST.MIN_KEYWORD_SEARCH_LEN) {
                    this.mappingFoodResults = [];
                    this.mappingFoodSearched = false;
                    return;
                }
                try {
                    const res = await fetch(`/api/foods?search=${encodeURIComponent(this.mappingFoodSearch)}`);
                    if (res.ok) {
                        const data = await res.json();
                        this.mappingFoodResults = data.results || data || [];
                    }
                } catch (e) {
                    this.mappingFoodResults = [];
                }
                this.mappingFoodSearched = true;
            }, CONST.FOOD_DEBOUNCE_MS);
        },

        selectMappingFood(food) {
            this.newFoodName = food.name;
            this.mappingFoodSearch = '';
            this.mappingFoodResults = [];
        },

        removeMapping(type, name) {
            const mapKey = type === 'keyword' ? 'keyword_icons' : 'food_icons';
            delete this.iconMappings[mapKey][name];
            this.saveIconMappings();
        },

        // ---- Reload Prompt ----

        _reloadToastMsg: '',
        _reloadToastShow: false,

        reloadPrompt(message) {
            this._reloadToastMsg = message;
            this._reloadToastShow = true;
        },

        dismissReloadPrompt() {
            this._reloadToastShow = false;
        },

        // ---- Error Toast ----

        _errorMsg: '',
        _errorShow: false,

        showError(msg) {
            this._errorMsg = msg;
            this._errorShow = true;
        },

        dismissError() {
            this._errorShow = false;
        },

        // ---- Recipe Modal ----

        openRecipe(recipe) {
            this.selectedRecipe = recipe;
        },

        closeRecipe() {
            this.selectedRecipe = null;
        },

        formatIngredient,

        // ---- Theming ----

        applyTheme(name) {
            this.currentTheme = applyThemeGlobal(name);
        },

        async changeTheme(name) {
            this.applyTheme(name);
            this.settings.theme = name;
            await this.saveSettings({ theme: name });
        },

        // ---- Helpers ----

        ratingStars,

        // ---- Kiosk ----

        async submitPin() {
            this.pinError = '';
            try {
                const res = await fetch('/api/settings/verify-pin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pin: this.pinInput }),
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.valid) {
                        if (data.token) {
                            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN, data.token);
                            sessionStorage.setItem(CONST.SS_ADMIN_TOKEN_TS, String(Date.now()));
                        }
                        this.showPinGate = false;
                        this.pinInput = '';
                        await this._loadAdminData();
                    } else {
                        this.pinError = 'Incorrect PIN';
                        this.pinInput = '';
                    }
                } else {
                    this.pinError = 'Failed to verify PIN';
                }
            } catch (e) {
                this.pinError = 'Cannot reach server';
            }
        },

        // ---- History & Analytics ----

        async loadHistory(fetchOpts = {}) {
            const page = (typeof fetchOpts === 'number') ? fetchOpts : 0;
            if (typeof fetchOpts === 'number') fetchOpts = {};
            this.historyLoading = true;
            try {
                const offset = page * this.historyPageSize;
                const res = await this.adminFetch(`/api/history?limit=${this.historyPageSize}&offset=${offset}`, fetchOpts);
                if (res.ok) {
                    const data = await res.json();
                    this.history = data.entries;
                    this.historyTotal = data.total;
                    this.historyPage = page;
                }
            } catch (e) { console.debug('loadHistory failed:', e); }
            finally { this.historyLoading = false; }
        },

        async loadAnalytics(fetchOpts = {}) {
            try {
                const res = await this.adminFetch('/api/history/analytics', fetchOpts);
                if (res.ok) this.analytics = await res.json();
            } catch (e) { console.debug('loadAnalytics failed:', e); }
        },

        toggleHistoryDetail(id) {
            this.expandedHistoryId = this.expandedHistoryId === id ? null : id;
        },

        clearHistory() {
            this.confirmModal = {
                show: true,
                title: 'Clear Generation History?',
                message: 'This will delete all generation history and reset analytics. This cannot be undone.',
                confirmText: 'Clear History',
                onConfirm: async () => {
                    try {
                        const res = await this.adminFetch('/api/history', { method: 'DELETE' });
                        if (res.ok) {
                            this.history = [];
                            this.historyTotal = 0;
                            this.historyPage = 0;
                            this.analytics = { total_generations: 0, avg_duration_ms: 0, status_counts: {}, profile_counts: {}, most_relaxed: [], avg_recipes_per_generation: 0 };
                        }
                    } catch (e) {
                        this.showError('Failed to clear history: ' + e.message);
                    }
                },
            };
        },

        get historyTotalPages() {
            return Math.max(1, Math.ceil(this.historyTotal / this.historyPageSize));
        },

        lockKiosk() {
            sessionStorage.removeItem(CONST.SS_ADMIN_TOKEN);
            window.location.href = '/';
        },

        factoryReset() {
            this.confirmModal = {
                show: true,
                title: 'Factory Reset?',
                message: 'This will permanently delete all profiles, categories, schedules, history, branding, and settings. The app will return to the first-run setup wizard. This cannot be undone.',
                confirmText: 'Reset Everything',
                onConfirm: async () => {
                    try {
                        const res = await this.adminFetch('/api/settings/factory-reset', { method: 'POST' });
                        if (res.ok) {
                            localStorage.clear();
                            sessionStorage.clear();
                            window.location.href = '/setup';
                        } else {
                            this.showError('Factory reset failed.');
                        }
                    } catch (e) {
                        this.showError('Factory reset failed: ' + e.message);
                    }
                },
            };
        },
    };
}
