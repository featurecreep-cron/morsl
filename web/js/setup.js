/**
 * Setup wizard — full-page guided first-run configuration.
 * Depends on: constants.js, icons.js
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('setupApp', () => ({
        // Navigation
        step: 1,                     // 1-6
        totalSteps: 6,
        profileSubPage: 'basics',
        profileIndex: 0,

        // Ordered sub-pages for step 3
        RULE_PAGES: ['basics','keywords','ingredients','books','avoid','rating','freshness','new-recipes','review'],

        // Step 1: Credentials
        url: '',
        token: '',
        testing: false,
        testResult: null,
        saving: false,
        error: '',

        // Step 2: Profile selection
        presets: [
            { key: 'breakfast', name: 'Breakfast', subtitle: 'Eggs, oats, and morning favorites', icon: 'breakfast', selected: false, choices: 3 },
            { key: 'lunch', name: 'Lunch', subtitle: 'Lighter dishes for midday', icon: 'lunch', selected: false, choices: 5 },
            { key: 'dinner', name: 'Dinner', subtitle: 'A full week of evening meals', icon: 'dinner', selected: false, choices: 5 },
            { key: 'weekday', name: 'Weekday Meals', subtitle: 'Everyday recipes for busy days', icon: 'lunchbox', selected: false, choices: 5 },
            { key: 'weekend', name: 'Weekend Meals', subtitle: 'More time to cook, more variety', icon: 'brunch', selected: false, choices: 3 },
            { key: 'weeknight', name: 'Weeknight Dinners', subtitle: 'Fast recipes when time is short', icon: 'timer', selected: false, choices: 5 },
        ],
        customProfileName: '',
        customProfiles: [],    // [{name, _id}]

        // Step 3: Profile configuration queue
        profileQueue: [],      // [{name, description, icon, choices, min_choices, default, rules}]

        // Step 4: Categories
        categoryPresets: [
            { key: 'by-cuisine', display_name: 'By Cuisine', subtitle: 'Italian, Mexican, Asian...', icon: 'bowl', selected: true },
            { key: 'by-meal', display_name: 'By Meal', subtitle: 'Breakfast, Lunch, Dinner...', icon: 'dinner', selected: true },
        ],
        customCategories: [],  // [{display_name, subtitle, _id}]
        customCatName: '',

        // Search state — 7 independent pairs (no collisions)
        themeSearch: '',
        themeResults: [],
        keywordSearch: '',
        keywordResults: [],
        foodSearch: '',
        foodResults: [],
        exceptFoodSearch: '',
        exceptFoodResults: [],
        bookSearch: '',
        bookResults: [],
        excludeKeywordSearch: '',
        excludeKeywordResults: [],
        excludeFoodSearch: '',
        excludeFoodResults: [],

        // Debounce timer IDs
        _themeDebounceId: null,
        _keywordDebounceId: null,
        _foodDebounceId: null,
        _exceptFoodDebounceId: null,
        _bookDebounceId: null,
        _excludeKeywordDebounceId: null,
        _excludeFoodDebounceId: null,

        // Status
        setupStatus: null,
        availableCategories: [],   // [{id, display_name}] — for add-profile mode

        resolveIcon(key) {
            return getIconByKey(key);
        },

        async init() {
            const params = new URLSearchParams(window.location.search);
            this._addProfileMode = params.get('mode') === 'add-profile';

            // Load saved theme
            try {
                const themeRes = await fetch('/api/settings');
                if (themeRes.ok) {
                    const s = await themeRes.json();
                    if (s.theme) applyThemeGlobal(s.theme);
                }
            } catch (e) { /* use default */ }

            try {
                const res = await fetch('/api/settings/setup-status');
                if (res.ok) {
                    this.setupStatus = await res.json();
                    if (this._addProfileMode && this.setupStatus.has_credentials) {
                        // Skip preset selection — go straight to configuring a single profile
                        this.profileQueue = [this._makeProfileEntry('', '', 5, false)];
                        this.profileIndex = 0;
                        this.profileSubPage = 'basics';
                        await this._loadCategories();
                        this.step = 3;
                    } else if (this.setupStatus.has_credentials) {
                        if (this.setupStatus.has_profiles) {
                            this.step = this.setupStatus.has_categories ? 6 : 4;
                        } else {
                            this.step = 2;
                        }
                    }
                }
            } catch (e) { /* start at step 1 */ }
        },

        destroy() {
            clearTimeout(this._themeDebounceId);
            clearTimeout(this._keywordDebounceId);
            clearTimeout(this._foodDebounceId);
            clearTimeout(this._exceptFoodDebounceId);
            clearTimeout(this._bookDebounceId);
            clearTimeout(this._excludeKeywordDebounceId);
            clearTimeout(this._excludeFoodDebounceId);
        },

        // ---- Step 1: Connection ----

        async testConnection() {
            if (!this.url || !this.token) return;
            this.testing = true;
            this.testResult = null;
            this.error = '';
            try {
                const res = await fetch('/api/settings/test-connection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: this.url, token: this.token }),
                });
                this.testResult = res.ok
                    ? await res.json()
                    : { success: false, error: 'Server error' };
            } catch (e) {
                this.testResult = { success: false, error: 'Cannot reach server' };
            } finally {
                this.testing = false;
            }
        },

        async saveCredentials() {
            if (!this.testResult?.success) return;
            this.saving = true;
            this.error = '';
            try {
                const res = await fetch('/api/settings/credentials', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: this.url, token: this.token }),
                });
                if (res.ok) {
                    const statusRes = await fetch('/api/settings/setup-status');
                    if (statusRes.ok) this.setupStatus = await statusRes.json();
                    this.step = 2;
                } else {
                    this.error = 'Failed to save credentials.';
                }
            } catch (e) {
                this.error = 'Failed to save credentials. Please try again.';
            } finally {
                this.saving = false;
            }
        },

        // ---- Step 2: Profile selection ----

        togglePreset(preset) {
            preset.selected = !preset.selected;
        },

        addCustomProfile() {
            const name = this.customProfileName.trim();
            if (!name) return;
            if (this.customProfiles.some(p => p.name.toLowerCase() === name.toLowerCase())) return;
            this.customProfiles.push({ name, _id: Date.now() + Math.random() });
            this.customProfileName = '';
        },

        removeCustomProfile(idx) {
            this.customProfiles.splice(idx, 1);
        },

        get hasProfileSelections() {
            return this.presets.some(p => p.selected) || this.customProfiles.length > 0;
        },

        buildProfileQueue() {
            const queue = [];
            let first = true;
            for (const p of this.presets) {
                if (!p.selected) continue;
                queue.push(this._makeProfileEntry(p.name, p.icon, p.choices, first));
                first = false;
            }
            for (const c of this.customProfiles) {
                queue.push(this._makeProfileEntry(c.name, '', 5, first));
                first = false;
            }
            this.profileQueue = queue;
            if (queue.length === 0) {
                this.step = 4;
            } else {
                this.profileIndex = 0;
                this.profileSubPage = 'basics';
                this.step = 3;
            }
        },

        async _loadCategories() {
            try {
                const res = await fetch('/api/categories');
                if (res.ok) this.availableCategories = await res.json();
            } catch (e) { /* best effort */ }
        },

        _makeProfileEntry(name, icon, choices, isDefault) {
            return {
                name,
                description: '',
                icon: icon || '',
                category: '',
                choices: choices || 5,
                min_choices: null,
                default: isDefault,
                rules: {
                    tagsInclude:  { active: false, theme: [], balance: [] },
                    foodsInclude: { active: false, items: [], except: [], count: 1 },
                    booksInclude: { active: false, items: [], count: choices || 5 },
                    tagsExclude:  { active: false, items: [] },
                    foodsExclude: { active: false, items: [] },
                    rating:       { active: false, min: 4 },
                    avoidRecent:  { active: false, days: 14 },
                    includeNew:   { active: false, count: 1, days: 30 },
                },
            };
        },

        // ---- Step 3: Profile configuration ----

        get currentProfile() {
            return this.profileQueue[this.profileIndex] || null;
        },

        get hasActiveConstraint() {
            const r = this.currentProfile?.rules;
            if (!r) return false;
            return r.tagsInclude.active || r.tagsExclude.active
                || r.foodsInclude.active || r.foodsExclude.active
                || r.booksInclude.active || r.rating.active
                || r.avoidRecent.active || r.includeNew.active;
        },

        // Sub-page navigation
        get subPageIndex() {
            return this.RULE_PAGES.indexOf(this.profileSubPage);
        },

        get subPageCount() {
            return this.RULE_PAGES.length;
        },

        nextSubPage() {
            const idx = this.subPageIndex;
            if (idx < this.RULE_PAGES.length - 1) {
                this._clearSearchState();
                this.profileSubPage = this.RULE_PAGES[idx + 1];
            }
        },

        prevSubPage() {
            const idx = this.subPageIndex;
            if (idx > 0) {
                this._clearSearchState();
                this.profileSubPage = this.RULE_PAGES[idx - 1];
            } else if (this.profileIndex > 0) {
                // Go back to previous profile's review page
                this.profileIndex--;
                this.profileSubPage = 'review';
                this._clearSearchState();
            } else if (this._addProfileMode) {
                window.location.href = '/admin';
            } else {
                this.step = 2;
            }
        },

        goToSubPage(page) {
            this._clearSearchState();
            this.profileSubPage = page;
        },

        _clearSearchState() {
            this.themeSearch = '';
            this.themeResults = [];
            this.keywordSearch = '';
            this.keywordResults = [];
            this.foodSearch = '';
            this.foodResults = [];
            this.exceptFoodSearch = '';
            this.exceptFoodResults = [];
            this.bookSearch = '';
            this.bookResults = [];
            this.excludeKeywordSearch = '';
            this.excludeKeywordResults = [];
            this.excludeFoodSearch = '';
            this.excludeFoodResults = [];
        },

        // ---- Keywords page (3B) — theme + balance ----

        _keywordExclusionSet() {
            const tags = this.currentProfile?.rules.tagsInclude;
            if (!tags) return new Set();
            return new Set([
                ...tags.theme.map(i => i.id),
                ...tags.balance.map(i => i.id),
            ]);
        },

        searchThemeKeywords(query) {
            this.themeSearch = query;
            this.keywordResults = [];
            clearTimeout(this._themeDebounceId);
            if (query.length < 2) { this.themeResults = []; return; }
            this._themeDebounceId = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/keywords?search=${encodeURIComponent(query)}&limit=20`);
                    if (res.ok) {
                        const data = await res.json();
                        const excluded = this._keywordExclusionSet();
                        this.themeResults = (data.results || data).filter(k => !excluded.has(k.id));
                    }
                } catch (e) { /* ignore */ }
            }, CONST.KEYWORD_DEBOUNCE_MS);
        },

        searchKeywords(query) {
            this.keywordSearch = query;
            this.themeResults = [];
            clearTimeout(this._keywordDebounceId);
            if (query.length < 2) { this.keywordResults = []; return; }
            this._keywordDebounceId = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/keywords?search=${encodeURIComponent(query)}&limit=20`);
                    if (res.ok) {
                        const data = await res.json();
                        const excluded = this._keywordExclusionSet();
                        this.keywordResults = (data.results || data).filter(k => !excluded.has(k.id));
                    }
                } catch (e) { /* ignore */ }
            }, CONST.KEYWORD_DEBOUNCE_MS);
        },

        addThemeKeyword(kw) {
            this.currentProfile.rules.tagsInclude.theme.push({ id: kw.id, name: kw.name });
            this.themeSearch = '';
            this.themeResults = [];
        },

        removeThemeKeyword(idx) {
            this.currentProfile.rules.tagsInclude.theme.splice(idx, 1);
        },

        addBalanceKeyword(kw) {
            this.currentProfile.rules.tagsInclude.balance.push({ id: kw.id, name: kw.name, count: 1 });
            this.keywordSearch = '';
            this.keywordResults = [];
        },

        removeBalanceKeyword(idx) {
            this.currentProfile.rules.tagsInclude.balance.splice(idx, 1);
        },

        get balanceAssigned() {
            return this.currentProfile?.rules.tagsInclude.balance.reduce((s, b) => s + b.count, 0) || 0;
        },

        get balanceComplete() {
            return this.currentProfile && this.balanceAssigned >= this.currentProfile.choices;
        },

        // ---- Ingredients page (3C) — include search ----

        searchFoods(query) {
            this.foodSearch = query;
            clearTimeout(this._foodDebounceId);
            if (query.length < 2) { this.foodResults = []; return; }
            this._foodDebounceId = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/foods?search=${encodeURIComponent(query)}&limit=20`);
                    if (res.ok) {
                        const data = await res.json();
                        const selected = new Set(this.currentProfile.rules.foodsInclude.items.map(i => i.id));
                        this.foodResults = (data.results || data).filter(f => !selected.has(f.id));
                    }
                } catch (e) { /* ignore */ }
            }, CONST.FOOD_DEBOUNCE_MS);
        },

        addIncludeFood(food) {
            this.currentProfile.rules.foodsInclude.items.push({ id: food.id, name: food.name });
            this.foodSearch = '';
            this.foodResults = [];
        },

        removeIncludeFood(idx) {
            this.currentProfile.rules.foodsInclude.items.splice(idx, 1);
        },

        // Ingredients page (3C) — exception search
        searchExceptFoods(query) {
            this.exceptFoodSearch = query;
            clearTimeout(this._exceptFoodDebounceId);
            if (query.length < 2) { this.exceptFoodResults = []; return; }
            this._exceptFoodDebounceId = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/foods?search=${encodeURIComponent(query)}&limit=20`);
                    if (res.ok) {
                        const data = await res.json();
                        const selected = new Set(this.currentProfile.rules.foodsInclude.except.map(i => i.id));
                        this.exceptFoodResults = (data.results || data).filter(f => !selected.has(f.id));
                    }
                } catch (e) { /* ignore */ }
            }, CONST.FOOD_DEBOUNCE_MS);
        },

        addFoodException(food) {
            this.currentProfile.rules.foodsInclude.except.push({ id: food.id, name: food.name });
            this.exceptFoodSearch = '';
            this.exceptFoodResults = [];
        },

        removeFoodException(idx) {
            this.currentProfile.rules.foodsInclude.except.splice(idx, 1);
        },

        // ---- Books page (3D) ----

        searchBooks(query) {
            this.bookSearch = query;
            clearTimeout(this._bookDebounceId);
            if (query.length < 2) { this.bookResults = []; return; }
            this._bookDebounceId = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/books?search=${encodeURIComponent(query)}`);
                    if (res.ok) {
                        const data = await res.json();
                        const selected = new Set(this.currentProfile.rules.booksInclude.items.map(i => i.id));
                        this.bookResults = (data.results || data).filter(b => !selected.has(b.id));
                    }
                } catch (e) { /* ignore */ }
            }, CONST.BOOK_DEBOUNCE_MS);
        },

        addBook(book) {
            this.currentProfile.rules.booksInclude.items.push({ id: book.id, name: book.name });
            this.bookSearch = '';
            this.bookResults = [];
        },

        removeBook(idx) {
            this.currentProfile.rules.booksInclude.items.splice(idx, 1);
        },

        // ---- Avoid page (3E) — exclude keyword search ----

        searchExcludeKeywords(query) {
            this.excludeKeywordSearch = query;
            clearTimeout(this._excludeKeywordDebounceId);
            if (query.length < 2) { this.excludeKeywordResults = []; return; }
            this._excludeKeywordDebounceId = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/keywords?search=${encodeURIComponent(query)}&limit=20`);
                    if (res.ok) {
                        const data = await res.json();
                        const selected = new Set(this.currentProfile.rules.tagsExclude.items.map(i => i.id));
                        this.excludeKeywordResults = (data.results || data).filter(k => !selected.has(k.id));
                    }
                } catch (e) { /* ignore */ }
            }, CONST.KEYWORD_DEBOUNCE_MS);
        },

        addExcludeKeyword(kw) {
            this.currentProfile.rules.tagsExclude.items.push({ id: kw.id, name: kw.name });
            this.excludeKeywordSearch = '';
            this.excludeKeywordResults = [];
        },

        removeExcludeKeyword(idx) {
            this.currentProfile.rules.tagsExclude.items.splice(idx, 1);
        },

        // ---- Avoid page (3E) — exclude food search ----

        searchExcludeFoods(query) {
            this.excludeFoodSearch = query;
            clearTimeout(this._excludeFoodDebounceId);
            if (query.length < 2) { this.excludeFoodResults = []; return; }
            this._excludeFoodDebounceId = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/foods?search=${encodeURIComponent(query)}&limit=20`);
                    if (res.ok) {
                        const data = await res.json();
                        const selected = new Set(this.currentProfile.rules.foodsExclude.items.map(i => i.id));
                        this.excludeFoodResults = (data.results || data).filter(f => !selected.has(f.id));
                    }
                } catch (e) { /* ignore */ }
            }, CONST.FOOD_DEBOUNCE_MS);
        },

        addExcludeFood(food) {
            this.currentProfile.rules.foodsExclude.items.push({ id: food.id, name: food.name });
            this.excludeFoodSearch = '';
            this.excludeFoodResults = [];
        },

        removeExcludeFood(idx) {
            this.currentProfile.rules.foodsExclude.items.splice(idx, 1);
        },

        // ---- Rating (3F) ----

        setRating(stars) {
            this.currentProfile.rules.rating.min = stars;
        },

        // ---- Freshness (3G) — day presets ----

        setAvoidDays(days) {
            this.currentProfile.rules.avoidRecent.days = days;
        },

        get avoidDaysIsPreset() {
            return [7, 14, 21, 30].includes(this.currentProfile?.rules.avoidRecent.days);
        },

        // ---- Icon picker ----

        openIconPicker() {
            if (!window.iconPicker || !this.currentProfile) return;
            window.iconPicker.show(this.currentProfile.icon, (key) => {
                this.currentProfile.icon = key;
            });
        },

        // ---- Review summary (3I) ----

        get ruleSummary() {
            if (!this.currentProfile) return [];
            const r = this.currentProfile.rules;
            const lines = [];

            if (r.tagsInclude.active) {
                if (r.tagsInclude.theme.length) {
                    const count = this.currentProfile.choices;
                    const names = r.tagsInclude.theme.map(i => i.name).join(' or ');
                    lines.push({ text: `${names}: at least ${count} recipe${count !== 1 ? 's' : ''}`, page: 'keywords' });
                }
                for (const item of r.tagsInclude.balance) {
                    lines.push({ text: `${item.name}: at least ${item.count} recipe${item.count !== 1 ? 's' : ''}`, page: 'keywords' });
                }
            }
            if (r.foodsInclude.active && r.foodsInclude.items.length) {
                let text = `Ingredients: ${r.foodsInclude.items.map(i => i.name).join(', ')} (at least ${r.foodsInclude.count})`;
                if (r.foodsInclude.except.length) {
                    text += `, except ${r.foodsInclude.except.map(i => i.name).join(', ')}`;
                }
                lines.push({ text, page: 'ingredients' });
            }
            if (r.booksInclude.active && r.booksInclude.items.length) {
                const names = r.booksInclude.items.map(i => i.name).join(', ');
                lines.push({ text: `Books: ${names} (at least ${r.booksInclude.count})`, page: 'books' });
            }
            if (r.tagsExclude.active && r.tagsExclude.items.length) {
                for (const item of r.tagsExclude.items) {
                    lines.push({ text: `Avoids: ${item.name} keyword`, page: 'avoid' });
                }
            }
            if (r.foodsExclude.active && r.foodsExclude.items.length) {
                for (const item of r.foodsExclude.items) {
                    lines.push({ text: `Avoids: ${item.name} ingredient`, page: 'avoid' });
                }
            }
            if (r.rating.active) {
                lines.push({ text: `Minimum rating: ${r.rating.min} stars`, page: 'rating' });
            }
            if (r.avoidRecent.active) {
                lines.push({ text: `Skips recipes cooked in last ${r.avoidRecent.days} days`, page: 'freshness' });
            }
            if (r.includeNew.active) {
                lines.push({ text: `Includes ${r.includeNew.count}+ recipes added in last ${r.includeNew.days} days`, page: 'new-recipes' });
            }
            return lines;
        },

        // ---- Build v2 constraints from rules ----

        buildConstraints(rules, choices) {
            const constraints = [];

            if (rules.tagsInclude.active) {
                if (rules.tagsInclude.theme.length) {
                    constraints.push({
                        type: 'keyword',
                        items: rules.tagsInclude.theme.map(i => ({ id: i.id, name: i.name })),
                        operator: '>=',
                        count: choices,
                    });
                }
                for (const item of rules.tagsInclude.balance) {
                    constraints.push({
                        type: 'keyword',
                        items: [{ id: item.id, name: item.name }],
                        operator: '>=',
                        count: item.count,
                    });
                }
            }
            if (rules.foodsInclude.active && rules.foodsInclude.items.length) {
                const c = {
                    type: 'food',
                    items: rules.foodsInclude.items.map(i => ({ id: i.id, name: i.name })),
                    operator: '>=',
                    count: rules.foodsInclude.count,
                };
                if (rules.foodsInclude.except.length) {
                    c.except = rules.foodsInclude.except.map(i => ({ id: i.id, name: i.name }));
                }
                constraints.push(c);
            }
            if (rules.booksInclude.active && rules.booksInclude.items.length) {
                constraints.push({
                    type: 'book',
                    items: rules.booksInclude.items.map(i => ({ id: i.id, name: i.name })),
                    operator: '>=',
                    count: rules.booksInclude.count,
                });
            }
            if (rules.tagsExclude.active && rules.tagsExclude.items.length) {
                constraints.push({
                    type: 'keyword',
                    items: rules.tagsExclude.items.map(i => ({ id: i.id, name: i.name })),
                    operator: '==',
                    count: 0,
                });
            }
            if (rules.foodsExclude.active && rules.foodsExclude.items.length) {
                constraints.push({
                    type: 'food',
                    items: rules.foodsExclude.items.map(i => ({ id: i.id, name: i.name })),
                    operator: '==',
                    count: 0,
                });
            }
            if (rules.rating.active) {
                constraints.push({
                    type: 'rating',
                    min: rules.rating.min,
                    operator: '>=',
                    count: 1,
                });
            }
            if (rules.avoidRecent.active) {
                constraints.push({
                    type: 'cookedon',
                    within_days: rules.avoidRecent.days,
                    operator: '==',
                    count: 0,
                });
            }
            if (rules.includeNew.active) {
                constraints.push({
                    type: 'createdon',
                    within_days: rules.includeNew.days,
                    operator: '>=',
                    count: rules.includeNew.count,
                });
            }
            return constraints;
        },

        async createCurrentProfile() {
            const p = this.currentProfile;
            if (!p) return;
            this.saving = true;
            this.error = '';
            try {
                const body = {
                    name: p.name.trim(),
                    description: p.description,
                    icon: p.icon,
                    choices: p.choices,
                    default: p.default,
                    constraints: this.buildConstraints(p.rules, p.choices),
                };
                if (p.min_choices) body.min_choices = p.min_choices;
                const res = await fetch('/api/profiles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (res.ok || res.status === 409) {
                    // Assign category if selected
                    if (p.category) {
                        await fetch(`/api/profiles/${encodeURIComponent(p.name.trim())}/category`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ category: p.category }),
                        });
                    }
                    this.advanceProfile();
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.error = err.detail || 'Failed to create profile.';
                }
            } catch (e) {
                this.error = 'Failed to create profile. Please try again.';
            } finally {
                this.saving = false;
            }
        },

        advanceProfile() {
            if (this.profileIndex < this.profileQueue.length - 1) {
                this.profileIndex++;
                this.profileSubPage = 'basics';
                this._clearSearchState();
                this.error = '';
            } else if (this._addProfileMode) {
                window.location.href = '/admin';
            } else {
                this.step = 4;
                this.error = '';
            }
        },

        backProfile() {
            this.prevSubPage();
        },

        skipProfile() {
            this.advanceProfile();
        },

        // ---- Step 4: Categories ----

        toggleCategory(preset) {
            preset.selected = !preset.selected;
        },

        addCustomCategory() {
            const name = this.customCatName.trim();
            if (!name) return;
            this.customCategories.push({ display_name: name, subtitle: '', _id: Date.now() + Math.random() });
            this.customCatName = '';
        },

        removeCustomCategory(idx) {
            this.customCategories.splice(idx, 1);
        },

        async createCategories() {
            const toCreate = [];
            for (const preset of this.categoryPresets) {
                if (preset.selected && preset.display_name?.trim()) {
                    toCreate.push({
                        display_name: preset.display_name.trim(),
                        subtitle: preset.subtitle?.trim() || '',
                        icon: preset.icon || '',
                    });
                }
            }
            for (const custom of this.customCategories) {
                if (custom.display_name?.trim()) {
                    toCreate.push({
                        display_name: custom.display_name.trim(),
                        subtitle: custom.subtitle?.trim() || '',
                        icon: '',
                    });
                }
            }
            if (toCreate.length === 0) { this.step = 6; return; }
            this.saving = true;
            this.error = '';
            try {
                for (const cat of toCreate) {
                    const res = await fetch('/api/categories', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(cat),
                    });
                    if (!res.ok && res.status !== 409) {
                        const err = await res.json().catch(() => ({}));
                        throw new Error(err.detail || res.statusText);
                    }
                }
                await this._loadAssignmentData();
                this.step = 5;
            } catch (e) {
                this.error = 'Failed to create categories: ' + e.message;
            } finally {
                this.saving = false;
            }
        },

        // ---- Step 5: Assign profiles to categories ----

        createdCategories: [],   // [{id, display_name}]
        profileAssignments: [],  // [{name, category}]

        async _loadAssignmentData() {
            try {
                const [catRes, profRes] = await Promise.all([
                    fetch('/api/categories'),
                    fetch('/api/profiles'),
                ]);
                if (catRes.ok) this.createdCategories = await catRes.json();
                if (profRes.ok) {
                    const profiles = await profRes.json();
                    this.profileAssignments = profiles.map(p => ({
                        name: p.name,
                        category: p.category || '',
                    }));
                }
            } catch (e) { /* best effort */ }
        },

        async saveAssignments() {
            this.saving = true;
            this.error = '';
            try {
                for (const pa of this.profileAssignments) {
                    if (!pa.category) continue;
                    await fetch(`/api/profiles/${encodeURIComponent(pa.name)}/category`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ category: pa.category }),
                    });
                }
                this.step = 6;
            } catch (e) {
                this.error = 'Failed to save assignments: ' + e.message;
            } finally {
                this.saving = false;
            }
        },

        // ---- Step 6: Finish ----

        finishSetup() {
            window.location.href = '/';
        },

        // ---- Helpers ----

        incrementChoices() {
            if (this.currentProfile && this.currentProfile.choices < 50) {
                this.currentProfile.choices++;
            }
        },

        decrementChoices() {
            const min = this.currentProfile?.min_choices || 1;
            if (this.currentProfile && this.currentProfile.choices > min) {
                this.currentProfile.choices--;
            }
        },

        incrementMin() {
            if (!this.currentProfile) return;
            const cur = this.currentProfile.min_choices || this.currentProfile.choices;
            if (cur < this.currentProfile.choices) {
                this.currentProfile.min_choices = cur + 1;
            }
        },

        decrementMin() {
            if (!this.currentProfile) return;
            const cur = this.currentProfile.min_choices || this.currentProfile.choices;
            if (cur > 1) {
                this.currentProfile.min_choices = cur - 1;
            }
        },
    }));
});
