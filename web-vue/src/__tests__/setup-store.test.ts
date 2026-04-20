import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSetupStore } from '@/stores/setup'

describe('useSetupStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('starts at step 1', () => {
      const store = useSetupStore()
      expect(store.step).toBe(1)
      expect(store.profileSubPage).toBe('basics')
    })

    it('has 6 profile presets', () => {
      const store = useSetupStore()
      expect(store.presets).toHaveLength(6)
      expect(store.presets[0].key).toBe('breakfast')
      expect(store.presets[5].key).toBe('weeknight')
    })

    it('has 2 category presets', () => {
      const store = useSetupStore()
      expect(store.categoryPresets).toHaveLength(2)
    })

    it('has no profile selections initially', () => {
      const store = useSetupStore()
      expect(store.hasProfileSelections).toBe(false)
    })
  })

  describe('preset toggling', () => {
    it('toggles preset selection', () => {
      const store = useSetupStore()
      const preset = store.presets[0]
      expect(preset.selected).toBe(false)

      store.togglePreset(preset)
      expect(preset.selected).toBe(true)
      expect(store.hasProfileSelections).toBe(true)

      store.togglePreset(preset)
      expect(preset.selected).toBe(false)
    })
  })

  describe('custom profiles', () => {
    it('adds custom profile', () => {
      const store = useSetupStore()
      store.customProfileName = 'Snacks'
      store.addCustomProfile()
      expect(store.customProfiles).toHaveLength(1)
      expect(store.customProfiles[0].name).toBe('Snacks')
      expect(store.customProfileName).toBe('')
    })

    it('rejects blank names', () => {
      const store = useSetupStore()
      store.customProfileName = '   '
      store.addCustomProfile()
      expect(store.customProfiles).toHaveLength(0)
    })

    it('rejects duplicate names (case-insensitive)', () => {
      const store = useSetupStore()
      store.customProfileName = 'Snacks'
      store.addCustomProfile()
      store.customProfileName = 'snacks'
      store.addCustomProfile()
      expect(store.customProfiles).toHaveLength(1)
    })

    it('removes custom profile by index', () => {
      const store = useSetupStore()
      store.customProfileName = 'A'
      store.addCustomProfile()
      store.customProfileName = 'B'
      store.addCustomProfile()
      store.removeCustomProfile(0)
      expect(store.customProfiles).toHaveLength(1)
      expect(store.customProfiles[0].name).toBe('B')
    })
  })

  describe('buildProfileQueue', () => {
    it('builds queue from selected presets', () => {
      const store = useSetupStore()
      store.presets[0].selected = true // breakfast
      store.presets[2].selected = true // dinner
      store.buildProfileQueue()

      expect(store.profileQueue).toHaveLength(2)
      expect(store.profileQueue[0].name).toBe('Breakfast')
      expect(store.profileQueue[0].default).toBe(true)
      expect(store.profileQueue[1].name).toBe('Dinner')
      expect(store.profileQueue[1].default).toBe(false)
      expect(store.step).toBe(3)
      expect(store.profileIndex).toBe(0)
    })

    it('includes custom profiles after presets', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.customProfileName = 'Snacks'
      store.addCustomProfile()
      store.buildProfileQueue()

      expect(store.profileQueue).toHaveLength(2)
      expect(store.profileQueue[0].name).toBe('Breakfast')
      expect(store.profileQueue[1].name).toBe('Snacks')
    })

    it('skips to step 4 when no profiles selected', () => {
      const store = useSetupStore()
      store.buildProfileQueue()
      expect(store.profileQueue).toHaveLength(0)
      expect(store.step).toBe(4)
    })
  })

  describe('profile entry structure', () => {
    it('creates profile with correct defaults', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      const profile = store.profileQueue[0]
      expect(profile.name).toBe('Breakfast')
      expect(profile.icon).toBe('breakfast')
      expect(profile.choices).toBe(3) // breakfast preset choices
      expect(profile.min_choices).toBeNull()
      expect(profile.description).toBe('')
      expect(profile.category).toBe('')
      expect(profile.rules.tagsInclude.active).toBe(false)
      expect(profile.rules.foodsInclude.active).toBe(false)
      expect(profile.rules.booksInclude.active).toBe(false)
      expect(profile.rules.tagsExclude.active).toBe(false)
      expect(profile.rules.foodsExclude.active).toBe(false)
      expect(profile.rules.rating.active).toBe(false)
      expect(profile.rules.rating.min).toBe(4)
      expect(profile.rules.avoidRecent.active).toBe(false)
      expect(profile.rules.avoidRecent.days).toBe(14)
      expect(profile.rules.includeNew.active).toBe(false)
    })
  })

  describe('sub-page navigation', () => {
    it('navigates forward through sub-pages', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      expect(store.profileSubPage).toBe('basics')
      store.nextSubPage()
      expect(store.profileSubPage).toBe('keywords')
      store.nextSubPage()
      expect(store.profileSubPage).toBe('ingredients')
    })

    it('navigates backward through sub-pages', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      store.profileSubPage = 'ingredients'

      store.prevSubPage()
      expect(store.profileSubPage).toBe('keywords')
      store.prevSubPage()
      expect(store.profileSubPage).toBe('basics')
    })

    it('goes back to step 2 from basics', () => {
      const store = useSetupStore()
      store.step = 3
      store.presets[0].selected = true
      store.buildProfileQueue()
      store.profileSubPage = 'basics'

      store.prevSubPage()
      expect(store.step).toBe(2)
    })

    it('goToSubPage jumps to specific page', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.goToSubPage('rating')
      expect(store.profileSubPage).toBe('rating')
    })

    it('subPageIndex is correct', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.profileSubPage = 'keywords'
      expect(store.subPageIndex).toBe(1)

      store.profileSubPage = 'review'
      expect(store.subPageIndex).toBe(8)
    })
  })

  describe('profile advancement', () => {
    it('advances to next profile', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.presets[1].selected = true
      store.buildProfileQueue()

      store.profileSubPage = 'review'
      store.advanceProfile()
      expect(store.profileIndex).toBe(1)
      expect(store.profileSubPage).toBe('basics')
    })

    it('advances to step 4 after last profile', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.advanceProfile()
      expect(store.step).toBe(4)
    })
  })

  describe('rule summary', () => {
    it('returns empty when no rules active', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      expect(store.ruleSummary).toEqual([])
    })

    it('summarizes keyword theme rule', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      const rules = store.currentProfile!.rules
      rules.tagsInclude.active = true
      rules.tagsInclude.theme = [{ id: 1, name: 'Italian' }]

      expect(store.ruleSummary).toHaveLength(1)
      expect(store.ruleSummary[0].text).toContain('Italian')
      expect(store.ruleSummary[0].page).toBe('keywords')
    })

    it('summarizes rating rule', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.currentProfile!.rules.rating.active = true
      store.currentProfile!.rules.rating.min = 4

      expect(store.ruleSummary).toHaveLength(1)
      expect(store.ruleSummary[0].text).toBe('Minimum rating: 4 stars')
    })

    it('summarizes multiple rules', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      const rules = store.currentProfile!.rules
      rules.rating.active = true
      rules.avoidRecent.active = true
      rules.avoidRecent.days = 14

      expect(store.ruleSummary).toHaveLength(2)
    })
  })

  describe('hasActiveConstraint', () => {
    it('false when no rules active', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      expect(store.hasActiveConstraint).toBe(false)
    })

    it('true when any rule is active', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      store.currentProfile!.rules.rating.active = true
      expect(store.hasActiveConstraint).toBe(true)
    })
  })

  describe('tag/food/book helpers', () => {
    it('addThemeKeyword and removeThemeKeyword', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addThemeKeyword({ id: 1, name: 'Italian' })
      expect(store.currentProfile!.rules.tagsInclude.theme).toHaveLength(1)

      store.removeThemeKeyword(0)
      expect(store.currentProfile!.rules.tagsInclude.theme).toHaveLength(0)
    })

    it('addBalanceKeyword tracks count', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addBalanceKeyword({ id: 1, name: 'Quick' })
      expect(store.currentProfile!.rules.tagsInclude.balance[0].count).toBe(1)
      expect(store.balanceAssigned).toBe(1)
    })

    it('balanceComplete when assigned >= choices', () => {
      const store = useSetupStore()
      store.presets[0].selected = true // 3 choices
      store.buildProfileQueue()

      store.addBalanceKeyword({ id: 1, name: 'Quick' })
      store.currentProfile!.rules.tagsInclude.balance[0].count = 3
      expect(store.balanceComplete).toBe(true)
    })

    it('keywordExclusionSet combines theme and balance ids', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addThemeKeyword({ id: 1, name: 'Italian' })
      store.addBalanceKeyword({ id: 2, name: 'Quick' })

      const excluded = store.keywordExclusionSet()
      expect(excluded.has(1)).toBe(true)
      expect(excluded.has(2)).toBe(true)
      expect(excluded.has(3)).toBe(false)
    })

    it('addIncludeFood and removeIncludeFood', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addIncludeFood({ id: 10, name: 'Chicken' })
      expect(store.currentProfile!.rules.foodsInclude.items).toHaveLength(1)

      store.removeIncludeFood(0)
      expect(store.currentProfile!.rules.foodsInclude.items).toHaveLength(0)
    })

    it('addFoodException and removeFoodException', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addFoodException({ id: 20, name: 'Shellfish' })
      expect(store.currentProfile!.rules.foodsInclude.except).toHaveLength(1)

      store.removeFoodException(0)
      expect(store.currentProfile!.rules.foodsInclude.except).toHaveLength(0)
    })

    it('addBook and removeBook', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addBook({ id: 5, name: 'Weeknight Favorites' })
      expect(store.currentProfile!.rules.booksInclude.items).toHaveLength(1)

      store.removeBook(0)
      expect(store.currentProfile!.rules.booksInclude.items).toHaveLength(0)
    })

    it('addExcludeKeyword and removeExcludeKeyword', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addExcludeKeyword({ id: 3, name: 'Seafood' })
      expect(store.currentProfile!.rules.tagsExclude.items).toHaveLength(1)

      store.removeExcludeKeyword(0)
      expect(store.currentProfile!.rules.tagsExclude.items).toHaveLength(0)
    })

    it('addExcludeFood and removeExcludeFood', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.addExcludeFood({ id: 30, name: 'Peanuts' })
      expect(store.currentProfile!.rules.foodsExclude.items).toHaveLength(1)

      store.removeExcludeFood(0)
      expect(store.currentProfile!.rules.foodsExclude.items).toHaveLength(0)
    })
  })

  describe('rating and freshness', () => {
    it('setRating updates min', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      store.setRating(3)
      expect(store.currentProfile!.rules.rating.min).toBe(3)
    })

    it('setAvoidDays updates days', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      store.setAvoidDays(21)
      expect(store.currentProfile!.rules.avoidRecent.days).toBe(21)
    })

    it('avoidDaysIsPreset for standard values', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()

      store.currentProfile!.rules.avoidRecent.days = 14
      expect(store.avoidDaysIsPreset).toBe(true)

      store.currentProfile!.rules.avoidRecent.days = 10
      expect(store.avoidDaysIsPreset).toBe(false)
    })
  })

  describe('choices helpers', () => {
    it('incrementChoices up to 50', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      store.currentProfile!.choices = 49
      store.incrementChoices()
      expect(store.currentProfile!.choices).toBe(50)
      store.incrementChoices()
      expect(store.currentProfile!.choices).toBe(50)
    })

    it('decrementChoices down to min_choices or 1', () => {
      const store = useSetupStore()
      store.presets[0].selected = true
      store.buildProfileQueue()
      store.currentProfile!.choices = 2
      store.decrementChoices()
      expect(store.currentProfile!.choices).toBe(1)
      store.decrementChoices()
      expect(store.currentProfile!.choices).toBe(1)
    })
  })

  describe('categories', () => {
    it('toggleCategory flips selection', () => {
      const store = useSetupStore()
      const cat = store.categoryPresets[0]
      expect(cat.selected).toBe(true) // defaults to selected
      store.toggleCategory(cat)
      expect(cat.selected).toBe(false)
    })

    it('addCustomCategory and removeCustomCategory', () => {
      const store = useSetupStore()
      store.customCatName = 'Cocktails'
      store.addCustomCategory()
      expect(store.customCategories).toHaveLength(1)
      expect(store.customCategories[0].display_name).toBe('Cocktails')
      expect(store.customCatName).toBe('')

      store.removeCustomCategory(0)
      expect(store.customCategories).toHaveLength(0)
    })

    it('rejects blank category names', () => {
      const store = useSetupStore()
      store.customCatName = '  '
      store.addCustomCategory()
      expect(store.customCategories).toHaveLength(0)
    })
  })
})
