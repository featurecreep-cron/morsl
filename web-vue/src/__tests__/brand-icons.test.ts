import { describe, it, expect, vi, afterEach } from 'vitest'
import { getBrandIcon, prefetchLoadingIcon, prefetchBrandSvg } from '@/utils/icons'

// stroke is a literal colour, exactly as an uploaded icon would carry it
const UPLOADED_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
  '<circle cx="16" cy="16" r="10" fill="none" stroke="#000000" stroke-width="3"/></svg>'

function stubFetch(body = UPLOADED_SVG) {
  const spy = vi.fn(async () => ({ ok: true, text: async () => body }))
  vi.stubGlobal('fetch', spy)
  return spy
}

describe('brand icon rendering', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('falls back to an <img>, which cannot take the theme colour', () => {
    // currentColor inside an <img> resolves against the SVG's own document and
    // paints black — this is the state the loading icon was stuck in.
    expect(getBrandIcon('/uploads/branding/unfetched.svg')).toContain('<img')
  })

  it('inlines the loading icon so currentColor resolves to the theme', async () => {
    const url = '/uploads/branding/loading-icon-1.svg'
    const fetchSpy = stubFetch()

    expect(await prefetchLoadingIcon(url)).toBe(true)
    expect(fetchSpy).toHaveBeenCalledWith(url)

    const html = getBrandIcon(url)
    expect(html).not.toContain('<img')
    expect(html).toContain('<svg')
  })

  it('rewrites a hardcoded stroke to currentColor', async () => {
    const url = '/uploads/branding/loading-icon-2.svg'
    stubFetch()
    await prefetchLoadingIcon(url)

    const html = getBrandIcon(url)
    expect(html).toContain('currentColor')
    expect(html).not.toContain('#000000')
  })

  it('does not fetch the default icon — it resolves to the built-in inline SVG', async () => {
    const fetchSpy = stubFetch()
    expect(await prefetchLoadingIcon('/icons/default-favicon.svg')).toBe(false)
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('does not fetch an empty url', async () => {
    const fetchSpy = stubFetch()
    expect(await prefetchLoadingIcon('')).toBe(false)
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('leaves the logo path working', async () => {
    const url = '/uploads/branding/logo-1.svg'
    stubFetch()
    expect(await prefetchBrandSvg(url)).toBe(true)
    expect(getBrandIcon(url)).not.toContain('<img')
  })
})
