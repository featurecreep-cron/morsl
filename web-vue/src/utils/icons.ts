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
  'pattern', 'marker', 'filter', 'fegaussianblur', 'feoffset', 'feblend',
  'fecolormatrix', 'fecomposite', 'feflood', 'femerge', 'femergenode', 'image',
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

// ─── Icon Library ─────────────────────────────────────────────────────────────

interface IconEntry {
  small: string
  large: string
}

const ICONS: Record<string, IconEntry> = {
    // --- Proteins ---
    beef: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16.4 13.7A6.5 6.5 0 1 0 6.28 6.6c-1.1 3.13-.78 3.9-3.18 6.08A3 3 0 0 0 5 18c4 0 8.4-1.8 11.4-4.3" /> <path d="m18.5 6 2.19 4.5a6.48 6.48 0 0 1-2.29 7.2C15.4 20.2 11 22 7 22a3 3 0 0 1-2.68-1.66L2.4 16.5" /> <circle cx="12.5" cy="8.5" r="2.5" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M16.4 13.7A6.5 6.5 0 1 0 6.28 6.6c-1.1 3.13-.78 3.9-3.18 6.08A3 3 0 0 0 5 18c4 0 8.4-1.8 11.4-4.3" /> <path d="m18.5 6 2.19 4.5a6.48 6.48 0 0 1-2.29 7.2C15.4 20.2 11 22 7 22a3 3 0 0 1-2.68-1.66L2.4 16.5" /> <circle cx="12.5" cy="8.5" r="2.5" /></g></svg>`,
    },
    chicken: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15.4 15.63a7.875 6 135 1 1 6.23-6.23 4.5 3.43 135 0 0-6.23 6.23" /> <path d="m8.29 12.71-2.6 2.6a2.5 2.5 0 1 0-1.65 4.65A2.5 2.5 0 1 0 8.7 18.3l2.59-2.59" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M15.4 15.63a7.875 6 135 1 1 6.23-6.23 4.5 3.43 135 0 0-6.23 6.23" /> <path d="m8.29 12.71-2.6 2.6a2.5 2.5 0 1 0-1.65 4.65A2.5 2.5 0 1 0 8.7 18.3l2.59-2.59" /></g></svg>`,
    },
    pork: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="13" r="7"/> <path d="M7 7l-1.5-3.5"/> <path d="M17 7l1.5-3.5"/> <ellipse cx="12" cy="15.5" rx="3" ry="2"/> <circle cx="10.8" cy="15.5" r="0.6" fill="currentColor"/> <circle cx="13.2" cy="15.5" r="0.6" fill="currentColor"/> <circle cx="9.5" cy="11" r="0.8"/> <circle cx="14.5" cy="11" r="0.8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><circle cx="12" cy="13" r="7"/> <path d="M7 7l-1.5-3.5"/> <path d="M17 7l1.5-3.5"/> <ellipse cx="12" cy="15.5" rx="3" ry="2"/> <circle cx="10.8" cy="15.5" r="0.6" fill="currentColor"/> <circle cx="13.2" cy="15.5" r="0.6" fill="currentColor"/> <circle cx="9.5" cy="11" r="0.8"/> <circle cx="14.5" cy="11" r="0.8"/></g></svg>`,
    },
    fish: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6s-7.56-2.53-8.5-6Z" /> <path d="M18 12v.5" /> <path d="M16 17.93a9.77 9.77 0 0 1 0-11.86" /> <path d="M7 10.67C7 8 5.58 5.97 2.73 5.5c-1 1.5-1 5 .23 6.5-1.24 1.5-1.24 5-.23 6.5C5.58 18.03 7 16 7 13.33" /> <path d="M10.46 7.26C10.2 5.88 9.17 4.24 8 3h5.8a2 2 0 0 1 1.98 1.67l.23 1.4" /> <path d="m16.01 17.93-.23 1.4A2 2 0 0 1 13.8 21H9.5a5.96 5.96 0 0 0 1.49-3.98" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6s-7.56-2.53-8.5-6Z" /> <path d="M18 12v.5" /> <path d="M16 17.93a9.77 9.77 0 0 1 0-11.86" /> <path d="M7 10.67C7 8 5.58 5.97 2.73 5.5c-1 1.5-1 5 .23 6.5-1.24 1.5-1.24 5-.23 6.5C5.58 18.03 7 16 7 13.33" /> <path d="M10.46 7.26C10.2 5.88 9.17 4.24 8 3h5.8a2 2 0 0 1 1.98 1.67l.23 1.4" /> <path d="m16.01 17.93-.23 1.4A2 2 0 0 1 13.8 21H9.5a5.96 5.96 0 0 0 1.49-3.98" /></g></svg>`,
    },
    shrimp: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 12h.01" /> <path d="M13 22c.5-.5 1.12-1 2.5-1-1.38 0-2-.5-2.5-1" /> <path d="M14 2a3.28 3.28 0 0 1-3.227 1.798l-6.17-.561A2.387 2.387 0 1 0 4.387 8H15.5a1 1 0 0 1 0 13 1 1 0 0 0 0-5H12a7 7 0 0 1-7-7V8" /> <path d="M14 8a8.5 8.5 0 0 1 0 8" /> <path d="M16 16c2 0 4.5-4 4-6" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M11 12h.01" /> <path d="M13 22c.5-.5 1.12-1 2.5-1-1.38 0-2-.5-2.5-1" /> <path d="M14 2a3.28 3.28 0 0 1-3.227 1.798l-6.17-.561A2.387 2.387 0 1 0 4.387 8H15.5a1 1 0 0 1 0 13 1 1 0 0 0 0-5H12a7 7 0 0 1-7-7V8" /> <path d="M14 8a8.5 8.5 0 0 1 0 8" /> <path d="M16 16c2 0 4.5-4 4-6" /></g></svg>`,
    },
    lamb: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 14.5Q6 11 9.5 11h5.3q3.7 0 3.7 3.6 0 3-2.6 4.9Q14.2 21 11.3 21q-3.2 0-4.8-1.8Q5 17.6 5.5 14.5Z"/> <path d="M8 11Q8.2 9 9.6 7.4 11 5.8 12.6 4.6"/> <path d="M11 11Q11.3 8.7 12.9 6.9 14.3 5.3 16.2 4.3"/> <path d="M14 11Q14.5 8.8 16.4 7.2 18 5.9 19.4 5.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 14.5Q6 11 9.5 11h5.3q3.7 0 3.7 3.6 0 3-2.6 4.9Q14.2 21 11.3 21q-3.2 0-4.8-1.8Q5 17.6 5.5 14.5Z"/> <path d="M8 11Q8.2 9 9.6 7.4 11 5.8 12.6 4.6"/> <path d="M11 11Q11.3 8.7 12.9 6.9 14.3 5.3 16.2 4.3"/> <path d="M14 11Q14.5 8.8 16.4 7.2 18 5.9 19.4 5.6"/></g></svg>`,
    },
    turkey: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="11" rx="5.5" ry="5"/><path d="M8.5 15.5c-1 1.5-1.5 3-1 4.5"/><path d="M15.5 15.5c1 1.5 1.5 3 1 4.5"/><path d="M7.5 20h2M14.5 20h2"/><circle cx="12" cy="6" r="1.2" fill="currentColor"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><ellipse cx="12" cy="11" rx="5.5" ry="5"/><path d="M8.5 15.5c-1 1.5-1.5 3-1 4.5"/><path d="M15.5 15.5c1 1.5 1.5 3 1 4.5"/><path d="M7.5 20h2M14.5 20h2"/><circle cx="12" cy="6" r="1.2" fill="currentColor"/></g></svg>`,
    },
    salmon: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12c0-3.5 3.2-6 7-6s7 2.5 7 6-3.2 6-7 6-7-2.5-7-6Z"/><path d="M8 9l8 6"/><path d="M8 15l8-6"/><path d="M12 6v12"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5 12c0-3.5 3.2-6 7-6s7 2.5 7 6-3.2 6-7 6-7-2.5-7-6Z"/><path d="M8 9l8 6"/><path d="M8 15l8-6"/><path d="M12 6v12"/></g></svg>`,
    },
    tofu: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="7" width="12" height="10" rx="2"/> <path d="M6 10h12"/> <path d="M6 13h12"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><rect x="6" y="7" width="12" height="10" rx="2"/> <path d="M6 10h12"/> <path d="M6 13h12"/></g></svg>`,
    },
    egg: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2C8 2 4 8 4 14a8 8 0 0 0 16 0c0-6-4-12-8-12" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 2C8 2 4 8 4 14a8 8 0 0 0 16 0c0-6-4-12-8-12" /></g></svg>`,
    },
    sausage: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 10c0-1.7 2.7-3 6-3s6 1.3 6 3v4c0 1.7-2.7 3-6 3s-6-1.3-6-3v-4Z"/><path d="M6 10c0 1.7 2.7 3 6 3s6-1.3 6-3"/><path d="M8.5 7.5v9M15.5 7.5v9"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 10c0-1.7 2.7-3 6-3s6 1.3 6 3v4c0 1.7-2.7 3-6 3s-6-1.3-6-3v-4Z"/><path d="M6 10c0 1.7 2.7 3 6 3s6-1.3 6-3"/><path d="M8.5 7.5v9M15.5 7.5v9"/></g></svg>`,
    },
    bacon: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 7c2 1.5 4-1.5 6 0s4-1.5 6 0"/><path d="M5 12c2 1.5 4-1.5 6 0s4-1.5 6 0"/><path d="M5 17c2 1.5 4-1.5 6 0s4-1.5 6 0"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5 7c2 1.5 4-1.5 6 0s4-1.5 6 0"/><path d="M5 12c2 1.5 4-1.5 6 0s4-1.5 6 0"/><path d="M5 17c2 1.5 4-1.5 6 0s4-1.5 6 0"/></g></svg>`,
    },
    // --- Grains & Carbs ---
    pasta: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 16c2.2-3.1 4.6-4.6 7.2-4.7 2.7-.1 4.3 1.2 5.9 2.6 1.6 1.4 3.2 2.6 5.9 2.6"/> <path d="M5.4 18.4c2.3-3 4.7-4.4 7.1-4.5 2.4-.1 4 1.1 5.6 2.5 1.6 1.4 3.3 2.7 6.3 2.7"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5 16c2.2-3.1 4.6-4.6 7.2-4.7 2.7-.1 4.3 1.2 5.9 2.6 1.6 1.4 3.2 2.6 5.9 2.6"/> <path d="M5.4 18.4c2.3-3 4.7-4.4 7.1-4.5 2.4-.1 4 1.1 5.6 2.5 1.6 1.4 3.3 2.7 6.3 2.7"/></g></svg>`,
    },
    rice: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M7 13Q12 9 17 13"/> <path d="M7.2 9.2l12.2-1.6"/> <path d="M8.2 10.8l12.2-1.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M7 13Q12 9 17 13"/> <path d="M7.2 9.2l12.2-1.6"/> <path d="M8.2 10.8l12.2-1.6"/></g></svg>`,
    },
    bread: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 12.5c0-4.7 3-7.5 6-7.5s6 2.8 6 7.5V19H6v-6.5Z"/> <path d="M8 12.2Q11.2 9.4 16 8.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 12.5c0-4.7 3-7.5 6-7.5s6 2.8 6 7.5V19H6v-6.5Z"/> <path d="M8 12.2Q11.2 9.4 16 8.6"/></g></svg>`,
    },
    noodles: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 16h14"/> <path d="M6 16c0 3.5 2.7 6 6 6s6-2.5 6-6"/> <path d="M10 16c-.3-2 .3-4-.3-6"/> <path d="M14 16c.3-2-.3-4 .3-6"/> <path d="M8 4l4 12"/> <path d="M18 4l-4 12"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5 16h14"/> <path d="M6 16c0 3.5 2.7 6 6 6s6-2.5 6-6"/> <path d="M10 16c-.3-2 .3-4-.3-6"/> <path d="M14 16c.3-2-.3-4 .3-6"/> <path d="M8 4l4 12"/> <path d="M18 4l-4 12"/></g></svg>`,
    },
    potato: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="13" rx="7" ry="5"/><path d="M7 11c2-2 5-2 10 0"/><path d="M9 10.5v-1.5M11 9.8v-1.5M13 9.8v-1.5M15 10.5v-1.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><ellipse cx="12" cy="13" rx="7" ry="5"/><path d="M7 11c2-2 5-2 10 0"/><path d="M9 10.5v-1.5M11 9.8v-1.5M13 9.8v-1.5M15 10.5v-1.5"/></g></svg>`,
    },
    couscous: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.4 18 13"/> <path d="M9.2 14h.01"/> <path d="M12 15.2h.01"/> <path d="M14.8 14.4h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.4 18 13"/> <path d="M9.2 14h.01"/> <path d="M12 15.2h.01"/> <path d="M14.8 14.4h.01"/></g></svg>`,
    },
    tortilla: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/> <path d="M6.8 15.8c2.2 1.7 5.4 2.6 8.4 2 2.2-.5 3.9-1.7 4.8-3.2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><circle cx="12" cy="12" r="8"/> <path d="M6.8 15.8c2.2 1.7 5.4 2.6 8.4 2 2.2-.5 3.9-1.7 4.8-3.2"/></g></svg>`,
    },
    oats: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.6 18 13"/> <path d="M16.6 9.6c1.6-2.2 3.2-3.3 4.4-3.6"/> <path d="M9.2 14.2h.01"/> <path d="M13.2 15.2h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.6 18 13"/> <path d="M16.6 9.6c1.6-2.2 3.2-3.3 4.4-3.6"/> <path d="M9.2 14.2h.01"/> <path d="M13.2 15.2h.01"/></g></svg>`,
    },
    quinoa: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M7 13Q12 9.2 17 13"/> <path d="M9.3 14.3h.01"/> <path d="M11.6 15.4h.01"/> <path d="M14.2 14.8h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M7 13Q12 9.2 17 13"/> <path d="M9.3 14.3h.01"/> <path d="M11.6 15.4h.01"/> <path d="M14.2 14.8h.01"/></g></svg>`,
    },
    cornbread: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 19L11.2 6.3c.3-.7 1.3-.7 1.6 0L18 19H6Z"/> <path d="M9.6 15h.01"/> <path d="M12 13h.01"/> <path d="M14.6 16.3h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 19L11.2 6.3c.3-.7 1.3-.7 1.6 0L18 19H6Z"/> <path d="M9.6 15h.01"/> <path d="M12 13h.01"/> <path d="M14.6 16.3h.01"/></g></svg>`,
    },
    // --- Fruits & Vegetables ---
    carrot: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 8q-1.5 6 2 13 3.5-7 2-13Z"/> <path d="M12 8V5"/> <path d="M9 5q3-4 6 0"/> <path d="M10.5 12h3"/> <path d="M11 16h2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M10 8q-1.5 6 2 13 3.5-7 2-13Z"/> <path d="M12 8V5"/> <path d="M9 5q3-4 6 0"/> <path d="M10.5 12h3"/> <path d="M11 16h2"/></g></svg>`,
    },
    broccoli: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.6 11.2C5.8 11 5 9.8 5 8.7A2.8 2.8 0 0 1 8.1 6c.8-1.5 2.1-2.3 3.9-2.3 1.9 0 3.3 1 4 2.6A2.7 2.7 0 0 1 19 8.9c0 1.3-.9 2.6-2.8 2.6-.8 1.6-2.6 2.7-4.2 2.7-1.6 0-3.5-1-4.4-3Z"/> <path d="M10 13.8V20c0 .6.4 1 1 1h2c.6 0 1-.4 1-1v-6.2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7.6 11.2C5.8 11 5 9.8 5 8.7A2.8 2.8 0 0 1 8.1 6c.8-1.5 2.1-2.3 3.9-2.3 1.9 0 3.3 1 4 2.6A2.7 2.7 0 0 1 19 8.9c0 1.3-.9 2.6-2.8 2.6-.8 1.6-2.6 2.7-4.2 2.7-1.6 0-3.5-1-4.4-3Z"/> <path d="M10 13.8V20c0 .6.4 1 1 1h2c.6 0 1-.4 1-1v-6.2"/></g></svg>`,
    },
    tomato: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 6c4 0 7 3.1 7 7s-3 7-7 7-7-3.1-7-7 3-7 7-7Z"/> <path d="M12 6c.6-1.2 1.6-2 3-2.3-.6 1.2-1.4 2-2.6 2.4 1.4-.2 2.6.3 3.6 1.4-1.6.1-2.9-.4-4-.9-1.1.5-2.4 1-4 .9 1-1.1 2.2-1.6 3.6-1.4-1.2-.4-2-.9-2.6-2.4 1.4.3 2.4 1.1 3 2.3Z"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 6c4 0 7 3.1 7 7s-3 7-7 7-7-3.1-7-7 3-7 7-7Z"/> <path d="M12 6c.6-1.2 1.6-2 3-2.3-.6 1.2-1.4 2-2.6 2.4 1.4-.2 2.6.3 3.6 1.4-1.6.1-2.9-.4-4-.9-1.1.5-2.4 1-4 .9 1-1.1 2.2-1.6 3.6-1.4-1.2-.4-2-.9-2.6-2.4 1.4.3 2.4 1.1 3 2.3Z"/></g></svg>`,
    },
    pepper: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9.2 7.2c-1.8.7-3.2 2.5-3.2 5.6 0 4.9 2.9 8.2 6 8.2s6-3.3 6-8.2c0-3.1-1.4-4.9-3.2-5.6-.7 1-1.7 1.6-2.8 1.6S9.9 8.2 9.2 7.2Z"/> <path d="M12 3c1.4 0 2.5 1.1 2.5 2.5 0 .7-.2 1.2-.6 1.7"/> <path d="M9.7 4.8c.7.4 1.4.6 2.3.6s1.6-.2 2.3-.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M9.2 7.2c-1.8.7-3.2 2.5-3.2 5.6 0 4.9 2.9 8.2 6 8.2s6-3.3 6-8.2c0-3.1-1.4-4.9-3.2-5.6-.7 1-1.7 1.6-2.8 1.6S9.9 8.2 9.2 7.2Z"/> <path d="M12 3c1.4 0 2.5 1.1 2.5 2.5 0 .7-.2 1.2-.6 1.7"/> <path d="M9.7 4.8c.7.4 1.4.6 2.3.6s1.6-.2 2.3-.6"/></g></svg>`,
    },
    onion: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4c-3.2 2.6-6 5.6-6 9.1A6 6 0 0 0 12 19a6 6 0 0 0 6-5.9c0-3.5-2.8-6.5-6-9.1Z"/> <path d="M12 4c.6 1.3 1.6 2.2 2.8 3"/> <path d="M9.8 8.6c-.7 2.2-.7 5.2 0 8"/> <path d="M14.2 8.6c.7 2.2.7 5.2 0 8"/> <path d="M10.2 19.2c-.7 1.2-1.4 1.8-2.2 2M13.8 19.2c.7 1.2 1.4 1.8 2.2 2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 4c-3.2 2.6-6 5.6-6 9.1A6 6 0 0 0 12 19a6 6 0 0 0 6-5.9c0-3.5-2.8-6.5-6-9.1Z"/> <path d="M12 4c.6 1.3 1.6 2.2 2.8 3"/> <path d="M9.8 8.6c-.7 2.2-.7 5.2 0 8"/> <path d="M14.2 8.6c.7 2.2.7 5.2 0 8"/> <path d="M10.2 19.2c-.7 1.2-1.4 1.8-2.2 2M13.8 19.2c.7 1.2 1.4 1.8 2.2 2"/></g></svg>`,
    },
    mushroom: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 11c0-4.1 3.1-7 6-7s6 2.9 6 7c0 1.4-1.2 2.5-2.6 2.5H8.6C7.2 13.5 6 12.4 6 11Z"/> <path d="M10 13.5c-.7 2.7-.4 6 2 6s2.7-3.3 2-6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 11c0-4.1 3.1-7 6-7s6 2.9 6 7c0 1.4-1.2 2.5-2.6 2.5H8.6C7.2 13.5 6 12.4 6 11Z"/> <path d="M10 13.5c-.7 2.7-.4 6 2 6s2.7-3.3 2-6"/></g></svg>`,
    },
    corn: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3c3.3 0 5.5 2.7 5.5 7.2v3.6c0 4.6-2.2 7.2-5.5 7.2s-5.5-2.6-5.5-7.2v-3.6C6.5 5.7 8.7 3 12 3Z"/> <path d="M9 7.2c.7.6 1.6.6 2.3 0 .7-.6 1.6-.6 2.3 0 .7.6 1.6.6 2.3 0"/> <path d="M9 10.3c.7.6 1.6.6 2.3 0 .7-.6 1.6-.6 2.3 0 .7.6 1.6.6 2.3 0"/> <path d="M7.2 18.6c1.6-.2 2.6-1 3.3-2.2M16.8 18.6c-1.6-.2-2.6-1-3.3-2.2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 3c3.3 0 5.5 2.7 5.5 7.2v3.6c0 4.6-2.2 7.2-5.5 7.2s-5.5-2.6-5.5-7.2v-3.6C6.5 5.7 8.7 3 12 3Z"/> <path d="M9 7.2c.7.6 1.6.6 2.3 0 .7-.6 1.6-.6 2.3 0 .7.6 1.6.6 2.3 0"/> <path d="M9 10.3c.7.6 1.6.6 2.3 0 .7-.6 1.6-.6 2.3 0 .7.6 1.6.6 2.3 0"/> <path d="M7.2 18.6c1.6-.2 2.6-1 3.3-2.2M16.8 18.6c-1.6-.2-2.6-1-3.3-2.2"/></g></svg>`,
    },
    apple: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 6.528V3a1 1 0 0 1 1-1h0" /> <path d="M18.237 21A15 15 0 0 0 22 11a6 6 0 0 0-10-4.472A6 6 0 0 0 2 11a15.1 15.1 0 0 0 3.763 10 3 3 0 0 0 3.648.648 5.5 5.5 0 0 1 5.178 0A3 3 0 0 0 18.237 21" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 6.528V3a1 1 0 0 1 1-1h0" /> <path d="M18.237 21A15 15 0 0 0 22 11a6 6 0 0 0-10-4.472A6 6 0 0 0 2 11a15.1 15.1 0 0 0 3.763 10 3 3 0 0 0 3.648.648 5.5 5.5 0 0 1 5.178 0A3 3 0 0 0 18.237 21" /></g></svg>`,
    },
    lemon: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.66 17.67a1.08 1.08 0 0 1-.04 1.6A12 12 0 0 1 4.73 2.38a1.1 1.1 0 0 1 1.61-.04z" /> <path d="M19.65 15.66A8 8 0 0 1 8.35 4.34" /> <path d="m14 10-5.5 5.5" /> <path d="M14 17.85V10H6.15" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M21.66 17.67a1.08 1.08 0 0 1-.04 1.6A12 12 0 0 1 4.73 2.38a1.1 1.1 0 0 1 1.61-.04z" /> <path d="M19.65 15.66A8 8 0 0 1 8.35 4.34" /> <path d="m14 10-5.5 5.5" /> <path d="M14 17.85V10H6.15" /></g></svg>`,
    },
    avocado: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3C8.4 3 6 6.1 6 10.1c0 2.7 1 4.7 2.4 6.6C9.9 18.8 10.6 21 12 21s2.1-2.2 3.6-4.3c1.4-1.9 2.4-3.9 2.4-6.6C18 6.1 15.6 3 12 3Z"/> <circle cx="12" cy="13" r="2.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 3C8.4 3 6 6.1 6 10.1c0 2.7 1 4.7 2.4 6.6C9.9 18.8 10.6 21 12 21s2.1-2.2 3.6-4.3c1.4-1.9 2.4-3.9 2.4-6.6C18 6.1 15.6 3 12 3Z"/> <circle cx="12" cy="13" r="2.6"/></g></svg>`,
    },
    garlic: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4c-2.7 1.8-5.5 4.6-5.5 8.2A6.5 6.5 0 0 0 12 19a6.5 6.5 0 0 0 5.5-6.8c0-3.6-2.8-6.4-5.5-8.2Z"/> <path d="M12 4V2"/> <path d="M10.2 8.6c-.8 2.1-.8 5.1 0 8"/> <path d="M13.8 8.6c.8 2.1.8 5.1 0 8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 4c-2.7 1.8-5.5 4.6-5.5 8.2A6.5 6.5 0 0 0 12 19a6.5 6.5 0 0 0 5.5-6.8c0-3.6-2.8-6.4-5.5-8.2Z"/> <path d="M12 4V2"/> <path d="M10.2 8.6c-.8 2.1-.8 5.1 0 8"/> <path d="M13.8 8.6c.8 2.1.8 5.1 0 8"/></g></svg>`,
    },
    leafy: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21c-3-1-6-4-7-8C4 9 5 5 8 3c2-1 3 0 4 1 1-1 2-2 4-1 3 2 4 6 3 10-1 4-4 7-7 8Z"/> <path d="M12 4v17"/> <path d="M8 9c2 1 3 2 4 4"/> <path d="M16 9c-2 1-3 2-4 4"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 21c-3-1-6-4-7-8C4 9 5 5 8 3c2-1 3 0 4 1 1-1 2-2 4-1 3 2 4 6 3 10-1 4-4 7-7 8Z"/> <path d="M12 4v17"/> <path d="M8 9c2 1 3 2 4 4"/> <path d="M16 9c-2 1-3 2-4 4"/></g></svg>`,
    },
    // --- Dairy & Pantry ---
    cheese: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 18.8V9.4c0-.8.5-1.5 1.3-1.8l11.2-4c1.1-.4 2.5.4 2.5 1.7v13.5H5Z"/> <path d="M10 12h.01"/> <path d="M14.5 14.2h.01"/> <path d="M16.8 10.4h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5 18.8V9.4c0-.8.5-1.5 1.3-1.8l11.2-4c1.1-.4 2.5.4 2.5 1.7v13.5H5Z"/> <path d="M10 12h.01"/> <path d="M14.5 14.2h.01"/> <path d="M16.8 10.4h.01"/></g></svg>`,
    },
    butter: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 11.2c0-1.2 1-2.2 2.2-2.2h11.6c1.2 0 2.2 1 2.2 2.2v6.6c0 1.2-1 2.2-2.2 2.2H6.7c-1.2 0-2.2-1-2.2-2.2v-6.6Z"/> <path d="M4.5 11.5h5.2c1.1 0 2-.9 2-2V9"/> <path d="M11.7 9h7.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M4.5 11.2c0-1.2 1-2.2 2.2-2.2h11.6c1.2 0 2.2 1 2.2 2.2v6.6c0 1.2-1 2.2-2.2 2.2H6.7c-1.2 0-2.2-1-2.2-2.2v-6.6Z"/> <path d="M4.5 11.5h5.2c1.1 0 2-.9 2-2V9"/> <path d="M11.7 9h7.6"/></g></svg>`,
    },
    milk: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 8V5c0-1 1-2 4-2s4 1 4 2v3"/> <path d="M8 8c-1 .5-2 1.5-2 3v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-8c0-1.5-1-2.5-2-3"/> <path d="M6 15c2-1 4-.5 6 0s4 1 6 0"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 8V5c0-1 1-2 4-2s4 1 4 2v3"/> <path d="M8 8c-1 .5-2 1.5-2 3v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-8c0-1.5-1-2.5-2-3"/> <path d="M6 15c2-1 4-.5 6 0s4 1 6 0"/></g></svg>`,
    },
    'olive-oil': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2h4v3c0 .6.3 1.1.7 1.5l.6.6c.4.4.7.9.7 1.5V19c0 2-1.6 3-4 3s-4-1-4-3V8.6c0-.6.3-1.1.7-1.5l.6-.6c.4-.4.7-.9.7-1.5V2Z"/> <path d="M9.4 13.8c1.2-1.6 3.2-1.9 4.7-.9 1.4 1 1.6 2.7.4 3.8-1.5 1.4-3.9 1.1-5-.5"/> <path d="M14.8 12.6c1.3-.2 2.4.2 3.2 1"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M10 2h4v3c0 .6.3 1.1.7 1.5l.6.6c.4.4.7.9.7 1.5V19c0 2-1.6 3-4 3s-4-1-4-3V8.6c0-.6.3-1.1.7-1.5l.6-.6c.4-.4.7-.9.7-1.5V2Z"/> <path d="M9.4 13.8c1.2-1.6 3.2-1.9 4.7-.9 1.4 1 1.6 2.7.4 3.8-1.5 1.4-3.9 1.1-5-.5"/> <path d="M14.8 12.6c1.3-.2 2.4.2 3.2 1"/></g></svg>`,
    },
    honey: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3h8v3c0 .6.3 1.1.7 1.5l.3.3c.6.6 1 1.4 1 2.2v8.7c0 1.7-1.6 3-6 3s-6-1.3-6-3v-8.7c0-.8.4-1.6 1-2.2l.3-.3C7.7 7.1 8 6.6 8 6V3Z"/> <path d="M6.8 10h10.4"/> <path d="M7 7.6h10"/> <path d="M5 8.6h14"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 3h8v3c0 .6.3 1.1.7 1.5l.3.3c.6.6 1 1.4 1 2.2v8.7c0 1.7-1.6 3-6 3s-6-1.3-6-3v-8.7c0-.8.4-1.6 1-2.2l.3-.3C7.7 7.1 8 6.6 8 6V3Z"/> <path d="M6.8 10h10.4"/> <path d="M7 7.6h10"/> <path d="M5 8.6h14"/></g></svg>`,
    },
    beans: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4c3.5 0 6.5 2.5 6.5 6 0 4.5-3 8-6.5 8s-6.5-3.5-6.5-8c0-3.5 3-6 6.5-6Z"/><path d="M12 5c-1 2.5-1 5 0 7.5 1 2.5 1.2 4 .5 5.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 4c3.5 0 6.5 2.5 6.5 6 0 4.5-3 8-6.5 8s-6.5-3.5-6.5-8c0-3.5 3-6 6.5-6Z"/><path d="M12 5c-1 2.5-1 5 0 7.5 1 2.5 1.2 4 .5 5.5"/></g></svg>`,
    },
    nuts: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="8" rx="3.5" ry="4"/><ellipse cx="12" cy="16" rx="3.5" ry="4"/><path d="M8.5 12h7"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><ellipse cx="12" cy="8" rx="3.5" ry="4"/><ellipse cx="12" cy="16" rx="3.5" ry="4"/><path d="M8.5 12h7"/></g></svg>`,
    },
    chocolate: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="6" width="14" height="12" rx="1.5"/><path d="M5 10h14"/><path d="M5 14h14"/><path d="M9.5 6v12"/><path d="M14.5 6v12"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><rect x="5" y="6" width="14" height="12" rx="1.5"/><path d="M5 10h14"/><path d="M5 14h14"/><path d="M9.5 6v12"/><path d="M14.5 6v12"/></g></svg>`,
    },
    flour: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 4h8c.8 0 1.4.6 1.4 1.4v1.2c0 .5-.3 1-.7 1.2l-.5.3c.9 1.7 1.8 3.9 1.8 6.3 0 4.1-2.4 6.6-6 6.6s-6-2.5-6-6.6c0-2.4.9-4.6 1.8-6.3l-.5-.3c-.4-.2-.7-.7-.7-1.2V5.4C6.6 4.6 7.2 4 8 4Z"/> <path d="M15.6 12.6l2.8-1.6"/> <path d="M12 13.2c1.3 0 2.4.4 3.4 1.2-1.1 1-2.3 1.5-3.4 1.5s-2.3-.5-3.4-1.5c1-.8 2.1-1.2 3.4-1.2Z"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 4h8c.8 0 1.4.6 1.4 1.4v1.2c0 .5-.3 1-.7 1.2l-.5.3c.9 1.7 1.8 3.9 1.8 6.3 0 4.1-2.4 6.6-6 6.6s-6-2.5-6-6.6c0-2.4.9-4.6 1.8-6.3l-.5-.3c-.4-.2-.7-.7-.7-1.2V5.4C6.6 4.6 7.2 4 8 4Z"/> <path d="M15.6 12.6l2.8-1.6"/> <path d="M12 13.2c1.3 0 2.4.4 3.4 1.2-1.1 1-2.3 1.5-3.4 1.5s-2.3-.5-3.4-1.5c1-.8 2.1-1.2 3.4-1.2Z"/></g></svg>`,
    },
    vinegar: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2h4v2.2c0 .5.2 1 .6 1.3l1.2 1c.7.6 1.2 1.5 1.2 2.4V19c0 2-1.6 3-6 3s-6-1-6-3V8.9c0-.9.5-1.8 1.2-2.4l1.2-1c.4-.3.6-.8.6-1.3V2Z"/> <path d="M14.4 2h3.6c.6 0 1 .4 1 1v1.2c0 .4-.2.8-.6 1l-2.4 1.4"/> <path d="M6.8 11.2h10.4"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M10 2h4v2.2c0 .5.2 1 .6 1.3l1.2 1c.7.6 1.2 1.5 1.2 2.4V19c0 2-1.6 3-6 3s-6-1-6-3V8.9c0-.9.5-1.8 1.2-2.4l1.2-1c.4-.3.6-.8.6-1.3V2Z"/> <path d="M14.4 2h3.6c.6 0 1 .4 1 1v1.2c0 .4-.2.8-.6 1l-2.4 1.4"/> <path d="M6.8 11.2h10.4"/></g></svg>`,
    },
    // --- Dishes & Styles ---
    soup: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11h18"/> <path d="M4 11c0 5.5 3.5 9 8 9s8-3.5 8-9"/> <path d="M8.5 8Q9 6 8.5 4"/> <path d="M12 8Q12.5 6 12 4"/> <path d="M15.5 8Q16 6 15.5 4"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M3 11h18"/> <path d="M4 11c0 5.5 3.5 9 8 9s8-3.5 8-9"/> <path d="M8.5 8Q9 6 8.5 4"/> <path d="M12 8Q12.5 6 12 4"/> <path d="M15.5 8Q16 6 15.5 4"/></g></svg>`,
    },
    salad: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 21h10" /> <path d="M12 21a9 9 0 0 0 9-9H3a9 9 0 0 0 9 9Z" /> <path d="M11.38 12a2.4 2.4 0 0 1-.4-4.77 2.4 2.4 0 0 1 3.2-2.77 2.4 2.4 0 0 1 3.47-.63 2.4 2.4 0 0 1 3.37 3.37 2.4 2.4 0 0 1-1.1 3.7 2.51 2.51 0 0 1 .03 1.1" /> <path d="m13 12 4-4" /> <path d="M10.9 7.25A3.99 3.99 0 0 0 4 10c0 .73.2 1.41.54 2" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7 21h10" /> <path d="M12 21a9 9 0 0 0 9-9H3a9 9 0 0 0 9 9Z" /> <path d="M11.38 12a2.4 2.4 0 0 1-.4-4.77 2.4 2.4 0 0 1 3.2-2.77 2.4 2.4 0 0 1 3.47-.63 2.4 2.4 0 0 1 3.37 3.37 2.4 2.4 0 0 1-1.1 3.7 2.51 2.51 0 0 1 .03 1.1" /> <path d="m13 12 4-4" /> <path d="M10.9 7.25A3.99 3.99 0 0 0 4 10c0 .73.2 1.41.54 2" /></g></svg>`,
    },
    pizza: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6q9-3 18 0"/> <path d="M3 6l9 16 9-16"/> <path d="M3 6q9 2 18 0"/> <circle cx="10" cy="10" r="1.2" fill="currentColor"/> <circle cx="15" cy="11" r="1.2" fill="currentColor"/> <circle cx="11.5" cy="15" r="1.2" fill="currentColor"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M3 6q9-3 18 0"/> <path d="M3 6l9 16 9-16"/> <path d="M3 6q9 2 18 0"/> <circle cx="10" cy="10" r="1.2" fill="currentColor"/> <circle cx="15" cy="11" r="1.2" fill="currentColor"/> <circle cx="11.5" cy="15" r="1.2" fill="currentColor"/></g></svg>`,
    },
    taco: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 17c.5-6 3.8-10 8-10s7.5 4 8 10"/><path d="M7 14c1.5 1 3.5 1 5 0s3.5-1 5 0"/><path d="M6 17h12"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M4 17c.5-6 3.8-10 8-10s7.5 4 8 10"/><path d="M7 14c1.5 1 3.5 1 5 0s3.5-1 5 0"/><path d="M6 17h12"/></g></svg>`,
    },
    burger: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16H4a2 2 0 1 1 0-4h16a2 2 0 1 1 0 4h-4.25" /> <path d="M5 12a2 2 0 0 1-2-2 9 7 0 0 1 18 0 2 2 0 0 1-2 2" /> <path d="M5 16a2 2 0 0 0-2 2 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 2 2 0 0 0-2-2q0 0 0 0" /> <path d="m6.67 12 6.13 4.6a2 2 0 0 0 2.8-.4l3.15-4.2" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 16H4a2 2 0 1 1 0-4h16a2 2 0 1 1 0 4h-4.25" /> <path d="M5 12a2 2 0 0 1-2-2 9 7 0 0 1 18 0 2 2 0 0 1-2 2" /> <path d="M5 16a2 2 0 0 0-2 2 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 2 2 0 0 0-2-2q0 0 0 0" /> <path d="m6.67 12 6.13 4.6a2 2 0 0 0 2.8-.4l3.15-4.2" /></g></svg>`,
    },
    bowl: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 12.5c0 5 3.1 8.5 6 8.5s6-3.5 6-8.5"/> <path d="M6 12.5Q12 9 18 12.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 12.5c0 5 3.1 8.5 6 8.5s6-3.5 6-8.5"/> <path d="M6 12.5Q12 9 18 12.5"/></g></svg>`,
    },
    sandwich: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m2.37 11.223 8.372-6.777a2 2 0 0 1 2.516 0l8.371 6.777" /> <path d="M21 15a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-5.25" /> <path d="M3 15a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h9" /> <path d="m6.67 15 6.13 4.6a2 2 0 0 0 2.8-.4l3.15-4.2" /> <rect width="20" height="4" x="2" y="11" rx="1" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="m2.37 11.223 8.372-6.777a2 2 0 0 1 2.516 0l8.371 6.777" /> <path d="M21 15a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-5.25" /> <path d="M3 15a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h9" /> <path d="m6.67 15 6.13 4.6a2 2 0 0 0 2.8-.4l3.15-4.2" /> <rect width="20" height="4" x="2" y="11" rx="1" /></g></svg>`,
    },
    sushi: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></g></svg>`,
    },
    curry: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.2 18 13"/> <path d="M17.2 10.2c1.8.7 2.9 2.2 2.9 4 0 2.4-1.9 4.4-4.6 4.9"/> <path d="M10.2 6.2c1.2 1.2 1.1 2.5.1 3.6-1 1.2-1 2.4.2 3.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.2 18 13"/> <path d="M17.2 10.2c1.8.7 2.9 2.2 2.9 4 0 2.4-1.9 4.4-4.6 4.9"/> <path d="M10.2 6.2c1.2 1.2 1.1 2.5.1 3.6-1 1.2-1 2.4.2 3.6"/></g></svg>`,
    },
    stew: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.2 12.2c0-2.8 2.8-4.7 5.8-4.7s5.8 1.9 5.8 4.7v6.1c0 2.3-2.6 3.7-5.8 3.7s-5.8-1.4-5.8-3.7v-6.1Z"/> <path d="M7 10.6h10"/> <path d="M9.5 6.2h7.8"/> <path d="M12.8 3.6c1.2 1.1 1.1 2.3.1 3.3-1 1.1-1 2.2.2 3.3"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.2 12.2c0-2.8 2.8-4.7 5.8-4.7s5.8 1.9 5.8 4.7v6.1c0 2.3-2.6 3.7-5.8 3.7s-5.8-1.4-5.8-3.7v-6.1Z"/> <path d="M7 10.6h10"/> <path d="M9.5 6.2h7.8"/> <path d="M12.8 3.6c1.2 1.1 1.1 2.3.1 3.3-1 1.1-1 2.2.2 3.3"/></g></svg>`,
    },
    casserole: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 9.5h13c.8 0 1.5.7 1.5 1.5v7c0 .8-.7 1.5-1.5 1.5h-13C4.7 19.5 4 18.8 4 18v-7c0-.8.7-1.5 1.5-1.5Z"/> <path d="M6 9.5c1.2-1.8 2.6-1.8 3.8 0 1.2 1.8 2.6 1.8 3.8 0 1.2-1.8 2.6-1.8 3.8 0"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 9.5h13c.8 0 1.5.7 1.5 1.5v7c0 .8-.7 1.5-1.5 1.5h-13C4.7 19.5 4 18.8 4 18v-7c0-.8.7-1.5 1.5-1.5Z"/> <path d="M6 9.5c1.2-1.8 2.6-1.8 3.8 0 1.2 1.8 2.6 1.8 3.8 0 1.2-1.8 2.6-1.8 3.8 0"/></g></svg>`,
    },
    wrap: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8c0-1.1 2.7-2 6-2s6 .9 6 2v8c0 1.1-2.7 2-6 2s-6-.9-6-2V8Z"/><path d="M6 8c0 1.1 2.7 2 6 2s6-.9 6-2"/><path d="M12 14c-1.5 0-2.5.8-2.5 2s1 2 2.5 2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 8c0-1.1 2.7-2 6-2s6 .9 6 2v8c0 1.1-2.7 2-6 2s-6-.9-6-2V8Z"/><path d="M6 8c0 1.1 2.7 2 6 2s6-.9 6-2"/><path d="M12 14c-1.5 0-2.5.8-2.5 2s1 2 2.5 2"/></g></svg>`,
    },
    risotto: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.5 18 13"/> <path d="M16.4 9.8c1.7-1.8 3.1-2.7 4.6-2.9"/> <path d="M10 14.2h.01"/> <path d="M13.3 15h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.5 18 13"/> <path d="M16.4 9.8c1.7-1.8 3.1-2.7 4.6-2.9"/> <path d="M10 14.2h.01"/> <path d="M13.3 15h.01"/></g></svg>`,
    },
    stirfry: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.2 14.4c2.1-4.3 4.9-6.4 6.8-6.4s4.7 2.1 6.8 6.4c-2.1 3.8-5.2 6.2-6.8 6.2s-4.7-2.4-6.8-6.2Z"/> <path d="M7.2 8.6l-1.8-3.2"/> <path d="M10.2 11.8h.01"/> <path d="M13 10.8h.01"/> <path d="M15.2 13.2h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.2 14.4c2.1-4.3 4.9-6.4 6.8-6.4s4.7 2.1 6.8 6.4c-2.1 3.8-5.2 6.2-6.8 6.2s-4.7-2.4-6.8-6.2Z"/> <path d="M7.2 8.6l-1.8-3.2"/> <path d="M10.2 11.8h.01"/> <path d="M13 10.8h.01"/> <path d="M15.2 13.2h.01"/></g></svg>`,
    },
    dumpling: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 14.6c1.6-3.8 4.2-6 7.5-6s5.9 2.2 7.5 6c-1.4 3.2-4.4 5.4-7.5 5.4s-6.1-2.2-7.5-5.4Z"/> <path d="M9 12.6c.9 1.2 1.8 1.8 3 1.8s2.1-.6 3-1.8"/> <path d="M12 10.2c.4.9 1 1.5 1.8 1.8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.5 14.6c1.6-3.8 4.2-6 7.5-6s5.9 2.2 7.5 6c-1.4 3.2-4.4 5.4-7.5 5.4s-6.1-2.2-7.5-5.4Z"/> <path d="M9 12.6c.9 1.2 1.8 1.8 3 1.8s2.1-.6 3-1.8"/> <path d="M12 10.2c.4.9 1 1.5 1.8 1.8"/></g></svg>`,
    },
    // --- Cooking Methods ---
    grill: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 10.5h13c.9 0 1.5.7 1.5 1.5s-.6 1.5-1.5 1.5h-13C4.6 13.5 4 12.8 4 12s.6-1.5 1.5-1.5Z"/> <path d="M7 10.6v2.8M10 10.6v2.8M13 10.6v2.8M16 10.6v2.8"/> <path d="M8.3 14.6c.6 1.7-.1 3.2-1.8 4.2 2.2.2 3.7-.6 4.5-2.1.6 1.7-.1 3.2-1.8 4.2 2.2.2 3.7-.6 4.5-2.1.6 1.7-.1 3.2-1.8 4.2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 10.5h13c.9 0 1.5.7 1.5 1.5s-.6 1.5-1.5 1.5h-13C4.6 13.5 4 12.8 4 12s.6-1.5 1.5-1.5Z"/> <path d="M7 10.6v2.8M10 10.6v2.8M13 10.6v2.8M16 10.6v2.8"/> <path d="M8.3 14.6c.6 1.7-.1 3.2-1.8 4.2 2.2.2 3.7-.6 4.5-2.1.6 1.7-.1 3.2-1.8 4.2 2.2.2 3.7-.6 4.5-2.1.6 1.7-.1 3.2-1.8 4.2"/></g></svg>`,
    },
    oven: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 4.5h11c1.1 0 2 .9 2 2v13c0 1.1-.9 2-2 2h-11c-1.1 0-2-.9-2-2v-13c0-1.1.9-2 2-2Z"/> <path d="M8 10h8c.6 0 1 .4 1 1v6c0 .6-.4 1-1 1H8c-.6 0-1-.4-1-1v-6c0-.6.4-1 1-1Z"/> <path d="M9.5 7h.01M12 7h.01M14.5 7h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.5 4.5h11c1.1 0 2 .9 2 2v13c0 1.1-.9 2-2 2h-11c-1.1 0-2-.9-2-2v-13c0-1.1.9-2 2-2Z"/> <path d="M8 10h8c.6 0 1 .4 1 1v6c0 .6-.4 1-1 1H8c-.6 0-1-.4-1-1v-6c0-.6.4-1 1-1Z"/> <path d="M9.5 7h.01M12 7h.01M14.5 7h.01"/></g></svg>`,
    },
    stovetop: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 16h20"/> <path d="M5 16V9a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v7"/> <path d="M4 8h2"/> <path d="M15 8h2"/> <path d="M9 6V4"/> <path d="M11 6V3"/> <path d="M8 19c.5-1 1-1.5 2-1.5S12 18 12 19s1 1.5 2 1.5 1.5-.5 2-1.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M2 16h20"/> <path d="M5 16V9a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v7"/> <path d="M4 8h2"/> <path d="M15 8h2"/> <path d="M9 6V4"/> <path d="M11 6V3"/> <path d="M8 19c.5-1 1-1.5 2-1.5S12 18 12 19s1 1.5 2 1.5 1.5-.5 2-1.5"/></g></svg>`,
    },
    slowcooker: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 11.2c0-3 2.7-5.2 6-5.2s6 2.2 6 5.2V18c0 2.6-2.7 4-6 4s-6-1.4-6-4v-6.8Z"/> <path d="M7.5 10h9"/> <path d="M13 16.2h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 11.2c0-3 2.7-5.2 6-5.2s6 2.2 6 5.2V18c0 2.6-2.7 4-6 4s-6-1.4-6-4v-6.8Z"/> <path d="M7.5 10h9"/> <path d="M13 16.2h.01"/></g></svg>`,
    },
    smoke: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13.2c0-3.3 2.7-6.2 6-6.2s6 2.9 6 6.2V19c0 2.1-2.7 3.4-6 3.4S6 21.1 6 19v-5.8Z"/> <path d="M8 12h8"/> <path d="M9.2 3.8c1.3 1.1 1.2 2.4.1 3.5-1 1.2-1 2.3.2 3.4"/> <path d="M14.2 3.5c1.4 1.2 1.3 2.6.1 3.8-1.1 1.2-1.1 2.5.2 3.8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13.2c0-3.3 2.7-6.2 6-6.2s6 2.9 6 6.2V19c0 2.1-2.7 3.4-6 3.4S6 21.1 6 19v-5.8Z"/> <path d="M8 12h8"/> <path d="M9.2 3.8c1.3 1.1 1.2 2.4.1 3.5-1 1.2-1 2.3.2 3.4"/> <path d="M14.2 3.5c1.4 1.2 1.3 2.6.1 3.8-1.1 1.2-1.1 2.5.2 3.8"/></g></svg>`,
    },
    steam: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.2 12.2c0-2.8 2.8-4.7 5.8-4.7s5.8 1.9 5.8 4.7v6.1c0 2.3-2.6 3.7-5.8 3.7s-5.8-1.4-5.8-3.7v-6.1Z"/> <path d="M8 12.2h8"/> <path d="M9.2 11.2h.01M12 11.2h.01M14.8 11.2h.01"/> <path d="M10 3.8c1.2 1.1 1.1 2.3.1 3.3-1 1.1-1 2.2.2 3.3"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.2 12.2c0-2.8 2.8-4.7 5.8-4.7s5.8 1.9 5.8 4.7v6.1c0 2.3-2.6 3.7-5.8 3.7s-5.8-1.4-5.8-3.7v-6.1Z"/> <path d="M8 12.2h8"/> <path d="M9.2 11.2h.01M12 11.2h.01M14.8 11.2h.01"/> <path d="M10 3.8c1.2 1.1 1.1 2.3.1 3.3-1 1.1-1 2.2.2 3.3"/></g></svg>`,
    },
    fry: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 14.5h10.8c1.2 0 2.2.9 2.2 2.1 0 1.7-1.7 3.2-7.6 3.2S3.3 18.3 3.3 16.6c0-1.2 1-2.1 2.2-2.1Z"/> <path d="M16.2 14.6l3.6-2.1"/> <path d="M9.2 10.6c.7 1 .6 2-.3 2.9"/> <path d="M12.4 9.6c.9 1.2.8 2.4-.3 3.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 14.5h10.8c1.2 0 2.2.9 2.2 2.1 0 1.7-1.7 3.2-7.6 3.2S3.3 18.3 3.3 16.6c0-1.2 1-2.1 2.2-2.1Z"/> <path d="M16.2 14.6l3.6-2.1"/> <path d="M9.2 10.6c.7 1 .6 2-.3 2.9"/> <path d="M12.4 9.6c.9 1.2.8 2.4-.3 3.5"/></g></svg>`,
    },
    roast: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 10.2h13c.8 0 1.5.7 1.5 1.5V19c0 .8-.7 1.5-1.5 1.5h-13C4.7 20.5 4 19.8 4 19v-7.3c0-.8.7-1.5 1.5-1.5Z"/> <path d="M8.2 14.2c1.1-2.6 2.8-4.1 3.8-4.1s2.7 1.5 3.8 4.1c-1.1 2.2-2.8 3.6-3.8 3.6s-2.7-1.4-3.8-3.6Z"/> <path d="M7 12.2c-.8.3-1.3 1-1.3 1.8s.5 1.5 1.3 1.8"/> <path d="M17 12.2c.8.3 1.3 1 1.3 1.8s-.5 1.5-1.3 1.8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 10.2h13c.8 0 1.5.7 1.5 1.5V19c0 .8-.7 1.5-1.5 1.5h-13C4.7 20.5 4 19.8 4 19v-7.3c0-.8.7-1.5 1.5-1.5Z"/> <path d="M8.2 14.2c1.1-2.6 2.8-4.1 3.8-4.1s2.7 1.5 3.8 4.1c-1.1 2.2-2.8 3.6-3.8 3.6s-2.7-1.4-3.8-3.6Z"/> <path d="M7 12.2c-.8.3-1.3 1-1.3 1.8s.5 1.5 1.3 1.8"/> <path d="M17 12.2c.8.3 1.3 1 1.3 1.8s-.5 1.5-1.3 1.8"/></g></svg>`,
    },
    bake: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 5.5h11c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2h-11c-1.1 0-2-.9-2-2v-10c0-1.1.9-2 2-2Z"/> <path d="M8 9h8c.6 0 1 .4 1 1v5c0 .6-.4 1-1 1H8c-.6 0-1-.4-1-1v-5c0-.6.4-1 1-1Z"/> <path d="M8.6 11.4h6.8M8.6 13.2h6.8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.5 5.5h11c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2h-11c-1.1 0-2-.9-2-2v-10c0-1.1.9-2 2-2Z"/> <path d="M8 9h8c.6 0 1 .4 1 1v5c0 .6-.4 1-1 1H8c-.6 0-1-.4-1-1v-5c0-.6.4-1 1-1Z"/> <path d="M8.6 11.4h6.8M8.6 13.2h6.8"/></g></svg>`,
    },
    broil: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 15.5h10c.8 0 1.4.6 1.4 1.4v.6c0 1-1.2 1.8-6.4 1.8S5.6 18.5 5.6 17.5v-.6c0-.8.6-1.4 1.4-1.4Z"/> <path d="M9 4.5c1.8 1.4 1.9 3.1.4 4.7-1.2 1.3-1.1 2.6.2 3.8"/> <path d="M15 4.5c1.8 1.4 1.9 3.1.4 4.7-1.2 1.3-1.1 2.6.2 3.8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7 15.5h10c.8 0 1.4.6 1.4 1.4v.6c0 1-1.2 1.8-6.4 1.8S5.6 18.5 5.6 17.5v-.6c0-.8.6-1.4 1.4-1.4Z"/> <path d="M9 4.5c1.8 1.4 1.9 3.1.4 4.7-1.2 1.3-1.1 2.6.2 3.8"/> <path d="M15 4.5c1.8 1.4 1.9 3.1.4 4.7-1.2 1.3-1.1 2.6.2 3.8"/></g></svg>`,
    },
    saute: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 15h10.6c1.3 0 2.4.9 2.4 2.1 0 1.7-1.8 3.2-7.7 3.2S3.1 18.8 3.1 17.1c0-1.2 1.1-2.1 2.4-2.1Z"/> <path d="M16.2 15.1l3.6-2.1"/> <path d="M7.4 9.6c2.3-2.7 6.3-3.4 9.2-1.6 1.6 1 2.6 2.6 2.8 4.3"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 15h10.6c1.3 0 2.4.9 2.4 2.1 0 1.7-1.8 3.2-7.7 3.2S3.1 18.8 3.1 17.1c0-1.2 1.1-2.1 2.4-2.1Z"/> <path d="M16.2 15.1l3.6-2.1"/> <path d="M7.4 9.6c2.3-2.7 6.3-3.4 9.2-1.6 1.6 1 2.6 2.6 2.8 4.3"/></g></svg>`,
    },
    blender: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 3h6l1.6 11.2c.2 1.5-.9 2.8-2.4 2.8h-4.4c-1.5 0-2.6-1.3-2.4-2.8L9 3Z"/> <path d="M8 17h8v4c0 .6-.4 1-1 1H9c-.6 0-1-.4-1-1v-4Z"/> <path d="M10 7h4"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M9 3h6l1.6 11.2c.2 1.5-.9 2.8-2.4 2.8h-4.4c-1.5 0-2.6-1.3-2.4-2.8L9 3Z"/> <path d="M8 17h8v4c0 .6-.4 1-1 1H9c-.6 0-1-.4-1-1v-4Z"/> <path d="M10 7h4"/></g></svg>`,
    },
    // --- Meal Types ---
    breakfast: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10" cy="13" r="6"/><circle cx="10" cy="13" r="2.2" fill="currentColor" fill-opacity="0.3"/><path d="M17 7c1.5 1 2-1 3.5 0"/><path d="M17 10c1.5 1 2-1 3.5 0"/><path d="M17 13c1.5 1 2-1 3.5 0"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><circle cx="10" cy="13" r="6"/><circle cx="10" cy="13" r="2.2" fill="currentColor" fill-opacity="0.3"/><path d="M17 7c1.5 1 2-1 3.5 0"/><path d="M17 10c1.5 1 2-1 3.5 0"/><path d="M17 13c1.5 1 2-1 3.5 0"/></g></svg>`,
    },
    brunch: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 6h10c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H7c-1.1 0-2-.9-2-2V8c0-1.1.9-2 2-2Z"/> <path d="M9 6v14M12 6v14M15 6v14"/> <path d="M6 10h14M6 14h14M6 18h14"/> <path d="M7.6 9.2c2.4 1.2 4.1 1.6 6 .8 1.7-.7 3.2-.6 5 .6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7 6h10c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H7c-1.1 0-2-.9-2-2V8c0-1.1.9-2 2-2Z"/> <path d="M9 6v14M12 6v14M15 6v14"/> <path d="M6 10h14M6 14h14M6 18h14"/> <path d="M7.6 9.2c2.4 1.2 4.1 1.6 6 .8 1.7-.7 3.2-.6 5 .6"/></g></svg>`,
    },
    lunch: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.2 12.2c0-2.9 2.6-5.2 5.8-5.2s5.8 2.3 5.8 5.2c-1.7 1.1-4.1 1.8-5.8 1.8s-4.1-.7-5.8-1.8Z"/> <path d="M6.6 15.2c1.8 1.1 3.8 1.8 5.4 1.8s3.6-.7 5.4-1.8c0 2.8-2.5 5-5.4 5s-5.4-2.2-5.4-5Z"/> <path d="M7.4 13.6c1.2.3 2.6.5 4.6.5s3.4-.2 4.6-.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.2 12.2c0-2.9 2.6-5.2 5.8-5.2s5.8 2.3 5.8 5.2c-1.7 1.1-4.1 1.8-5.8 1.8s-4.1-.7-5.8-1.8Z"/> <path d="M6.6 15.2c1.8 1.1 3.8 1.8 5.4 1.8s3.6-.7 5.4-1.8c0 2.8-2.5 5-5.4 5s-5.4-2.2-5.4-5Z"/> <path d="M7.4 13.6c1.2.3 2.6.5 4.6.5s3.4-.2 4.6-.5"/></g></svg>`,
    },
    dinner: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.8 18.2c1.6 4.2 12.8 4.2 14.4 0"/> <path d="M6.5 16.2c.6-4.4 3.2-7.2 5.5-7.2s4.9 2.8 5.5 7.2"/> <path d="M11.2 5.2h1.6"/> <path d="M12.8 6.4c1.2 1.1 1.1 2.3.1 3.3"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M4.8 18.2c1.6 4.2 12.8 4.2 14.4 0"/> <path d="M6.5 16.2c.6-4.4 3.2-7.2 5.5-7.2s4.9 2.8 5.5 7.2"/> <path d="M11.2 5.2h1.6"/> <path d="M12.8 6.4c1.2 1.1 1.1 2.3.1 3.3"/></g></svg>`,
    },
    snack: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.6 18 13"/> <path d="M8.3 12.2l2-1.2 1.1 2.2-2 1.2-1.1-2.2Z"/> <path d="M13 11.2l2.2-.8.7 2.3-2.2.8-.7-2.3Z"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.6 18 13"/> <path d="M8.3 12.2l2-1.2 1.1 2.2-2 1.2-1.1-2.2Z"/> <path d="M13 11.2l2.2-.8.7 2.3-2.2.8-.7-2.3Z"/></g></svg>`,
    },
    appetizer: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 15.2c1.6 4.2 11.4 4.2 13 0"/> <path d="M8 7.4l2.4 4.8M12 6.8l1.2 5.2M16 7.8l-2 4.6"/> <path d="M9.6 11.4h.01M12 11.6h.01M14.4 11.4h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 15.2c1.6 4.2 11.4 4.2 13 0"/> <path d="M8 7.4l2.4 4.8M12 6.8l1.2 5.2M16 7.8l-2 4.6"/> <path d="M9.6 11.4h.01M12 11.6h.01M14.4 11.4h.01"/></g></svg>`,
    },
    dessert: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 18.5c1.6 3.2 9.4 3.2 11 0"/> <path d="M7.5 18.2l3.8-11.2c.2-.7 1.2-.7 1.4 0l3.8 11.2H7.5Z"/> <path d="M9.3 13h5.4"/> <path d="M9.9 10.7h4.2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.5 18.5c1.6 3.2 9.4 3.2 11 0"/> <path d="M7.5 18.2l3.8-11.2c.2-.7 1.2-.7 1.4 0l3.8 11.2H7.5Z"/> <path d="M9.3 13h5.4"/> <path d="M9.9 10.7h4.2"/></g></svg>`,
    },
    cocktail: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 22h8" /> <path d="M12 11v11" /> <path d="m19 3-7 8-7-8Z" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 22h8" /> <path d="M12 11v11" /> <path d="m19 3-7 8-7-8Z" /></g></svg>`,
    },
    picnic: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 10.5h12c1.1 0 2 .9 2 2V20c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2v-7.5c0-1.1.9-2 2-2Z"/> <path d="M8 10.5c0-3.7 2-6.5 4-6.5s4 2.8 4 6.5"/> <path d="M4.5 14.2h15"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 10.5h12c1.1 0 2 .9 2 2V20c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2v-7.5c0-1.1.9-2 2-2Z"/> <path d="M8 10.5c0-3.7 2-6.5 4-6.5s4 2.8 4 6.5"/> <path d="M4.5 14.2h15"/></g></svg>`,
    },
    lunchbox: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 7.5h12c1.1 0 2 .9 2 2V19c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V9.5c0-1.1.9-2 2-2Z"/> <path d="M8 7.5c0-1.9 1.6-3.5 4-3.5s4 1.6 4 3.5"/> <path d="M12 9.8v11.2"/> <path d="M12 14.2h8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 7.5h12c1.1 0 2 .9 2 2V19c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V9.5c0-1.1.9-2 2-2Z"/> <path d="M8 7.5c0-1.9 1.6-3.5 4-3.5s4 1.6 4 3.5"/> <path d="M12 9.8v11.2"/> <path d="M12 14.2h8"/></g></svg>`,
    },
    // --- Beverages ---
    coffee: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2v2" /> <path d="M14 2v2" /> <path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1" /> <path d="M6 2v2" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M10 2v2" /> <path d="M14 2v2" /> <path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1" /> <path d="M6 2v2" /></g></svg>`,
    },
    tea: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.5 10h9c.2 2.5-.6 4.6-2 5.8-1 .9-2.5 1.4-2.5 1.4s-1.5-.5-2.5-1.4c-1.4-1.2-2.2-3.3-2-5.8Z"/> <path d="M6.5 18c3.2 1.4 7.8 1.4 11 0"/> <path d="M16 10.4h1.2c1.5 0 2.8 1.2 2.8 2.8S18.7 16 17.2 16h-1.1"/> <path d="M16.5 11.2c.2 2.3-.4 4.3-1.6 5.6"/> <path d="M8.2 11.1v6.1c0 .7-.4 1.2-1 1.6l-1.1.7"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7.5 10h9c.2 2.5-.6 4.6-2 5.8-1 .9-2.5 1.4-2.5 1.4s-1.5-.5-2.5-1.4c-1.4-1.2-2.2-3.3-2-5.8Z"/> <path d="M6.5 18c3.2 1.4 7.8 1.4 11 0"/> <path d="M16 10.4h1.2c1.5 0 2.8 1.2 2.8 2.8S18.7 16 17.2 16h-1.1"/> <path d="M16.5 11.2c.2 2.3-.4 4.3-1.6 5.6"/> <path d="M8.2 11.1v6.1c0 .7-.4 1.2-1 1.6l-1.1.7"/></g></svg>`,
    },
    wine: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 22h8" /> <path d="M7 10h10" /> <path d="M12 15v7" /> <path d="M12 15a5 5 0 0 0 5-5c0-2-.5-4-2-8H9c-1.5 4-2 6-2 8a5 5 0 0 0 5 5Z" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 22h8" /> <path d="M7 10h10" /> <path d="M12 15v7" /> <path d="M12 15a5 5 0 0 0 5-5c0-2-.5-4-2-8H9c-1.5 4-2 6-2 8a5 5 0 0 0 5 5Z" /></g></svg>`,
    },
    beer: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 11h1a3 3 0 0 1 0 6h-1" /> <path d="M9 12v6" /> <path d="M13 12v6" /> <path d="M14 7.5c-1 0-1.44.5-3 .5s-2-.5-3-.5-1.72.5-2.5.5a2.5 2.5 0 0 1 0-5c.78 0 1.57.5 2.5.5S9.44 2 11 2s2 1.5 3 1.5 1.72-.5 2.5-.5a2.5 2.5 0 0 1 0 5c-.78 0-1.5-.5-2.5-.5Z" /> <path d="M5 8v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M17 11h1a3 3 0 0 1 0 6h-1" /> <path d="M9 12v6" /> <path d="M13 12v6" /> <path d="M14 7.5c-1 0-1.44.5-3 .5s-2-.5-3-.5-1.72.5-2.5.5a2.5 2.5 0 0 1 0-5c.78 0 1.57.5 2.5.5S9.44 2 11 2s2 1.5 3 1.5 1.72-.5 2.5-.5a2.5 2.5 0 0 1 0 5c-.78 0-1.5-.5-2.5-.5Z" /> <path d="M5 8v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8" /></g></svg>`,
    },
    smoothie: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 4h6c.9 0 1.6.7 1.6 1.6v2.1c0 .7-.4 1.2-1 1.5l-.6.3c.6 1.6 1 3.6 1 5.8 0 4.2-1.7 6.7-4 6.7s-4-2.5-4-6.7c0-2.2.4-4.2 1-5.8l-.6-.3c-.6-.3-1-.8-1-1.5V5.6C7.4 4.7 8.1 4 9 4Z"/> <path d="M12 10l4-4"/> <path d="M8.6 9h6.8"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M9 4h6c.9 0 1.6.7 1.6 1.6v2.1c0 .7-.4 1.2-1 1.5l-.6.3c.6 1.6 1 3.6 1 5.8 0 4.2-1.7 6.7-4 6.7s-4-2.5-4-6.7c0-2.2.4-4.2 1-5.8l-.6-.3c-.6-.3-1-.8-1-1.5V5.6C7.4 4.7 8.1 4 9 4Z"/> <path d="M12 10l4-4"/> <path d="M8.6 9h6.8"/></g></svg>`,
    },
    juice: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 4h8l-1.2 17.2A2 2 0 0 1 12.8 23h-1.6a2 2 0 0 1-2-1.8L8 4Z"/> <path d="M16.6 6.2l2.6 1.8"/> <path d="M16.6 6.2A2.6 2.6 0 0 0 14 4.2"/> <path d="M17.6 7.5A2.6 2.6 0 0 0 15 5.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 4h8l-1.2 17.2A2 2 0 0 1 12.8 23h-1.6a2 2 0 0 1-2-1.8L8 4Z"/> <path d="M16.6 6.2l2.6 1.8"/> <path d="M16.6 6.2A2.6 2.6 0 0 0 14 4.2"/> <path d="M17.6 7.5A2.6 2.6 0 0 0 15 5.5"/></g></svg>`,
    },
    water: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2C9.5 5.9 6 9.7 6 14a6 6 0 0 0 12 0c0-4.3-3.5-8.1-6-12Z"/> <path d="M9.2 14.2c.3 1.7 1.5 2.8 3.1 3.2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M12 2C9.5 5.9 6 9.7 6 14a6 6 0 0 0 12 0c0-4.3-3.5-8.1-6-12Z"/> <path d="M9.2 14.2c.3 1.7 1.5 2.8 3.1 3.2"/></g></svg>`,
    },
    lemonade: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 4h8l-1.2 17.2A2 2 0 0 1 12.8 23h-1.6a2 2 0 0 1-2-1.8L8 4Z"/> <circle cx="16.5" cy="6.5" r="2.2"/> <path d="M15.2 6.5h2.6"/> <path d="M11 6l4-3"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 4h8l-1.2 17.2A2 2 0 0 1 12.8 23h-1.6a2 2 0 0 1-2-1.8L8 4Z"/> <circle cx="16.5" cy="6.5" r="2.2"/> <path d="M15.2 6.5h2.6"/> <path d="M11 6l4-3"/></g></svg>`,
    },
    milkshake: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9.2 4.8c.6-1.2 1.7-1.8 2.8-1.8s2.2.6 2.8 1.8c.5 1 .2 2.2-.7 3.1H9.9c-.9-.9-1.2-2.1-.7-3.1Z"/> <path d="M8.3 7.9h7.4l-1 13.9A2 2 0 0 1 12.7 23h-1.4a2 2 0 0 1-2-1.8l-1-13.9Z"/> <path d="M13 9l4-4"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M9.2 4.8c.6-1.2 1.7-1.8 2.8-1.8s2.2.6 2.8 1.8c.5 1 .2 2.2-.7 3.1H9.9c-.9-.9-1.2-2.1-.7-3.1Z"/> <path d="M8.3 7.9h7.4l-1 13.9A2 2 0 0 1 12.7 23h-1.4a2 2 0 0 1-2-1.8l-1-13.9Z"/> <path d="M13 9l4-4"/></g></svg>`,
    },
    espresso: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 9.5h8c.2 2.6-.6 5-2.1 6.2-1 .8-1.9 1.1-1.9 1.1s-.9-.3-1.9-1.1C8.6 14.5 7.8 12.1 8 9.5Z"/> <path d="M7 18c2.8 1.4 7.2 1.4 10 0"/> <path d="M7 18.2h10.2"/> <path d="M12.6 3.5c1.2 1.2 1.1 2.5.1 3.6-1 1.2-1 2.4.2 3.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 9.5h8c.2 2.6-.6 5-2.1 6.2-1 .8-1.9 1.1-1.9 1.1s-.9-.3-1.9-1.1C8.6 14.5 7.8 12.1 8 9.5Z"/> <path d="M7 18c2.8 1.4 7.2 1.4 10 0"/> <path d="M7 18.2h10.2"/> <path d="M12.6 3.5c1.2 1.2 1.1 2.5.1 3.6-1 1.2-1 2.4.2 3.6"/></g></svg>`,
    },
    soda: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 8 1.75 12.28a2 2 0 0 0 2 1.72h4.54a2 2 0 0 0 2-1.72L18 8" /> <path d="M5 8h14" /> <path d="M7 15a6.47 6.47 0 0 1 5 0 6.47 6.47 0 0 0 5 0" /> <path d="m12 8 1-6h2" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="m6 8 1.75 12.28a2 2 0 0 0 2 1.72h4.54a2 2 0 0 0 2-1.72L18 8" /> <path d="M5 8h14" /> <path d="M7 15a6.47 6.47 0 0 1 5 0 6.47 6.47 0 0 0 5 0" /> <path d="m12 8 1-6h2" /></g></svg>`,
    },
    kombucha: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2h4v3c0 .6.3 1.1.7 1.5l.6.6c.4.4.7.9.7 1.5V19c0 2-1.6 3-4 3s-4-1-4-3V8.6c0-.6.3-1.1.7-1.5l.6-.6c.4-.4.7-.9.7-1.5V2Z"/> <circle cx="12" cy="12" r="0.9"/> <circle cx="10.8" cy="15.2" r="0.8"/> <circle cx="13.6" cy="16.8" r="0.7"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M10 2h4v3c0 .6.3 1.1.7 1.5l.6.6c.4.4.7.9.7 1.5V19c0 2-1.6 3-4 3s-4-1-4-3V8.6c0-.6.3-1.1.7-1.5l.6-.6c.4-.4.7-.9.7-1.5V2Z"/> <circle cx="12" cy="12" r="0.9"/> <circle cx="10.8" cy="15.2" r="0.8"/> <circle cx="13.6" cy="16.8" r="0.7"/></g></svg>`,
    },
    // --- Dishware ---
    plate: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="13" rx="8" ry="6"/> <ellipse cx="12" cy="13" rx="4.6" ry="3.4"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><ellipse cx="12" cy="13" rx="8" ry="6"/> <ellipse cx="12" cy="13" rx="4.6" ry="3.4"/></g></svg>`,
    },
    'bowl-dish': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.2 18 13"/> <path d="M8.2 12.8c1.2-2.2 2.6-3.4 3.8-3.4s2.6 1.2 3.8 3.4c-1.2 1.9-2.8 3.2-3.8 3.2s-2.6-1.3-3.8-3.2Z"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6 13c0 4 3.1 7 6 7s6-3 6-7"/> <path d="M6 13Q12 9.2 18 13"/> <path d="M8.2 12.8c1.2-2.2 2.6-3.4 3.8-3.4s2.6 1.2 3.8 3.4c-1.2 1.9-2.8 3.2-3.8 3.2s-2.6-1.3-3.8-3.2Z"/></g></svg>`,
    },
    mug: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 9.2h9v8.1c0 2.4-1.9 4.2-4.5 4.2s-4.5-1.8-4.5-4.2V9.2Z"/> <path d="M15.5 10.2h1.3c1.8 0 3.2 1.4 3.2 3.2s-1.4 3.2-3.2 3.2h-1.3"/> <path d="M9.2 3.8c1.2 1.1 1.1 2.3.1 3.3-1 1.1-1 2.2.2 3.3"/> <path d="M12.6 3.5c1.2 1.2 1.1 2.5.1 3.6-1 1.2-1 2.4.2 3.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.5 9.2h9v8.1c0 2.4-1.9 4.2-4.5 4.2s-4.5-1.8-4.5-4.2V9.2Z"/> <path d="M15.5 10.2h1.3c1.8 0 3.2 1.4 3.2 3.2s-1.4 3.2-3.2 3.2h-1.3"/> <path d="M9.2 3.8c1.2 1.1 1.1 2.3.1 3.3-1 1.1-1 2.2.2 3.3"/> <path d="M12.6 3.5c1.2 1.2 1.1 2.5.1 3.6-1 1.2-1 2.4.2 3.6"/></g></svg>`,
    },
    glass: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 4h8l-1.2 17.2A2 2 0 0 1 12.8 23h-1.6a2 2 0 0 1-2-1.8L8 4Z"/> <path d="M8.4 8h7.2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 4h8l-1.2 17.2A2 2 0 0 1 12.8 23h-1.6a2 2 0 0 1-2-1.8L8 4Z"/> <path d="M8.4 8h7.2"/></g></svg>`,
    },
    ramekin: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 10.5h10c1 0 1.8.8 1.8 1.8v3.4c0 2.2-2.9 4-6.8 4S5.2 17.9 5.2 15.7v-3.4c0-1 .8-1.8 1.8-1.8Z"/> <path d="M7 10.5c.6-1.2 1.6-1.8 2.8-1.8s2.2.6 3.2.6 2-.6 3.2-.6 2.2.6 2.8 1.8"/> <path d="M8.4 12.2h.01M10.6 12.2h.01M12.8 12.2h.01M15 12.2h.01"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7 10.5h10c1 0 1.8.8 1.8 1.8v3.4c0 2.2-2.9 4-6.8 4S5.2 17.9 5.2 15.7v-3.4c0-1 .8-1.8 1.8-1.8Z"/> <path d="M7 10.5c.6-1.2 1.6-1.8 2.8-1.8s2.2.6 3.2.6 2-.6 3.2-.6 2.2.6 2.8 1.8"/> <path d="M8.4 12.2h.01M10.6 12.2h.01M12.8 12.2h.01M15 12.2h.01"/></g></svg>`,
    },
    skillet: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10.5" cy="12.5" r="6.5"/> <path d="M16.2 11.8l6.3-2.1"/> <path d="M16.5 13.6l6.3-2.1"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><circle cx="10.5" cy="12.5" r="6.5"/> <path d="M16.2 11.8l6.3-2.1"/> <path d="M16.5 13.6l6.3-2.1"/></g></svg>`,
    },
    wok: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.2 13.6c2.1-4.6 4.9-6.8 6.8-6.8s4.7 2.2 6.8 6.8c-2.1 4-5.2 6.6-6.8 6.6s-4.7-2.6-6.8-6.6Z"/> <path d="M4.4 12.4c-1.2.3-2 .9-2.4 1.8.6 1 1.6 1.5 3 1.6"/> <path d="M19.6 12.4c1.2.3 2 .9 2.4 1.8-.6 1-1.6 1.5-3 1.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.2 13.6c2.1-4.6 4.9-6.8 6.8-6.8s4.7 2.2 6.8 6.8c-2.1 4-5.2 6.6-6.8 6.6s-4.7-2.6-6.8-6.6Z"/> <path d="M4.4 12.4c-1.2.3-2 .9-2.4 1.8.6 1 1.6 1.5 3 1.6"/> <path d="M19.6 12.4c1.2.3 2 .9 2.4 1.8-.6 1-1.6 1.5-3 1.6"/></g></svg>`,
    },
    'dutch-oven': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.2 12.2c0-2.8 2.8-4.7 5.8-4.7s5.8 1.9 5.8 4.7v6.1c0 2.3-2.6 3.7-5.8 3.7s-5.8-1.4-5.8-3.7v-6.1Z"/> <path d="M7.2 10.6h9.6"/> <path d="M6.2 14.2c-1.2.2-2.1.8-2.6 1.8.7 1.1 1.9 1.6 3.6 1.6"/> <path d="M17.8 14.2c1.2.2 2.1.8 2.6 1.8-.7 1.1-1.9 1.6-3.6 1.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.2 12.2c0-2.8 2.8-4.7 5.8-4.7s5.8 1.9 5.8 4.7v6.1c0 2.3-2.6 3.7-5.8 3.7s-5.8-1.4-5.8-3.7v-6.1Z"/> <path d="M7.2 10.6h9.6"/> <path d="M6.2 14.2c-1.2.2-2.1.8-2.6 1.8.7 1.1 1.9 1.6 3.6 1.6"/> <path d="M17.8 14.2c1.2.2 2.1.8 2.6 1.8-.7 1.1-1.9 1.6-3.6 1.6"/></g></svg>`,
    },
    'sheet-pan': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.5 8.2h13c.8 0 1.5.7 1.5 1.5V18c0 .8-.7 1.5-1.5 1.5h-13C4.7 19.5 4 18.8 4 18V9.7c0-.8.7-1.5 1.5-1.5Z"/> <path d="M6.2 8.2c.2 1 .8 1.6 1.8 1.6h8c1 0 1.6-.6 1.8-1.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.5 8.2h13c.8 0 1.5.7 1.5 1.5V18c0 .8-.7 1.5-1.5 1.5h-13C4.7 19.5 4 18.8 4 18V9.7c0-.8.7-1.5 1.5-1.5Z"/> <path d="M6.2 8.2c.2 1 .8 1.6 1.8 1.6h8c1 0 1.6-.6 1.8-1.6"/></g></svg>`,
    },
    'cutting-board': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 5.5h11c1.1 0 2 .9 2 2v10.8c0 1.1-.9 2-2 2h-11c-1.1 0-2-.9-2-2V7.5c0-1.1.9-2 2-2Z"/> <path d="M8.2 17.2l8.2-8.2"/> <path d="M15.8 8.6l2.1 2.1"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M6.5 5.5h11c1.1 0 2 .9 2 2v10.8c0 1.1-.9 2-2 2h-11c-1.1 0-2-.9-2-2V7.5c0-1.1.9-2 2-2Z"/> <path d="M8.2 17.2l8.2-8.2"/> <path d="M15.8 8.6l2.1 2.1"/></g></svg>`,
    },
    // --- Utensils ---
    fork: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3v7c0 1.7 1.3 3 3 3h2c1.7 0 3-1.3 3-3V3"/> <path d="M12 13v9"/> <path d="M9 3v6M12 3v6M15 3v6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8 3v7c0 1.7 1.3 3 3 3h2c1.7 0 3-1.3 3-3V3"/> <path d="M12 13v9"/> <path d="M9 3v6M12 3v6M15 3v6"/></g></svg>`,
    },
    knife: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19.5 4.5L10 14"/><path d="M10 14l-6.5 4L10 14Z"/><path d="M10 14c1.5-4.5 4-8 9.5-9.5"/><path d="M3.5 18l1.5 2.5 2-1"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M19.5 4.5L10 14"/><path d="M10 14l-6.5 4L10 14Z"/><path d="M10 14c1.5-4.5 4-8 9.5-9.5"/><path d="M3.5 18l1.5 2.5 2-1"/></g></svg>`,
    },
    spoon: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 8.8c0-2.4 1.4-4.3 3-4.3s3 1.9 3 4.3-1.4 4.2-3 4.2-3-1.8-3-4.2Z"/> <path d="M12 13v9"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M9 8.8c0-2.4 1.4-4.3 3-4.3s3 1.9 3 4.3-1.4 4.2-3 4.2-3-1.8-3-4.2Z"/> <path d="M12 13v9"/></g></svg>`,
    },
    spatula: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.2 4.8h6.6c.9 0 1.6.7 1.6 1.6v6.8c0 1-.8 1.8-1.8 1.8H8.4c-1 0-1.8-.8-1.8-1.8V6.4c0-.9.7-1.6 1.6-1.6Z"/> <path d="M11 15v7"/> <path d="M9 7.6v5M12 7.6v5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7.2 4.8h6.6c.9 0 1.6.7 1.6 1.6v6.8c0 1-.8 1.8-1.8 1.8H8.4c-1 0-1.8-.8-1.8-1.8V6.4c0-.9.7-1.6 1.6-1.6Z"/> <path d="M11 15v7"/> <path d="M9 7.6v5M12 7.6v5"/></g></svg>`,
    },
    whisk: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8.2 4.8h7.6"/> <path d="M12 4.8v5.2"/> <path d="M12 10c-2.6 0-5 2.2-5 4.8 0 2.8 2.2 5.2 5 7.2 2.8-2 5-4.4 5-7.2 0-2.6-2.4-4.8-5-4.8Z"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M8.2 4.8h7.6"/> <path d="M12 4.8v5.2"/> <path d="M12 10c-2.6 0-5 2.2-5 4.8 0 2.8 2.2 5.2 5 7.2 2.8-2 5-4.4 5-7.2 0-2.6-2.4-4.8-5-4.8Z"/></g></svg>`,
    },
    'rolling-pin': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.8 10h8.4c1.3 0 2.3 1 2.3 2.3s-1 2.3-2.3 2.3H7.8c-1.3 0-2.3-1-2.3-2.3S6.5 10 7.8 10Z"/> <path d="M5.5 11.2H3.8c-.9 0-1.6.7-1.6 1.6s.7 1.6 1.6 1.6h1.7"/> <path d="M18.5 11.2h1.7c.9 0 1.6.7 1.6 1.6s-.7 1.6-1.6 1.6h-1.7"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7.8 10h8.4c1.3 0 2.3 1 2.3 2.3s-1 2.3-2.3 2.3H7.8c-1.3 0-2.3-1-2.3-2.3S6.5 10 7.8 10Z"/> <path d="M5.5 11.2H3.8c-.9 0-1.6.7-1.6 1.6s.7 1.6 1.6 1.6h1.7"/> <path d="M18.5 11.2h1.7c.9 0 1.6.7 1.6 1.6s-.7 1.6-1.6 1.6h-1.7"/></g></svg>`,
    },
    chopsticks: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5.2 6.4l13.8 11.2"/> <path d="M7.2 4.8l13.6 11.4"/> <path d="M18.9 17.6l-1.3 1.6"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M5.2 6.4l13.8 11.2"/> <path d="M7.2 4.8l13.6 11.4"/> <path d="M18.9 17.6l-1.3 1.6"/></g></svg>`,
    },
    'mortar-pestle': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 12.8h10c0 4-2.6 7.2-5 7.2s-5-3.2-5-7.2Z"/> <path d="M7 12.8Q12 9.8 17 12.8"/> <path d="M10.6 6.2l7-2.2"/> <path d="M12.2 6.4l2.2 6.4"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M7 12.8h10c0 4-2.6 7.2-5 7.2s-5-3.2-5-7.2Z"/> <path d="M7 12.8Q12 9.8 17 12.8"/> <path d="M10.6 6.2l7-2.2"/> <path d="M12.2 6.4l2.2 6.4"/></g></svg>`,
    },
    thermometer: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z" /></g></svg>`,
    },

    // ─── Utility ───────────────────────────────────
    dice: {
        small: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="18" y="18" width="64" height="64" rx="10" stroke-width="2" fill="currentColor" fill-opacity="0.10"/><circle cx="35" cy="35" r="4" fill="currentColor" stroke="none"/><circle cx="65" cy="35" r="4" fill="currentColor" stroke="none"/><circle cx="50" cy="50" r="4" fill="currentColor" stroke="none"/><circle cx="35" cy="65" r="4" fill="currentColor" stroke="none"/><circle cx="65" cy="65" r="4" fill="currentColor" stroke="none"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><rect x="100" y="22" width="100" height="100" rx="14" stroke-width="2" fill="currentColor" fill-opacity="0.10"/><circle cx="125" cy="47" r="6" fill="currentColor" stroke="none"/><circle cx="175" cy="47" r="6" fill="currentColor" stroke="none"/><circle cx="150" cy="72" r="6" fill="currentColor" stroke="none"/><circle cx="125" cy="97" r="6" fill="currentColor" stroke="none"/><circle cx="175" cy="97" r="6" fill="currentColor" stroke="none"/></svg>`,
    },
    star: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z" /></g></svg>`,
    },
    timer: {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="10" x2="14" y1="2" y2="2" /> <line x1="12" x2="15" y1="14" y2="11" /> <circle cx="12" cy="14" r="8" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><line x1="10" x2="14" y1="2" y2="2" /> <line x1="12" x2="15" y1="14" y2="11" /> <circle cx="12" cy="14" r="8" /></g></svg>`,
    },
    'chef-hat': {
        small: `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z" /> <path d="M6 17h12" /></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/><path d="M70 165 H90 V155"/><path d="M230 165 H210 V155"/></g><g transform="translate(90,30) scale(5)"><path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z" /> <path d="M6 17h12" /></g></svg>`,
    },
    // --- Extra Utensils ---
    ladle: {
        small: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="45" cy="65" r="18" stroke-width="2"/><path d="M45 47 Q45 32 55 22 L65 12" stroke-width="2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g opacity="0.12"><path d="M70 15 H90 V25"/><path d="M230 15 H210 V25"/></g><circle cx="140" cy="110" r="35" stroke-width="2"/><path d="M140 75 Q140 48 160 32 L178 18" stroke-width="2"/></svg>`,
    },
    peeler: {
        small: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M35 15 Q30 30 35 40 L65 40 Q70 30 65 15" stroke-width="2"/><line x1="35" y1="15" x2="65" y2="15" stroke-width="1"/><line x1="50" y1="15" x2="50" y2="40" stroke-width="1" opacity="0.3"/><line x1="50" y1="40" x2="50" y2="88" stroke-width="2.5"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g opacity="0.12"><rect x="75" y="10" width="150" height="160" rx="2"/></g><path d="M122 18 Q115 42 122 60 L178 60 Q185 42 178 18" stroke-width="2"/><line x1="122" y1="18" x2="178" y2="18" stroke-width="1"/><line x1="150" y1="18" x2="150" y2="60" opacity="0.3"/><line x1="150" y1="60" x2="150" y2="158" stroke-width="2.5"/></svg>`,
    },
    tongs: {
        small: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M42 15 Q38 45 30 65 Q25 78 35 82" stroke-width="2"/><path d="M58 15 Q62 45 70 65 Q75 78 65 82" stroke-width="2"/><path d="M42 15 L58 15" stroke-width="2"/></svg>`,
        large: `<svg viewBox="0 0 300 180" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g opacity="0.12"><rect x="75" y="10" width="150" height="160" rx="2"/></g><path d="M135 18 Q128 68 112 108 Q105 132 120 140" stroke-width="2"/><path d="M165 18 Q172 68 188 108 Q195 132 180 140" stroke-width="2"/><path d="M135 18 L165 18" stroke-width="2"/></svg>`,
    },
};

