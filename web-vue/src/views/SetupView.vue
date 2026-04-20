<script setup lang="ts">
import { onMounted, onUnmounted, computed } from 'vue'
import { useSetupStore } from '@/stores/setup'
import { CONST } from '@/constants'
import ProgressBar from '@/components/setup/ProgressBar.vue'
import ChoiceCard from '@/components/setup/ChoiceCard.vue'
import SearchBox from '@/components/setup/SearchBox.vue'
import ChipList from '@/components/setup/ChipList.vue'
import NumberControl from '@/components/setup/NumberControl.vue'

const store = useSetupStore()

// Computed exclusion sets for search boxes
const themeExcludeIds = computed(() => store.keywordExclusionSet())
const balanceExcludeIds = computed(() => store.keywordExclusionSet())
const foodIncludeExcludeIds = computed(
  () => new Set(store.currentProfile?.rules.foodsInclude.items.map((i) => i.id) ?? []),
)
const foodExceptExcludeIds = computed(
  () => new Set(store.currentProfile?.rules.foodsInclude.except.map((i) => i.id) ?? []),
)
const bookExcludeIds = computed(
  () => new Set(store.currentProfile?.rules.booksInclude.items.map((i) => i.id) ?? []),
)
const excludeKeywordExcludeIds = computed(
  () => new Set(store.currentProfile?.rules.tagsExclude.items.map((i) => i.id) ?? []),
)
const excludeFoodExcludeIds = computed(
  () => new Set(store.currentProfile?.rules.foodsExclude.items.map((i) => i.id) ?? []),
)

const minChoicesDisplay = computed(
  () => store.currentProfile?.min_choices ?? store.currentProfile?.choices ?? 1,
)

const recipeRangeText = computed(() => {
  const p = store.currentProfile
  if (!p) return ''
  if (p.min_choices && p.min_choices !== p.choices) {
    return `${p.min_choices}\u2013${p.choices} recipes`
  }
  return `${p.choices} recipes`
})

onMounted(() => {
  store.init()
})

// No persistent state to clean up beyond the store
</script>

