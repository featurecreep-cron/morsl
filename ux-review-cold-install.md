# Cold UX Review: Morsl (Fresh Install)

**Date:** 2026-03-06
**Method:** Playwright browser automation, walking through every page as a fresh user
**Reviewer persona:** A Tandoor Recipes user who just found morsl on GitHub. Knows Tandoor well (recipes, meal plans, keywords) but has no technical/API background. Just docker-composed the thing and opened the browser.

---

## Full Findings: Problem-to-Solution Map

### Setup Wizard

| # | Finding | Severity | Problem | Solution | Files |
|---|---------|----------|---------|----------|-------|
| 1 | API Token discovery | High | Step 1 asks for "API Token" with hint "Found in Tandoor under Settings -> API Tokens." A non-technical user doesn't know what an API token is or how to create one. The hint names the page but doesn't explain the process. | Add a collapsible "How do I get a token?" section with 3-step instructions: "1. Open Tandoor. 2. Go to Settings (gear icon). 3. Scroll to API Tokens, click Create, copy the token." Optionally include a screenshot or link to Tandoor docs. | `web/setup.html:60-67` |
| 2 | "Skip Profiles" wording | Low | Step 2 has a "Skip Profiles" button. The step title is "Set Up Your Meal Plans" — so "skip profiles" is jarring because the user hasn't been told they're setting up profiles. The step subtitle explains it, but the button label conflicts with the heading. | Rename button to "Skip for Now" or "I'll set these up later." Consistent with the step's own framing. | `web/setup.html:145` |
| 3 | Profile configuration sub-pages overwhelm | Medium | Step 3 walks through 6 sub-pages per profile: basics, keywords, ingredients, books, avoidance, freshness, rating. For a first-time user who picked 3 presets, that's 18 sub-pages. The sub-page dots help orientation, but the volume is daunting. | Add a "Use defaults for all" shortcut after the first profile is configured. Or: batch-apply defaults and only show detailed config for profiles the user explicitly wants to customize. | `web/setup.html:153-729` (step 3 sub-pages) |
| 4 | ~~INVALID — Categories step ordering~~ | ~~Medium~~ | ~~Originally flagged as "categories before profiles" but the wizard already does profiles (step 2-3) before categories (step 4). The ordering is correct.~~ | N/A — wizard flow is already right. | N/A |
| 5 | No "skip" on categories step | Low | Categories step has no explicit skip button. User must click Next with no categories configured to proceed. Not blocking, but a "Skip" button like Step 2's "Skip for Now" would reduce friction. | Add "Skip" or "I'll organize later" button on Step 4, consistent with Step 2. | `web/setup.html` (step 4 actions) |

### Menu Page (index.html)

| # | Finding | Severity | Problem | Solution | Files |
|---|---------|----------|---------|----------|-------|
| 6 | "No profiles yet" empty state | Good | When no profiles exist, shows "No profiles yet / Create a profile to start generating menus" with a link to `/admin#profiles`. This is correct UX. | No change needed. Already well-handled. | `web/index.html:178-181` |
| 7 | "No recipes yet" text says "Browse a category" | Medium | When profiles exist but no menu is generated, shows "No recipes yet / Browse a category above to build your menu." The nav bar can show either profiles or categories (they look identical visually), but the user doesn't know which. Saying "category" is confusing when profiles are showing. | Change to "Tap a profile above to generate your menu" — names the thing, names the action, works whether profiles show directly or inside categories. | `web/index.html:184-186` |
| 8 | No CTA to generate on empty menu | High | Clicking a profile button on the menu page does nothing when no menu exists. There's no feedback, no "Generate" button, no link to admin. The user is stuck staring at an empty page with no path forward. | Add a "Generate your first menu" button below the empty state text that links to `/admin#generate`, or better: trigger generation directly from the menu page when a profile is clicked and no menu exists. | `web/index.html:184-186` (empty state div) |
| 9 | Hamburger menu low visibility | Low | The hamburger icon (top-left) is small and low-contrast on dark themes. A new user might not realize there's an admin page at all, especially if they came from the setup wizard's "Open Menu" button. | Increase icon size or add a subtle tooltip/pulse animation on first visit. Or: add an "Admin" link in the empty state CTA area. | `web/index.html` (nav hamburger) |
| 10 | No post-setup onboarding | Medium | After completing the setup wizard and clicking "Open Menu," the user lands on the menu page with no guidance. The wizard created profiles but didn't generate a menu. There's a gap between "setup complete" and "first useful result." | Option A: Auto-generate first menu at end of wizard. Option B: Show a one-time banner on menu page: "Setup complete. Pick a profile above to generate your first menu." Option C: The wizard's "All Set" step could have a "Generate First Menu" button instead of (or in addition to) "Open Menu." | `web/setup.html` (step 6), `web/index.html` |

### Admin - Generate Tab

