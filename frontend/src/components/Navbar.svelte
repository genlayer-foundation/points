<script>
  import { push, location } from 'svelte-spa-router';
  import AuthButton from './AuthButton.svelte';
  import Icon from './Icons.svelte';
  import { authState } from '../lib/auth.js';
  import { categoryTheme, currentCategory } from '../stores/category.js';
  
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
  <div class="flex">
    <!-- Left section with logo - aligned with sidebar content -->
    <div class="w-64 flex items-center h-16 px-7">
      <a href="/" onclick={(e) => { e.preventDefault(); navigate('/'); }} class="flex items-center">
        <Icon name="genlayer" size="lg" className="text-black" />
        <span class="ml-3 text-sm sm:text-xl font-bold {$currentCategory === 'global' ? 'text-black' : $categoryTheme.text}">
          <span class="hidden sm:inline">GenLayer Points</span>
          <span class="sm:hidden">GenLayer</span>
        </span>
      </a>
    </div>
    
    <!-- Right section with actions -->
    <div class="flex-1 flex justify-end items-center h-16 px-4">
      <div class="hidden md:flex items-center gap-4">
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