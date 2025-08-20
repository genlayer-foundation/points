<script context="module">
  // Icon paths for all icons used in the application
  export const icons = {
    // GenLayer logo (just the geometric logo without text)
    genlayer: 'M44.26 32.35L27.72 67.12L43.29 74.9L0 91.93L44.26 0L44.26 32.35ZM53.5 32.35L70.04 67.12L54.47 74.9L97.76 91.93L53.5 0L53.5 32.35ZM48.64 43.78L58.33 62.94L48.64 67.69L39.47 62.92L48.64 43.78Z',
    
    // Category icons
    global: 'M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm-1 17.93c-4.956-.46-8.93-4.436-9.39-9.39h4.653c.088 1.85.347 3.55.742 4.82 1.068 1.408 2.355 2.365 3.995 2.57zm0-5.116c-.877-.196-1.615-.88-2.254-1.894-.304-.977-.508-2.14-.58-3.42h2.834v5.314zm0-6.814h-2.834c.072-1.28.276-2.443.58-3.42.639-1.014 1.377-1.698 2.254-1.894v5.314zm0-6.816c-1.64.205-2.927 1.162-3.995 2.57-.395 1.27-.654 2.97-.742 4.82H2.61c.46-4.954 4.434-8.93 9.39-9.39zm2 0c4.956.46 8.93 4.436 9.39 9.39h-4.653c-.088-1.85-.347-3.55-.742-4.82-1.068-1.408-2.355-2.365-3.995-2.57zm0 5.116c.877.196 1.615.88 2.254 1.894.304.977.508 2.14.58 3.42H13v-5.314zm0 6.814h2.834c-.072 1.28-.276 2.443-.58 3.42-.639 1.014-1.377 1.698-2.254 1.894v-5.314zm0 6.816c1.64-.205 2.927-1.162 3.995-2.57.395-1.27.654-2.97.742-4.82h4.653c-.46 4.954-4.434 8.93-9.39 9.39z',
    
    builder: 'M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z',
    
    validator: 'M12 2L4 7v5c0 5 3.5 9.5 8 10.5 4.5-1 8-5.5 8-10.5V7L12 2z',
    
    steward: 'M60.352 30.213c-.867-.744-8.626-7.27-14.026-7.27c-6.732 0-9.982 5.871-10.762 8.976l-.118.475a16.762 16.762 0 0 0-2.812 2.015a15.544 15.544 0 0 0-2.447 2.772c-.056-.267-.111-.534-.179-.792c-.794-2.901-2.068-5.467-3.441-7.961c-1.11-1.971-2.336-3.856-3.62-5.695l.063-.127c1.344-2.712 2.531-9.261-2.588-14.628C16.253 3.605 5.39 2.354 4.166 2.228L2 2l.213 2.236c.122 1.284 1.311 12.653 5.473 17.015c2.317 2.429 5.215 3.714 8.382 3.714c2.602 0 4.747-.862 5.703-1.32a68.516 68.516 0 0 1 3.157 5.697c1.19 2.469 2.271 5.043 2.816 7.614c.131.639-.77 25.044-.77 25.044h4.454s-.696-20.141-.573-20.625c.52-2.013 1.652-3.906 3.144-5.448a14.7 14.7 0 0 1 2.094-1.774c1.303 2.616 4.515 6.158 10.233 6.158c5.4 0 13.159-6.525 14.026-7.269L62 31.627l-1.648-1.414',
    
    // Navigation icons
    dashboard: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
    
    leaderboard: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z',
    
    participants: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    
    contributions: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01',
    
    metrics: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    
    mySubmissions: 'M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z',
    
    profile: 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z',
    
    builders: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
    
    // UI icons
    menu: 'M4 6h16M4 12h8m-8 6h16',
    
    search: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
    
    plus: 'M12 6v6m0 0v6m0-6h6m-6 0H6',
    
    externalLink: 'M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14',
    
    download: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4',
    
    clock: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    
    warning: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z',
    
    error: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z',
    
    lightning: 'M13 10V3L4 14h7v7l9-11h-7z',
    
    // Chevron for expanded/collapsed sections
    chevronDown: 'M6 9l6 6 6-6',
    chevronRight: 'M9 6l6 6-6 6',
    
    // Stats icons
    users: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    
    document: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    
    points: 'M13 10V3L4 14h7v7l9-11h-7z',
    
    star: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z'
  };
</script>

<script>
  let { name = '', size = 'md', className = '' } = $props();
  
  // Size mappings
  const sizes = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
    xl: 'w-8 h-8'
  };
  
  // Icons that use fill instead of stroke
  const fillIcons = ['genlayer', 'global', 'builder', 'validator', 'steward', 'leaderboard', 'profile'];
  
  let sizeClass = $derived(sizes[size] || sizes.md);
  let iconPath = $derived(icons[name] || '');
  let useFill = $derived(fillIcons.includes(name));
</script>

{#if iconPath}
  {#if name === 'genlayer'}
    <!-- Special case for GenLayer logo with different viewBox -->
    <svg 
      class="{sizeClass} {className}" 
      fill="currentColor" 
      viewBox="0 0 97.76 91.93"
      aria-hidden="true"
    >
      <path d={iconPath} />
    </svg>
  {:else if name === 'steward'}
    <!-- Special case for steward icon with different viewBox -->
    <svg 
      class="{sizeClass} {className}" 
      fill="currentColor" 
      viewBox="0 0 64 64"
      aria-hidden="true"
    >
      <path d={iconPath} />
    </svg>
  {:else if useFill}
    <svg 
      class="{sizeClass} {className}" 
      fill="currentColor" 
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path d={iconPath} />
    </svg>
  {:else}
    <svg 
      class="{sizeClass} {className}" 
      fill="none" 
      stroke="currentColor" 
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path 
        stroke-linecap="round" 
        stroke-linejoin="round" 
        stroke-width="2" 
        d={iconPath} 
      />
    </svg>
  {/if}
{:else}
  <!-- Fallback for missing icon -->
  <span class="{sizeClass} {className}">?</span>
{/if}