# Portal Components

Reusable components for the GL Portal Home page (`/` route, `Overview.svelte`).

## CategoryIcon

**File**: `CategoryIcon.svelte`

Reusable icon component with two display modes for category icons.

### Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `category` | `string` | `'genlayer'` | One of: `genlayer`, `builder`, `validator`, `community` |
| `mode` | `string` | `'small'` | Display mode: `small` (16px black icon) or `hexagon` (48px gradient hexagon with white icon) |
| `size` | `number` | `undefined` | Override default size in px |

### Usage
```svelte
<!-- Sidebar-style small black icon -->
<CategoryIcon category="builder" />

<!-- LiveStats-style hexagon gradient icon -->
<CategoryIcon category="builder" mode="hexagon" />

<!-- Custom size hexagon -->
<CategoryIcon category="validator" mode="hexagon" size={64} />
```

### Variants
- **genlayer**: Dark gradient hexagon + GL symbol (white) / Dashboard icon (black)
- **builder**: Orange gradient hexagon + Terminal icon (white) / Terminal icon (black)
- **validator**: Blue gradient hexagon + Shield icon (white) / Folder-shield icon (black)
- **community**: Purple gradient hexagon + Group icon (white) / Group icon (black)

---

## HeroBanner

**File**: `HeroBanner.svelte`

Featured project showcase with background image, gradient overlay, and info card.

- Background: `hero-bg.png` with gradient overlay
- Card: Glassmorphic card with project info, verified badge, CTA button
- Static content (will be wired to API later)

---

## LiveStats

**File**: `LiveStats.svelte`

Live statistics dashboard with 4 stat cards in a grid.

- Title: "GenLayer Live" with green dot indicator
- Subtitle: "What's going on today in GenLayer?"
- Cards: Hexagon gradient icon (via `CategoryIcon`), stat value, label, delta indicator
- Data source: `statsAPI.getDashboardStats()`

---

## PointsAwarded

**File**: `PointsAwarded.svelte`

Dark-themed card showing total points supply and distribution progress bar.

- Background: #131214
- Gradient progress bar from purple to orange
- Stat pills for distributed/remaining

---

## TrendingContributors

**File**: `TrendingContributors.svelte`

Horizontal scrolling list of trending contributor cards.

- Data source: `leaderboardAPI.getLeaderboard()`
- Shows avatar, name, points, rank

---

## FeaturedBuilds

**File**: `FeaturedBuilds.svelte`

Grid of featured project cards (placeholder, needs API).

---

## NewestMembers

**File**: `NewestMembers.svelte`

Tabbed member grid with pill-style tab navigation.

- Tabs: All, Builders, Validators, Community
- Data source: `usersAPI.getUsers()`

---

## MiniLeaderboard

**File**: `MiniLeaderboard.svelte`

Three side-by-side top-5 leaderboard columns.

- Columns: Builders, Validators, Community
- Category-colored point values
- Data source: `leaderboardAPI.getBuilders()`, `.getValidators()`, `.getCommunity()`

---

## CTAFooter

**File**: `CTAFooter.svelte`

Call-to-action footer with "Start contributing today" message and dark button.

---

## SVG Assets

All icons are in `/public/assets/icons/`. Key assets:

### Hexagon Backgrounds
- `hexagon-genlayer.svg` - Dark gradient (GenLayer)
- `hexagon-builder.svg` - Orange gradient (Builder)
- `hexagon-validator.svg` - Blue gradient (Validator)
- `hexagon-community.svg` - Purple gradient (Community)

### White Icons (for hexagon overlay)
- `gl-symbol-white.svg` - GenLayer logo symbol
- `terminal-fill-white.svg` - Terminal/builder icon
- `shield-white.svg` - Shield/validator icon
- `group-white.svg` - Group/community icon

### Black Icons (for sidebar)
- `dashboard-fill.svg` / `dashboard-fill-black.svg` - Dashboard (active purple / inactive black)
- `terminal-line.svg` - Builder
- `folder-shield-line.svg` - Validator
- `group-3-line.svg` - Community
- `seedling-line.svg` - Steward

### UI Icons
- `search-line.svg` - Search magnifying glass
- `add-line.svg` / `add-line-sidebar.svg` - Plus icon (white / gray)
- `arrow-up-s-line.svg` - Up arrow (green, for deltas)
- `arrow-right-line.svg` - Right arrow
- `arrow-left-s-line.svg` / `arrow-right-s-line.svg` / `arrow-right-s-line-expand.svg` - Sidebar collapse/expand
- `verified-badge-fill.svg` - Purple verified checkmark badge
