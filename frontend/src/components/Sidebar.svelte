<script>
  import { push, location } from 'svelte-spa-router';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';

  let { isOpen = $bindable(false), collapsed = $bindable(false) } = $props();

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
              href="/testnets"
              onclick={(e) => { e.preventDefault(); navigate('/testnets'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/testnets') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              }"
            >
              Testnets
            </a>
            <a
              href="/metrics"
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
              href="/builders/contributions"
              onclick={(e) => { e.preventDefault(); navigate('/builders/contributions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/builders/contributions') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
              }"
            >
              Contributions
            </a>
            <a
              href="/builders/leaderboard"
              onclick={(e) => { e.preventDefault(); navigate('/builders/leaderboard'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/builders/leaderboard') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
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
              href="/validators/contributions"
              onclick={(e) => { e.preventDefault(); navigate('/validators/contributions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/contributions') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Contributions
            </a>
            <a
              href="/validators/leaderboard"
              onclick={(e) => { e.preventDefault(); navigate('/validators/leaderboard'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/leaderboard') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
            </a>
            <a
              href="/validators/participants"
              onclick={(e) => { e.preventDefault(); navigate('/validators/participants'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/participants') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Participants
            </a>
            <a
              href="/validators/waitlist"
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
      <a
        href="/community"
        onclick={(e) => { e.preventDefault(); navigate('/community'); }}
        class="flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
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
      </a>

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
              href="/stewards/submissions"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/stewards/submissions') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Contribution Submissions
            </a>
            <a
              href="/stewards/manage-users"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/manage-users'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/stewards/manage-users') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Manage Users
            </a>
          </div>
        {/if}
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
            href="/testnets"
            onclick={(e) => { e.preventDefault(); navigate('/testnets'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/testnets') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            }"
          >
            Testnets
          </a>
          <a
            href="/metrics"
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
            href="/builders/contributions"
            onclick={(e) => { e.preventDefault(); navigate('/builders/contributions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/builders/contributions') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
            }"
          >
            Contributions
          </a>
          <a
            href="/builders/leaderboard"
            onclick={(e) => { e.preventDefault(); navigate('/builders/leaderboard'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/builders/leaderboard') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
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
            href="/validators/contributions"
            onclick={(e) => { e.preventDefault(); navigate('/validators/contributions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/contributions') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Contributions
          </a>
          <a
            href="/validators/leaderboard"
            onclick={(e) => { e.preventDefault(); navigate('/validators/leaderboard'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/leaderboard') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
          </a>
          <a
            href="/validators/participants"
            onclick={(e) => { e.preventDefault(); navigate('/validators/participants'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/participants') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Participants
          </a>
          <a
            href="/validators/waitlist"
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
        onclick={() => navigate('/community')}
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
            href="/stewards/submissions"
            onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/stewards/submissions') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
            }"
          >
            Contribution Submissions
          </a>
          <a
            href="/stewards/manage-users"
            onclick={(e) => { e.preventDefault(); navigate('/stewards/manage-users'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/stewards/manage-users') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
            }"
          >
            Manage Users
          </a>
        </div>
      {/if}

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
