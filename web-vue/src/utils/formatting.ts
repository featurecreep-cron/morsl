import type { Ingredient, RelaxedConstraint } from '@/types/api'

export function formatIngredient(ing: Ingredient): string {
  const parts: string[] = []
  if (ing.amount) {
    parts.push(
      ing.amount % 1 === 0
        ? ing.amount.toString()
        : ing.amount.toFixed(2).replace(/\.?0+$/, ''),
    )
  }
  if (ing.unit) parts.push(ing.unit)
  parts.push(ing.food)
  return parts.join(' ')
}

export function itemNounText(n: number, noun?: string): string {
  const word = noun || 'recipe'
  return n + ' ' + word + (n === 1 ? '' : 's')
}

export function ratingStars(rating: number | null | undefined): number {
  if (!rating) return 0
  return Math.round(rating)
}

export function formatDisplayName(name: string): string {
  const displayNames: Record<string, string> = {
    oldfashioned: 'Old Fashioned',
  }
  return displayNames[name.toLowerCase()] || name.charAt(0).toUpperCase() + name.slice(1)
}

export function formatRelaxedConstraint(rc: RelaxedConstraint): string {
  const ops: Record<string, string> = { '>=': 'at least', '<=': 'at most', '==': 'exactly' }
  if (rc.operator && rc.original_count) {
    const actual = Math.round(rc.original_count - rc.slack_value)
    return `Relaxed "${rc.label}" from ${ops[rc.operator] || rc.operator} ${rc.original_count} to ${actual}`
  }
  return `${rc.label} adjusted by ${rc.slack_value.toFixed(1)}`
}

export function timeAgo(isoString: string): string {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 60) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHour < 24) return `${diffHour}h ago`
  if (diffDay < 7) return `${diffDay}d ago`
  return date.toLocaleDateString()
}

export function formatMenuDate(isoString: string): string {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
}