// ─── Icon Categories (for grouped picker UI) ──────────────────────────────────

const ICON_CATEGORIES: Record<string, string[]> = {
  'Proteins': ['beef', 'chicken', 'pork', 'fish', 'shrimp', 'lamb', 'turkey', 'salmon', 'tofu', 'egg', 'sausage', 'bacon'],
  'Grains & Carbs': ['pasta', 'rice', 'bread', 'noodles', 'potato', 'couscous', 'tortilla', 'oats', 'quinoa', 'cornbread'],
  'Fruits & Vegetables': ['carrot', 'broccoli', 'tomato', 'pepper', 'onion', 'mushroom', 'corn', 'apple', 'lemon', 'avocado', 'garlic', 'leafy'],
  'Dairy & Pantry': ['cheese', 'butter', 'milk', 'olive-oil', 'honey', 'beans', 'nuts', 'chocolate', 'flour', 'vinegar'],
  'Dishes & Styles': ['soup', 'salad', 'pizza', 'taco', 'burger', 'bowl', 'sandwich', 'sushi', 'curry', 'stew', 'casserole', 'wrap', 'risotto', 'stirfry', 'dumpling'],
  'Cooking Methods': ['grill', 'oven', 'stovetop', 'slowcooker', 'smoke', 'steam', 'fry', 'roast', 'bake', 'broil', 'saute', 'blender'],
  'Meal Types': ['breakfast', 'brunch', 'lunch', 'dinner', 'snack', 'appetizer', 'dessert', 'picnic', 'lunchbox'],
  'Beverages': ['coffee', 'tea', 'wine', 'beer', 'smoothie', 'juice', 'water', 'lemonade', 'milkshake', 'espresso', 'soda', 'cocktail'],
  'Dishware': ['plate', 'bowl-dish', 'mug', 'glass', 'ramekin', 'skillet', 'wok', 'dutch-oven', 'sheet-pan', 'cutting-board'],
  'Utensils': ['fork', 'knife', 'spoon', 'spatula', 'whisk', 'rolling-pin', 'chopsticks', 'mortar-pestle', 'tongs', 'ladle', 'peeler', 'thermometer'],
  'Utility': ['dice', 'star', 'timer', 'chef-hat'],
}