<template>
  <div class="setup-page">
    <div class="setup-container">
      <!-- Progress bar (hidden in add-profile mode) -->
      <ProgressBar
        v-if="!store.addProfileMode"
        :step="store.step"
        :total-steps="6"
      />

      <!-- ============================================ -->
      <!-- Step 1: Connect to Tandoor                   -->
      <!-- ============================================ -->
      <Transition name="step">
        <div v-if="store.step === 1" class="setup-step-content">
          <h2 class="setup-title">Connect to Tandoor</h2>
          <p class="setup-subtitle">
            Enter your Tandoor instance URL and API token to get started.
          </p>

          <div class="setup-field">
            <label class="setup-label" for="setup-url">Tandoor URL</label>
            <input
              id="setup-url"
              v-model="store.url"
              type="url"
              class="setup-input"
              placeholder="https://tandoor.example.com"
              @keydown.enter="store.testConnection()"
            >
          </div>

          <div class="setup-field">
            <label class="setup-label" for="setup-token">API Token</label>
            <input
              id="setup-token"
              v-model="store.token"
              type="password"
              class="setup-input"
              placeholder="Your Tandoor API token"
              @keydown.enter="store.testConnection()"
            >
            <span class="setup-hint">Found in Tandoor under Settings &rarr; API Tokens</span>
            <details class="setup-details">
              <summary>How do I get a token?</summary>
              <ol class="setup-help-steps">
                <li>Open your Tandoor instance in a browser</li>
                <li>Click the user icon (top right) &rarr; <strong>Settings</strong></li>
                <li>Scroll down to <strong>API Tokens</strong></li>
                <li>Click <strong>Create</strong>, give it a name (e.g. "morsl"), and copy the token</li>
              </ol>
            </details>
          </div>

          <div
            v-if="store.testResult"
            class="setup-test-result"
            :class="{ success: store.testResult.success, error: !store.testResult.success }"
            role="alert"
          >
            <span v-if="store.testResult.success">&#10003; Connection successful</span>
            <span v-else>&#10007; {{ store.testResult.error || 'Connection failed' }}</span>
          </div>

          <p
            v-if="store.error"
            class="setup-test-result error"
            role="alert"
          >
            {{ store.error }}
          </p>

          <div class="setup-actions">
            <button
              class="setup-btn setup-btn-secondary"
              :disabled="!store.url || !store.token || store.testing"
              @click="store.testConnection()"
            >
              {{ store.testing ? 'Testing...' : 'Test Connection' }}
            </button>
            <button
              class="setup-btn setup-btn-primary"
              :disabled="!store.testResult?.success || store.saving"
              @click="store.saveCredentials()"
            >
              {{ store.saving ? 'Saving...' : 'Save & Continue' }}
            </button>
          </div>
        </div>
      </Transition>

      <!-- ============================================ -->
      <!-- Step 2: Choose Profiles                      -->
      <!-- ============================================ -->
      <Transition name="step">
        <div v-if="store.step === 2" class="setup-step-content">
          <h2 class="setup-title">Set Up Your Meal Plans</h2>
          <p class="setup-subtitle">
            Each profile tells the app what kind of meals to plan for you &mdash;
            like breakfasts, weeknight dinners, or weekend cooking projects.
            Pick a few presets to get started, or create your own.
          </p>

          <div class="setup-card-grid">
            <div
              v-for="preset in store.presets"
              :key="preset.key"
              class="setup-preset-card"
              :class="{ selected: preset.selected }"
              role="checkbox"
              tabindex="0"
              :aria-checked="preset.selected"
              @click="store.togglePreset(preset)"
              @keydown.enter="store.togglePreset(preset)"
              @keydown.space.prevent="store.togglePreset(preset)"
            >
              <span class="card-check">&#10003;</span>
              <div class="card-name">{{ preset.name }}</div>
              <div class="card-subtitle">{{ preset.subtitle }}</div>
            </div>
          </div>

          <!-- Custom profiles -->
          <div
            v-for="(cp, cpIdx) in store.customProfiles"
            :key="cp._id"
            class="setup-custom-row"
          >
            <span style="flex:1; font-size:0.9rem;">{{ cp.name }}</span>
            <button
              class="setup-btn setup-btn-secondary"
              style="padding:0.3rem 0.6rem; font-size:0.8rem;"
              @click="store.removeCustomProfile(cpIdx)"
            >
              &times; Remove
            </button>
          </div>

          <div class="setup-custom-row">
            <input
              v-model="store.customProfileName"
              class="setup-input"
              type="text"
              placeholder="Custom profile name"
              @keydown.enter="store.addCustomProfile()"
            >
            <button
              class="setup-btn setup-btn-secondary"
              style="padding:0.4rem 0.8rem; white-space:nowrap;"
              :disabled="!store.customProfileName.trim()"
              @click="store.addCustomProfile()"
            >
              + Add
            </button>
          </div>

          <div class="setup-actions">
            <button
              class="setup-btn setup-btn-secondary"
              @click="store.addProfileMode ? (window.location.href = '/admin') : (store.step = 1)"
            >
              Back
            </button>
            <button
              v-if="!store.addProfileMode"
              class="setup-btn setup-btn-secondary"
              @click="store.profileQueue = []; store.step = 4"
            >
              Skip for Now
            </button>
            <button
              class="setup-btn setup-btn-primary"
              :disabled="!store.hasProfileSelections"
              @click="store.buildProfileQueue()"
            >
              Next
            </button>
          </div>
        </div>
      </Transition>

      <!-- ============================================ -->
      <!-- Step 3: Configure Profile                    -->
      <!-- ============================================ -->
      <Transition name="step">
        <div
          v-if="store.step === 3 && store.currentProfile"
          class="setup-step-content"
        >
          <!-- Profile progress indicator -->
          <div v-if="store.profileQueue.length > 1" class="setup-profile-indicator">
            <span>
              Profile <strong>{{ store.profileIndex + 1 }}</strong>
              of <strong>{{ store.profileQueue.length }}</strong>
            </span>
            <div class="setup-profile-dots">
              <span
                v-for="(_, pi) in store.profileQueue"
                :key="pi"
                class="setup-profile-dot"
                :class="{ active: pi === store.profileIndex }"
              />
            </div>
          </div>

          <!-- Sub-page A: Basics -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'basics'" :key="'basics'">
              <h2 class="setup-title">
                {{ store.addProfileMode ? 'New Profile' : 'Configure: ' + (store.currentProfile.name || '') }}
              </h2>
              <p class="setup-subtitle">
                {{ store.addProfileMode
                  ? 'Give your profile a name and set the basics.'
                  : 'Set up the basics for this profile. You can always change these later in the admin panel.'
                }}
              </p>

              <div class="setup-field">
                <label class="setup-label">Profile Name</label>
                <input
                  v-model="store.currentProfile.name"
                  type="text"
                  class="setup-input"
                  placeholder="Profile name"
                >
              </div>

              <div class="setup-field">
                <label class="setup-label">Description</label>
                <textarea
                  v-model="store.currentProfile.description"
                  class="setup-input"
                  placeholder="What kind of recipes is this profile for?"
                  rows="2"
                />
                <span class="setup-hint">Optional &mdash; helps you remember the purpose of this profile</span>
              </div>

              <div v-if="store.availableCategories.length > 0" class="setup-field">
                <label class="setup-label">Category</label>
                <select v-model="store.currentProfile.category" class="setup-input">
                  <option value="">No category</option>
                  <option
                    v-for="cat in store.availableCategories"
                    :key="cat.id"
                    :value="cat.id"
                  >
                    {{ cat.display_name }}
                  </option>
                </select>
                <span class="setup-hint">Which tab this profile appears under on the menu page</span>
              </div>

              <div class="setup-field">
                <label class="setup-label">Number of Recipes</label>
                <div class="setup-range-row">
                  <span>Between</span>
                  <NumberControl
                    :model-value="minChoicesDisplay"
                    :min="1"
                    :max="store.currentProfile.choices"
                    @update:model-value="store.currentProfile.min_choices = $event"
                    @increment="store.incrementMin()"
                    @decrement="store.decrementMin()"
                  />
                  <span>and</span>
                  <NumberControl
                    :model-value="store.currentProfile.choices"
                    :min="store.currentProfile.min_choices || 1"
                    :max="50"
                    @update:model-value="store.currentProfile.choices = $event"
                    @increment="store.incrementChoices()"
                    @decrement="store.decrementChoices()"
                  />
                  <span>recipes</span>
                </div>
                <span class="setup-hint">The solver will pick a number of recipes in this range</span>
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page dots -->
          <div
            v-if="store.profileSubPage !== 'basics'"
            class="setup-sub-dots"
            :aria-label="'Step ' + (store.subPageIndex + 1) + ' of ' + store.subPageCount + ': ' + store.profileSubPage"
          >
            <span
              v-for="(pg, pi) in store.rulePages"
              :key="pg"
              class="setup-sub-dot"
              :class="{ active: pi === store.subPageIndex, done: pi < store.subPageIndex }"
            />
          </div>

          <!-- Sub-page B: Keywords -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'keywords'" :key="'keywords'">
              <h2 class="setup-title">
                What kind of recipes should <em>{{ store.currentProfile.name || 'this profile' }}</em> pick?
              </h2>
              <p class="setup-subtitle">
                Keywords in Tandoor describe your recipes &mdash; things like "Breakfast," "Lunch," "Main Course," or "Vegetarian."
              </p>

              <div class="setup-choice-group" role="radiogroup" aria-label="Keyword preference">
                <ChoiceCard
                  :selected="!store.currentProfile.rules.tagsInclude.active"
                  label="Any recipe is fine"
                  description="Don't limit by keywords. This profile will choose from all your recipes."
                  @select="store.currentProfile.rules.tagsInclude.active = false"
                />
                <ChoiceCard
                  :selected="store.currentProfile.rules.tagsInclude.active"
                  label="Use keywords"
                  description="Focus on a theme, balance your mix, or both."
                  @select="store.currentProfile.rules.tagsInclude.active = true"
                />
              </div>

              <div v-if="store.currentProfile.rules.tagsInclude.active">
                <!-- Theme sub-section -->
                <div class="setup-section-label">Theme or Style</div>
                <p class="setup-hint" style="margin-bottom: 0.5rem; font-style: normal;">
                  Focus all recipes on a theme &mdash; like Italian, or Quick and Easy.
                </p>

                <ChipList
                  :items="store.currentProfile.rules.tagsInclude.theme"
                  @remove="store.removeThemeKeyword($event)"
                />
                <SearchBox
                  endpoint="/api/keywords"
                  :debounce-ms="CONST.KEYWORD_DEBOUNCE_MS"
                  placeholder="Search keywords..."
                  aria-label="Search theme keywords"
                  :exclude-ids="themeExcludeIds"
                  @select="store.addThemeKeyword($event)"
                />
                <div v-if="store.currentProfile.rules.tagsInclude.theme.length" class="setup-sentence">
                  <span>All <strong>{{ store.currentProfile.choices }}</strong> recipes will match at least one of these keywords.</span>
                </div>

                <!-- Balance sub-section -->
                <div class="setup-section-label">Balance the Mix</div>
                <p class="setup-hint" style="margin-bottom: 0.5rem; font-style: normal;">
                  Set how many recipes come from each keyword.
                </p>

                <div v-if="store.currentProfile.rules.tagsInclude.balance.length">
                  <div
                    v-for="(tag, tagIdx) in store.currentProfile.rules.tagsInclude.balance"
                    :key="tag.id"
                    class="setup-keyword-row"
                  >
                    <span class="setup-chip">
                      <span>{{ tag.name }}</span>
                      <button
                        :aria-label="'Remove ' + tag.name"
                        @click="store.removeBalanceKeyword(tagIdx)"
                      >
                        &times;
                      </button>
                    </span>
                    <span class="setup-keyword-row-sentence">at least</span>
                    <input
                      v-model.number="tag.count"
                      type="number"
                      min="1"
                      :max="store.currentProfile.choices"
                      class="setup-count-inline"
                      :aria-label="'Count for ' + tag.name"
                    >
                    <span class="setup-keyword-row-sentence">{{ tag.count === 1 ? 'recipe' : 'recipes' }}</span>
                  </div>
                </div>

                <SearchBox
                  endpoint="/api/keywords"
                  :debounce-ms="CONST.KEYWORD_DEBOUNCE_MS"
                  placeholder="Search keywords..."
                  aria-label="Search balance keywords"
                  :exclude-ids="balanceExcludeIds"
                  @select="store.addBalanceKeyword($event)"
                />

                <div
                  v-if="store.currentProfile.rules.tagsInclude.balance.length > 0"
                  class="setup-balance-progress"
                  :class="{ complete: store.balanceComplete }"
                  role="progressbar"
                  :aria-valuenow="store.balanceAssigned"
                  :aria-valuemax="store.currentProfile.choices"
                >
                  <span>{{ store.balanceAssigned }} of {{ store.currentProfile.choices }} recipes assigned</span>
                  <span v-if="store.balanceComplete">&#10003;</span>
                  <span v-else> &mdash; add more keywords to fill your plan</span>
                </div>
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page C: Ingredients -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'ingredients'" :key="'ingredients'">
              <h2 class="setup-title">Prefer certain ingredients?</h2>
              <p class="setup-subtitle">
                If you want this profile to favor recipes with specific ingredients &mdash;
                like chicken, tofu, or seasonal produce &mdash; add them here.
              </p>

              <div class="setup-choice-group" role="radiogroup" aria-label="Ingredient preference">
                <ChoiceCard
                  :selected="!store.currentProfile.rules.foodsInclude.active"
                  label="No ingredient preference"
                  description="Any ingredients are fine."
                  @select="store.currentProfile.rules.foodsInclude.active = false"
                />
                <ChoiceCard
                  :selected="store.currentProfile.rules.foodsInclude.active"
                  label="Favor specific ingredients"
                  description="Pick recipes that use certain ingredients."
                  @select="store.currentProfile.rules.foodsInclude.active = true"
                />
              </div>

              <div v-if="store.currentProfile.rules.foodsInclude.active" class="setup-config-section">
                <ChipList
                  :items="store.currentProfile.rules.foodsInclude.items"
                  @remove="store.removeIncludeFood($event)"
                />
                <SearchBox
                  endpoint="/api/foods"
                  :debounce-ms="CONST.FOOD_DEBOUNCE_MS"
                  placeholder="Search ingredients..."
                  aria-label="Search ingredients"
                  :exclude-ids="foodIncludeExcludeIds"
                  @select="store.addIncludeFood($event)"
                />
                <div v-if="store.currentProfile.rules.foodsInclude.items.length" class="setup-sentence">
                  <span>Pick <strong>at least</strong></span>
                  <input v-model.number="store.currentProfile.rules.foodsInclude.count" type="number" min="1">
                  <span>recipes with any of these ingredients</span>
                </div>

                <!-- Exception foods -->
                <template v-if="store.currentProfile.rules.foodsInclude.items.length">
                  <div class="setup-section-label" style="margin-top:1.25rem;">But not:</div>
                  <ChipList
                    :items="store.currentProfile.rules.foodsInclude.except"
                    variant="exclude"
                    @remove="store.removeFoodException($event)"
                  />
                  <SearchBox
                    endpoint="/api/foods"
                    :debounce-ms="CONST.FOOD_DEBOUNCE_MS"
                    placeholder="Search ingredients to exclude..."
                    aria-label="Search ingredients to exclude"
                    :exclude-ids="foodExceptExcludeIds"
                    @select="store.addFoodException($event)"
                  />
                </template>
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page D: Books -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'books'" :key="'books'">
              <h2 class="setup-title">Pick from a recipe book?</h2>
              <p class="setup-subtitle">
                Tandoor lets you organize recipes into books &mdash; like curated collections.
                You can tell this profile to only pick from specific books.
              </p>

              <div class="setup-choice-group" role="radiogroup" aria-label="Book preference">
                <ChoiceCard
                  :selected="!store.currentProfile.rules.booksInclude.active"
                  label="All recipes"
                  description="Don't limit by book. Choose from your entire collection."
                  @select="store.currentProfile.rules.booksInclude.active = false"
                />
                <ChoiceCard
                  :selected="store.currentProfile.rules.booksInclude.active"
                  label="Pick from specific books"
                  description="Only use recipes from certain books."
                  @select="store.currentProfile.rules.booksInclude.active = true"
                />
              </div>

              <div v-if="store.currentProfile.rules.booksInclude.active" class="setup-config-section">
                <ChipList
                  :items="store.currentProfile.rules.booksInclude.items"
                  @remove="store.removeBook($event)"
                />
                <SearchBox
                  endpoint="/api/books"
                  :debounce-ms="CONST.BOOK_DEBOUNCE_MS"
                  placeholder="Search books..."
                  aria-label="Search books"
                  :exclude-ids="bookExcludeIds"
                  @select="store.addBook($event)"
                />
                <div v-if="store.currentProfile.rules.booksInclude.items.length" class="setup-sentence">
                  <span>Pick <strong>at least</strong></span>
                  <input v-model.number="store.currentProfile.rules.booksInclude.count" type="number" min="1">
                  <span>recipes from any of these books</span>
                </div>
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page E: Avoid -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'avoid'" :key="'avoid'">
              <h2 class="setup-title">Anything you want to avoid?</h2>
              <p class="setup-subtitle">
                If there are keywords or ingredients you never want this profile to pick,
                list them here. Great for allergies, dietary restrictions, or categories you want to skip.
              </p>

              <div class="setup-choice-group" role="radiogroup" aria-label="Avoidance preference">
                <ChoiceCard
                  :selected="!store.currentProfile.rules.tagsExclude.active && !store.currentProfile.rules.foodsExclude.active"
                  label="No restrictions"
                  description="Any recipe is fair game."
                  @select="store.currentProfile.rules.tagsExclude.active = false; store.currentProfile.rules.foodsExclude.active = false"
                />
                <ChoiceCard
                  :selected="store.currentProfile.rules.tagsExclude.active || store.currentProfile.rules.foodsExclude.active"
                  label="Avoid certain keywords or ingredients"
                  description="Keep specific things out of this profile's picks."
                  @select="store.currentProfile.rules.tagsExclude.active = true; store.currentProfile.rules.foodsExclude.active = true"
                />
              </div>

              <div v-if="store.currentProfile.rules.tagsExclude.active || store.currentProfile.rules.foodsExclude.active" class="setup-config-section">
                <div class="setup-section-label">Keywords to exclude:</div>
                <ChipList
                  :items="store.currentProfile.rules.tagsExclude.items"
                  variant="exclude"
                  @remove="store.removeExcludeKeyword($event)"
                />
                <SearchBox
                  endpoint="/api/keywords"
                  :debounce-ms="CONST.KEYWORD_DEBOUNCE_MS"
                  placeholder="Search keywords to avoid..."
                  aria-label="Search keywords to avoid"
                  :exclude-ids="excludeKeywordExcludeIds"
                  @select="store.addExcludeKeyword($event)"
                />

                <div class="setup-section-label">Ingredients to exclude:</div>
                <ChipList
                  :items="store.currentProfile.rules.foodsExclude.items"
                  variant="exclude"
                  @remove="store.removeExcludeFood($event)"
                />
                <SearchBox
                  endpoint="/api/foods"
                  :debounce-ms="CONST.FOOD_DEBOUNCE_MS"
                  placeholder="Search ingredients to avoid..."
                  aria-label="Search ingredients to avoid"
                  :exclude-ids="excludeFoodExcludeIds"
                  @select="store.addExcludeFood($event)"
                />
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page F: Rating -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'rating'" :key="'rating'">
              <h2 class="setup-title">Only the good stuff?</h2>
              <p class="setup-subtitle">
                If you rate recipes in Tandoor, you can tell this profile to skip low-rated ones.
                Unrated recipes are always included &mdash; this only filters out recipes you've
                explicitly rated below the threshold.
              </p>

              <div class="setup-choice-group" role="radiogroup" aria-label="Rating preference">
                <ChoiceCard
                  :selected="!store.currentProfile.rules.rating.active"
                  label="Include all ratings"
                  description="Don't filter by rating. Even lower-rated recipes can appear."
                  @select="store.currentProfile.rules.rating.active = false"
                />
                <ChoiceCard
                  :selected="store.currentProfile.rules.rating.active"
                  label="Set a minimum rating"
                  description="Only pick recipes rated above a threshold."
                  @select="store.currentProfile.rules.rating.active = true"
                />
              </div>

              <div v-if="store.currentProfile.rules.rating.active" class="setup-config-section">
                <span style="font-size:0.85rem; color:var(--text-muted);">Minimum rating:</span>
                <div class="setup-star-row" role="radiogroup" aria-label="Minimum star rating">
                  <span
                    v-for="s in [1, 2, 3, 4, 5]"
                    :key="s"
                    class="setup-star"
                    role="radio"
                    tabindex="0"
                    :aria-checked="s <= (store.currentProfile.rules.rating.min || 0)"
                    :aria-label="s + ' star' + (s > 1 ? 's' : '')"
                    :class="{ filled: s <= (store.currentProfile.rules.rating.min || 0) }"
                    @click="store.setRating(s)"
                    @keydown.enter="store.setRating(s)"
                    @keydown.space.prevent="store.setRating(s)"
                  >
                    &#9733;
                  </span>
                </div>
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page G: Freshness -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'freshness'" :key="'freshness'">
              <h2 class="setup-title">Keep things fresh?</h2>
              <p class="setup-subtitle">
                If you log when you cook in Tandoor, this profile can avoid picking things
                you've made recently. Great for keeping your meal plans varied from week to week.
              </p>

              <div class="setup-choice-group" role="radiogroup" aria-label="Freshness preference">
                <ChoiceCard
                  :selected="!store.currentProfile.rules.avoidRecent.active"
                  label="Repeats are fine"
                  description="Don't worry about what I've cooked recently."
                  @select="store.currentProfile.rules.avoidRecent.active = false"
                />
                <ChoiceCard
                  :selected="store.currentProfile.rules.avoidRecent.active"
                  label="Avoid recent repeats"
                  description="Skip recipes I've made in the last..."
                  @select="store.currentProfile.rules.avoidRecent.active = true"
                />
              </div>

              <div v-if="store.currentProfile.rules.avoidRecent.active" class="setup-config-section">
                <div class="setup-day-presets">
                  <button
                    v-for="d in [7, 14, 21, 30]"
                    :key="d"
                    :class="{ active: store.currentProfile.rules.avoidRecent.days === d }"
                    :aria-label="d + ' days'"
                    @click="store.setAvoidDays(d)"
                  >
                    {{ d }}
                  </button>
                  <button
                    :class="{ active: !store.avoidDaysIsPreset }"
                    aria-label="Custom days"
                    @click="store.setAvoidDays(10)"
                  >
                    Custom
                  </button>
                </div>
                <div v-if="!store.avoidDaysIsPreset" class="setup-custom-days">
                  <input
                    v-model.number="store.currentProfile.rules.avoidRecent.days"
                    type="number"
                    min="1"
                    max="365"
                  >
                  <span>days</span>
                </div>
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page H: New Recipes -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'new-recipes'" :key="'new-recipes'">
              <h2 class="setup-title">Try new recipes?</h2>
              <p class="setup-subtitle">
                When you add new recipes to Tandoor, this profile can make sure some of them
                show up in your meal plans. Keeps new finds from getting buried.
              </p>

              <div class="setup-choice-group" role="radiogroup" aria-label="New recipe preference">
                <ChoiceCard
                  :selected="!store.currentProfile.rules.includeNew.active"
                  label="All recipes are equal"
                  description="New recipes have the same chance as old ones."
                  @select="store.currentProfile.rules.includeNew.active = false"
                />
                <ChoiceCard
                  :selected="store.currentProfile.rules.includeNew.active"
                  label="Include some new additions"
                  description="Guarantee recently added recipes get picked."
                  @select="store.currentProfile.rules.includeNew.active = true"
                />
              </div>

              <div v-if="store.currentProfile.rules.includeNew.active" class="setup-config-section">
                <div class="setup-sentence">
                  <span>Include at least</span>
                  <input v-model.number="store.currentProfile.rules.includeNew.count" type="number" min="1">
                  <span>recipe(s) added in the last</span>
                  <input v-model.number="store.currentProfile.rules.includeNew.days" type="number" min="1">
                  <span>days</span>
                </div>
              </div>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button class="setup-btn setup-btn-primary" @click="store.nextSubPage()">Next</button>
              </div>
            </div>
          </Transition>

          <!-- Sub-page I: Review -->
          <Transition name="fade">
            <div v-if="store.profileSubPage === 'review'" :key="'review'">
              <h2 class="setup-title">Review: <em>{{ store.currentProfile.name || '' }}</em></h2>
              <p class="setup-subtitle">
                Here's what this profile will do. You can always fine-tune it later in the admin panel.
              </p>

              <div class="setup-review-card">
                <div class="setup-review-header">
                  <div>
                    <div class="setup-review-name">{{ store.currentProfile.name || '' }}</div>
                    <div class="setup-review-meta">
                      <span>{{ recipeRangeText }}</span>
                      <template v-if="store.currentProfile.description">
                        <span> &mdash; {{ store.currentProfile.description }}</span>
                      </template>
                    </div>
                  </div>
                </div>

                <ul v-if="store.ruleSummary.length > 0" class="setup-review-rules">
                  <li
                    v-for="(line, li) in store.ruleSummary"
                    :key="li"
                    class="setup-review-line"
                    tabindex="0"
                    @click="store.goToSubPage(line.page)"
                    @keydown.enter="store.goToSubPage(line.page)"
                  >
                    {{ line.text }}
                  </li>
                </ul>
                <div v-else class="setup-review-empty">
                  No rules &mdash; picks from all your recipes.
                </div>
              </div>

              <p v-if="store.error" class="setup-test-result error" role="alert">
                {{ store.error }}
              </p>

              <div class="setup-actions">
                <button class="setup-btn setup-btn-secondary" @click="store.skipProfile()">Skip</button>
                <button class="setup-btn setup-btn-secondary" @click="store.prevSubPage()">Back</button>
                <button
                  class="setup-btn setup-btn-primary"
                  :disabled="store.saving || !store.currentProfile.name?.trim() || !store.hasActiveConstraint"
                  @click="store.createCurrentProfile()"
                >
                  {{ store.saving ? 'Creating...' : 'Create Profile' }}
                </button>
              </div>
              <p
                v-if="!store.hasActiveConstraint"
                class="setup-hint"
                style="text-align:center;margin-top:0.5rem;color:var(--accent-color);font-weight:600;"
              >
                Toggle at least one rule above to create this profile
              </p>
            </div>
          </Transition>
        </div>
      </Transition>

      <!-- ============================================ -->
      <!-- Step 4: Categories                           -->
      <!-- ============================================ -->
      <Transition name="step">
        <div v-if="store.step === 4" class="setup-step-content">
          <h2 class="setup-title">Configure Categories</h2>
          <p class="setup-subtitle">
            Categories group your profiles into tabs on the menu page.
            Pick some presets or add your own.
          </p>

          <div class="setup-category-list">
            <div
              v-for="preset in store.categoryPresets"
              :key="preset.key"
              class="setup-category-card"
              :class="{ selected: preset.selected }"
              role="checkbox"
              tabindex="0"
              :aria-checked="preset.selected"
              @click="store.toggleCategory(preset)"
              @keydown.enter="store.toggleCategory(preset)"
              @keydown.space.prevent="store.toggleCategory(preset)"
            >
              <div class="cat-info">
                <div class="cat-name">{{ preset.display_name }}</div>
                <div class="cat-sub">{{ preset.subtitle }}</div>
              </div>
              <span class="cat-check">&#10003;</span>
            </div>
          </div>

          <!-- Custom categories -->
          <div
            v-for="(custom, cidx) in store.customCategories"
            :key="custom._id"
            class="setup-custom-row"
            style="margin-bottom:0.5rem;"
          >
            <span style="flex:1; font-size:0.9rem;">{{ custom.display_name }}</span>
            <button
              class="setup-btn setup-btn-secondary"
              style="padding:0.3rem 0.6rem; font-size:0.8rem;"
              @click="store.removeCustomCategory(cidx)"
            >
              &times; Remove
            </button>
          </div>

          <div class="setup-custom-row">
            <input
              v-model="store.customCatName"
              class="setup-input"
              type="text"
              placeholder="Custom category name"
              @keydown.enter="store.addCustomCategory()"
            >
            <button
              class="setup-btn setup-btn-secondary"
              style="padding:0.4rem 0.8rem; white-space:nowrap;"
              :disabled="!store.customCatName.trim()"
              @click="store.addCustomCategory()"
            >
              + Add
            </button>
          </div>

          <p v-if="store.error" class="setup-test-result error" role="alert">
            {{ store.error }}
          </p>

          <div class="setup-actions">
            <button
              class="setup-btn setup-btn-secondary"
              @click="store.step = store.profileQueue.length > 0 ? 3 : 2"
            >
              Back
            </button>
            <button class="setup-btn setup-btn-secondary" @click="store.step = 5">Skip</button>
            <button
              class="setup-btn setup-btn-primary"
              :disabled="store.saving"
              @click="store.createCategories()"
            >
              {{ store.saving ? 'Creating...' : 'Create Categories' }}
            </button>
          </div>
        </div>
      </Transition>

      <!-- ============================================ -->
      <!-- Step 5: Assign profiles to categories        -->
      <!-- ============================================ -->
      <Transition name="step">
        <div v-if="store.step === 5" class="setup-step-content">
          <h2 class="setup-title">Organize Your Profiles</h2>
          <p class="setup-subtitle">
            Assign each profile to a category. This controls which tab it appears under on the menu page.
          </p>

          <div style="display:flex; flex-direction:column; gap:0.75rem; margin-bottom:1.25rem;">
            <div
              v-for="pa in store.profileAssignments"
              :key="pa.name"
              class="setup-assignment-row"
            >
              <span class="setup-assignment-name">{{ pa.name }}</span>
              <select v-model="pa.category" class="setup-input" style="width:auto; min-width:140px; flex:0;">
                <option value="">No category</option>
                <option
                  v-for="cat in store.createdCategories"
                  :key="cat.id"
                  :value="cat.id"
                >
                  {{ cat.display_name }}
                </option>
              </select>
            </div>
          </div>

          <div class="setup-actions">
            <button class="setup-btn setup-btn-secondary" @click="store.step = 4">Back</button>
            <button class="setup-btn setup-btn-secondary" @click="store.step = 6">Skip</button>
            <button
              class="setup-btn setup-btn-primary"
              :disabled="store.saving"
              @click="store.saveAssignments()"
            >
              {{ store.saving ? 'Saving...' : 'Save & Finish' }}
            </button>
          </div>
        </div>
      </Transition>

      <!-- ============================================ -->
      <!-- Step 6: All Set                              -->
      <!-- ============================================ -->
      <Transition name="step">
        <div v-if="store.step === 6" class="setup-step-content">
          <div class="setup-finish">
            <div class="setup-finish-icon">&#127881;</div>
            <h2 class="setup-title">All Set!</h2>
            <p class="setup-subtitle">
              Your meal plan generator is ready. Let's see what's on the menu.
            </p>

            <div class="setup-actions" style="justify-content:center;">
              <button class="setup-btn setup-btn-primary" @click="store.generateAndFinish()">
                Generate First Menu
              </button>
              <button class="setup-btn setup-btn-secondary" @click="store.finishSetup()">
                Show Me the Menu
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
/* Setup page — full-page wizard layout */
.setup-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--bg-color, #0d0d0d);
  color: var(--text-color, #e8e0d0);
  font-family: var(--body-font, 'Lato', sans-serif);
  padding: 2rem 1rem 3rem;
}

