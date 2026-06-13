/**
 * Centralized category color definitions for consistent theming across the app
 */

export const getCategoryColors = (category) => {
  switch (category) {
    case 'builder':
      return {
        // Primary colors
        primary: 'orange',
        primaryShade: 'orange-600',
        
        // Backgrounds
        pageBg: 'bg-orange-50',
        cardBg: 'bg-white',  // Clean white cards
        headerBg: 'bg-white',  // White header card too
        statBg: 'bg-orange-100',   // Slightly saturated for stat icons
        
        // Borders
        border: 'border-orange-300',
        borderLight: 'border-orange-200',  
        expandBorder: 'border-orange-200',
        
        // Text colors
        text: 'text-orange-600',
        textDark: 'text-orange-900',
        textMedium: 'text-orange-700',
        hoverText: 'hover:text-orange-700',
        
        // Icon colors
        icon: 'text-orange-600',
        
        // Solid backgrounds
        bg: 'bg-orange-500',
        
        // Other
        expandBg: 'bg-orange-50',
        accentColor: 'text-orange-600'
      };
      
    case 'validator':
      return {
        // Primary colors
        primary: 'sky',
        primaryShade: 'sky-600',
        
        // Backgrounds
        pageBg: 'bg-sky-50',
        cardBg: 'bg-white',     // Clean white cards
        headerBg: 'bg-white',   // White header card too
        statBg: 'bg-sky-100',     // Slightly saturated for stat icons
        
        // Borders
        border: 'border-sky-300',
        borderLight: 'border-sky-200',  
        expandBorder: 'border-sky-200',
        
        // Text colors
        text: 'text-sky-600',
        textDark: 'text-sky-900',
        textMedium: 'text-sky-700',
        hoverText: 'hover:text-sky-700',
        
        // Icon colors
        icon: 'text-sky-600',
        
        // Solid backgrounds
        bg: 'bg-sky-500',
        
        // Other
        expandBg: 'bg-sky-50',
        accentColor: 'text-sky-600'
      };

    case 'community':
      return {
        // Primary colors
        primary: 'purple',
        primaryShade: 'purple-600',

        // Backgrounds
        pageBg: 'bg-purple-50',
        cardBg: 'bg-white',
        headerBg: 'bg-white',
        statBg: 'bg-purple-100',

        // Borders
        border: 'border-purple-300',
        borderLight: 'border-purple-200',
        expandBorder: 'border-purple-200',

        // Text colors
        text: 'text-purple-600',
        textDark: 'text-purple-900',
        textMedium: 'text-purple-700',
        hoverText: 'hover:text-purple-700',

        // Icon colors
        icon: 'text-purple-600',

        // Solid backgrounds
        bg: 'bg-purple-500',

        // Other
        expandBg: 'bg-purple-50',
        accentColor: 'text-purple-600'
      };

    case 'global':
    default:
      return {
        // Primary colors
        primary: 'gray',
        primaryShade: 'gray-600',
        
        // Backgrounds
        pageBg: 'bg-gray-50',
        cardBg: 'bg-white',
        headerBg: 'bg-white',
        statBg: 'bg-gray-100',
        
        // Borders
        border: 'border-gray-400',
        borderLight: 'border-gray-200',
        expandBorder: 'border-gray-200',
        
        // Text colors
        text: 'text-gray-600',
        textDark: 'text-gray-900',
        textMedium: 'text-gray-700',
        hoverText: 'hover:text-gray-700',
        
        // Icon colors
        icon: 'text-gray-600',
        
        // Solid backgrounds
        bg: 'bg-gray-500',
        
        // Other
        expandBg: 'bg-gray-50',
        accentColor: 'text-gray-600'
      };
  }
};

/**
 * Get colors for pioneer contributions section (opportunities with zero contributions)
 */
