<script>
  import { push, location } from 'svelte-spa-router';
  import AuthButton from './AuthButton.svelte';
  import SearchBar from './SearchBar.svelte';
  import { authState } from '../lib/auth.js';
  
  let { toggleSidebar, sidebarOpen = false } = $props();
  
  let isMenuOpen = $state(false);
  
  function toggleMenu() {
    isMenuOpen = !isMenuOpen;
  }
  
  function navigate(path) {
    push(path);
    isMenuOpen = false;
  }
  
  function handleSubmitContribution() {
    if ($authState.isAuthenticated) {
      navigate('/submit-contribution');
    } else {
      // Store the intended destination
      sessionStorage.setItem('redirectAfterLogin', '/submit-contribution');
      // Trigger login by programmatically clicking the auth button
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
    }
  }
  
  // Check if a route is active
  function isActive(path) {
    return $location === path;
  }
</script>

<header class="bg-white relative z-50" style="border-bottom: 1.2px solid #e5e5e6;">
  <div class="flex items-center justify-between p-3">
    <!-- Left: Logo -->
    <div class="flex items-center gap-1 px-1">
      <a href="/" onclick={(e) => { e.preventDefault(); navigate('/'); }} class="flex items-center">
        <img src="/assets/gl-logo-points.svg" alt="GenLayer Points" class="h-8 w-auto">
      </a>
    </div>

    <!-- Right: Actions -->
    <div class="hidden md:flex items-center gap-2">
      <SearchBar />
      <button
        onclick={handleSubmitContribution}
        class="h-10 px-4 bg-gradient-to-r from-[#be8ff5] to-[#ac6df3] text-white rounded-[20px] flex items-center gap-2 font-medium text-sm"
        style="letter-spacing: 0.28px;"
      >
        <span>Submit a contribution</span>
        <img src="/assets/icons/add-line.svg" alt="" class="w-4 h-4">
      </button>
      <AuthButton />
    </div>

    <!-- Mobile: Actions -->
    <div class="flex items-center md:hidden gap-2">
      <AuthButton />
      <button
        onclick={() => {
          if (toggleSidebar) {
            toggleSidebar();
          }
        }}
        class="p-2 rounded-md text-gray-700 hover:bg-gray-100 relative"
        aria-label="{sidebarOpen ? 'Close' : 'Open'} menu"
      >
        <div class="h-6 w-6 relative flex items-center justify-center">
          <!-- Top line -->
          <span class="absolute h-0.5 w-6 bg-current transform transition-all duration-300 ease-in-out {sidebarOpen ? 'rotate-45' : 'rotate-0 -translate-y-2'}"></span>
          <!-- Middle line -->
          <span class="absolute h-0.5 w-6 bg-current transform transition-all duration-300 ease-in-out {sidebarOpen ? 'opacity-0' : 'opacity-100'}"></span>
          <!-- Bottom line -->
          <span class="absolute h-0.5 w-6 bg-current transform transition-all duration-300 ease-in-out {sidebarOpen ? '-rotate-45' : 'rotate-0 translate-y-2'}"></span>
        </div>
      </button>
    </div>
  </div>
</header>