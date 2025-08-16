<script>
  import { push, location } from 'svelte-spa-router';
  import AuthButton from './AuthButton.svelte';
  import { authState } from '../lib/auth.js';
  
  let { toggleSidebar } = $props();
  
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

<header class="bg-white shadow">
  <div class="container mx-auto px-4">
    <div class="flex justify-between h-16">
      <div class="flex items-center">
        <a href="/" onclick={(e) => { e.preventDefault(); navigate('/'); }} class="flex-shrink-0 flex items-center">
          <img class="h-8 w-8" src="/assets/logo.svg" alt="GenLayer Logo" />
          <span class="ml-2 text-sm sm:text-xl font-bold text-primary-700">
            <span class="hidden sm:inline">GenLayer Testnet Contributions</span>
            <span class="sm:hidden">GenLayer</span>
          </span>
        </a>
      </div>
      
      <div class="hidden md:flex items-center gap-4">
        <button 
          onclick={handleSubmitContribution}
          class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 font-medium"
        >
          Submit Contribution
        </button>
        <AuthButton />
      </div>
      
      <div class="flex items-center md:hidden gap-2">
        <AuthButton />
        <button 
          onclick={toggleSidebar} 
          class="p-2 rounded-md text-gray-700 hover:bg-gray-100"
          aria-label="Open menu"
        >
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
    </div>
  </div>
  
</header>