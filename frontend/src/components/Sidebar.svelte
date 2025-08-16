<script>
  import { push, location } from 'svelte-spa-router';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Icon from './Icons.svelte';
  import { authState } from '../lib/auth.js';
  
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
    // Close sidebar on mobile after navigation
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
  
  // Function to change category and navigate
  function changeCategory(category, path = '/') {
    currentCategory.set(category);
    push(path);
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }
  
  // Define the complete navigation structure
  const navigationStructure = [
    {
      title: 'Testnet Asimov',
      category: 'global',
      iconName: 'genlayer',
      dashboardPath: '/',
      dashboardAction: () => changeCategory('global', '/'),
      items: [
        { name: 'Metrics', path: '/metrics', iconName: 'metrics' }
      ]
    },
    {
      title: 'Builders',
      category: 'builder',
      iconName: 'builder',
      color: 'orange',
      dashboardPath: '/builders',
      dashboardAction: () => changeCategory('builder', '/builders'),
      items: [
        { name: 'Contributions', path: '/builders/contributions', iconName: 'contributions' },
        { name: 'Leaderboard', path: '/builders/leaderboard', iconName: 'leaderboard' },
        { name: 'Participants', path: '/builders/participants', iconName: 'participants' }
      ]
    },
    {
      title: 'Validators',
      category: 'validator',
      iconName: 'validator', 
      color: 'sky',
      dashboardPath: '/validators',
      dashboardAction: () => changeCategory('validator', '/validators'),
      items: [
        { name: 'Contributions', path: '/validators/contributions', iconName: 'contributions' },
        { name: 'Leaderboard', path: '/validators/leaderboard', iconName: 'leaderboard' },
        { name: 'Participants', path: '/validators/participants', iconName: 'participants' }
      ]
    }
  ];
  
  // Profile section items (same for all categories)
  const profileItems = [
    { name: 'My Submissions', path: '/my-submissions', iconName: 'mySubmissions', requiresAuth: true },
    { name: 'Profile', path: 'profile', iconName: 'profile', isProfile: true }
  ];
</script>