.setup-container {
  width: 100%;
  max-width: 560px;
}

/* Progress bar */
.setup-progress {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 2rem;
}

.setup-progress-step {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
}

.setup-progress-step:last-child {
  flex: 0;
}

.setup-progress-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  flex-shrink: 0;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  border: 2px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  color: var(--text-muted, rgba(255, 255, 255, 0.45));
  transition: all 0.3s;
}

.setup-progress-dot.active {
  background: var(--accent-color, #d4a847);
  border-color: var(--accent-color, #d4a847);
  color: #000;
}

.setup-progress-dot.done {
  background: #4ade80;
  border-color: #4ade80;
  color: #000;
}

.setup-progress-line {
  flex: 1;
  height: 2px;
  background: var(--card-border-color, rgba(255, 255, 255, 0.15));
  transition: background 0.3s;
}

.setup-progress-line.done {
  background: #4ade80;
}

/* Step content */
.setup-step-content {
  background: var(--card-bg, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.1));
  border-radius: 12px;
  padding: 2rem;
}

.setup-title {
  font-family: var(--heading-font, 'Playfair Display', serif);
  color: var(--accent-color, #d4a847);
  font-size: 1.5rem;
  margin: 0 0 0.5rem;
}

.setup-subtitle {
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  font-size: 0.95rem;
  margin: 0 0 1.5rem;
  line-height: 1.5;
}

/* Profile progress indicator */
.setup-profile-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding: 0.5rem 0.75rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  border-radius: 8px;
  font-size: 0.85rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
}

.setup-profile-indicator strong {
  color: var(--accent-color, #d4a847);
}

.setup-profile-dots {
  display: flex;
  gap: 0.35rem;
}

.setup-profile-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--card-border-color, rgba(255, 255, 255, 0.15));
}

