import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProfilesStore } from '@/stores/profiles'
import type { ProfileSummary } from '@/types/api'

function makeProfile(overrides: Partial<ProfileSummary> = {}): ProfileSummary {
  return {
    name: 'dinner',
    display_name: 'Dinner',
    choices: 5,
    is_default: false,
    show_on_menu: true,
    icon: 'dinner',
    item_noun: 'recipe',
    ...overrides,
  }
}

describe('useProfilesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts empty', () => {
    const store = useProfilesStore()
    expect(store.profiles).toEqual([])
    expect(store.hasProfiles).toBe(false)
    expect(store.visibleProfiles).toEqual([])
  })

  it('visibleProfiles filters out hidden profiles', () => {
    const store = useProfilesStore()
    store.profiles = [
      makeProfile({ name: 'dinner', show_on_menu: true }),
      makeProfile({ name: 'hidden', show_on_menu: false }),
      makeProfile({ name: 'breakfast', show_on_menu: true }),
    ]
    expect(store.visibleProfiles).toHaveLength(2)
    expect(store.visibleProfiles.map((p) => p.name)).toEqual(['dinner', 'breakfast'])
  })

  it('defaultProfile finds is_default', () => {
    const store = useProfilesStore()
    store.profiles = [
      makeProfile({ name: 'a', is_default: false }),
      makeProfile({ name: 'b', is_default: true }),
    ]
    expect(store.defaultProfile?.name).toBe('b')
  })

  it('defaultProfile falls back to first profile', () => {
    const store = useProfilesStore()
    store.profiles = [
      makeProfile({ name: 'a', is_default: false }),
      makeProfile({ name: 'b', is_default: false }),
    ]
    expect(store.defaultProfile?.name).toBe('a')
  })

  it('defaultProfile returns null when empty', () => {
    const store = useProfilesStore()
    expect(store.defaultProfile).toBeNull()
  })

  it('displayCategories returns _all fallback when no categories defined', () => {
    const store = useProfilesStore()
    store.profiles = [makeProfile()]
    expect(store.displayCategories).toHaveLength(1)
    expect(store.displayCategories[0].id).toBe('_all')
  })

  it('displayCategories uses real categories when defined', () => {
    const store = useProfilesStore()
    store.categories = [
      { id: 1, display_name: 'Meals', subtitle: '', icon: '' },
      { id: 2, display_name: 'Drinks', subtitle: '', icon: '' },
    ]
    expect(store.displayCategories).toHaveLength(2)
  })

  it('categorizedProfiles groups by category', () => {
    const store = useProfilesStore()
    store.categories = [
      { id: 1, display_name: 'Meals', subtitle: '', icon: '' },
    ]
    store.profiles = [
      makeProfile({ name: 'dinner', category: 1 }),
      makeProfile({ name: 'breakfast', category: 1 }),
      makeProfile({ name: 'cocktails' }),
    ]
    expect(store.categorizedProfiles[1]).toHaveLength(2)
    expect(store.categorizedProfiles['_uncategorized']).toHaveLength(1)
  })

  it('resolveNoun finds profile-specific noun', () => {
    const store = useProfilesStore()
    store.profiles = [
      makeProfile({ name: 'drinks', item_noun: 'cocktail' }),
    ]
    expect(store.resolveNoun('drinks', 'recipe')).toBe('cocktail')
  })

  it('resolveNoun falls back to global noun', () => {
    const store = useProfilesStore()
    store.profiles = [
      makeProfile({ name: 'dinner', item_noun: undefined }),
    ]
    expect(store.resolveNoun('dinner', 'dish')).toBe('dish')
  })

  it('resolveNoun falls back to recipe', () => {
    const store = useProfilesStore()
    expect(store.resolveNoun('nonexistent', '')).toBe('recipe')
  })
})