<!-- Desktop Sidebar -->
<aside class="hidden md:block w-64 bg-white shadow-md h-screen sticky top-0">
  <nav class="mt-8 px-4">
    <div class="space-y-2">
      <!-- Navigation sections - all visible -->
      {#each navigationStructure as section, index}
        <div>
          <!-- Section header - clickable dashboard link -->
          <button
            onclick={section.dashboardAction}
            class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
              isActive(section.dashboardPath) && section.category === $currentCategory
                ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
                : 'hover:bg-gray-50'
            }"
          >
            <Icon 
              name={section.iconName}
              size="sm"
              className="mr-2 {section.category === 'global' ? 'text-black' : section.category === 'builder' ? 'text-orange-600' : section.category === 'validator' ? 'text-sky-600' : 'text-gray-500'}"
            />
            <h3 class="text-xs font-medium uppercase tracking-wider {section.category === 'global' && section.category === $currentCategory ? 'text-black' : 'text-gray-700'}">
              {section.title}
            </h3>
          </button>
          
          <!-- Section items (only if they exist) -->
          {#if section.items.length > 0}
            <div class="space-y-0.5 mb-3">
              {#each section.items as item}
                <!-- Regular navigation item -->
                <a 
                  href={item.path}
                  onclick={(e) => { e.preventDefault(); navigate(item.path); }}
                  class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                    isActive(item.path) || $location.startsWith(item.path + '/')
                      ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` 
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                  }"
                >
                  <Icon 
                    name={item.iconName}
                    size="sm"
                    className="mr-2 {section.category === 'global' ? 'text-black' : section.category === 'builder' ? 'text-orange-600' : section.category === 'validator' ? 'text-sky-600' : 'text-gray-400'}"
                  />
                  {item.name}
                </a>
              {/each}
            </div>
          {/if}
          
          <!-- Separator after each section except the last -->
          {#if index < navigationStructure.length - 1}
            <div class="border-t border-gray-200 mb-3"></div>
          {/if}
        </div>
      {/each}
      
      <!-- Profile section (always visible) -->
      <div>
        <div class="border-t border-gray-200 pt-4"></div>
        <div class="flex items-center px-3 py-2 mb-2">
          <Icon 
            name="profile"
            size="sm"
            className="mr-2 text-gray-500"
          />
          <h3 class="text-xs font-medium text-gray-700 uppercase tracking-wider">
            Account
          </h3>
        </div>
        <div class="space-y-0.5">
          {#each profileItems as item}
            {#if item.isProfile}
              <button
                onclick={handleProfileClick}
                class="group flex items-center px-3 py-1.5 text-sm rounded-md text-gray-500 hover:bg-gray-50 hover:text-gray-700 w-full text-left"
              >
                <Icon 
                  name={item.iconName}
                  size="sm"
                  className="mr-2 text-gray-400 group-hover:text-gray-500"
                />
                {item.name}
              </button>
            {:else}
              <a 
                href={item.path}
                onclick={(e) => { e.preventDefault(); navigate(item.path, item.requiresAuth); }}
                class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                  isActive(item.path) ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                }"
              >
                <Icon 
                  name={item.iconName}
                  size="sm"
                  className="mr-2 {isActive(item.path) ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
                />
                {item.name}
              </a>
            {/if}
          {/each}
        </div>
      </div>
    </div>
  </nav>
</aside>

<!-- Mobile Sidebar Overlay -->
{#if isOpen}
  <!-- Backdrop -->
  <div 
    class="md:hidden fixed inset-0 z-40 bg-gray-600 bg-opacity-75"
    onclick={toggleSidebar}
    onkeydown={(e) => e.key === 'Escape' && toggleSidebar()}
    role="button"
    tabindex="0"
    aria-label="Close sidebar"
  ></div>
  
  <!-- Mobile Sidebar -->
  <aside class="md:hidden fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl">
    <div class="flex items-center justify-between h-16 px-4 border-b">
      <span class="text-xl font-semibold text-gray-900">Menu</span>
      <button 
        onclick={toggleSidebar}
        class="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
        aria-label="Close menu"
      >
        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    
    <nav class="mt-5 px-4 overflow-y-auto" style="max-height: calc(100vh - 5rem);">
      <div class="space-y-2">
        <!-- Navigation sections - all visible -->
        {#each navigationStructure as section, index}
          <div>
            <!-- Section header - clickable dashboard link -->
            <button
              onclick={section.dashboardAction}
              class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
                isActive(section.dashboardPath) && section.category === $currentCategory
                  ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
                  : 'hover:bg-gray-50'
              }"
            >
              <Icon 
                name={section.iconName}
                size="sm"
                className="mr-2 {section.category === 'global' ? 'text-black' : section.category === 'builder' ? 'text-orange-600' : section.category === 'validator' ? 'text-sky-600' : 'text-gray-500'}"
              />
              <h3 class="text-xs font-medium uppercase tracking-wider {section.category === 'global' && section.category === $currentCategory ? 'text-black' : 'text-gray-700'}">
                {section.title}
              </h3>
            </button>
            
            <!-- Section items (only if they exist) -->
            {#if section.items.length > 0}
              <div class="space-y-0.5 mb-3">
                {#each section.items as item}
                  <!-- Regular navigation item -->
                  <a 
                    href={item.path}
                    onclick={(e) => { e.preventDefault(); navigate(item.path); }}
                    class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                      isActive(item.path) || $location.startsWith(item.path + '/')
                        ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` 
                        : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                    }"
                  >
                    <Icon 
                      name={item.iconName}
                      size="sm"
                      className="mr-2 {section.category === 'global' ? 'text-black' : section.category === 'builder' ? 'text-orange-600' : section.category === 'validator' ? 'text-sky-600' : 'text-gray-400'}"
                    />
                    {item.name}
                  </a>
                {/each}
              </div>
            {/if}
            
            <!-- Separator after each section except the last -->
            {#if index < navigationStructure.length - 1}
              <div class="border-t border-gray-200 mb-3"></div>
            {/if}
          </div>
        {/each}
        
        <!-- Profile section (always visible) -->
        <div>
          <div class="border-t border-gray-200 pt-4"></div>
          <div class="flex items-center px-3 py-2 mb-2">
            <Icon 
              name="profile"
              size="sm"
              className="mr-2 text-gray-500"
            />
            <h3 class="text-xs font-medium text-gray-700 uppercase tracking-wider">
              Account
            </h3>
          </div>
          <div class="space-y-0.5">
            {#each profileItems as item}
              {#if item.isProfile}
                <button
                  onclick={handleProfileClick}
                  class="group flex items-center px-3 py-1.5 text-sm rounded-md text-gray-500 hover:bg-gray-50 hover:text-gray-700 w-full text-left"
                >
                  <Icon 
                    name={item.iconName}
                    size="sm"
                    className="mr-2 text-gray-400 group-hover:text-gray-500"
                  />
                  {item.name}
                </button>
              {:else}
                <a 
                  href={item.path}
                  onclick={(e) => { e.preventDefault(); navigate(item.path, item.requiresAuth); }}
                  class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                    isActive(item.path) ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                  }"
                >
                  <Icon 
                    name={item.iconName}
                    size="sm"
                    className="mr-2 {isActive(item.path) ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
                  />
                  {item.name}
                </a>
              {/if}
            {/each}
          </div>
        </div>
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