/**
 * Reusable icon picker Alpine.js component.
 * Register with Alpine.data('iconPicker', iconPicker).
 * Open via: window.iconPicker.show(currentValue, onSelect)
 */
function iconPicker() {
    return {
        open: false,
        activeTab: '',
        currentIcon: '',
        searchQuery: '',
        customIcons: [],
        _onSelect: null,

        init() {
            window.iconPicker = this;
            this.loadCustomIcons();
        },

        get tabs() {
            const base = Object.keys(ICON_TABS);
            base.push('Custom');
            return base;
        },

        get tabGroups() {
            if (this.activeTab === 'Custom') {
                return { 'Custom': this.customIcons.map(c => c.key) };
            }
            return ICON_TABS[this.activeTab] || {};
        },

        get tabGroupEntries() {
            const groups = this.tabGroups;
            const keys = Object.keys(groups);
            return keys.map(k => ({ name: k, icons: groups[k], solo: keys.length === 1 }));
        },

        get filteredIcons() {
            if (!this.searchQuery) return [];
            const q = this.searchQuery.toLowerCase();
            return getAllIconKeys().filter(k => k.includes(q));
        },

        get isSearching() {
            return this.searchQuery.length > 0;
        },

        show(currentValue, onSelect) {
            this.currentIcon = currentValue || '';
            this._onSelect = onSelect;
            this.searchQuery = '';
            this.activeTab = this.tabs[0] || '';
            this.open = true;
        },

        pick(key) {
            if (this._onSelect) this._onSelect(key);
            this.open = false;
        },

        close() {
            this.open = false;
        },

        // ── Custom icons ──────────────────────────────────────

        async loadCustomIcons() {
            try {
                const resp = await fetch('/api/custom-icons');
                if (!resp.ok) return;
                const list = await resp.json();
                this.customIcons = list;
                // Only bulk-fetch SVGs if the eager loader in icons.js hasn't already
                if (getCustomIconKeys().length === 0) {
                    const bulkResp = await fetch('/api/custom-icons/all');
                    if (bulkResp.ok) {
                        const svgMap = await bulkResp.json();
                        for (const [key, svg] of Object.entries(svgMap)) {
                            registerCustomIcon(key, svg);
                        }
                    }
                }
            } catch (e) {
                // Custom icons not available — that's fine
            }
        },

        async uploadIcon(event) {
            const file = event.target.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('file', file);
            try {
                const resp = await fetch('/api/custom-icons', { method: 'POST', body: formData });
                if (resp.ok) {
                    await this.loadCustomIcons();
                    window.dispatchEvent(new CustomEvent('custom-icons-loaded'));
                }
            } catch (e) {
                console.error('Upload failed:', e);
            }
            event.target.value = '';
        },

        async renameCustomIcon(key, newName) {
            const oldName = key.replace('custom:', '');
            try {
                const resp = await fetch(`/api/custom-icons/${oldName}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: newName }),
                });
                if (resp.ok) {
                    const result = await resp.json();
                    removeCustomIcon(key);
                    await this.loadCustomIcons();
                    window.dispatchEvent(new CustomEvent('custom-icons-loaded'));
                    return result;
                } else {
                    const err = await resp.json();
                    console.error('Rename failed:', err.detail);
                }
            } catch (e) {
                console.error('Rename failed:', e);
            }
            return null;
        },

        async deleteCustomIcon(key) {
            const name = key.replace('custom:', '');
            try {
                const resp = await fetch(`/api/custom-icons/${name}`, { method: 'DELETE' });
                if (resp.ok) {
                    removeCustomIcon(key);
                    this.customIcons = this.customIcons.filter(c => c.key !== key);
                    window.dispatchEvent(new CustomEvent('custom-icons-loaded'));
                }
            } catch (e) {
                console.error('Delete failed:', e);
            }
        },
    };
}

document.addEventListener('alpine:init', () => {
    Alpine.data('iconPicker', iconPicker);
});
