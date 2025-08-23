<script>
  import { push, location } from 'svelte-spa-router';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Icon from './Icons.svelte';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { getCategoryIconColor } from '../lib/categoryColors';
  
  let { isOpen = $bindable(false) } = $props();
  
  // Track previous location to detect route changes
  let previousLocation = $state($location);
  
  // Determine which section should be expanded based on current route
  function getActiveSection() {
    const path = $location;
    
    // Check for specific sections
    if (path === '/' || path === '/metrics') {
      return 'global';
    } else if (path.startsWith('/builders') || (path.startsWith('/contribution-type/') && $currentCategory === 'builder')) {
      return 'builder';
    } else if (path.startsWith('/validators') || (path.startsWith('/contribution-type/') && $currentCategory === 'validator')) {
      return 'validator';
    } else if (path.startsWith('/stewards')) {
      return 'steward';
    } else if (path === '/my-submissions' || path.startsWith('/participant/')) {
      return 'profile';
    }
    
    return null;
  }
  
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
<aside class="hidden md:flex flex-col w-64 bg-white shadow-md min-h-screen sticky top-0 overflow-y-auto">
  <!-- Navigation content - takes only what it needs -->
  <div class="px-4 pt-8 pb-4">
    <nav class="space-y-2">
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
              className="mr-2 {getCategoryIconColor(section.category)}"
            />
            <h3 class="text-xs font-medium uppercase tracking-wider flex-1 text-left {section.category === 'global' && section.category === $currentCategory ? 'text-black' : 'text-gray-700'}">
              {section.title}
            </h3>
            {#if section.items.length > 0}
              <Icon 
                name={getActiveSection() === section.category ? "chevronDown" : "chevronRight"}
                size="xs"
                className="text-gray-400 transition-transform duration-200"
              />
            {/if}
          </button>
          
          <!-- Section items (only if they exist and section is active) -->
          {#if section.items.length > 0 && getActiveSection() === section.category}
            <div class="space-y-0.5 mb-3 pl-2">
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
                    className="mr-2 {getCategoryIconColor(section.category)}"
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
            onclick={() => changeCategory('steward', '/stewards')}
            class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
              isActive('/stewards') && $currentCategory === 'steward'
                ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
                : 'hover:bg-gray-50'
            }"
          >
            <span class="mr-2 text-green-600">🌱</span>
            <h3 class="text-xs font-medium uppercase tracking-wider flex-1 text-left {$currentCategory === 'steward' ? 'text-green-700' : 'text-gray-700'}">
              STEWARDS
            </h3>
            <Icon 
              name={getActiveSection() === 'steward' ? "chevronDown" : "chevronRight"}
              size="xs"
              className="text-gray-400 transition-transform duration-200"
            />
          </button>
          {#if getActiveSection() === 'steward'}
          <div class="space-y-0.5 pl-2">
            <a
              href="/stewards/submissions"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
              class="group flex items-center px-3 py-1.5 text-sm rounded-md {
                isActive('/stewards/submissions') || $location.startsWith('/stewards/submissions/')
                  ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` 
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
              }"
            >
              <Icon 
                name="contributions"
                size="sm"
                className="mr-2 {isActive('/stewards/submissions') ? 'text-green-600' : 'text-gray-400 group-hover:text-green-500'}"
              />
              Contribution Submissions
            </a>
          </div>
          {/if}
        </div>
      {/if}
      
      <!-- Profile section -->
      <div>
        <div class="border-t border-gray-200 mb-3"></div>
        <button
          onclick={handleProfileClick}
          class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
            getActiveSection() === 'profile'
              ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
              : 'hover:bg-gray-50'
          }"
        >
          <Icon 
            name="profile"
            size="sm"
            className="mr-2 text-purple-600"
          />
          <h3 class="text-xs font-medium uppercase tracking-wider flex-1 text-left text-gray-700">
            Profile
          </h3>
          <Icon 
            name="chevronDown"
            size="xs"
            className="text-gray-400"
          />
        </button>
        {#if getActiveSection() === 'profile'}
        <div class="space-y-0.5 mb-3 pl-2">
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
              className="mr-2 text-purple-600"
            />
            My Submissions
          </a>
        </div>
        {/if}
      </div>
    </nav>
  </div>
  
  <!-- Spacer to push footer to bottom -->
  <div class="flex-1"></div>
  
  <!-- Footer - Always at bottom -->
  <div class="p-4 border-t border-gray-200 bg-white">
      <div class="flex flex-col items-center space-y-2 text-xs text-gray-500">
        <a 
          href="https://github.com/genlayer-foundation/tally" 
          target="_blank" 
          rel="noopener noreferrer"
          class="flex items-center hover:text-gray-700 transition-colors"
        >
          <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
          GitHub
        </a>
        <div class="text-center">
          © {new Date().getFullYear()} GenLayer Foundation
        </div>
      </div>
  </div>
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
<aside class="md:hidden fixed top-16 left-0 right-0 bottom-0 z-40 bg-white transform transition-transform duration-300 ease-in-out flex flex-col overflow-y-auto {isOpen ? 'translate-y-0' : '-translate-y-full'}">
    <!-- Navigation content - takes only what it needs -->
    <div class="px-4 py-4">
      <nav class="space-y-2">
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
                className="mr-2 {getCategoryIconColor(section.category)}"
              />
              <h3 class="text-sm font-medium uppercase tracking-wider {section.category === 'global' && section.category === $currentCategory ? 'text-black' : 'text-gray-700'}">
                {section.title}
              </h3>
            </button>
            
            <!-- Section items (only if they exist) -->
            {#if section.items.length > 0}
              <div class="space-y-0.5 mb-3 pl-2">
                {#each section.items as item}
                  <!-- Regular navigation item -->
                  <a 
                    href={item.path}
                    onclick={(e) => { e.preventDefault(); navigate(item.path); }}
                    class="group flex items-center px-3 py-1.5 text-base rounded-md {
                      isActive(item.path) || $location.startsWith(item.path + '/')
                        ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` 
                        : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                    }"
                  >
                    <Icon 
                      name={item.iconName}
                      size="sm"
                      className="mr-2 {getCategoryIconColor(section.category)}"
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
              onclick={() => changeCategory('steward', '/stewards')}
              class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
                isActive('/stewards') && $currentCategory === 'steward'
                  ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
                  : 'hover:bg-gray-50'
              }"
            >
              <span class="mr-2 text-green-600">🌱</span>
              <h3 class="text-sm font-medium uppercase tracking-wider {$currentCategory === 'steward' ? 'text-green-700' : 'text-gray-700'}">
                STEWARDS
              </h3>
            </button>
            <div class="space-y-0.5 pl-2">
              <a
                href="/stewards/submissions"
                onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
                class="group flex items-center px-3 py-1.5 text-base rounded-md {
                  isActive('/stewards/submissions') || $location.startsWith('/stewards/submissions/')
                    ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` 
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                }"
              >
                <Icon 
                  name="contributions"
                  size="sm"
                  className="mr-2 {isActive('/stewards/submissions') ? 'text-green-600' : 'text-gray-400 group-hover:text-green-500'}"
                />
                Contribution Submissions
              </a>
            </div>
          </div>
        {/if}
        
        <!-- Profile section -->
        <div>
          <div class="border-t border-gray-200 mb-3"></div>
          <button
            onclick={handleProfileClick}
            class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
              getActiveSection() === 'profile'
                ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
                : 'hover:bg-gray-50'
            }"
          >
            <Icon 
              name="profile"
              size="sm"
              className="mr-2 text-purple-600"
            />
            <h3 class="text-sm font-medium uppercase tracking-wider text-gray-700">
              Profile
            </h3>
          </button>
          <div class="space-y-0.5 mb-3 pl-2">
            <a 
              href="/my-submissions"
              onclick={(e) => { e.preventDefault(); navigate('/my-submissions', true); }}
              class="group flex items-center px-3 py-1.5 text-base rounded-md {
                isActive('/my-submissions') ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}` : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
              }"
            >
              <Icon 
                name="mySubmissions"
                size="sm"
                className="mr-2 text-purple-600"
              />
              My Submissions
            </a>
          </div>
        </div>
      </nav>
    </div>
    
    <!-- Spacer to push footer to bottom -->
    <div class="flex-1"></div>
    
    <!-- Footer (Mobile) - Always at bottom -->
    <div class="p-4 border-t border-gray-200 bg-white">
        <div class="flex flex-col items-center space-y-2 text-xs text-gray-500">
          <a 
            href="https://github.com/genlayer-foundation/tally" 
            target="_blank" 
            rel="noopener noreferrer"
            class="flex items-center hover:text-gray-700 transition-colors"
          >
            <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            GitHub
          </a>
          <div class="text-center">
            © {new Date().getFullYear()} GenLayer Foundation
          </div>
        </div>
    </div>
  </aside>