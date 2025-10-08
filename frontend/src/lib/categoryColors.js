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
 * Get pioneer/empty state colors (usually blue themed)
 */
export const getPioneerColors = (category) => {
  // For pioneer states, we can use themed colors or default to blue
  if (category === 'builder') {
    return {
      bg: 'bg-white',      // White background with colored border
      border: 'border-orange-300',
      headerBg: 'bg-orange-100',
      text: 'text-orange-900',
      accent: 'text-orange-700',
      icon: 'text-orange-600'
    };
  } else if (category === 'validator') {
    return {
      bg: 'bg-white',         // White background with colored border
      border: 'border-sky-300',
      headerBg: 'bg-sky-100',
      text: 'text-sky-900',
      accent: 'text-sky-700',
      icon: 'text-sky-600'
    };
  } else {
    // Default blue theme for pioneer states
    return {
      bg: 'bg-white',
      border: 'border-blue-300',
      headerBg: 'bg-blue-100',
      text: 'text-blue-900',
      accent: 'text-blue-700',
      icon: 'text-blue-600'
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
 * Get simple icon color for sidebar and navigation
 */
export const getCategoryIconColor = (category) => {
  switch (category) {
    case 'builder':
      return 'text-orange-600';
    case 'validator':
      return 'text-sky-600';
    case 'global':
      return 'text-black';
    default:
      return 'text-gray-500';
  }
};