| # | Finding | Severity | Problem | Solution | Files |
|---|---------|----------|---------|----------|-------|
| 11 | "0 rules" in dropdown unexplained | Low | Profile dropdown shows "Quick Dinner (5 recipes, 0 rules)." A new user doesn't know what rules are. The count is technically accurate but introduces undefined jargon. | Add a tooltip or "?" icon next to the dropdown explaining: "Rules filter which recipes are eligible — like keyword requirements, rating minimums, or ingredient preferences." | `web/admin.html` (generate tab, profile dropdown) |
| 12 | Schedule form needs simpler framing | Low | "+ Add Schedule" opens a form with day_of_week, hour, minute fields. This is cron-syntax thinking. The subtitle "Automatically generate menus on a recurring schedule" is good, but the form itself feels technical. | Replace raw hour/minute inputs with a time picker. Replace day_of_week text input with checkboxes for Mon-Sun. Frame as: "Generate a new menu every [days] at [time]." | `web/admin.html` (schedule section) |

### Admin - Profiles Tab

| # | Finding | Severity | Problem | Solution | Files |
|---|---------|----------|---------|----------|-------|
| 13 | Categories concept unclear | Medium | "Organize profiles into tabs that appear on the menu page" — but the relationship isn't visual. With 2 profiles and 0 categories, both appear as direct buttons. What changes if I add a category? No inline preview. | Add a visual hint: "Without categories, profiles appear as buttons. With categories, profiles are grouped under category tabs." A small diagram or before/after mockup. | `web/admin.html` (profiles tab, categories section) |
| 14 | "Item Noun" in profile editor | Low | Power-user field ("cocktail," "dessert") mixed in with essential fields like name and recipe count. First-time editor doesn't need this. | Move Item Noun into an "Advanced" collapsible section in the editor, or only show it at Advanced/Expert tier. | `web/admin.html` (profile editor drawer) |
| 15 | "Test" button label vague | Low | Footer of profile editor has "Test" / "Save Profile" / "Cancel." "Test" presumably test-runs the solver against Tandoor. But "Test" alone doesn't communicate what's being tested. | Rename to "Preview Matches" or "Test Profile" with a tooltip: "Run this profile against your Tandoor recipes to see how many match." | `web/admin.html` (profile editor footer) |

### Admin - Weekly Tab

| # | Finding | Severity | Problem | Solution | Files |
|---|---------|----------|---------|----------|-------|
| 16 | Generate section shown with no templates | Medium | "Generate Weekly Plan" section appears with an empty dropdown and disabled Generate button even when no templates exist. Looks like a broken form. | Hide the Generate section entirely when no templates exist. Show it only after the first template is created. Or: replace with "Create a template above to generate weekly plans." | `web/admin.html` (weekly tab, generate section) |
| 17 | Relationship between Generate tab schedules and Weekly templates unclear | Medium | Weekly tab says "set up automatic scheduling on the Generate tab." But the Generate tab has its own scheduling for single profiles. A user might wonder: do I schedule weekly plans from the Generate tab or the Weekly tab? | Clarify in both places. Weekly tab: "To auto-generate weekly plans, create a schedule on the Generate tab and select a template." Generate tab schedule form: when creating a schedule, let the user choose between "Single profile" and "Weekly template" modes explicitly. | `web/admin.html` (weekly tab description, generate tab schedule form) |

### Admin - Settings Tab

| # | Finding | Severity | Problem | Solution | Files |
|---|---------|----------|---------|----------|-------|
| 18 | Tier system unexplained | High | Three radio buttons in top-right corner: Standard / Advanced / Expert. No tooltip, no help text. Clicking Expert reveals a hidden "Branding" tab. User has no idea what each tier controls or whether they should change it. | Add a "?" icon next to the tier selector that explains: "Standard: essential settings for everyday use. Advanced: display and integration options. Expert: branding, tuning, and all features." Consider also showing a one-time tooltip on first admin visit. | `web/admin.html:44-59` (tier selector) |
| 19 | "Show Ratings" vs "Ratings" confusing | Low | Two toggles in Display & Features: "Show Ratings — Display existing star ratings on recipe cards" and "Ratings — Let users rate recipes from the menu page." The first is display-only, the second is interactive. Labels are too similar. | Rename: "Show Ratings" stays. "Ratings" becomes "Enable Rating" or "Allow User Ratings." | `web/admin.html` (settings tab, display & features section) |
| 20 | API Cache shown as raw minutes | Low | "API Cache: 240" with subtitle about minutes. 240 minutes = 4 hours, but requiring mental math is unnecessary friction. | Show as "4 hours" or use a dropdown with presets: "15 minutes / 1 hour / 4 hours (default) / 12 hours / 24 hours." Keep the raw number input available at Expert tier for fine-tuning. | `web/admin.html` (settings tab, Tandoor Integration section) |

### Admin - Branding Tab (Expert only)

| # | Finding | Severity | Problem | Solution | Files |
|---|---------|----------|---------|----------|-------|
| 21 | Placeholder Mappings search requires live Tandoor | Medium | "Search keywords..." input does nothing without a working Tandoor connection. No error message, no loading state — just silent failure. User types, nothing happens. | Show a loading indicator while searching. If the search fails or returns nothing, show "Could not load keywords from Tandoor" or "No matching keywords found." Don't silently fail. | `web/admin.html` (branding tab, placeholder mappings) |
| 22 | Custom Icons two-tab workflow | Low | "Upload SVG icons for use in profile and category cards. Manage icons here; assign them in the Profiles tab." Two-step process across two tabs isn't obvious. | Add "Assign to Profile" button directly on each uploaded icon in the Branding tab. Or: in the Profile editor's icon picker, add an "Upload new icon" shortcut so the user doesn't need to visit Branding separately. | `web/admin.html` (branding tab, custom icons section) |

