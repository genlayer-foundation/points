<script>
  import { push, location } from 'svelte-spa-router';
  import AuthButton from './AuthButton.svelte';
  import { authState } from '../lib/auth.js';
  
  
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
          <span class="ml-2 text-xl font-bold text-primary-700">GenLayer Testnet Contributions</span>
        </a>
      </div>
      
      <div class="hidden md:flex items-center space-x-4">
        <a 
          href="/" 
          onclick={(e) => { e.preventDefault(); navigate('/'); }}
          class="px-3 py-2 text-gray-700 hover:text-primary-600 {isActive('/') ? 'text-primary-600 font-medium' : ''}"
        >
          Dashboard
        </a>
        <a 
          href="/highlights" 
          onclick={(e) => { e.preventDefault(); navigate('/highlights'); }}
          class="px-3 py-2 text-gray-700 hover:text-primary-600 {isActive('/highlights') ? 'text-primary-600 font-medium' : ''}"
        >
          Highlights
        </a>
        <a 
          href="/contributions" 
          onclick={(e) => { e.preventDefault(); navigate('/contributions'); }}
          class="px-3 py-2 text-gray-700 hover:text-primary-600 {isActive('/contributions') ? 'text-primary-600 font-medium' : ''}"
        >
          Contributions
        </a>
        <button 
          onclick={handleSubmitContribution}
          class="px-3 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          Submit Contribution
        </button>
        <div class="ml-4 flex items-center space-x-4">
          <AuthButton />
        </div>
      </div>
      
      <div class="flex items-center md:hidden">
        <button 
          onclick={toggleMenu} 
          class="p-2 rounded-md text-gray-700 hover:bg-gray-100"
          aria-label="Main menu"
        >
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {#if isMenuOpen}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            {:else}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            {/if}
          </svg>
        </button>
      </div>
    </div>
  </div>
  
  <!-- Mobile menu -->
  {#if isMenuOpen}
    <div class="md:hidden">
      <div class="px-2 pt-2 pb-3 space-y-1">
        <a 
          href="/" 
          onclick={(e) => { e.preventDefault(); navigate('/'); }}
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 {isActive('/') ? 'bg-gray-50 text-primary-600' : ''}"
        >
          Dashboard
        </a>
        <a 
          href="/highlights" 
          onclick={(e) => { e.preventDefault(); navigate('/highlights'); }}
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 {isActive('/highlights') ? 'bg-gray-50 text-primary-600' : ''}"
        >
          Highlights
        </a>
        <a 
          href="/contributions" 
          onclick={(e) => { e.preventDefault(); navigate('/contributions'); }}
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-600 hover:bg-gray-50 {isActive('/contributions') ? 'bg-gray-50 text-primary-600' : ''}"
        >
          Contributions
        </a>
        <button 
          onclick={handleSubmitContribution}
          class="block w-full text-left px-3 py-2 rounded-md text-base font-medium bg-primary-600 text-white hover:bg-primary-700"
        >
          Submit Contribution
        </button>
        <div class="px-3 py-2">
          <AuthButton />
        </div>
      </div>
    </div>
  {/if}
</header>