// Grouped tabs for icon picker (each tab contains sub-categories)
const ICON_TABS: Record<string, Record<string, string[]>> = {
  'Ingredients': {
    'Proteins': ICON_CATEGORIES['Proteins'],
    'Grains & Carbs': ICON_CATEGORIES['Grains & Carbs'],
    'Fruits & Vegetables': ICON_CATEGORIES['Fruits & Vegetables'],
    'Dairy & Pantry': ICON_CATEGORIES['Dairy & Pantry'],
  },
  'Meals': {
    'Dishes & Styles': ICON_CATEGORIES['Dishes & Styles'],
    'Meal Types': ICON_CATEGORIES['Meal Types'],
    'Beverages': ICON_CATEGORIES['Beverages'],
  },
  'Kitchen': {
    'Cooking Methods': ICON_CATEGORIES['Cooking Methods'],
    'Dishware': ICON_CATEGORIES['Dishware'],
    'Utensils': ICON_CATEGORIES['Utensils'],
    'Utility': ICON_CATEGORIES['Utility'],
  },
}

// Profile name → icon auto-matching
const PROFILE_STYLE_MAP: Record<string, string> = {
  'beef': 'beef', 'steak': 'beef', 'burger': 'burger',
  'chicken': 'chicken', 'poultry': 'chicken', 'turkey': 'turkey',
  'pork': 'pork', 'ham': 'pork', 'bacon': 'bacon', 'sausage': 'sausage',
  'fish': 'fish', 'seafood': 'fish', 'shrimp': 'shrimp', 'salmon': 'salmon',
  'lamb': 'lamb',
  'tofu': 'tofu', 'vegan': 'tofu', 'vegetarian': 'leafy',
  'pasta': 'pasta', 'noodle': 'noodles', 'rice': 'rice', 'bread': 'bread',
  'potato': 'potato', 'tortilla': 'tortilla',
  'pizza': 'pizza', 'taco': 'taco', 'sandwich': 'sandwich', 'wrap': 'wrap',
  'soup': 'soup', 'salad': 'salad', 'stew': 'stew', 'curry': 'curry',
  'sushi': 'sushi', 'bowl': 'bowl', 'casserole': 'casserole',
  'risotto': 'risotto', 'stirfry': 'stirfry', 'dumpling': 'dumpling',
  'grill': 'grill', 'bbq': 'grill', 'barbecue': 'grill',
  'bake': 'bake', 'roast': 'roast', 'fry': 'fry', 'saute': 'saute',
  'slowcooker': 'slowcooker', 'slow cooker': 'slowcooker', 'crockpot': 'slowcooker',
  'smoke': 'smoke', 'smoked': 'smoke',
  'breakfast': 'breakfast', 'brunch': 'brunch', 'lunch': 'lunch',
  'dinner': 'dinner', 'snack': 'snack', 'dessert': 'dessert',
  'appetizer': 'appetizer', 'cocktail': 'cocktail',
  'coffee': 'coffee', 'tea': 'tea', 'smoothie': 'smoothie',
}

