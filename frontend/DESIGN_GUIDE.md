# Tally Frontend Design Guide

## Spacing Standards

### Vertical Spacing (Y-axis)

We use consistent vertical spacing throughout the application to create visual hierarchy and improve readability.

#### Main Container Spacing
- **Page-level containers**: `space-y-6` or `space-y-8`
  - Use `space-y-8` for dashboards and content-heavy pages
  - Use `space-y-6` for simpler pages with less content

#### Section Spacing
- **Between major sections**: `space-y-8` with optional `mt-10` for extra emphasis
- **Within sections**: `space-y-4` for related content
- **Card content padding**: `p-4` for contained elements
- **Header/content separation**: `mb-6` after headers in cards

#### Component-Specific Spacing
- **Dashboard columns**: `gap-8` between grid columns
- **Form fields**: `space-y-4`
- **List items**: `space-y-2` or `divide-y` for compact lists
- **Button groups**: `gap-2` or `gap-4`

### Color Scheme

#### Category Colors
- **Validators**: Sky blue theme
  - Primary: `sky-600`, `sky-700`
  - Backgrounds: `sky-50`, `sky-100`
  - Borders: `sky-100`, `sky-200`
  
- **Builders**: Orange theme
  - Primary: `orange-600`, `orange-700`
  - Backgrounds: `orange-50`, `orange-100`
  - Borders: `orange-100`, `orange-200`

- **Global/Testnet Asimov**: Neutral/Black
  - Primary: `gray-900`, `black`
  - Backgrounds: `gray-50`, `gray-100`

### Card Design

#### Column Cards (Dashboard)
- **Container**: `bg-[category]-50/30 rounded-lg shadow-sm border border-[category]-100`
- **Header**: `bg-[category]-100/50 px-5 py-3 border-b border-[category]-200`
- **Content**: `p-4 space-y-8`

#### Content Cards
- **Featured/Highlight**: `bg-yellow-50 border-l-4 border-yellow-400 p-4`
- **Standard**: `bg-white rounded-lg shadow divide-y divide-gray-200`
- **Hover states**: `hover:bg-gray-50` for white backgrounds

### Typography

#### Headers
- **Page titles**: `text-2xl font-bold text-gray-900`
- **Section titles**: `text-lg font-semibold text-gray-900`
- **Category headers**: `text-lg font-semibold text-[category]-700 uppercase tracking-wider`
- **Subsection titles**: `text-base font-semibold text-gray-900`

#### Body Text
- **Primary**: `text-gray-900`
- **Secondary**: `text-gray-700`
- **Muted**: `text-gray-500`
- **Small/Meta**: `text-xs text-gray-500`

### Interactive Elements

#### Buttons
- **View all links**: `text-sm text-gray-500 hover:text-primary-600 transition-colors`
- **Category-specific links**: `text-sm text-[category]-600 hover:text-[category]-700`
- **Icon buttons**: Include chevron icon for navigation `<svg class="inline-block w-3 h-3 ml-1">`

#### Icons
- **Size classes**: 
  - Small sections: `w-4 h-4`
  - Stats/Features: `w-6 h-6`
- **Container**: `p-1.5 bg-[color]-100 rounded-lg` for small icons
- **Spacing**: `mr-2` or `gap-2` when paired with text

### Responsive Design
- **Grid layouts**: `grid-cols-1 lg:grid-cols-2` for two-column layouts
- **Mobile sidebar**: Hidden by default, toggle with menu button
- **Padding**: Consistent `px-4` on mobile, can increase on desktop

## Implementation Notes

1. Always use Tailwind's spacing scale for consistency
2. Prefer `space-y-*` over manual margins for vertical spacing
3. Use `gap-*` for flexbox and grid spacing
4. Apply transitions to interactive elements: `transition-colors` or `transition-shadow`
5. Maintain consistent border radius: `rounded-lg` for cards, `rounded-full` for badges
6. Use opacity modifiers for subtle backgrounds: `bg-color-50/30` for very light tints

## Accessibility
- Ensure sufficient color contrast for text
- Include hover and focus states for all interactive elements
- Use semantic HTML elements
- Provide aria-labels for icon-only buttons