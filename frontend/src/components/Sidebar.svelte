<script>
  import { push, location } from 'svelte-spa-router';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Icon from './Icons.svelte';
  import { authState } from '../lib/auth.js';
  
  $effect(() => {
    // Reset mobile menu when route changes
    if (isOpen && window.innerWidth < 768) {
      isOpen = false;
    }
  });
  
  let isOpen = $state(false);
  
  function toggleSidebar() {
    isOpen = !isOpen;
  }
  
  function navigate(path, requiresAuth = false) {
    if (requiresAuth && !$authState.isAuthenticated) {
      // Store the intended destination
      sessionStorage.setItem('redirectAfterLogin', path);
      // Trigger login by programmatically clicking the auth button
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
      return;
    }
    
    push(path);
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }
  
  function handleProfileClick() {
    if ($authState.isAuthenticated) {
      // Go to public profile, not edit
      push(`/participant/${$authState.address}`);
    } else {
      // Trigger login
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
    }
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }
  
  // Check if a route is active
  function isActive(path) {
    return $location === path;
  }
  
  // Define navigation structure with sections - consistent ordering across all categories
  const navigationStructure = {
    global: {
      main: [
        { name: 'Dashboard', path: '/', iconName: 'dashboard' },
        { name: 'Contributions', path: '/contributions', iconName: 'contributions' },
        { name: 'Leaderboard', path: '/leaderboard', iconName: 'leaderboard' },
        { name: 'Participants', path: '/participants', iconName: 'participants' }
      ],
      profile: [
        { name: 'My Submissions', path: '/my-submissions', iconName: 'mySubmissions', requiresAuth: true },
        { name: 'Profile', path: 'profile', iconName: 'profile', isProfile: true }
      ]
    },
    builder: {
      main: [
        { name: 'Dashboard', path: '/', iconName: 'dashboard' },
        { name: 'Contributions', path: '/contributions', iconName: 'contributions' },
        { name: 'Leaderboard', path: '/leaderboard', iconName: 'leaderboard' },
        { name: 'Builders', path: '/participants', iconName: 'builder' }
      ],
      profile: [
        { name: 'My Submissions', path: '/my-submissions', iconName: 'mySubmissions', requiresAuth: true },
        { name: 'Profile', path: 'profile', iconName: 'profile', isProfile: true }
      ]
    },
    validator: {
      main: [
        { name: 'Dashboard', path: '/', iconName: 'dashboard' },
        { name: 'Contributions', path: '/contributions', iconName: 'contributions' },
        { name: 'Leaderboard', path: '/leaderboard', iconName: 'leaderboard' },
        { name: 'Validators', path: '/participants', iconName: 'validator' }
      ],
      profile: [
        { name: 'My Submissions', path: '/my-submissions', iconName: 'mySubmissions', requiresAuth: true },
        { name: 'Profile', path: 'profile', iconName: 'profile', isProfile: true }
      ]
    }
  };
  
  // Get nav sections based on current category
  let navSections = $derived(navigationStructure[$currentCategory] || navigationStructure.global);
</script>

<div class="md:w-64 flex flex-col fixed md:sticky top-0 z-10">
  <!-- Mobile toggle -->
  <div class="md:hidden px-4 py-3 bg-gray-50">
    <button 
      onclick={toggleSidebar} 
      class="text-gray-600 hover:text-gray-900 focus:outline-none"
      aria-label="Toggle sidebar"
    >
      <Icon name="menu" size="lg" />
    </button>
  </div>
  
  <!-- Sidebar content -->
  <aside class={`bg-white shadow-md md:h-screen md:sticky md:top-16 md:block transition-all duration-300 ${isOpen ? 'block' : 'hidden'}`}>
    <div class="p-4">
      <nav class="mt-4 space-y-1">
        <!-- Main navigation items -->
        {#each navSections.main as item}
          <a 
            href={item.path}
            onclick={(e) => { e.preventDefault(); navigate(item.path); }}
            class={`group flex items-center px-3 py-2 text-sm font-medium rounded-md ${isActive(item.path) ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-700 hover:bg-gray-50'}`}
          >
            <Icon 
              name={item.iconName}
              size="md"
              className="mr-3 {isActive(item.path) ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
            />
            {item.name}
          </a>
        {/each}
        
        <!-- Profile section separator and items -->
        {#if navSections.profile && navSections.profile.length > 0}
          <div class="my-3 border-t border-gray-200"></div>
          {#each navSections.profile as item}
            {#if item.isProfile}
              <button
                onclick={handleProfileClick}
                class="group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50 w-full text-left"
              >
                <Icon 
                  name={item.iconName}
                  size="md"
                  className="mr-3 text-gray-400 group-hover:text-gray-500"
                />
                {item.name}
              </button>
            {:else}
              <a 
                href={item.path}
                onclick={(e) => { e.preventDefault(); navigate(item.path, item.requiresAuth); }}
                class={`group flex items-center px-3 py-2 text-sm font-medium rounded-md ${isActive(item.path) ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-700 hover:bg-gray-50'}`}
              >
                <Icon 
                  name={item.iconName}
                  size="md"
                  className="mr-3 {isActive(item.path) ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
                />
                {item.name}
              </a>
            {/if}
          {/each}
        {/if}
      </nav>
    </div>
  </aside>
</div>