// ─── Custom Icon Cache ────────────────────────────────────────────────────────

const _customIconCache: Record<string, string> = {}

export function registerCustomIcon(key: string, svg: string): void {
  _customIconCache[key] = sanitizeSVG(svg)
}

export function removeCustomIcon(key: string): void {
  delete _customIconCache[key]
}

export function getCustomIconKeys(): string[] {
  return Object.keys(_customIconCache)
}

// ─── Public API ───────────────────────────────────────────────────────────────

/** Returns array of all icon key strings (built-in + custom) */
export function getAllIconKeys(): string[] {
  return [...Object.keys(ICONS), ...Object.keys(_customIconCache)]
}

/** Returns the small SVG string for the given key, or the chef-hat fallback */
export function getIconByKey(key: string): string {
  if (key && key.startsWith('custom:') && _customIconCache[key]) {
    return _customIconCache[key]
  }
  const entry = ICONS[key]
  if (entry) return entry.small
  return ICONS['chef-hat'] ? ICONS['chef-hat'].small : ''
}

/** Returns the small SVG for the key if it exists, or null (no fallback) */
export function getIconIfExists(key: string): string | null {
  if (key && key.startsWith('custom:') && _customIconCache[key]) {
    return _customIconCache[key]
  }
  const entry = ICONS[key]
  return entry ? entry.small : null
}

