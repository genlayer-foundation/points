<script>
  import { push, location } from 'svelte-spa-router';
  import AuthButton from './AuthButton.svelte';
  import ReferralSection from './ReferralSection.svelte';
  import Icon from './Icons.svelte';
  import { authState } from '../lib/auth.js';
  import { categoryTheme, currentCategory } from '../stores/category.js';
  
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

<header class="bg-white shadow relative z-50">
  <div class="flex">
    <!-- Left section with logo - aligned with sidebar content on desktop, normal padding on mobile -->
    <div class="md:w-64 flex items-center h-16 px-4 md:px-7">
      <a href="/" onclick={(e) => { e.preventDefault(); navigate('/'); }} class="flex items-center">
        <Icon name="genlayer" size="lg" className="text-black" />
        <span class="ml-3 text-sm sm:text-xl font-bold font-heading {$currentCategory === 'global' ? 'text-black' : $categoryTheme.text}">
          GenLayer <span class="text-xs sm:text-xl">Points</span>
        </span>
      </a>
    </div>
    
    <!-- Right section with actions -->
    <div class="flex-1 flex justify-end items-center h-16 px-4">
      <div class="hidden md:flex items-center gap-4">
        <ReferralSection />
        <button 
          onclick={handleSubmitContribution}
          class="px-4 py-2 {$categoryTheme.button} rounded-md font-medium"
        >
          Submit Contribution
        </button>
        <AuthButton />
      </div>
      
      <div class="flex items-center md:hidden gap-2">
        <AuthButton />
        <button 
          onclick={() => {
            if (toggleSidebar) {
              toggleSidebar();
            } else {
              console.error('toggleSidebar function not provided to Navbar');
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
  </div>
</header>