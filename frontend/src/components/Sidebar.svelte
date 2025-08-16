<script>
  import { push, location } from 'svelte-spa-router';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Icon from './Icons.svelte';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  
  let { isOpen = $bindable(false) } = $props();
  
  // Track previous location to detect route changes
  let previousLocation = $state($location);
  
  // Close sidebar on route change on mobile
  $effect(() => {
    // Only close if the location actually changed
    if ($location !== previousLocation) {
      previousLocation = $location;
      if (isOpen && window.innerWidth < 768) {
        isOpen = false;
      }
    }
  });
  
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
    // Direct match
    if ($location === path) return true;
    
    // Special case: contribution-type pages should highlight the contributions item
    if (path.includes('/contributions') && $location.startsWith('/contribution-type/')) {
      // Determine which contributions section based on current category
      const category = $currentCategory;
      if (category === 'builder' && path === '/builders/contributions') return true;
      if (category === 'validator' && path === '/validators/contributions') return true;
      if (category === 'global' && path === '/contributions') return true;
    }
    
    return false;
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
      
      <!-- Stewards - Only show if user is a steward -->
      {#if $userStore.user?.steward}
        <div>
          <div class="border-t border-gray-200 pt-4"></div>
          <button
            onclick={() => navigate('/stewards')}
            class="px-3 text-xs font-semibold text-green-600 uppercase tracking-wider mb-2 hover:text-green-700 transition-colors w-full text-left"
          >
            <span class="mr-1">🌱</span> STEWARDS
          </button>
          <div class="space-y-0.5">
            <a
              href="/stewards/submissions"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
              class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                isActive('/stewards/submissions') ? 'bg-green-100 text-green-800' : 'text-gray-500 hover:bg-green-50 hover:text-green-700'
              }"
            >
              <Icon 
                name="contributions"
                size="sm"
                className="mr-2 {isActive('/stewards/submissions') ? 'text-green-600' : 'text-gray-400 group-hover:text-green-500'}"
              />
              Review Submissions
            </a>
          </div>
        </div>
      {/if}
      
      <!-- Profile links -->
      <div>
        <div class="border-t border-gray-200 pt-4"></div>
        <div class="space-y-0.5">
          <a 
            href="/my-submissions"
            onclick={(e) => { e.preventDefault(); navigate('/my-submissions', true); }}
            class="group flex items-center px-3 py-1.5 text-sm rounded-md {
              isActive('/my-submissions') ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
            }"
          >
            <Icon 
              name="mySubmissions"
              size="sm"
              className="mr-2 {isActive('/my-submissions') ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
            />
            My Submissions
          </a>
          <button
            onclick={handleProfileClick}
            class="group flex items-center px-3 py-1.5 text-sm rounded-md text-gray-500 hover:bg-gray-50 hover:text-gray-700 w-full text-left"
          >
            <Icon 
              name="profile"
              size="sm"
              className="mr-2 text-gray-400 group-hover:text-gray-500"
            />
            Profile
          </button>
        </div>
      </div>
    </div>
  </nav>
</aside>

<!-- Mobile Sidebar Overlay -->
<!-- Backdrop -->
<div 
  class="md:hidden fixed inset-0 z-30 bg-gray-600 transition-opacity duration-300 {isOpen ? 'bg-opacity-75 pointer-events-auto' : 'bg-opacity-0 pointer-events-none'}"
  onclick={() => isOpen = false}
  onkeydown={(e) => e.key === 'Escape' && (isOpen = false)}
  role="button"
  tabindex="0"
  aria-label="Close sidebar"
></div>

<!-- Mobile Sidebar -->
<aside class="md:hidden fixed top-16 left-0 right-0 bottom-0 z-40 bg-white transform transition-transform duration-300 ease-in-out {isOpen ? 'translate-y-0' : '-translate-y-full'}">
    <nav class="px-4 py-4 overflow-y-auto h-full">
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
        
        <!-- Stewards - Only show if user is a steward -->
        {#if $userStore.user?.steward}
          <div>
            <div class="border-t border-gray-200 pt-4"></div>
            <button
              onclick={() => navigate('/stewards')}
              class="px-3 text-xs font-semibold text-green-600 uppercase tracking-wider mb-2 hover:text-green-700 transition-colors w-full text-left"
            >
              <span class="mr-1">🌱</span> STEWARDS
            </button>
            <div class="space-y-0.5">
              <a
                href="/stewards/submissions"
                onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
                class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                  isActive('/stewards/submissions') ? 'bg-green-100 text-green-800' : 'text-gray-500 hover:bg-green-50 hover:text-green-700'
                }"
              >
                <Icon 
                  name="contributions"
                  size="sm"
                  className="mr-2 {isActive('/stewards/submissions') ? 'text-green-600' : 'text-gray-400 group-hover:text-green-500'}"
                />
                Review Submissions
              </a>
            </div>
          </div>
        {/if}
        
        <!-- Profile links -->
        <div>
          <div class="border-t border-gray-200 pt-4"></div>
          <div class="space-y-0.5">
            <a 
              href="/my-submissions"
              onclick={(e) => { e.preventDefault(); navigate('/my-submissions', true); }}
              class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                isActive('/my-submissions') ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
              }"
            >
              <Icon 
                name="mySubmissions"
                size="sm"
                className="mr-2 {isActive('/my-submissions') ? $categoryTheme.text : 'text-gray-400 group-hover:text-gray-500'}"
              />
              My Submissions
            </a>
            <button
              onclick={handleProfileClick}
              class="group flex items-center px-3 py-1.5 text-sm rounded-md text-gray-500 hover:bg-gray-50 hover:text-gray-700 w-full text-left"
            >
              <Icon 
                name="profile"
                size="sm"
                className="mr-2 text-gray-400 group-hover:text-gray-500"
              />
              Profile
            </button>
          </div>
        </div>
      </div>
    </nav>
  </aside>