/** Returns the large (300x180) SVG string for the given key, or the chef-hat fallback */
export function getLargeIcon(key: string): string {
  const entry = ICONS[key]
  if (entry) return entry.large
  return ICONS['chef-hat'] ? ICONS['chef-hat'].large : ''
}

/** Returns the ICON_CATEGORIES as an array for grouped picker UI */
export function getIconCategories(): Array<{ name: string; keys: string[] }> {
  return Object.entries(ICON_CATEGORIES).map(([name, keys]) => ({ name, keys }))
}

/** Returns the ICON_TABS structure for the tabbed icon picker */
export function getIconTabs(): Record<string, Record<string, string[]>> {
  return ICON_TABS
}

/** Returns the large SVG for a key (built-in or custom), or null if not found */
export function resolveIconLarge(key: string): string | null {
  if (key && key.startsWith('custom:') && _customIconCache[key]) {
    return _customIconCache[key]
  }
  const entry = ICONS[key]
  return entry ? entry.large : null
}

/**
 * Returns a large placeholder SVG for a recipe card.
 * Lookup priority:
 *   1. Keyword match via iconMappings.keyword_icons
 *   2. Food/ingredient match via iconMappings.food_icons
 *   3. Profile name match via PROFILE_STYLE_MAP
 *   4. Brand logo fallback
 *   5. Random built-in icon
 */
