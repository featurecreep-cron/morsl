/**
 * Shared utility functions used by both app.js and admin.js.
 * Depends on: THEME_REGISTRY (theme-registry.js)
 */

const DEFAULT_FAVICON_PATH = '/icons/default-favicon.svg';
const STOCK_ICON_SVG = `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;display:block"><g transform="translate(4,3) scale(1.1)" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z"/><path d="M6 17h12"/></g></svg>`;

/**
 * Return inline HTML for the brand icon. If a logo URL is provided and its
 * inline SVG has been prefetched (see prefetchBrandSvg), returns the SVG with
 * currentColor so it inherits theme accent colors. Falls back to STOCK_ICON_SVG.
 */
const _svgPrefetchCache = new Map();

function getBrandIcon(logoUrl) {
    if (logoUrl) {
        const cached = _svgPrefetchCache.get(logoUrl);
        if (cached) return cached;
        // Fallback before prefetch completes: <img> with CSS filter
        return `<img src="${logoUrl}" class="favicon-icon" style="width:100%;height:100%;object-fit:contain" alt="">`;
    }
    return STOCK_ICON_SVG;
}

/**
 * Prefetch an SVG URL, replace hardcoded colors with currentColor,
 * and cache the result so getBrandIcon() returns theme-aware inline SVG.
 * Works for brand logos, loading icons, or any SVG that needs theme awareness.
 * @param {string} url - SVG URL
 * @returns {Promise<boolean>} true if successfully cached
 */
async function prefetchBrandSvg(url) {
    if (!url) return false;
    if (_svgPrefetchCache.has(url)) return true;
    try {
        const res = await fetch(url);
        if (!res.ok) return false;
        let text = await res.text();
        text = sanitizeSVG(text);
        if (!text) return false;
        const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
        const svg = doc.querySelector('svg');
        if (!svg) return false;
        // Replace hardcoded colors with currentColor for theme awareness
        for (const el of doc.querySelectorAll('*')) {
            for (const attr of ['stroke', 'fill']) {
                const val = el.getAttribute(attr);
                if (val && val !== 'none' && val !== 'transparent' && val !== 'currentColor' && val !== 'inherit') {
                    el.setAttribute(attr, 'currentColor');
                }
            }
        }
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.display = 'block';
        svg.setAttribute('aria-hidden', 'true');
        _svgPrefetchCache.set(url, svg.outerHTML);
        return true;
    } catch (e) {
        console.warn('prefetchBrandSvg failed:', e);
        return false;
    }
}

function applyThemeGlobal(name) {
    const theme = THEME_REGISTRY[name] || THEME_REGISTRY['cast-iron'];
    const safeName = THEME_REGISTRY[name] ? name : 'cast-iron';
    const link = document.getElementById('theme-css');
    if (link) link.href = '/css/theme-' + safeName + '.css';
    document.body.dataset.theme = safeName;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme.accentColor);
    try { localStorage.setItem('morsl-theme', safeName); } catch (e) { /* private browsing */ }
    return safeName;
}

function formatIngredient(ing) {
    const parts = [];
    if (ing.amount) parts.push(ing.amount % 1 === 0 ? ing.amount.toString() : ing.amount.toFixed(2).replace(/\.?0+$/, ''));
    if (ing.unit) parts.push(ing.unit);
    parts.push(ing.food);
    return parts.join(' ');
}

/**
 * Return "N cocktail(s)" or "N recipe(s)" using an explicit noun string.
 * @param {number} n - count
 * @param {string} [noun] - singular noun (e.g. "cocktail"); defaults to "recipe"
 */
function itemNounText(n, noun) {
    const word = noun || 'recipe';
    return n + ' ' + word + (n === 1 ? '' : 's');
}

function ratingStars(rating) {
    if (!rating) return 0;
    return Math.round(rating);
}

/**
 * Fetch an SVG URL, sanitize it, and inject it inline into a container element.
 * Uses currentColor so SVGs inherit the theme's text color.
 * @param {string} url - SVG URL to fetch
 * @param {HTMLElement} el - Container element to inject into
 * @param {AbortSignal} [signal] - Optional abort signal for cleanup
 */
const _inlineSvgCache = {};
async function inlineSvg(url, el, signal) {
    if (!url || !el) return;
    try {
        let svgText = _inlineSvgCache[url];
        if (!svgText) {
            const res = await fetch(url, { signal });
            if (!res.ok) return;
            svgText = await res.text();
            svgText = sanitizeSVG(svgText);
            if (!svgText) return;
            _inlineSvgCache[url] = svgText;
        }
        const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
        const svg = doc.querySelector('svg');
        if (!svg) return;
        // Copy sizing classes from container
        if (el.className) svg.setAttribute('class', el.className);
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.display = 'block';
        svg.setAttribute('aria-hidden', 'true');
        el.innerHTML = svg.outerHTML;
    } catch (e) {
        if (e.name !== 'AbortError') console.warn('inlineSvg failed:', e);
    }
}
