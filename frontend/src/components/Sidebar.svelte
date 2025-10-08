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
    if (path === '/' || path === '/asimov' || path === '/metrics') {
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

    // Navigate to legal pages with refresh
    if (path === '/terms-of-use' || path === '/privacy-policy') {
      // Navigate directly and reload to ensure fresh start
      window.location.href = `#${path}`;
      window.location.reload();
    } else {
      push(path);
    }

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
      title: 'Overview',
      category: 'global',
      iconName: 'genlayer',
      dashboardPath: '/',
      dashboardAction: () => changeCategory('global', '/'),
      items: [
        { name: 'Testnet Asimov', path: '/asimov', iconName: 'network' },
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
        { name: 'Participants', path: '/validators/participants', iconName: 'participants' },
        { name: 'Waitlist', path: '/validators/waitlist', iconName: 'waitlist' }
      ]
    }
  ];
</script>

<!-- Desktop Sidebar -->
<aside class="hidden md:flex flex-col w-64 bg-white shadow-md h-full overflow-y-auto">
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
      
      <!-- Stewards - Show for all users, submissions only for stewards -->
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
          {#if $userStore.user?.steward}
            <Icon 
              name={getActiveSection() === 'steward' ? "chevronDown" : "chevronRight"}
              size="xs"
              className="text-gray-400 transition-transform duration-200"
            />
          {/if}
        </button>
        {#if getActiveSection() === 'steward' && $userStore.user?.steward}
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
              className="mr-2 text-green-600"
            />
            Contribution Submissions
          </a>
          <a
            href="/stewards/manage-users"
            onclick={(e) => { e.preventDefault(); navigate('/stewards/manage-users'); }}
            class="group flex items-center px-3 py-1.5 text-sm rounded-md {
              isActive('/stewards/manage-users') || $location.startsWith('/stewards/manage-users/')
                ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
                : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
            }"
          >
            <Icon
              name="participants"
              size="sm"
              className="mr-2 text-green-600"
            />
            Manage Users
          </a>
        </div>
        {/if}
      </div>

      <!-- Supporters section -->
      <div>
        <div class="border-t border-gray-200 mb-3"></div>
        <a
          href="/supporters"
          onclick={(e) => { e.preventDefault(); navigate('/supporters'); }}
          class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
            isActive('/supporters')
              ? 'bg-purple-50 text-purple-600'
              : 'hover:bg-gray-50'
          }"
        >
          <svg class="w-4 h-4 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
          </svg>
          <h3 class="text-xs font-medium uppercase tracking-wider flex-1 text-left {isActive('/supporters') ? 'text-purple-700' : 'text-gray-700'}">
            SUPPORTERS
          </h3>
        </a>
      </div>

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
        <div class="flex items-center space-x-3">
          <a
            href="https://github.com/genlayer-foundation/points"
            target="_blank"
            rel="noopener noreferrer"
            class="hover:text-gray-700 transition-colors"
            aria-label="GitHub"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
          </a>
          <a
            href="https://x.com/GenLayerFDN"
            target="_blank"
            rel="noopener noreferrer"
            class="hover:text-gray-700 transition-colors"
            aria-label="X (Twitter)"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
          </a>
          <a
            href="https://discord.gg/qjCU4AWnKE"
            target="_blank"
            rel="noopener noreferrer"
            class="hover:text-gray-700 transition-colors"
            aria-label="Discord"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
            </svg>
          </a>
        </div>
        <div class="flex items-center space-x-1">
          <a href="/terms-of-use" onclick={(e) => { e.preventDefault(); navigate('/terms-of-use'); }} class="hover:text-gray-700 transition-colors">Terms of Use</a>
          <span>·</span>
          <a href="/privacy-policy" onclick={(e) => { e.preventDefault(); navigate('/privacy-policy'); }} class="hover:text-gray-700 transition-colors">Privacy Policy</a>
        </div>
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
        
        <!-- Stewards - Show for all users, submissions only for stewards -->
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
          {#if $userStore.user?.steward}
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
                className="mr-2 text-green-600"
              />
              Contribution Submissions
            </a>
            <a
              href="/stewards/manage-users"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/manage-users'); }}
              class="group flex items-center px-3 py-1.5 text-base rounded-md {
                isActive('/stewards/manage-users') || $location.startsWith('/stewards/manage-users/')
                  ? `${$categoryTheme.buttonLight} ${$categoryTheme.text}`
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
              }"
            >
              <Icon
                name="participants"
                size="sm"
                className="mr-2 text-green-600"
              />
              Manage Users
            </a>
          </div>
          {/if}
        </div>

        <!-- Supporters section -->
        <div>
          <div class="border-t border-gray-200 mb-3"></div>
          <a
            href="/supporters"
            onclick={(e) => { e.preventDefault(); navigate('/supporters'); }}
            class="w-full flex items-center px-3 py-2 mb-1 rounded-md transition-colors {
              isActive('/supporters')
                ? 'bg-purple-50 text-purple-600'
                : 'hover:bg-gray-50'
            }"
          >
            <svg class="w-4 h-4 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
            <h3 class="text-sm font-medium uppercase tracking-wider {isActive('/supporters') ? 'text-purple-700' : 'text-gray-700'}">
              SUPPORTERS
            </h3>
          </a>
        </div>

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
          <div class="flex items-center space-x-3">
            <a
              href="https://github.com/genlayer-foundation/points"
              target="_blank"
              rel="noopener noreferrer"
              class="hover:text-gray-700 transition-colors"
              aria-label="GitHub"
            >
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
            </a>
            <a
              href="https://x.com/GenLayerFDN"
              target="_blank"
              rel="noopener noreferrer"
              class="hover:text-gray-700 transition-colors"
              aria-label="X (Twitter)"
            >
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
            </a>
            <a
              href="https://discord.gg/qjCU4AWnKE"
              target="_blank"
              rel="noopener noreferrer"
              class="hover:text-gray-700 transition-colors"
              aria-label="Discord"
            >
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
              </svg>
            </a>
          </div>
          <div class="flex items-center space-x-1">
            <a href="/terms-of-use" onclick={(e) => { e.preventDefault(); navigate('/terms-of-use'); }} class="hover:text-gray-700 transition-colors">Terms of Use</a>
            <span>·</span>
            <a href="/privacy-policy" onclick={(e) => { e.preventDefault(); navigate('/privacy-policy'); }} class="hover:text-gray-700 transition-colors">Privacy Policy</a>
          </div>
          <div class="text-center">
            © {new Date().getFullYear()} GenLayer Foundation
          </div>
        </div>
    </div>
  </aside>