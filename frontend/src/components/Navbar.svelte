<script>
  import { push, location } from 'svelte-spa-router';
  import AuthButton from './AuthButton.svelte';
  import SearchBar from './SearchBar.svelte';
  import NotificationCenter from './NotificationCenter.svelte';
  import WhatsNewTrigger from './WhatsNewTrigger.svelte';
  import { authState } from '../lib/auth.js';
  import { currentCategory } from '../stores/category.js';
  
  let { toggleSidebar, sidebarOpen = false } = $props();
  
  let isMenuOpen = $state(false);

  const submitButtonBaseClass = 'h-10 px-4 text-white rounded-[20px] flex items-center gap-2 font-medium text-sm';
  const DISCORD_URL = 'https://discord.gg/pSHDngcR';
  const socialLinks = [
    { label: 'X', href: 'https://x.com/GenLayer', icon: 'x' },
    { label: 'Discord', href: DISCORD_URL, icon: 'discord' },
    { label: 'GitHub', href: 'https://github.com/genlayerlabs', icon: 'github' },
  ];

  let submitButtonStyle = $derived(
    $currentCategory === 'builder'
      ? 'background: linear-gradient(168deg, #f8b93d 15%, #ee8d24 50%, #db6917 85%);'
      : $currentCategory === 'validator'
      ? 'background: linear-gradient(168deg, #6fa3f8 15%, #4f76f6 50%, #3b5dd6 85%);'
      : 'background: linear-gradient(to right, #be8ff5, #ac6df3);'
  );
  
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
  <div class="navbar-inner flex items-center justify-between p-3">
    <!-- Left: Logo -->
    <div class="navbar-logo-wrap flex items-center gap-1 px-1 min-w-0">
      <a href="/" onclick={(e) => { e.preventDefault(); navigate('/'); }} class="flex items-center">
        <img src="/assets/genlayer-portal-logo.svg" alt="GenLayer Portal" class="portal-logo h-[32px] w-auto">
      </a>
      <div class="navbar-social-links hidden sm:flex items-center gap-2 pl-2 ml-2 border-l border-[#ececee]" aria-label="GenLayer social links">
        {#each socialLinks as link (link.href)}
          <a
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex h-7 w-7 items-center justify-center rounded-[6px] text-[#656567] transition-colors hover:bg-[#f5f5f5] hover:text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8D81E1]"
            aria-label={link.label}
            title={link.label}
          >
            {#if link.icon === 'x'}
              <svg class="h-[13px] w-[13px]" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.657l-5.214-6.817-5.965 6.817H1.681l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z" />
              </svg>
            {:else if link.icon === 'discord'}
              <svg class="h-[15px] w-[15px]" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M20.317 4.369A19.791 19.791 0 0 0 15.366 2.8a.074.074 0 0 0-.079.037c-.213.38-.45.875-.616 1.265a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.626-1.265.077.077 0 0 0-.079-.037 19.736 19.736 0 0 0-4.951 1.569.07.07 0 0 0-.032.027C.533 8.824-.319 13.144.079 17.41a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 6.073 3.075.078.078 0 0 0 .084-.027c.468-.638.885-1.312 1.24-2.02a.076.076 0 0 0-.041-.105 13.1 13.1 0 0 1-1.872-.892.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.009c.12.099.246.198.373.292a.077.077 0 0 1-.007.128 12.299 12.299 0 0 1-1.873.891.077.077 0 0 0-.04.106c.36.707.777 1.381 1.238 2.019a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.082-3.075.077.077 0 0 0 .031-.055c.477-4.932-.8-9.216-3.419-13.015a.061.061 0 0 0-.031-.028ZM8.02 14.801c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.211 0 2.176 1.096 2.157 2.419 0 1.333-.955 2.419-2.157 2.419Zm7.975 0c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.211 0 2.176 1.096 2.157 2.419 0 1.333-.946 2.419-2.157 2.419Z" />
              </svg>
            {:else}
              <svg class="h-[15px] w-[15px]" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" clip-rule="evenodd" d="M12 .5C5.649.5.5 5.649.5 12c0 5.087 3.292 9.396 7.863 10.918.575.101.791-.244.791-.546 0-.273-.014-1.178-.014-2.141-2.89.532-3.637-.704-3.867-1.351-.129-.331-.69-1.351-1.178-1.624-.403-.216-.978-.748-.014-.762.906-.014 1.552.834 1.768 1.179 1.035 1.739 2.688 1.25 3.35.949.101-.748.403-1.25.733-1.538-2.559-.288-5.232-1.279-5.232-5.678 0-1.25.446-2.285 1.178-3.091-.115-.288-.517-1.466.115-3.049 0 0 .963-.302 3.162 1.178A10.856 10.856 0 0 1 12 6.056c.978.004 1.956.133 2.846.388 2.199-1.494 3.162-1.178 3.162-1.178.632 1.583.23 2.761.115 3.049.733.806 1.178 1.826 1.178 3.091 0 4.414-2.688 5.39-5.246 5.678.417.359.776 1.049.776 2.127 0 1.538-.014 2.775-.014 3.162 0 .302.216.662.791.546C20.208 21.396 23.5 17.073 23.5 12 23.5 5.649 18.351.5 12 .5Z" />
              </svg>
            {/if}
          </a>
        {/each}
      </div>
    </div>

    <!-- Right: Actions -->
    <div class="hidden md:flex items-center gap-2">
      <WhatsNewTrigger />
      <NotificationCenter />
      {#if $authState.isAuthenticated}
        <SearchBar />
      {/if}
      <button
        onclick={handleSubmitContribution}
        class={submitButtonBaseClass}
        style={submitButtonStyle}
      >
        <span>Submit a contribution</span>
        <img src="/assets/icons/add-line.svg" alt="" class="w-4 h-4">
      </button>
      <AuthButton />
    </div>

    <!-- Mobile: Actions -->
    <div class="navbar-mobile-actions flex items-center md:hidden gap-2">
      <WhatsNewTrigger />
      <NotificationCenter />
      <AuthButton />
      <button
        onclick={() => {
          if (toggleSidebar) {
            toggleSidebar();
          }
        }}
        class="mobile-menu-button p-2 rounded-md text-gray-700 hover:bg-gray-100 relative"
        aria-label="{sidebarOpen ? 'Close' : 'Open'} menu"
      >
        <div class="mobile-menu-icon h-6 w-6 relative flex items-center justify-center">
          <!-- Top line -->
          <span class="mobile-menu-line absolute h-0.5 w-6 bg-current transform transition-all duration-300 ease-in-out {sidebarOpen ? 'rotate-45' : 'rotate-0 -translate-y-2'}"></span>
          <!-- Middle line -->
          <span class="mobile-menu-line absolute h-0.5 w-6 bg-current transform transition-all duration-300 ease-in-out {sidebarOpen ? 'opacity-0' : 'opacity-100'}"></span>
          <!-- Bottom line -->
          <span class="mobile-menu-line absolute h-0.5 w-6 bg-current transform transition-all duration-300 ease-in-out {sidebarOpen ? '-rotate-45' : 'rotate-0 translate-y-2'}"></span>
        </div>
      </button>
    </div>
  </div>
</header>

<style>
  @media (max-width: 767px) {
    .navbar-inner {
      gap: 0.5rem;
      padding: 0.5rem 0.625rem;
    }

    .navbar-logo-wrap {
      flex: 1 1 auto;
      padding-left: 0;
      padding-right: 0;
    }

    .portal-logo {
      height: 1.375rem;
      max-width: 7.625rem;
    }

    .navbar-mobile-actions {
      flex: 0 0 auto;
      gap: 0.375rem;
    }

    .mobile-menu-button {
      padding: 0.375rem;
    }

    .mobile-menu-icon {
      height: 1.25rem;
      width: 1.25rem;
    }

    .mobile-menu-line {
      width: 1.25rem;
    }
  }
</style>
