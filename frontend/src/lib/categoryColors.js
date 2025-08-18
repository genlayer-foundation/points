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