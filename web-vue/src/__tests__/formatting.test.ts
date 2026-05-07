import { describe, it, expect } from 'vitest'
import {
  formatIngredient,
  itemNounText,
  ratingStars,
  formatDisplayName,
  formatRelaxedConstraint,
  formatMenuDate,
} from '@/utils/formatting'

describe('formatIngredient', () => {
  it('formats amount + unit + food', () => {
    expect(formatIngredient({ amount: 2, unit: 'cups', food: 'flour', note: null, is_header: false, original_text: null }))
      .toBe('2 cups flour')
  })

  it('formats fractional amounts without trailing zeros', () => {
    expect(formatIngredient({ amount: 0.5, unit: 'tsp', food: 'salt', note: null, is_header: false, original_text: null }))
      .toBe('0.5 tsp salt')
  })

  it('formats whole amounts without decimals', () => {
    expect(formatIngredient({ amount: 3, unit: null, food: 'eggs', note: null, is_header: false, original_text: null }))
      .toBe('3 eggs')
  })

  it('formats food only when no amount or unit', () => {
    expect(formatIngredient({ amount: null, unit: null, food: 'parsley', note: null, is_header: false, original_text: null }))
      .toBe('parsley')
  })

  it('includes unit without amount when amount is 0', () => {
    expect(formatIngredient({ amount: 0, unit: 'pinch', food: 'salt', note: null, is_header: false, original_text: null }))
      .toBe('pinch salt')
  })
})

describe('itemNounText', () => {
  it('pluralizes recipes', () => {
    expect(itemNounText(5)).toBe('5 recipes')
  })

  it('uses singular for 1', () => {
    expect(itemNounText(1)).toBe('1 recipe')
  })

  it('uses custom noun', () => {
    expect(itemNounText(3, 'cocktail')).toBe('3 cocktails')
  })

  it('uses singular custom noun for 1', () => {
    expect(itemNounText(1, 'cocktail')).toBe('1 cocktail')
  })
})

describe('ratingStars', () => {
  it('rounds to nearest integer', () => {
    expect(ratingStars(3.7)).toBe(4)
    expect(ratingStars(3.2)).toBe(3)
  })

  it('returns 0 for null/undefined/0', () => {
    expect(ratingStars(null)).toBe(0)
    expect(ratingStars(undefined)).toBe(0)
    expect(ratingStars(0)).toBe(0)
  })
})

describe('formatDisplayName', () => {
  it('capitalizes first letter', () => {
    expect(formatDisplayName('dinner')).toBe('Dinner')
  })

  it('handles known display name overrides', () => {
    expect(formatDisplayName('oldfashioned')).toBe('Old Fashioned')
  })

  it('preserves already-capitalized names', () => {
    expect(formatDisplayName('Breakfast')).toBe('Breakfast')
  })
})

describe('formatRelaxedConstraint', () => {
  it('formats with operator and original count', () => {
    const result = formatRelaxedConstraint({
      label: 'Italian',
      slack_value: 2,
      operator: '>=',
      original_count: 5,
    })
    expect(result).toBe('Relaxed "Italian" from at least 5 to 3')
  })

  it('falls back to generic format', () => {
    const result = formatRelaxedConstraint({
      label: 'Rating',
      slack_value: 1.5,
    })
    expect(result).toBe('Rating adjusted by 1.5')
  })
})

describe('formatMenuDate', () => {
  it('returns empty string for empty input', () => {
    expect(formatMenuDate('')).toBe('')
  })

  it('formats ISO date to readable string', () => {
    const result = formatMenuDate('2026-04-19T12:00:00Z')
    // Locale-dependent but should contain day/month info
    expect(result).toBeTruthy()
    expect(result.length).toBeGreaterThan(5)
  })
})
