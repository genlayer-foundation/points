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
      iconName: 'global',
      items: [
        { name: 'Dashboard', path: '/', iconName: 'dashboard' },
        { name: 'Builders', action: () => changeCategory('builder', '/'), iconName: 'builder' },
        { name: 'Validators', action: () => changeCategory('validator', '/'), iconName: 'validator' }
      ]
    },
    {
      title: 'Builders',
      category: 'builder',
      iconName: 'builder',
      color: 'orange',
      items: [
        { name: 'Dashboard', path: '/', iconName: 'dashboard' },
        { name: 'Contributions', path: '/contributions', iconName: 'contributions' },
        { name: 'Leaderboard', path: '/leaderboard', iconName: 'leaderboard' },
        { name: 'Participants', path: '/participants', iconName: 'participants' }
      ]
    },
    {
      title: 'Validators',
      category: 'validator',
      iconName: 'validator', 
      color: 'sky',
      items: [
        { name: 'Dashboard', path: '/', iconName: 'dashboard' },
        { name: 'Contributions', path: '/contributions', iconName: 'contributions' },
        { name: 'Leaderboard', path: '/leaderboard', iconName: 'leaderboard' },
        { name: 'Participants', path: '/participants', iconName: 'participants' }
      ]
    }
  ];
  
  // Profile section items (same for all categories)
  const profileItems = [
    { name: 'My Submissions', path: '/my-submissions', iconName: 'mySubmissions', requiresAuth: true },
    { name: 'Profile', path: 'profile', iconName: 'profile', isProfile: true }
  ];
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
      <nav class="mt-4 space-y-6">
        <!-- Navigation sections -->
        {#each navigationStructure as section}
          <!-- Only show sections that match current category or Testnet Asimov -->
          {#if section.category === $currentCategory || section.category === 'global'}
            <div>
              <!-- Section header -->
              <div class="flex items-center px-3 py-2 mb-2">
                <Icon 
                  name={section.iconName}
                  size="md"
                  className="mr-2 {section.category === $currentCategory ? $categoryTheme.text : 'text-gray-500'}"
                />
                <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                  {section.title}
                </h3>
              </div>
              
              <!-- Section items -->
              <div class="space-y-1 ml-2">
                {#each section.items as item}
                  {#if item.action}
                    <!-- Action item (category switcher) -->
                    <button
                      onclick={item.action}
                      class="group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50 w-full text-left"
                    >
                      <Icon 
                        name={item.iconName}
                        size="sm"
                        className="mr-3 text-gray-400 group-hover:text-gray-500"
                      />
                      {item.name}
                    </button>
                  {:else}
                    <!-- Regular navigation item -->
                    <a 
                      href={item.path}
                      onclick={(e) => { e.preventDefault(); navigate(item.path); }}
                      class={`group flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                        isActive(item.path) && section.category === $currentCategory
                          ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` 
                          : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <Icon 
                        name={item.iconName}
                        size="sm"
                        className="mr-3 {isActive(item.path) && section.category === $currentCategory ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
                      />
                      {item.name}
                    </a>
                  {/if}
                {/each}
              </div>
            </div>
          {/if}
        {/each}
        
        <!-- Profile section (always visible) -->
        <div>
          <div class="border-t border-gray-200 pt-4"></div>
          <div class="flex items-center px-3 py-2 mb-2">
            <Icon 
              name="profile"
              size="md"
              className="mr-2 text-gray-500"
            />
            <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wider">
              Account
            </h3>
          </div>
          <div class="space-y-1 ml-2">
            {#each profileItems as item}
              {#if item.isProfile}
                <button
                  onclick={handleProfileClick}
                  class="group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50 w-full text-left"
                >
                  <Icon 
                    name={item.iconName}
                    size="sm"
                    className="mr-3 text-gray-400 group-hover:text-gray-500"
                  />
                  {item.name}
                </button>
              {:else}
                <a 
                  href={item.path}
                  onclick={(e) => { e.preventDefault(); navigate(item.path, item.requiresAuth); }}
                  class={`group flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                    isActive(item.path) ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon 
                    name={item.iconName}
                    size="sm"
                    className="mr-3 {isActive(item.path) ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
                  />
                  {item.name}
                </a>
              {/if}
            {/each}
          </div>
        </div>
      </nav>
    </div>
  </aside>
</div>