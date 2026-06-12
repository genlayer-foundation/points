<script>
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { contributionsAPI } from '../lib/api.js';
  import { stewardPermissions } from '../lib/stewardPermissions.js';

  let { isOpen = $bindable(false), collapsed = $bindable(false) } = $props();
  let stewardPermissionMap = $state({});
  let communityContributionTypes = $state([]);
  let stewardNavPermissionsLoaded = $state(false);

  let canAccessDiscordXP = $derived(
    communityContributionTypes.some(type =>
      (stewardPermissionMap[String(type.id)] || []).includes('accept')
    )
  );
  let canAccessManageUsers = $derived(
    Object.values(stewardPermissionMap || {}).some(actions =>
      (actions || []).some(action => action !== 'propose')
    )
  );

  async function loadStewardNavigationPermissions() {
    try {
      await stewardPermissions.load();
      const response = await contributionsAPI.getContributionTypes({
        page_size: 100,
        category: 'community',
      });
      communityContributionTypes = response.data.results || response.data || [];
    } catch (err) {
      communityContributionTypes = [];
    }
  }

  onMount(() => {
    const unsubscribe = stewardPermissions.subscribe(value => {
      stewardPermissionMap = value || {};
    });
    return unsubscribe;
  });

  $effect(() => {
    if ($userStore.user?.steward && !stewardNavPermissionsLoaded) {
      stewardNavPermissionsLoaded = true;
      loadStewardNavigationPermissions();
    } else if (!$userStore.user?.steward) {
      stewardNavPermissionsLoaded = false;
      communityContributionTypes = [];
    }
  });

  // Track previous location to detect route changes
  let previousLocation = $state($location);

  // Close sidebar on route change on mobile
  $effect(() => {
    if ($location !== previousLocation) {
      previousLocation = $location;
      if (isOpen && window.innerWidth < 768) {
        isOpen = false;
      }
    }
  });

  function navigate(path, requiresAuth = false) {
    if (requiresAuth && !$authState.isAuthenticated) {
      sessionStorage.setItem('redirectAfterLogin', path);
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
      return;
    }
    push(path);
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }

  function handleSubmitContribution() {
    if ($authState.isAuthenticated) {
      navigate('/submit-contribution');
    } else {
      sessionStorage.setItem('redirectAfterLogin', '/submit-contribution');
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
    }
  }

  function handleProfileClick() {
    if ($authState.isAuthenticated) {
      push(`/participant/${$authState.address}`);
    } else {
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
    }
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }

  // Check if a route is active
  function isActive(path) {
    if ($location === path) return true;
    if (path !== '/' && $location.startsWith(path + '/')) return true;
    return false;
  }

  // Determine which top-level section is active
  function getActiveSection() {
    const path = $location;
    if (path === '/' || path === '/testnets' || path === '/metrics') return 'global';
    if (path.startsWith('/builders')) return 'builder';
    if (path.startsWith('/validators')) return 'validator';
    if (path.startsWith('/community')) return 'community';
    if (path.startsWith('/stewards')) return 'steward';
    if (path.startsWith('/ecosystem-partners')) return 'partners';
    if (path.startsWith('/gen-tv')) return 'gentv';
    if (path.startsWith('/gen-news')) return 'gennews';
    if (path.startsWith('/foundations') || path.startsWith('/manifesto')) return 'foundations';
    return null;
  }

  function changeCategory(category, path) {
    currentCategory.set(category);
    push(path);
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }

  // Shorten address for display
  function shortAddress(addr) {
    if (!addr) return '';
    return addr.slice(0, 6) + '...' + addr.slice(-4);
  }

  let displayName = $derived(
    $userStore.user?.name || ($authState.address ? shortAddress($authState.address) : '')
  );
</script>

<!-- Desktop Sidebar -->
<aside
  class="hidden md:flex flex-col justify-between bg-white border-r border-[#e6e6e6] h-full transition-all duration-300 ease-in-out flex-shrink-0 p-3 relative {collapsed ? 'w-16' : 'w-56'}"