export const getPioneerContributionsColors = (category) => {
  switch (category) {
    case 'builder':
      return {
        // Container colors
        containerBg: 'bg-orange-50',
        containerBorder: 'border-orange-200',
        containerBorderLeft: 'border-l-orange-500',

        // Header colors
        headerBg: 'bg-orange-100',
        headerBorder: 'border-orange-200',
        headerText: 'text-orange-900',
        headerIcon: 'text-orange-600',
        descriptionText: 'text-orange-700',

        // Table colors
        tableHeaderBg: 'bg-orange-50',
        tableHeaderText: 'text-orange-700',
        tableRowBg: 'bg-orange-50',
        tableRowHover: 'hover:bg-orange-100',
        tableBorder: 'divide-orange-100',

        // Text colors
        titleText: 'text-orange-600',
        titleTextHover: 'text-orange-700',
        contentText: 'text-orange-800',
        pointsText: 'text-orange-900',

        // Badge colors
        badgeColor: 'orange',
        badgeBg: 'bg-orange-100',
        badgeText: 'text-orange-800'
      };

    case 'validator':
      return {
        // Container colors
        containerBg: 'bg-sky-50',
        containerBorder: 'border-sky-200',
        containerBorderLeft: 'border-l-sky-500',

        // Header colors
        headerBg: 'bg-sky-100',
        headerBorder: 'border-sky-200',
        headerText: 'text-sky-900',
        headerIcon: 'text-sky-600',
        descriptionText: 'text-sky-700',

        // Table colors
        tableHeaderBg: 'bg-sky-50',
        tableHeaderText: 'text-sky-700',
        tableRowBg: 'bg-sky-50',
        tableRowHover: 'hover:bg-sky-100',
        tableBorder: 'divide-sky-100',

        // Text colors
        titleText: 'text-sky-600',
        titleTextHover: 'text-sky-700',
        contentText: 'text-sky-800',
        pointsText: 'text-sky-900',

        // Badge colors
        badgeColor: 'blue',
        badgeBg: 'bg-sky-100',
        badgeText: 'text-sky-800'
      };

    case 'community':
      return {
        // Container colors
        containerBg: 'bg-purple-50',
        containerBorder: 'border-purple-200',
        containerBorderLeft: 'border-l-purple-500',

        // Header colors
        headerBg: 'bg-purple-100',
        headerBorder: 'border-purple-200',
        headerText: 'text-purple-900',
        headerIcon: 'text-purple-600',
        descriptionText: 'text-purple-700',

        // Table colors
        tableHeaderBg: 'bg-purple-50',
        tableHeaderText: 'text-purple-700',
        tableRowBg: 'bg-purple-50',
        tableRowHover: 'hover:bg-purple-100',
        tableBorder: 'divide-purple-100',

        // Text colors
        titleText: 'text-purple-600',
        titleTextHover: 'text-purple-700',
        contentText: 'text-purple-800',
        pointsText: 'text-purple-900',

        // Badge colors
        badgeColor: 'purple',
        badgeBg: 'bg-purple-100',
        badgeText: 'text-purple-800'
      };

    case 'steward':
      return {
        // Container colors
        containerBg: 'bg-green-50',
        containerBorder: 'border-green-200',
        containerBorderLeft: 'border-l-green-500',

        // Header colors
        headerBg: 'bg-green-100',
        headerBorder: 'border-green-200',
        headerText: 'text-green-900',
        headerIcon: 'text-green-600',
        descriptionText: 'text-green-700',

        // Table colors
        tableHeaderBg: 'bg-green-50',
        tableHeaderText: 'text-green-700',
        tableRowBg: 'bg-green-50',
        tableRowHover: 'hover:bg-green-100',
        tableBorder: 'divide-green-100',

        // Text colors
        titleText: 'text-green-600',
        titleTextHover: 'text-green-700',
        contentText: 'text-green-800',
        pointsText: 'text-green-900',

        // Badge colors
        badgeColor: 'green',
        badgeBg: 'bg-green-100',
        badgeText: 'text-green-800'
      };

    case 'global':
    default:
      return {
        // Container colors
        containerBg: 'bg-gray-50',
        containerBorder: 'border-gray-200',
        containerBorderLeft: 'border-l-gray-500',

        // Header colors
        headerBg: 'bg-gray-100',
        headerBorder: 'border-gray-200',
        headerText: 'text-gray-900',
        headerIcon: 'text-gray-600',
        descriptionText: 'text-gray-700',

        // Table colors
        tableHeaderBg: 'bg-gray-50',
        tableHeaderText: 'text-gray-700',
        tableRowBg: 'bg-gray-50',
        tableRowHover: 'hover:bg-gray-100',
        tableBorder: 'divide-gray-100',

        // Text colors
        titleText: 'text-gray-600',
        titleTextHover: 'text-gray-700',
        contentText: 'text-gray-800',
        pointsText: 'text-gray-900',

        // Badge colors
        badgeColor: 'gray',
        badgeBg: 'bg-gray-100',
        badgeText: 'text-gray-800'
      };
  }
};

/**
 * Canonical hex accent per category (matches PortalContributionCard and the
 * portal gradient/glow treatments). Use these instead of redefining hex maps
 * in components.
 */
const CATEGORY_ACCENTS = {
  builder: '#ee8521',
  validator: '#387DE8',
  community: '#7F52E1',
  steward: '#3eb359',
  global: '#7F52E1',
};

export const getCategoryAccent = (category) =>
  CATEGORY_ACCENTS[category] || CATEGORY_ACCENTS.community;

/**
 * Points-pill colors (tinted background + accent text), same palette as
 * PortalContributionCard's pill.
 */
export const getCategoryPillColors = (category) => {
  const pillBgByCategory = {
    builder: 'rgba(238,133,33,0.1)',
    validator: 'rgba(56,125,232,0.1)',
    community: 'rgba(127,82,225,0.1)',
    steward: 'rgba(62,179,89,0.1)',
  };
  return {
    pillBg: pillBgByCategory[category] || pillBgByCategory.community,
    pillText: getCategoryAccent(category),
  };
};
