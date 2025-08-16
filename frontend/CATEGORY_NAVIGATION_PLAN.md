# Category Navigation Implementation Plan

## Overview
Create a category-based navigation system with three modes: Global, Builders, and Validators. Each category will have its own color theme and filtered content.

## Color Themes

### Global (Default)
- Primary: Current default colors
- Background: White/neutral
- Purpose: Dashboard and overall metrics

### Builders
- Primary: Light orange (sunset/breeze theme)
- Background: `#FFF7ED` (orange-50)
- Accent: `#FB923C` (orange-400)
- Border: `#FED7AA` (orange-200)
- Text: `#EA580C` (orange-600)

### Validators  
- Primary: Light blue (cool/sterile/technical)
- Background: `#F0F9FF` (sky-50)
- Accent: `#38BDF8` (sky-400)
- Border: `#BAE6FD` (sky-200)
- Text: `#0284C7` (sky-600)

## Architecture

### 1. Category Store (`/src/stores/category.js`)
```javascript
import { writable, derived } from 'svelte/store';

export const currentCategory = writable('global');

export const categoryTheme = derived(currentCategory, $category => {
  const themes = {
    global: {
      bg: 'bg-white',
      primary: 'bg-indigo-600',
      text: 'text-indigo-600',
      border: 'border-gray-200'
    },
    builders: {
      bg: 'bg-orange-50',
      primary: 'bg-orange-400',
      text: 'text-orange-600',
      border: 'border-orange-200'
    },
    validators: {
      bg: 'bg-sky-50',
      primary: 'bg-sky-400',
      text: 'text-sky-600',
      border: 'border-sky-200'
    }
  };
  return themes[$category] || themes.global;
});
```

### 2. Category Switcher Component (`/src/components/CategorySwitcher.svelte`)
- Three buttons: Global, Builders, Validators
- Only one active at a time
- Updates the category store
- Applied theme colors to active button

### 3. Layout Changes
- Add CategorySwitcher to Navbar
- Apply theme background to main container
- Pass category context to all child components

### 4. Component Updates

#### Shared Components (filter by category):
- **Sidebar.svelte**: Filter menu items based on category
- **LeaderboardTable.svelte**: Show category-specific leaderboard
- **ContributionsList.svelte**: Filter contributions by category
- **Dashboard.svelte**: Show category-specific metrics

#### Category-Specific Routes:
- **/dashboard/global**: Overall metrics and stats
- **/dashboard/builders**: Builder-specific dashboard
- **/dashboard/validators**: Validator-specific dashboard

### 5. Code Duplication Strategy

#### Approach: Composition over Duplication
1. **Base Components**: Create base components with props for customization
2. **Category Props**: Pass category as prop to filter data
3. **Theme Props**: Use derived store for consistent theming
4. **Duplicate Only When Logic Differs**: Only create separate components when business logic is fundamentally different

#### Example Pattern:
```svelte
<!-- BaseLeaderboard.svelte -->
<script>
  let { category = 'global' } = $props();
  import { categoryTheme } from '../stores/category';
</script>

<div class="{$categoryTheme.bg} rounded-lg p-6">
  <!-- Shared leaderboard logic -->
</div>
```

```svelte
<!-- BuildersLeaderboard.svelte (only if needed) -->
<script>
  import BaseLeaderboard from './BaseLeaderboard.svelte';
</script>

<BaseLeaderboard category="builders">
  <!-- Builder-specific additions -->
</BaseLeaderboard>
```

### 6. API Integration
- Update API calls to include category filter
- `/api/v1/leaderboard/category/{slug}/` for category leaderboards
- `/api/v1/contributions/?category={slug}` for filtered contributions

### 7. Implementation Order
1. Create category store
2. Update Navbar with CategorySwitcher
3. Apply theme to App.svelte layout
4. Update Sidebar filtering
5. Update Dashboard for category context
6. Update Leaderboard for category filtering
7. Update Contributions for category filtering
8. Create category-specific dashboard routes
9. Test all category switches

## File Structure
```
src/
├── stores/
│   └── category.js          # Category state management
├── components/
│   ├── CategorySwitcher.svelte  # Navigation buttons
│   ├── Sidebar.svelte       # Updated with filtering
│   └── ...                  # Other updated components
├── routes/
│   ├── Dashboard.svelte     # Updated for category
│   ├── GlobalDashboard.svelte   # Global-specific
│   ├── BuilderDashboard.svelte  # Builder-specific
│   └── ValidatorDashboard.svelte # Validator-specific
└── App.svelte               # Updated with theming
```

## Migration Strategy
1. Keep existing functionality intact
2. Add category layer on top
3. Default to 'global' for backward compatibility
4. Gradually add category-specific features