>
  <!-- Top section: Collapse toggle + Navigation -->
  <div>
    <!-- Collapse toggle - absolutely positioned on border -->
    <button
      onclick={() => (collapsed = !collapsed)}
      class="absolute z-10 hover:opacity-80 transition-opacity cursor-pointer"
      style="top: 28px; right: -10px;"
      aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
    >
      {#if collapsed}
        <img src="/assets/icons/arrow-right-s-line-expand.svg" alt="" class="w-5 h-5">
      {:else}
        <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="w-5 h-5">
      {/if}
    </button>

    <!-- Navigation content -->
    <nav class="space-y-1">

      <!-- Overview section (with sub-items) -->
      <div>
        <button
          onclick={() => changeCategory('global', '/')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
          style={getActiveSection() === 'global' ? 'background: #eeedfb;' : ''}
          onmouseenter={(e) => { if (getActiveSection() !== 'global') { e.currentTarget.style.background = '#eeedfb'; e.currentTarget.querySelector('img').src = '/assets/icons/dashboard-fill.svg'; }}}
          onmouseleave={(e) => { if (getActiveSection() !== 'global') { e.currentTarget.style.background = ''; e.currentTarget.querySelector('img').src = '/assets/icons/dashboard-fill-black.svg'; }}}
          title={collapsed ? 'Overview' : ''}
        >
          {#if getActiveSection() === 'global'}
            <img src="/assets/icons/dashboard-fill.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {:else}
            <img src="/assets/icons/dashboard-fill-black.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {/if}
          {#if !collapsed}
            <span>Overview</span>
          {/if}
        </button>

        <!-- Sub-items: only shown when expanded and section is active -->
        {#if !collapsed && getActiveSection() === 'global'}
          <div class="pl-5">
            <a
              href="#/testnets"
              onclick={(e) => { e.preventDefault(); navigate('/testnets'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/testnets') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              }"
            >
              Testnets
            </a>
            <a
              href="#/metrics"
              onclick={(e) => { e.preventDefault(); navigate('/metrics'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/metrics') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              }"
            >
              Metrics
            </a>
          </div>
        {/if}
      </div>

      <!-- Contribute section header -->
      {#if !collapsed}
        <div class="pt-2 pb-1 px-3">
          <span class="text-[12px] font-normal text-[#6b6b6b] tracking-[0.24px]">Contribute</span>
        </div>
      {:else}
        <div class="border-t border-gray-100 my-2"></div>
      {/if}

      <!-- Builders -->
      <div>
        <button
          onclick={() => changeCategory('builder', '/builders')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
          style={getActiveSection() === 'builder' ? 'background: #fef3e2;' : ''}
          onmouseenter={(e) => { if (getActiveSection() !== 'builder') { e.currentTarget.style.background = '#fef3e2'; e.currentTarget.querySelector('img').src = '/assets/icons/terminal-line-orange.svg'; }}}
          onmouseleave={(e) => { if (getActiveSection() !== 'builder') { e.currentTarget.style.background = ''; e.currentTarget.querySelector('img').src = '/assets/icons/terminal-line.svg'; }}}
          title={collapsed ? 'Builders' : ''}
        >
          {#if getActiveSection() === 'builder'}
            <img src="/assets/icons/terminal-line-orange.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {:else}
            <img src="/assets/icons/terminal-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {/if}
          {#if !collapsed}
            <span>Builders</span>
          {/if}
        </button>

        {#if !collapsed && getActiveSection() === 'builder'}
          <div class="pl-5">
            <a
              href="#/builders/contributions"
              onclick={(e) => { e.preventDefault(); navigate('/builders/contributions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/builders/contributions') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
              }"
            >
              Contributions
            </a>
            <a
              href="#/builders/leaderboard"
              onclick={(e) => { e.preventDefault(); navigate('/builders/leaderboard'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/builders/leaderboard') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
            </a>
            <a
              href="#/builders/resources"
              onclick={(e) => { e.preventDefault(); navigate('/builders/resources'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/builders/resources') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
              }"
            >
              Resources
            </a>
          </div>
        {/if}
      </div>

      <!-- Validators -->
      <div>
        <button
          onclick={() => changeCategory('validator', '/validators')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
          style={getActiveSection() === 'validator' ? 'background: #e8f0fd;' : ''}
          onmouseenter={(e) => { if (getActiveSection() !== 'validator') { e.currentTarget.style.background = '#e8f0fd'; e.currentTarget.querySelector('img').src = '/assets/icons/folder-shield-line-blue.svg'; }}}
          onmouseleave={(e) => { if (getActiveSection() !== 'validator') { e.currentTarget.style.background = ''; e.currentTarget.querySelector('img').src = '/assets/icons/folder-shield-line.svg'; }}}
          title={collapsed ? 'Validators' : ''}
        >
          {#if getActiveSection() === 'validator'}
            <img src="/assets/icons/folder-shield-line-blue.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {:else}
            <img src="/assets/icons/folder-shield-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {/if}
          {#if !collapsed}
            <span>Validators</span>
          {/if}
        </button>

        {#if !collapsed && getActiveSection() === 'validator'}
          <div class="pl-5">
            <a
              href="#/validators/contributions"
              onclick={(e) => { e.preventDefault(); navigate('/validators/contributions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/contributions') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Contributions
            </a>
            <a
              href="#/validators/leaderboard"
              onclick={(e) => { e.preventDefault(); navigate('/validators/leaderboard'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/leaderboard') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
            </a>
            <a
              href="#/validators/participants"
              onclick={(e) => { e.preventDefault(); navigate('/validators/participants'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/participants') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Participants
            </a>
            <a
              href="#/validators/wall-of-shame"
              onclick={(e) => { e.preventDefault(); navigate('/validators/wall-of-shame'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/wall-of-shame') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Wall of Shame
            </a>
            <a
              href="#/validators/waitlist"
              onclick={(e) => { e.preventDefault(); navigate('/validators/waitlist'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/waitlist') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Waitlist
            </a>
          </div>
        {/if}
      </div>

      <!-- Community -->
      <div>
        <button
          onclick={() => changeCategory('community', '/community')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
          style={getActiveSection() === 'community' ? 'background: #f0eafb;' : ''}
          onmouseenter={(e) => { if (getActiveSection() !== 'community') { e.currentTarget.style.background = '#f0eafb'; e.currentTarget.querySelector('img').src = '/assets/icons/group-3-line-purple.svg'; }}}
          onmouseleave={(e) => { if (getActiveSection() !== 'community') { e.currentTarget.style.background = ''; e.currentTarget.querySelector('img').src = '/assets/icons/group-3-line.svg'; }}}
          title={collapsed ? 'Community' : ''}
        >
          {#if getActiveSection() === 'community'}
            <img src="/assets/icons/group-3-line-purple.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {:else}
            <img src="/assets/icons/group-3-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {/if}
          {#if !collapsed}
            <span>Community</span>
          {/if}
        </button>

        {#if !collapsed && getActiveSection() === 'community'}
          <div class="pl-5">
            <a
              href="#/community/contributions"
              onclick={(e) => { e.preventDefault(); navigate('/community/contributions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/community/contributions') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              }"
            >
              Contributions
            </a>
            <a
              href="#/community/leaderboard"
              onclick={(e) => { e.preventDefault(); navigate('/community/leaderboard'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/community/leaderboard') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
            </a>
            <a
              href="#/community/poaps"
              onclick={(e) => { e.preventDefault(); navigate('/community/poaps'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/community/poaps') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              }"
            >
              POAPs
            </a>
          </div>
        {/if}
      </div>

      <!-- Stewards -->
      <div>
        <button
          onclick={() => changeCategory('steward', '/stewards')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
          style={getActiveSection() === 'steward' ? 'background: #e6f7ed;' : ''}
          onmouseenter={(e) => { if (getActiveSection() !== 'steward') { e.currentTarget.style.background = '#e6f7ed'; e.currentTarget.querySelector('img').src = '/assets/icons/seedling-line-green.svg'; }}}
          onmouseleave={(e) => { if (getActiveSection() !== 'steward') { e.currentTarget.style.background = ''; e.currentTarget.querySelector('img').src = '/assets/icons/seedling-line.svg'; }}}
          title={collapsed ? 'Stewards' : ''}
        >
          {#if getActiveSection() === 'steward'}
            <img src="/assets/icons/seedling-line-green.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {:else}
            <img src="/assets/icons/seedling-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
          {/if}
          {#if !collapsed}
            <span>Stewards</span>
          {/if}
        </button>

        <!-- Steward sub-items -->
        {#if !collapsed && getActiveSection() === 'steward' && $userStore.user?.steward}
          <div class="pl-5">
            <a
              href="#/stewards/submissions"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/stewards/submissions') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Contribution Submissions
            </a>
            {#if canAccessDiscordXP}
              <a
                href="#/stewards/discord-xp"
                onclick={(e) => { e.preventDefault(); navigate('/stewards/discord-xp'); }}
                class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                  isActive('/stewards/discord-xp') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
                }"
              >
                Discord XP
              </a>
            {/if}
            {#if canAccessManageUsers}
              <a
                href="#/stewards/manage-users"
                onclick={(e) => { e.preventDefault(); navigate('/stewards/manage-users'); }}
                class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                  isActive('/stewards/manage-users') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
                }"
              >
                Manage Users
              </a>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Discover section header -->
      {#if !collapsed}
        <div class="pt-2 pb-1 px-3">
          <span class="text-[12px] font-normal text-[#6b6b6b] tracking-[0.24px]">Discover</span>
        </div>
      {:else}
        <div class="border-t border-gray-100 my-2"></div>
      {/if}

      <!-- Manifesto (Foundations documents) -->
      <div>
        <button
          onclick={() => changeCategory('foundations', '/foundations')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px] {getActiveSection() === 'foundations' ? '' : 'hover:bg-[#eeedfb]'}"
          style={getActiveSection() === 'foundations' ? 'background: #eeedfb;' : ''}
          title={collapsed ? 'Manifesto' : ''}
        >
          <!-- GenLayer symbol (from /assets/gl-symbol-black.svg) -->
          <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 34.0294 32" fill={getActiveSection() === 'foundations' ? '#6D5DD3' : '#1a1a1a'}>
            <path d="M15.4065 11.2607L9.64908 23.3639L15.0689 26.072L0 32L15.4065 0V11.2607Z" />
            <path d="M18.6229 11.2607L24.3803 23.3639L18.9605 26.072L34.0294 32L18.6229 0V11.2607Z" />
            <path d="M16.9311 15.2394L20.3041 21.9088L16.9311 23.5623L13.7392 21.9019L16.9311 15.2394Z" />
          </svg>
          {#if !collapsed}
            <span>Manifesto</span>
          {/if}
        </button>
      </div>

      <!-- Ecosystem Partners -->
      <div>
        <button
          onclick={() => changeCategory('partners', '/ecosystem-partners')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px] {getActiveSection() === 'partners' ? '' : 'hover:bg-[#eeedfb]'}"
          style={getActiveSection() === 'partners' ? 'background: #eeedfb;' : ''}
          title={collapsed ? 'Ecosystem Partners' : ''}
        >
          <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={getActiveSection() === 'partners' ? '#6D5DD3' : '#1a1a1a'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6" cy="6" r="2.5" />
            <circle cx="18" cy="6" r="2.5" />
            <circle cx="12" cy="18" r="2.5" />
            <line x1="8.2" y1="7" x2="15.8" y2="7" />
            <line x1="7.4" y1="8.2" x2="11" y2="15.6" />
            <line x1="16.6" y1="8.2" x2="13" y2="15.6" />
          </svg>
          {#if !collapsed}
            <span>Ecosystem Partners</span>
          {/if}
        </button>
      </div>

      <!-- Gen TV -->
      <div>
        <button
          onclick={() => changeCategory('gentv', '/gen-tv')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px] {getActiveSection() === 'gentv' ? '' : 'hover:bg-[#eeedfb]'}"
          style={getActiveSection() === 'gentv' ? 'background: #eeedfb;' : ''}
          title={collapsed ? 'Gen TV' : ''}
        >
          <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={getActiveSection() === 'gentv' ? '#6D5DD3' : '#1a1a1a'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="5" width="20" height="14" rx="2" />
            <polygon points="10,9 16,12 10,15" fill={getActiveSection() === 'gentv' ? '#6D5DD3' : '#1a1a1a'} />
          </svg>
          {#if !collapsed}
            <span>Gen TV</span>
          {/if}
        </button>
      </div>

      <!-- GenNews -->
      <div>
        <button
          onclick={() => changeCategory('gennews', '/gen-news')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px] {getActiveSection() === 'gennews' ? '' : 'hover:bg-[#eeedfb]'}"
          style={getActiveSection() === 'gennews' ? 'background: #eeedfb;' : ''}
          title={collapsed ? 'GenNews' : ''}
        >
          <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={getActiveSection() === 'gennews' ? '#6D5DD3' : '#1a1a1a'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m3 11 18-5v12L3 14v-3z" />
            <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
          </svg>
          {#if !collapsed}
            <span>GenNews</span>
          {/if}
        </button>
      </div>

    </nav>
  </div>

  <!-- Bottom pinned area -->
  <div class="space-y-2">
    <!-- How it works link -->
    {#if !collapsed}
      <button
        onclick={() => navigate('/how-it-works')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-left {isActive('/how-it-works') ? 'bg-[#eeedfb]' : 'hover:bg-[#f5f5f5]'}"
      >
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={isActive('/how-it-works') ? '#6D5DD3' : '#656567'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
        <span class="text-[14px] font-medium tracking-[0.28px] {isActive('/how-it-works') ? 'text-[#6D5DD3]' : 'text-[#656567]'}">How it works</span>
      </button>
    {:else}
      <button
        onclick={() => navigate('/how-it-works')}
        class="w-full flex px-3 py-2 rounded-[8px] transition-colors {isActive('/how-it-works') ? 'bg-[#eeedfb]' : 'hover:bg-[#f5f5f5]'}"
        title="How it works"
      >
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={isActive('/how-it-works') ? '#6D5DD3' : '#656567'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
      </button>
    {/if}

    <!-- Submit Contribution link -->
    {#if !collapsed}
      <button
        onclick={handleSubmitContribution}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors text-left"
      >
        <img src="/assets/icons/add-line-sidebar.svg" alt="" class="w-4 h-4 flex-shrink-0">
        <span class="text-[14px] font-medium text-[#656567] tracking-[0.28px]">Submit Contribution</span>
      </button>
    {:else}
      <button
        onclick={handleSubmitContribution}
        class="w-full flex px-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors"
        title="Submit Contribution"
      >
        <img src="/assets/icons/add-line-sidebar.svg" alt="" class="w-4 h-4 flex-shrink-0">
      </button>
    {/if}

    <!-- My Submissions link (authenticated only) -->
    {#if $authState.isAuthenticated}
      {#if !collapsed}
        <button
          onclick={() => navigate('/my-submissions')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors text-left"
        >
          <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="#656567" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
          </svg>
          <span class="text-[14px] font-medium text-[#656567] tracking-[0.28px]">My Submissions</span>
        </button>
      {:else}
        <button
          onclick={() => navigate('/my-submissions')}
          class="w-full flex px-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors"
          title="My Submissions"
        >
          <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="#656567" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
          </svg>
        </button>
      {/if}
    {/if}

    <!-- User profile row -->
    <button
      onclick={handleProfileClick}
      class="w-full flex items-center justify-between pl-2 pr-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors"
      title={collapsed ? (displayName || 'Profile') : ''}
    >
      <div class="flex items-center gap-2">
        <!-- Avatar circle -->
        <div class="w-8 h-8 rounded-full bg-[#f5f5f5] flex items-center justify-center flex-shrink-0">
          <span class="text-xs font-semibold text-gray-700">
            {#if displayName}
              {displayName[0].toUpperCase()}
            {:else}
              ?
            {/if}
          </span>
        </div>
        {#if !collapsed}
          <span class="text-[14px] font-medium text-black tracking-[0.28px] truncate text-left">
            {displayName || 'Connect wallet'}
          </span>
        {/if}
      </div>
      {#if !collapsed}
        <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
      {/if}
    </button>
  </div>
</aside>

<!-- Mobile Sidebar Overlay -->
<div
  class="md:hidden fixed inset-0 z-30 bg-gray-600 transition-opacity duration-300 {isOpen ? 'bg-opacity-75 pointer-events-auto' : 'bg-opacity-0 pointer-events-none'}"
  onclick={() => (isOpen = false)}
  onkeydown={(e) => e.key === 'Escape' && (isOpen = false)}
  role="button"
  tabindex="0"
  aria-label="Close sidebar"
></div>

<!-- Mobile Sidebar -->
<aside class="md:hidden fixed top-16 left-0 right-0 bottom-0 z-40 bg-white border-r border-[#e6e6e6] transform transition-transform duration-300 ease-in-out flex flex-col overflow-y-auto {isOpen ? 'translate-y-0' : '-translate-y-full'}">
  <div class="p-3 flex-1">
    <nav class="space-y-1">

      <!-- Overview -->
      <button
        onclick={() => changeCategory('global', '/')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'global' ? 'background: #eeedfb;' : ''}
      >
        {#if getActiveSection() === 'global'}
          <img src="/assets/icons/dashboard-fill.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {:else}
          <img src="/assets/icons/dashboard-fill-black.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {/if}
        <span>Overview</span>
      </button>

      {#if getActiveSection() === 'global'}
        <div class="pl-5">
          <a
            href="#/testnets"
            onclick={(e) => { e.preventDefault(); navigate('/testnets'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/testnets') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            }"
          >
            Testnets
          </a>
          <a
            href="#/metrics"
            onclick={(e) => { e.preventDefault(); navigate('/metrics'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/metrics') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            }"
          >
            Metrics
          </a>
        </div>
      {/if}

      <!-- Contribute header -->
      <div class="pt-2 pb-1 px-3">
        <span class="text-[12px] font-normal text-[#6b6b6b] tracking-[0.24px]">Contribute</span>
      </div>

      <!-- Builders -->
      <button
        onclick={() => changeCategory('builder', '/builders')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'builder' ? 'background: #fef3e2;' : ''}
      >
        {#if getActiveSection() === 'builder'}
          <img src="/assets/icons/terminal-line-orange.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {:else}
          <img src="/assets/icons/terminal-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {/if}
        <span>Builders</span>
      </button>

      {#if getActiveSection() === 'builder'}
        <div class="pl-5">
          <a
            href="#/builders/contributions"
            onclick={(e) => { e.preventDefault(); navigate('/builders/contributions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/builders/contributions') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
            }"
          >
            Contributions
          </a>
          <a
            href="#/builders/leaderboard"
            onclick={(e) => { e.preventDefault(); navigate('/builders/leaderboard'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/builders/leaderboard') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
          </a>
          <a
            href="#/builders/resources"
            onclick={(e) => { e.preventDefault(); navigate('/builders/resources'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/builders/resources') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
            }"
          >
            Resources
          </a>
        </div>
      {/if}

      <!-- Validators -->
      <button
        onclick={() => changeCategory('validator', '/validators')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'validator' ? 'background: #e8f0fd;' : ''}
      >
        {#if getActiveSection() === 'validator'}
          <img src="/assets/icons/folder-shield-line-blue.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {:else}
          <img src="/assets/icons/folder-shield-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {/if}
        <span>Validators</span>
      </button>

      {#if getActiveSection() === 'validator'}
        <div class="pl-5">
          <a
            href="#/validators/contributions"
            onclick={(e) => { e.preventDefault(); navigate('/validators/contributions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/contributions') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Contributions
          </a>
          <a
            href="#/validators/leaderboard"
            onclick={(e) => { e.preventDefault(); navigate('/validators/leaderboard'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/leaderboard') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
          </a>
          <a
            href="#/validators/participants"
            onclick={(e) => { e.preventDefault(); navigate('/validators/participants'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/participants') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Participants
          </a>
          <a
            href="#/validators/wall-of-shame"
            onclick={(e) => { e.preventDefault(); navigate('/validators/wall-of-shame'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/wall-of-shame') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Wall of Shame
          </a>
          <a
            href="#/validators/waitlist"
            onclick={(e) => { e.preventDefault(); navigate('/validators/waitlist'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/waitlist') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Waitlist
          </a>
        </div>
      {/if}

      <!-- Community -->
      <button
        onclick={() => changeCategory('community', '/community')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'community' ? 'background: #f0eafb;' : ''}
      >
        {#if getActiveSection() === 'community'}
          <img src="/assets/icons/group-3-line-purple.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {:else}
          <img src="/assets/icons/group-3-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {/if}
        <span>Community</span>
      </button>

      {#if getActiveSection() === 'community'}
        <div class="pl-5">
          <a
            href="#/community/contributions"
            onclick={(e) => { e.preventDefault(); navigate('/community/contributions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/community/contributions') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            }"
          >
            Contributions
          </a>
          <a
            href="#/community/leaderboard"
            onclick={(e) => { e.preventDefault(); navigate('/community/leaderboard'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/community/leaderboard') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
          </a>
          <a
            href="#/community/poaps"
            onclick={(e) => { e.preventDefault(); navigate('/community/poaps'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/community/poaps') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            }"
          >
            POAPs
          </a>
        </div>
      {/if}

      <!-- Stewards -->
      <button
        onclick={() => changeCategory('steward', '/stewards')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'steward' ? 'background: #e6f7ed;' : ''}
      >
        {#if getActiveSection() === 'steward'}
          <img src="/assets/icons/seedling-line-green.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {:else}
          <img src="/assets/icons/seedling-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
        {/if}
        <span>Stewards</span>
      </button>

      {#if getActiveSection() === 'steward' && $userStore.user?.steward}
        <div class="pl-5">
          <a
            href="#/stewards/submissions"
            onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/stewards/submissions') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
            }"
          >
            Contribution Submissions
          </a>
          {#if canAccessDiscordXP}
            <a
              href="#/stewards/discord-xp"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/discord-xp'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/stewards/discord-xp') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Discord XP
            </a>
          {/if}
          {#if canAccessManageUsers}
            <a
              href="#/stewards/manage-users"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/manage-users'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/stewards/manage-users') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Manage Users
            </a>
          {/if}
        </div>
      {/if}

      <!-- Discover header (mobile) -->
      <div class="pt-2 pb-1 px-3">
        <span class="text-[12px] font-normal text-[#6b6b6b] tracking-[0.24px]">Discover</span>
      </div>

      <!-- Manifesto (mobile) -->
      <button
        onclick={() => changeCategory('foundations', '/foundations')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'foundations' ? 'background: #eeedfb;' : ''}
      >
        <!-- GenLayer symbol (from /assets/gl-symbol-black.svg) -->
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 34.0294 32" fill={getActiveSection() === 'foundations' ? '#6D5DD3' : '#1a1a1a'}>
          <path d="M15.4065 11.2607L9.64908 23.3639L15.0689 26.072L0 32L15.4065 0V11.2607Z" />
          <path d="M18.6229 11.2607L24.3803 23.3639L18.9605 26.072L34.0294 32L18.6229 0V11.2607Z" />
          <path d="M16.9311 15.2394L20.3041 21.9088L16.9311 23.5623L13.7392 21.9019L16.9311 15.2394Z" />
        </svg>
        <span>Manifesto</span>
      </button>

      <!-- Ecosystem Partners (mobile) -->
      <button
        onclick={() => changeCategory('partners', '/ecosystem-partners')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'partners' ? 'background: #eeedfb;' : ''}
      >
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={getActiveSection() === 'partners' ? '#6D5DD3' : '#1a1a1a'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="6" cy="6" r="2.5" />
          <circle cx="18" cy="6" r="2.5" />
          <circle cx="12" cy="18" r="2.5" />
          <line x1="8.2" y1="7" x2="15.8" y2="7" />
          <line x1="7.4" y1="8.2" x2="11" y2="15.6" />
          <line x1="16.6" y1="8.2" x2="13" y2="15.6" />
        </svg>
        <span>Ecosystem Partners</span>
      </button>

      <!-- Gen TV (mobile) -->
      <button
        onclick={() => changeCategory('gentv', '/gen-tv')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'gentv' ? 'background: #eeedfb;' : ''}
      >
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={getActiveSection() === 'gentv' ? '#6D5DD3' : '#1a1a1a'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="5" width="20" height="14" rx="2" />
          <polygon points="10,9 16,12 10,15" fill={getActiveSection() === 'gentv' ? '#6D5DD3' : '#1a1a1a'} />
        </svg>
        <span>Gen TV</span>
      </button>

      <!-- GenNews (mobile) -->
      <button
        onclick={() => changeCategory('gennews', '/gen-news')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'gennews' ? 'background: #eeedfb;' : ''}
      >
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={getActiveSection() === 'gennews' ? '#6D5DD3' : '#1a1a1a'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m3 11 18-5v12L3 14v-3z" />
          <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
        </svg>
        <span>GenNews</span>
      </button>

    </nav>
  </div>

  <!-- Bottom pinned area (mobile) -->
  <div class="p-3 space-y-2">
    <button
      onclick={() => navigate('/how-it-works')}
      class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-left {isActive('/how-it-works') ? 'bg-[#eeedfb]' : 'hover:bg-[#f5f5f5]'}"
    >
      <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke={isActive('/how-it-works') ? '#6D5DD3' : '#656567'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
      <span class="text-[14px] font-medium tracking-[0.28px] {isActive('/how-it-works') ? 'text-[#6D5DD3]' : 'text-[#656567]'}">How it works</span>
    </button>
    <button
      onclick={handleSubmitContribution}
      class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors text-left"
    >
      <img src="/assets/icons/add-line-sidebar.svg" alt="" class="w-4 h-4 flex-shrink-0">
      <span class="text-[14px] font-medium text-[#656567] tracking-[0.28px]">Submit Contribution</span>
    </button>
    {#if $authState.isAuthenticated}
      <button
        onclick={() => navigate('/my-submissions')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors text-left"
      >
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="#656567" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
        </svg>
        <span class="text-[14px] font-medium text-[#656567] tracking-[0.28px]">My Submissions</span>
      </button>
    {/if}
    <button
      onclick={handleProfileClick}
      class="w-full flex items-center justify-between pl-2 pr-3 py-2 rounded-[8px] hover:bg-[#f5f5f5] transition-colors"
    >
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-[#f5f5f5] flex items-center justify-center flex-shrink-0">
          <span class="text-xs font-semibold text-gray-700">
            {#if displayName}
              {displayName[0].toUpperCase()}
            {:else}
              ?
            {/if}
          </span>
        </div>
        <span class="text-[14px] font-medium text-black tracking-[0.28px] truncate text-left">
          {displayName || 'Connect wallet'}
        </span>
      </div>
      <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
    </button>
  </div>
</aside>