---

## Summary by Severity

### High (3)
- **#1** API Token discovery — users don't know how to get one
- **#8** No CTA to generate on empty menu — dead end after setup
- **#18** Tier system unexplained — hidden features with no discoverability

### Medium (6)
- **#3** Profile configuration sub-page volume — 6 pages per profile is daunting
- ~~#4 INVALID — wizard order is already correct (profiles before categories)~~
- **#7** "Browse a category" text says category, means profile
- **#10** No post-setup onboarding — gap between wizard completion and first value
- **#16** Generate Weekly section shown with no templates — broken-looking form
- **#17** Generate/Weekly scheduling relationship unclear — cross-tab confusion
- **#21** Placeholder Mappings silent failure — no feedback on search

### Low (6)
- **#2** "Skip Profiles" wording mismatch with step title
- **#5** No skip button on categories step
- **#9** Hamburger menu low visibility
- **#11** "0 rules" jargon in dropdown
- **#12** Schedule form needs simpler framing
- **#14** Item Noun power-user field mixed with essentials
- **#15** "Test" button label vague
- **#19** "Show Ratings" vs "Ratings" confusing
- **#20** API Cache raw minutes
- **#22** Custom Icons two-tab workflow

### Already Good (1)
- **#6** No-profiles empty state correctly links to admin

---

## Implementation Plan

### Phase 1: Copy fixes (minimal code changes, maximum clarity)
Text/label changes only. No structural changes, no new components.

1. **#7** Change "Browse a category above" to "Tap a profile above to generate your menu" — one line in `index.html:186`
2. **#19** Rename "Ratings" toggle to "Enable Rating" — one line in `admin.html`
3. **#15** Rename "Test" button to "Test Profile" — one line in `admin.html`
4. **#2** Rename "Skip Profiles" to "Skip for Now" — one line in `setup.html:145`
5. **#11** Add title attribute to profile dropdown option template explaining rules

### Phase 2: CTAs and guidance (small additions, big UX impact)
6. **#8** Add "Generate your first menu" link-button in the empty-state div on `index.html` pointing to `/admin#generate`
7. **#1** Add collapsible "How do I get a token?" help section on setup step 1
8. **#18** Add "?" tooltip next to tier selector explaining the three levels
9. **#10** On setup step 6 ("All Set"), add "Generate First Menu" button alongside existing CTAs
10. **#16** Hide "Generate Weekly Plan" section when no templates exist (`x-show="templates.length > 0"`)

### Phase 3: Structural improvements (larger changes, each independent)
11. **#3** Add "Use defaults for remaining profiles" shortcut in step 3
12. **#13** Add visual hint to categories section explaining with/without behavior
13. **#17** Clarify scheduling cross-references in both Generate and Weekly tabs
14. **#21** Add loading/error states to placeholder mapping search
15. **#12** Tier the schedule form: simple day/time picker at Standard, show cron details at Advanced/Expert
16. **#20** Show API Cache as human-readable duration with preset dropdown
17. **#14** Tier the profile editor: move power-user fields to Advanced visibility

**Profile editor tiering (#14 detail):**

| Field | Standard | Advanced | Notes |
|-------|----------|----------|-------|
| Name | visible | visible | Essential |
| Description | visible | visible | Essential |
| Icon | visible | visible | Helps identity |
| Recipes count | visible | visible | Core setting |
| Rules (+ Add Rule) | visible | visible | Core feature |
| Save / Cancel | visible | visible | Essential |
| Default Profile | hidden | visible | Only matters with multiple profiles |
| Show on Menu | hidden | visible | For hidden/scheduling-only profiles |
| Item Noun | hidden | visible | Cosmetic customization |
| Min Recipes | hidden | visible | Solver fallback behavior |
| Category | hidden | visible | Organizational |
| Test Profile button | hidden | visible | Useful but confusing without context |

### Phase 4: Nice-to-haves (polish)
18. **#5** Add skip button to categories step
19. **#22** Add "Upload new icon" shortcut to profile editor icon picker

### Bugs Found During Review
- **Timezone bug (FIXED):** Scheduler defaulted to UTC. "6am" schedule fired at midnight local time. Fix: added `timezone` setting (defaults to `TZ` env var), passed to `AsyncIOScheduler` and `CronTrigger`, added timezone setting in admin UI, shown in schedule preview.

### Feature Requests
- **QR code for menu access:** Generate a QR code (guest wifi and/or menu page URL) for kiosk/tablet deployments. Natural home: Branding tab or Kiosk settings. Use client-side JS library (qrcode.js).

### Dropped
- ~~#9 Hamburger menu visibility~~ — per Chris, skip this
- ~~#4 Wizard step ordering~~ — already correct