export function getPlaceholderSvg(
  recipe: Recipe | null,
  profileName: string | null,
  iconMappings: IconMappings,
  logoUrl: string,
): string {
  const kwIcons = (iconMappings && iconMappings.keyword_icons) || {}
  const foodIcons = (iconMappings && iconMappings.food_icons) || {}

  // 1. Try keyword match (admin-configured mappings, A-Z by name)
  if (recipe && recipe.keywords && Object.keys(kwIcons).length > 0) {
    const sorted = [...recipe.keywords]
      .map(kw => typeof kw === 'object' ? (kw.name || '') : '')
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b))
    for (const name of sorted) {
      const iconKey = kwIcons[name.toLowerCase()]
      if (iconKey) {
        const svg = resolveIconLarge(iconKey)
        if (svg) return svg
      }
    }
  }

  // 2. Try food match (admin-configured mappings, A-Z by food name)
  if (recipe && recipe.ingredients && Object.keys(foodIcons).length > 0) {
    const foods = [...new Set(recipe.ingredients.map(i => i.food).filter(Boolean))]
      .sort((a, b) => a!.localeCompare(b!))
    for (const food of foods) {
      const iconKey = foodIcons[food!.toLowerCase()]
      if (iconKey) {
        const svg = resolveIconLarge(iconKey)
        if (svg) return svg
      }
    }
  }

  // 3. Try profile name match
  if (profileName) {
    const pLower = profileName.toLowerCase()
    for (const [term, iconKey] of Object.entries(PROFILE_STYLE_MAP)) {
      if (pLower.includes(term)) {
        const svg = resolveIconLarge(iconKey)
        if (svg) return svg
      }
    }
  }

  // 4. Fall back to logo
  if (logoUrl) return getBrandIcon(logoUrl)

  // 5. Last resort: random built-in icon
  const keys = Object.keys(ICONS)
  const randomKey = keys[Math.floor(Math.random() * keys.length)]
  return ICONS[randomKey].large
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
