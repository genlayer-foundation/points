<script>
  import { push, location } from 'svelte-spa-router';
  import AuthButton from './AuthButton.svelte';
  import Icon from './Icons.svelte';
  import { authState } from '../lib/auth.js';
  import { categoryTheme, currentCategory } from '../stores/category.js';
  
  
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
          <Icon name="genlayer" size="lg" className="text-black" />
          <span class="ml-3 text-xl font-bold {$currentCategory === 'global' ? 'text-black' : $categoryTheme.text}">GenLayer Testnet Contributions</span>
        </a>
      </div>
      
      <div class="hidden md:flex items-center gap-4">
        <button 
          onclick={handleSubmitContribution}
          class="px-3 py-2 {$categoryTheme.button} rounded-md"
        >
          Submit Contribution
        </button>
        <div class="ml-4 flex items-center gap-4">
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