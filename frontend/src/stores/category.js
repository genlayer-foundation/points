import { writable, derived } from 'svelte/store';

// Current active category
export const currentCategory = writable('global');

// Category configuration with SVG icon paths
export const categories = [
  { 
    id: 'global', 
    name: 'Testnet Asimov', 
    iconPath: 'M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm-1 17.93c-4.956-.46-8.93-4.436-9.39-9.39h4.653c.088 1.85.347 3.55.742 4.82 1.068 1.408 2.355 2.365 3.995 2.57zm0-5.116c-.877-.196-1.615-.88-2.254-1.894-.304-.977-.508-2.14-.58-3.42h2.834v5.314zm0-6.814h-2.834c.072-1.28.276-2.443.58-3.42.639-1.014 1.377-1.698 2.254-1.894v5.314zm0-6.816c-1.64.205-2.927 1.162-3.995 2.57-.395 1.27-.654 2.97-.742 4.82H2.61c.46-4.954 4.434-8.93 9.39-9.39zm2 0c4.956.46 8.93 4.436 9.39 9.39h-4.653c-.088-1.85-.347-3.55-.742-4.82-1.068-1.408-2.355-2.365-3.995-2.57zm0 5.116c.877.196 1.615.88 2.254 1.894.304.977.508 2.14.58 3.42H13v-5.314zm0 6.814h2.834c-.072 1.28-.276 2.443-.58 3.42-.639 1.014-1.377 1.698-2.254 1.894v-5.314zm0 6.816c1.64-.205 2.927-1.162 3.995-2.57.395-1.27.654-2.97.742-4.82h4.653c-.46 4.954-4.434 8.93-9.39 9.39z'
  },
  { 
    id: 'builder', 
    name: 'Builders', 
    iconPath: 'M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z'
  },
  { 
    id: 'validator', 
    name: 'Validators', 
    iconPath: 'M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm1 6h-2v4H9l3 4 3-4h-2V8z'
  }
];

// Theme configuration for each category
export const categoryTheme = derived(currentCategory, $category => {
  const themes = {
    global: {
      // Default theme - indigo/purple
      bg: 'bg-white',
      bgSecondary: 'bg-gray-50',
      primary: 'bg-indigo-600',
      primaryHover: 'hover:bg-indigo-700',
      text: 'text-indigo-600',
      textLight: 'text-indigo-500',
      border: 'border-gray-200',
      borderAccent: 'border-indigo-200',
      ring: 'focus:ring-indigo-500',
      badge: 'bg-indigo-100 text-indigo-800',
      button: 'bg-indigo-600 hover:bg-indigo-700 text-white',
      buttonLight: 'bg-indigo-50 hover:bg-indigo-100 text-indigo-700'
    },
    builder: {
      // Orange/sunset theme
      bg: 'bg-orange-50',
      bgSecondary: 'bg-orange-100',
      primary: 'bg-orange-500',
      primaryHover: 'hover:bg-orange-600',
      text: 'text-orange-600',
      textLight: 'text-orange-500',
      border: 'border-orange-200',
      borderAccent: 'border-orange-300',
      ring: 'focus:ring-orange-500',
      badge: 'bg-orange-100 text-orange-800',
      button: 'bg-orange-500 hover:bg-orange-600 text-white',
      buttonLight: 'bg-orange-100 hover:bg-orange-200 text-orange-700'
    },
    validator: {
      // Blue/technical theme
      bg: 'bg-sky-50',
      bgSecondary: 'bg-sky-100',
      primary: 'bg-sky-500',
      primaryHover: 'hover:bg-sky-600',
      text: 'text-sky-600',
      textLight: 'text-sky-500',
      border: 'border-sky-200',
      borderAccent: 'border-sky-300',
      ring: 'focus:ring-sky-500',
      badge: 'bg-sky-100 text-sky-800',
      button: 'bg-sky-500 hover:bg-sky-600 text-white',
      buttonLight: 'bg-sky-100 hover:bg-sky-200 text-sky-700'
    }
  };
  
  return themes[$category] || themes.global;
});

// Helper to get API endpoint for category
export function getCategoryEndpoint(category, baseEndpoint) {
  if (category === 'global') {
    return baseEndpoint;
  }
  return `${baseEndpoint}/category/${category}`;
}

// Helper to detect category from route
export function detectCategoryFromRoute(path) {
  if (path.startsWith('/builders')) {
    return 'builder';
  } else if (path.startsWith('/validators')) {
    return 'validator';
  }
  return 'global';
}