.setup-profile-dot.active {
  background: var(--accent-color, #d4a847);
}

/* Form fields */
.setup-field {
  text-align: left;
  margin-bottom: 1.25rem;
}

.setup-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-color, #e8e0d0);
  margin-bottom: 0.4rem;
}

.setup-input {
  display: block;
  width: 100%;
  padding: 0.6rem 0.85rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  color: var(--text-color, #e8e0d0);
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: var(--body-font, sans-serif);
  box-sizing: border-box;
}

.setup-input:focus {
  outline: none;
  border-color: var(--accent-color, #d4a847);
  box-shadow: 0 0 0 2px rgba(212, 168, 71, 0.25);
}

select.setup-input {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23999' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  padding-right: 2rem;
  color-scheme: var(--color-scheme, dark);
}

textarea.setup-input {
  resize: vertical;
  min-height: 70px;
}

.setup-hint {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.4));
  margin-top: 0.3rem;
  font-style: italic;
}

/* Test result */
.setup-test-result {
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.setup-test-result.success {
  background: rgba(34, 197, 94, 0.1);
  color: #4ade80;
}

.setup-test-result.error {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
}

/* Buttons */
.setup-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.setup-btn {
  padding: 0.6rem 1.5rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  font-family: var(--body-font, sans-serif);
}

.setup-btn-primary {
  background: var(--accent-color, #d4a847);
  color: #000;
}

.setup-btn-primary:hover:not(:disabled) {
  filter: brightness(1.1);
}

.setup-btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.setup-btn-secondary {
  background: transparent;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
}

.setup-btn-secondary:hover {
  color: var(--text-color, #e8e0d0);
  border-color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

/* Preset card grid */
.setup-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.setup-preset-card {
  position: relative;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  border: 2px solid var(--card-border-color, rgba(255, 255, 255, 0.12));
  border-radius: 10px;
  padding: 1rem 0.75rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.setup-preset-card:hover {
  border-color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.setup-preset-card.selected {
  border-color: var(--accent-color, #d4a847);
  background: rgba(212, 168, 71, 0.08);
}

.setup-preset-card .card-check {
  position: absolute;
  top: 0.4rem;
  right: 0.5rem;
  color: #4ade80;
  font-size: 1rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.setup-preset-card.selected .card-check {
  opacity: 1;
}

.setup-preset-card .card-name {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 0.15rem;
}

.setup-preset-card .card-subtitle {
  font-size: 0.75rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.45));
}

/* Custom profile input row */
.setup-custom-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-top: 0.75rem;
}

.setup-custom-row .setup-input {
  flex: 1;
}

/* Number control */
:deep(.setup-number-control) {
  display: inline-flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  border-radius: 8px;
  overflow: hidden;
}

:deep(.setup-number-control button) {
  width: 36px;
  height: 36px;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  border: none;
  color: var(--text-color, #e8e0d0);
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.setup-number-control button:hover) {
  background: rgba(255, 255, 255, 0.1);
}

:deep(.setup-number-control input) {
  width: 50px;
  text-align: center;
  background: transparent;
  border: none;
  border-left: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  border-right: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  color: var(--text-color, #e8e0d0);
  font-size: 0.95rem;
  font-family: var(--body-font, sans-serif);
  padding: 0.4rem 0;
}

:deep(.setup-number-control input:focus) {
  outline: none;
}

.setup-range-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.9rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.6));
}

/* Choice card radio group */
.setup-choice-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

:deep(.setup-choice-card) {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.03));
  border: 2px solid var(--card-border-color, rgba(255, 255, 255, 0.12));
  border-left: 4px solid var(--card-border-color, rgba(255, 255, 255, 0.12));
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
  min-height: 56px;
}

:deep(.setup-choice-card:hover) {
  border-color: var(--text-muted, rgba(255, 255, 255, 0.3));
  border-left-color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

:deep(.setup-choice-card.selected) {
  border-color: var(--accent-color, #d4a847);
  border-left-color: var(--accent-color, #d4a847);
  background: rgba(212, 168, 71, 0.06);
  box-shadow: 0 0 12px rgba(212, 168, 71, 0.1);
}

:deep(.setup-choice-radio) {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--card-border-color, rgba(255, 255, 255, 0.25));
  flex-shrink: 0;
  margin-top: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

:deep(.setup-choice-card.selected .setup-choice-radio) {
  border-color: var(--accent-color, #d4a847);
}

:deep(.setup-choice-radio-dot) {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent-color, #d4a847);
  opacity: 0;
  transition: opacity 0.2s;
}

:deep(.setup-choice-card.selected .setup-choice-radio-dot) {
  opacity: 1;
}

:deep(.setup-choice-content) {
  flex: 1;
  min-width: 0;
}

:deep(.setup-choice-label) {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-color, #e8e0d0);
  margin-bottom: 0.15rem;
}

:deep(.setup-choice-desc) {
  font-size: 0.8rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.45));
  line-height: 1.4;
}

/* Config section */
.setup-config-section {
  padding: 0 0 0.5rem;
}

/* Search + chips (from child components) */
:deep(.setup-search-box) {
  position: relative;
  margin-bottom: 0.5rem;
}

:deep(.setup-search-box input) {
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  border-radius: 6px;
  color: var(--text-color, #e8e0d0);
  font-size: 0.85rem;
  font-family: var(--body-font, sans-serif);
  box-sizing: border-box;
}

:deep(.setup-search-box input:focus) {
  outline: none;
  border-color: var(--accent-color, #d4a847);
}

:deep(.setup-search-results) {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--modal-bg, #1e1e1e);
  border: 1px solid var(--accent-color-dim, rgba(212, 168, 71, 0.3));
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
  margin-top: 2px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

:deep(.setup-search-results button) {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.08));
  color: var(--text-color, #e8e0d0);
  font-size: 0.85rem;
  cursor: pointer;
  font-family: var(--body-font, sans-serif);
}

:deep(.setup-search-results button:last-child) {
  border-bottom: none;
}

:deep(.setup-search-results button:hover) {
  background: rgba(255, 255, 255, 0.08);
}

:deep(.setup-chips) {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.setup-chip,
:deep(.setup-chip) {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.25rem 0.6rem;
  background: rgba(212, 168, 71, 0.12);
  border: 1px solid rgba(212, 168, 71, 0.3);
  border-radius: 20px;
  font-size: 0.8rem;
  color: var(--accent-color, #d4a847);
}

.setup-chip button,
:deep(.setup-chip button) {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0;
  line-height: 1;
  opacity: 0.6;
}

.setup-chip button:hover,
:deep(.setup-chip button:hover) {
  opacity: 1;
}

:deep(.setup-chip.exclude) {
  background: rgba(220, 80, 60, 0.15);
  border-color: rgba(220, 80, 60, 0.35);
  color: #f08070;
}

/* Per-keyword row */
.setup-keyword-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0;
  flex-wrap: wrap;
}

.setup-keyword-row-sentence {
  font-size: 0.8rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
}

.setup-count-inline {
  width: 52px;
  padding: 0.25rem 0.4rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  color: var(--text-color, #e8e0d0);
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  border-radius: 6px;
  font-size: 0.85rem;
  font-family: var(--body-font, sans-serif);
  text-align: center;
}

/* Balance progress */
.setup-balance-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
}

.setup-balance-progress.complete {
  color: var(--accent-color, #d4a847);
}

/* Sentence builder */
.setup-sentence {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.6));
}

.setup-sentence strong {
  color: var(--text-color, #e8e0d0);
}

.setup-sentence input[type="number"] {
  width: 60px;
  padding: 0.3rem 0.5rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  color: var(--text-color, #e8e0d0);
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  border-radius: 6px;
  font-size: 0.85rem;
  font-family: var(--body-font, sans-serif);
  text-align: center;
}

/* Star rating */
.setup-star-row {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.setup-star {
  font-size: 1.4rem;
  cursor: pointer;
  color: var(--card-border-color, rgba(255, 255, 255, 0.2));
  transition: color 0.15s;
}

.setup-star.filled {
  color: var(--accent-color, #d4a847);
}

/* Day presets */
.setup-day-presets {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.setup-day-presets button {
  padding: 0.4rem 0.9rem;
  border-radius: 8px;
  font-size: 0.85rem;
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  background: transparent;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--body-font, sans-serif);
  min-width: 44px;
  text-align: center;
}

.setup-day-presets button:hover {
  border-color: var(--text-muted, rgba(255, 255, 255, 0.3));
  color: var(--text-color, #e8e0d0);
}

.setup-day-presets button.active {
  background: var(--accent-color, #d4a847);
  border-color: var(--accent-color, #d4a847);
  color: #000;
  font-weight: 600;
}

.setup-custom-days {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
}

.setup-custom-days input[type="number"] {
  width: 70px;
  padding: 0.35rem 0.5rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  color: var(--text-color, #e8e0d0);
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.15));
  border-radius: 6px;
  font-size: 0.85rem;
  font-family: var(--body-font, sans-serif);
  text-align: center;
}

/* Section label */
.setup-section-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 1rem 0 0.5rem;
}

.setup-section-label:first-child {
  margin-top: 0;
}

/* Review card */
.setup-review-card {
  background: var(--input-bg, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.12));
  border-radius: 10px;
  padding: 1.25rem;
  margin-bottom: 1rem;
}

.setup-review-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.1));
}

.setup-review-name {
  font-family: var(--heading-font, 'Playfair Display', serif);
  font-size: 1.1rem;
  color: var(--accent-color, #d4a847);
}

.setup-review-meta {
  font-size: 0.8rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.45));
}

.setup-review-rules {
  list-style: none;
  padding: 0;
  margin: 0;
}

.setup-review-line {
  padding: 0.5rem 0.6rem;
  margin: 0 -0.3rem;
  border-radius: 6px;
  font-size: 0.85rem;
  color: var(--text-color, #e8e0d0);
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setup-review-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.setup-review-line::before {
  content: '\2022';
  color: var(--accent-color, #d4a847);
  font-size: 1.1rem;
  flex-shrink: 0;
}

.setup-review-empty {
  font-size: 0.85rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.4));
  font-style: italic;
  padding: 0.5rem 0;
}

/* Sub-page dots */
.setup-sub-dots {
  display: flex;
  justify-content: center;
  gap: 0.35rem;
  margin-bottom: 1.25rem;
}

.setup-sub-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--card-border-color, rgba(255, 255, 255, 0.15));
  transition: all 0.2s;
}

.setup-sub-dot.active {
  background: var(--accent-color, #d4a847);
  transform: scale(1.25);
}

.setup-sub-dot.done {
  background: rgba(212, 168, 71, 0.4);
}

/* Category cards */
.setup-category-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.setup-category-card {
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  border: 2px solid var(--card-border-color, rgba(255, 255, 255, 0.12));
  border-radius: 10px;
  padding: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.setup-category-card:hover {
  border-color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.setup-category-card.selected {
  border-color: var(--accent-color, #d4a847);
  background: rgba(212, 168, 71, 0.08);
}

.setup-category-card .cat-info {
  flex: 1;
}

.setup-category-card .cat-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.setup-category-card .cat-sub {
  font-size: 0.75rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.45));
}

.setup-category-card .cat-check {
  color: #4ade80;
  font-size: 1rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.setup-category-card.selected .cat-check {
  opacity: 1;
}

/* Assignment row */
.setup-assignment-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  background: var(--input-bg, rgba(255, 255, 255, 0.05));
  border: 1px solid var(--card-border-color, rgba(255, 255, 255, 0.12));
  border-radius: 8px;
}

.setup-assignment-name {
  flex: 1;
  font-size: 0.9rem;
  font-weight: 600;
}

/* Finish step */
.setup-finish {
  text-align: center;
  padding: 1rem 0;
}

.setup-finish-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

/* Transitions */
.step-enter-active {
  transition: all 0.2s ease-out;
}

.step-enter-from {
  opacity: 0;
  transform: translateX(16px);
}

.fade-enter-active {
  transition: opacity 0.15s ease-out;
}

.fade-enter-from {
  opacity: 0;
}

/* Collapsible help sections */
.setup-details {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-muted, rgba(255, 255, 255, 0.5));
}

.setup-details summary {
  cursor: pointer;
  color: var(--accent-color, #7a8b9a);
}

.setup-details summary:hover {
  text-decoration: underline;
}

.setup-help-steps {
  margin: 0.5rem 0 0 1.25rem;
  padding: 0;
  line-height: 1.6;
}

.setup-help-steps li {
  margin-bottom: 0.25rem;
}

/* Responsive */
@media (max-width: 480px) {
  .setup-page {
    padding: 1rem 0.75rem 2rem;
  }

  .setup-step-content {
    padding: 1.5rem 1rem;
  }

  .setup-card-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .setup-actions {
    flex-direction: column-reverse;
  }

  .setup-btn {
    width: 100%;
    text-align: center;
  }
}
</style>
