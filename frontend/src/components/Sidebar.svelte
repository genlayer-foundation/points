<script>
  import { push, location } from 'svelte-spa-router';
  
  let { isOpen = $bindable(false) } = $props();
  
  // Close sidebar on route change on mobile
  $effect(() => {
    if (isOpen && window.innerWidth < 768) {
      isOpen = false;
    }
  });
  
  function toggleSidebar() {
    isOpen = !isOpen;
  }
  
  function navigate(path) {
    push(path);
    // Close sidebar on mobile after navigation
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }
  
  // Check if a route is active
  function isActive(path) {
    return $location === path;
  }
  
  const navItems = [
    { 
      name: 'Dashboard', 
      path: '/', 
      icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' 
    },
    { 
      name: 'Leaderboard', 
      path: '/leaderboard', 
      icon: 'M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3' 
    },
    { 
      name: 'Contributions', 
      path: '/contributions', 
      icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' 
    },
    {
      name: 'My Submissions',
      path: '/my-submissions',
      icon: 'M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z'
    },
    {
      name: 'Validators',
      path: '/validators',
      icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z'
    },
    {
      name: 'Metrics',
      path: '/metrics',
      icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
    }
  ];
</script>

<!-- Desktop Sidebar -->
<aside class="hidden md:block w-64 bg-white shadow-md h-screen sticky top-0">
  <nav class="mt-8 px-4">
    <div class="space-y-1">
      {#each navItems as item}
        <button
          onclick={() => navigate(item.path)}
          class="w-full group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors {isActive(item.path) ? 'bg-primary-50 text-primary-700' : 'text-gray-700 hover:bg-gray-50'}"
        >
          <svg 
            class="mr-3 h-5 w-5 {isActive(item.path) ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'}"
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor" 
            aria-hidden="true"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={item.icon} />
          </svg>
          {item.name}
        </button>
      {/each}
    </div>
  </nav>
</aside>

<!-- Mobile Sidebar Overlay -->
{#if isOpen}
  <!-- Backdrop -->
  <div 
    class="md:hidden fixed inset-0 z-40 bg-gray-600 bg-opacity-75"
    onclick={toggleSidebar}
  ></div>
  
  <!-- Mobile Sidebar -->
  <aside class="md:hidden fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl">
    <div class="flex items-center justify-between h-16 px-4 border-b">
      <span class="text-xl font-semibold text-gray-900">Menu</span>
      <button 
        onclick={toggleSidebar}
        class="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
      >
        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    
    <nav class="mt-5 px-4">
      <div class="space-y-1">
        {#each navItems as item}
          <button
            onclick={() => navigate(item.path)}
            class="w-full group flex items-center px-3 py-2 text-base font-medium rounded-md transition-colors {isActive(item.path) ? 'bg-primary-50 text-primary-700' : 'text-gray-700 hover:bg-gray-50'}"
          >
            <svg 
              class="mr-3 h-5 w-5 {isActive(item.path) ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'}"
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor" 
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={item.icon} />
            </svg>
            {item.name}
          </button>
        {/each}
      </div>
    </nav>
  </aside>
{/if}

<style>
  /* Add smooth transition for mobile sidebar */
  aside {
    transition: transform 0.3s ease-in-out;
  }
</style>