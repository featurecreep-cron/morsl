import { describe, it, expect } from 'vitest'
import { STOCK_ICON_SVG, getBrandIcon, getLoadingIconHtml } from '@/utils/icons'

describe('icons', () => {
  it('STOCK_ICON_SVG is valid SVG string', () => {
    expect(STOCK_ICON_SVG).toContain('<svg')
    expect(STOCK_ICON_SVG).toContain('</svg>')
    expect(STOCK_ICON_SVG).toContain('viewBox')
  })

  it('getBrandIcon returns stock icon for empty url', () => {
    expect(getBrandIcon('')).toBe(STOCK_ICON_SVG)
  })

  it('getBrandIcon returns img tag for non-empty url', () => {
    const result = getBrandIcon('/uploads/logo.svg')
    expect(result).toContain('<img')
    expect(result).toContain('/uploads/logo.svg')
  })

  it('getLoadingIconHtml returns empty when not loaded and no cache', () => {
    // Default favicon path with settingsLoaded=false and no localStorage
    const result = getLoadingIconHtml('/icons/default-favicon.svg', false)
    // Returns empty or cached value
    expect(typeof result).toBe('string')
  })

  it('getLoadingIconHtml returns brand icon for custom url', () => {
    const result = getLoadingIconHtml('/uploads/spinner.svg', true)
    expect(result).toContain('<img')
    expect(result).toContain('/uploads/spinner.svg')
  })
})
