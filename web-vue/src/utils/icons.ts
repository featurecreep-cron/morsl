import type { Recipe, IconMappings } from '@/types/api'

const DEFAULT_FAVICON_PATH = '/icons/default-favicon.svg'

export const STOCK_ICON_SVG = `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;display:block"><g transform="translate(4,3) scale(1.1)" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z"/><path d="M6 17h12"/></g></svg>`

// SVG prefetch cache (logo, loading icon)
const _svgPrefetchCache = new Map<string, string>()

export function getBrandIcon(logoUrl: string): string {
  if (logoUrl) {
    const cached = _svgPrefetchCache.get(logoUrl)
    if (cached) return cached
    return `<img src="${logoUrl}" class="favicon-icon" style="width:100%;height:100%;object-fit:contain" alt="">`
  }
  return STOCK_ICON_SVG
}

const SVG_ALLOWED_ELEMENTS = new Set([
  'svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'line', 'polyline',
  'polygon', 'text', 'tspan', 'defs', 'use', 'clippath', 'mask',
  'lineargradient', 'radialgradient', 'stop', 'symbol', 'title', 'desc',
])

function sanitizeSVG(svgString: string): string {
  const doc = new DOMParser().parseFromString(svgString, 'image/svg+xml')
  if (doc.querySelector('parsererror')) return ''
  for (const el of [...doc.querySelectorAll('*')]) {
    if (!SVG_ALLOWED_ELEMENTS.has(el.localName)) {
      el.remove()
      continue
    }
    for (const attr of [...el.attributes]) {
      if (attr.name.startsWith('on')) {
        el.removeAttribute(attr.name)
      }
    }
  }
  const svg = doc.querySelector('svg')
  return svg ? svg.outerHTML : ''
}

export async function prefetchBrandSvg(url: string): Promise<boolean> {
  if (!url) return false
  if (_svgPrefetchCache.has(url)) return true
  try {
    const res = await fetch(url)
    if (!res.ok) return false
    let text = await res.text()
    text = sanitizeSVG(text)
    if (!text) return false
    const doc = new DOMParser().parseFromString(text, 'image/svg+xml')
    const svg = doc.querySelector('svg')
    if (!svg) return false
    for (const el of doc.querySelectorAll('*')) {
      for (const attr of ['stroke', 'fill']) {
        const val = el.getAttribute(attr)
        if (val && val !== 'none' && val !== 'transparent' && val !== 'currentColor' && val !== 'inherit') {
          el.setAttribute(attr, 'currentColor')
        }
      }
    }
    svg.style.width = '100%'
    svg.style.height = '100%'
    svg.style.display = 'block'
    svg.setAttribute('aria-hidden', 'true')
    _svgPrefetchCache.set(url, svg.outerHTML)
    return true
  } catch {
    return false
  }
}

/**
 * Inline SVG fetching for elements — fetches URL, sanitizes, injects with currentColor.
 */
const _inlineSvgCache: Record<string, string> = {}

export async function inlineSvg(url: string, el: HTMLElement, signal?: AbortSignal): Promise<void> {
  if (!url || !el) return
  try {
    let svgText = _inlineSvgCache[url]
    if (!svgText) {
      const res = await fetch(url, { signal })
      if (!res.ok) return
      svgText = await res.text()
      svgText = sanitizeSVG(svgText)
      if (!svgText) return
      _inlineSvgCache[url] = svgText
    }
    const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml')
    const svg = doc.querySelector('svg')
    if (!svg) return
    if (el.className) svg.setAttribute('class', el.className)
    svg.style.width = '100%'
    svg.style.height = '100%'
    svg.style.display = 'block'
    svg.setAttribute('aria-hidden', 'true')
    el.innerHTML = svg.outerHTML
  } catch (e: unknown) {
    if (e instanceof Error && e.name !== 'AbortError') {
      console.warn('inlineSvg failed:', e)
    }
  }
}

/**
 * Simple placeholder SVG for recipes without images.
 * Returns the stock broccoli icon — the icon system from icons.js
 * is too large to port inline; it gets loaded dynamically via /api/icon-mappings.
 */
export function getPlaceholderSvg(
  _recipe: Recipe | null,
  _profileName: string | null,
  _iconMappings: IconMappings,
  _logoUrl: string,
): string {
  // The icons.js icon library (ICONS object with 60+ SVGs) is loaded at runtime.
  // For the Vue port, we use the stock icon as the placeholder.
  // Custom icon matching via keyword/food mappings would require porting the full ICONS object.
  return STOCK_ICON_SVG
}

export function getLoadingIconHtml(loadingIconUrl: string, settingsLoaded: boolean): string {
  if (loadingIconUrl === DEFAULT_FAVICON_PATH && !settingsLoaded) {
    try {
      const c = localStorage.getItem('morsl-loading-icon')
      if (c) return c
    } catch {
      // ignore
    }
    return ''
  }
  return getBrandIcon(loadingIconUrl !== DEFAULT_FAVICON_PATH ? loadingIconUrl : '')
}
