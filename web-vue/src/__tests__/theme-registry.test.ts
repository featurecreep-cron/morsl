import { describe, it, expect } from 'vitest'
import { THEME_REGISTRY } from '@/theme-registry'

describe('THEME_REGISTRY', () => {
  it('has 16 themes', () => {
    expect(Object.keys(THEME_REGISTRY)).toHaveLength(16)
  })

  it('has cast-iron as default', () => {
    expect(THEME_REGISTRY['cast-iron']).toBeDefined()
    expect(THEME_REGISTRY['cast-iron'].label).toBe('Cast Iron')
    expect(THEME_REGISTRY['cast-iron'].mode).toBe('dark')
  })

  it('every theme has required fields', () => {
    for (const [key, entry] of Object.entries(THEME_REGISTRY)) {
      expect(entry.label, `${key} missing label`).toBeTruthy()
      expect(entry.accentColor, `${key} missing accentColor`).toMatch(/^#[0-9a-f]{6}$/i)
      expect(entry.mode, `${key} invalid mode`).toMatch(/^(dark|light)$/)
      expect(entry.family, `${key} missing family`).toBeTruthy()
    }
  })

  it('has both dark and light themes', () => {
    const modes = new Set(Object.values(THEME_REGISTRY).map((t) => t.mode))
    expect(modes.has('dark')).toBe(true)
    expect(modes.has('light')).toBe(true)
  })

  it('has expected theme names', () => {
    const keys = Object.keys(THEME_REGISTRY)
    expect(keys).toContain('honey')
    expect(keys).toContain('espresso')
    expect(keys).toContain('porcelain')
    expect(keys).toContain('sage')
    expect(keys).toContain('basil')
  })
})
