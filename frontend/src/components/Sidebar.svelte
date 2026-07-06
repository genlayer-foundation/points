<script>
  import { push, location } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { currentCategory } from '../stores/category.js';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { contributionsAPI, stewardAPI } from '../lib/api.js';
  import { stewardPermissions } from '../lib/stewardPermissions.js';
  import { hasEarnedRole, journeyPath, rolePath } from '../lib/roleState.js';
  import { getAnalyticsContext, setConnectWalletIntent, trackEvent } from '../lib/analytics.js';
  import Avatar from './Avatar.svelte';

  let { isOpen = $bindable(false), collapsed = $bindable(false) } = $props();
  let stewardPermissionMap = $state({});
  let communityContributionTypes = $state([]);
  let featureReviewAccess = $state({ can_review: false, can_admin: false });
  let stewardNavPermissionsLoaded = $state(false);

  let canAccessDiscordXP = $derived(
    communityContributionTypes.some(type =>
      (stewardPermissionMap[String(type.id)] || []).includes('accept')
    )
  );
  let canAccessFeatureReviews = $derived(
    featureReviewAccess.can_review || featureReviewAccess.can_admin
  );

  async function loadStewardNavigationPermissions() {
    try {
      await stewardPermissions.load();
      const response = await contributionsAPI.getAllContributionTypes({
        category: 'community',
      });
      communityContributionTypes = response.data || [];
    } catch (err) {
      communityContributionTypes = [];
    }

    try {
      const featureAccessResponse = await stewardAPI.getFeatureReviewAccess();
      featureReviewAccess = featureAccessResponse.data || { can_review: false, can_admin: false };
    } catch (err) {
      featureReviewAccess = { can_review: false, can_admin: false };
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
      featureReviewAccess = { can_review: false, can_admin: false };
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

  function roleContextForCategory(category) {
    if (['builder', 'validator', 'community', 'steward'].includes(category)) return category;
    if (['partners', 'gentv', 'gennews', 'foundations'].includes(category)) return 'ecosystem';
    return 'overview';
  }

  function trackSidebarNav(path, { locked = false, roleContext = null } = {}) {
    trackEvent('nav_item_click', getAnalyticsContext({
      surface: 'sidebar',
      target_route: path,
      role_context: roleContext || roleContextForCategory(getActiveSection() || 'global'),
      locked,
    }));
  }

  function closeMobileSidebar() {
    if (window.innerWidth < 768) {
      isOpen = false;
    }
  }

  function navigate(path, requiresAuth = false, options = {}) {
    if (options.track !== false) {
      trackSidebarNav(path, {
        locked: Boolean(options.locked),
        roleContext: options.roleContext,
      });
    }
    if (requiresAuth && !$authState.isAuthenticated) {
      setConnectWalletIntent({
        surface: 'sidebar',
        cta_id: options.ctaId || 'protected_nav',
        target_route: path,
      });
      sessionStorage.setItem('redirectAfterLogin', path);
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
      closeMobileSidebar();
      return;
    }
    push(path);
    closeMobileSidebar();
  }

  function handleSubmitContribution() {
    trackEvent('submit_contribution_click', getAnalyticsContext({
      surface: 'sidebar',
    }));

    navigate('/submit-contribution', true, {
      ctaId: 'submit_contribution',
      track: false,
    });
  }

  // A signed-in user who has not earned this category's role: the role's
  // subsections are shown but locked.
  function isRoleLocked(category) {
    return $authState.isAuthenticated && !hasEarnedRole($userStore.user, category);
  }

  // Clicking a locked role subsection nudges the user to that role's funnel
  // instead of the (route-gated) subsection.
  function openRoleSection(path, category) {
    const locked = isRoleLocked(category);
    const redirectTarget = locked ? (category === 'community' ? journeyPath(category) : rolePath(category)) : path;
    trackSidebarNav(path, { locked, roleContext: category });
    if (locked) {
      trackEvent('role_locked_redirect', getAnalyticsContext({
        role_context: category,
        target_route: path,
        redirect_target: redirectTarget,
        surface: 'sidebar',
      }));
    }
    navigate(redirectTarget, false, { track: false });
  }

  function handleProfileClick() {
    if ($authState.isAuthenticated) {
      trackSidebarNav(`/participant/${$authState.address || ':address'}`, { roleContext: 'overview' });
      push(`/participant/${$authState.address}`);
    } else {
      setConnectWalletIntent({
        surface: 'sidebar',
        cta_id: 'profile',
      });
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
    }
    closeMobileSidebar();
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
    if (path.startsWith('/genesis') || path.startsWith('/foundations') || path.startsWith('/manifesto')) return 'foundations';
    return null;
  }

  function changeCategory(category, path) {
    currentCategory.set(category);
    trackSidebarNav(path, { roleContext: roleContextForCategory(category) });
    push(path);
    closeMobileSidebar();
  }

  // Shorten address for display
  function shortAddress(addr) {
    if (!addr) return '';
    return addr.slice(0, 6) + '...' + addr.slice(-4);
  }

  let displayName = $derived(
    $userStore.user?.name || ($authState.address ? shortAddress($authState.address) : '')
  );
  let sidebarUser = $derived(
    $userStore.user || ($authState.address ? { address: $authState.address } : null)
  );
</script>

<!-- Desktop Sidebar -->
<aside
  class="hidden md:flex flex-col bg-white border-r border-[#e6e6e6] h-full min-h-0 overflow-hidden transition-all duration-300 ease-in-out flex-shrink-0 p-3 relative {collapsed ? 'w-16' : 'w-56'}"
>
  <!-- Top section: Collapse toggle + Navigation -->
  <div class="min-h-0 flex-1 overflow-y-auto pb-2">
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

        {#if !collapsed && getActiveSection() === 'builder' && $authState.isAuthenticated}
          <div class="pl-5">
            <a
              href="/builders/contributions"
              onclick={(e) => { e.preventDefault(); openRoleSection('/builders/contributions', 'builder'); }}
              class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
                isActive('/builders/contributions') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
              } {isRoleLocked('builder') ? 'text-gray-400' : 'text-black'}"
              title={isRoleLocked('builder') ? 'Become a builder to unlock' : ''}
            >
              <span>Contributions</span>
              {#if isRoleLocked('builder')}
                <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              {/if}
            </a>
            <a
              href="/builders/leaderboard"
              onclick={() => trackSidebarNav('/builders/leaderboard', { roleContext: 'builder' })}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/builders/leaderboard') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
            </a>
            <a
              href="/builders/resources"
              onclick={() => trackSidebarNav('/builders/resources', { roleContext: 'builder' })}
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

        {#if !collapsed && getActiveSection() === 'validator' && $authState.isAuthenticated}
          <div class="pl-5">
            <a
              href="/validators/contributions"
              onclick={(e) => { e.preventDefault(); openRoleSection('/validators/contributions', 'validator'); }}
              class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
                isActive('/validators/contributions') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              } {isRoleLocked('validator') ? 'text-gray-400' : 'text-black'}"
              title={isRoleLocked('validator') ? 'Become a validator to unlock' : ''}
            >
              <span>Contributions</span>
              {#if isRoleLocked('validator')}
                <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              {/if}
            </a>
            <a
              href="/validators/leaderboard"
              onclick={() => trackSidebarNav('/validators/leaderboard', { roleContext: 'validator' })}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/leaderboard') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
            </a>
            <a
              href="/validators/participants"
              onclick={() => trackSidebarNav('/validators/participants', { roleContext: 'validator' })}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/validators/participants') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              }"
            >
              Participants
            </a>
            <a
              href="/validators/wall-of-shame"
              onclick={(e) => { e.preventDefault(); openRoleSection('/validators/wall-of-shame', 'validator'); }}
              class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
                isActive('/validators/wall-of-shame') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
              } {isRoleLocked('validator') ? 'text-gray-400' : 'text-black'}"
              title={isRoleLocked('validator') ? 'Become a validator to unlock' : ''}
            >
              <span>Wall of Shame</span>
              {#if isRoleLocked('validator')}
                <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              {/if}
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

        {#if !collapsed && getActiveSection() === 'community' && $authState.isAuthenticated}
          <div class="pl-5">
            <a
              href="/community/contributions"
              onclick={(e) => { e.preventDefault(); openRoleSection('/community/contributions', 'community'); }}
              class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
                isActive('/community/contributions') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              } {isRoleLocked('community') ? 'text-gray-400' : 'text-black'}"
              title={isRoleLocked('community') ? 'Join the community to unlock' : ''}
            >
              <span>Contributions</span>
              {#if isRoleLocked('community')}
                <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              {/if}
            </a>
            <a
              href="/community/leaderboard"
              onclick={() => trackSidebarNav('/community/leaderboard', { roleContext: 'community' })}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/community/leaderboard') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              }"
            >
              Leaderboard
            </a>
            <a
              href="/community/poaps"
              onclick={(e) => { e.preventDefault(); openRoleSection('/community/poaps', 'community'); }}
              class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
                isActive('/community/poaps') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
              } {isRoleLocked('community') ? 'text-gray-400' : 'text-black'}"
              title={isRoleLocked('community') ? 'Join the community to unlock' : ''}
            >
              <span>POAPs</span>
              {#if isRoleLocked('community')}
                <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              {/if}
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
              href="/stewards/submissions"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/stewards/submissions') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Contribution Submissions
            </a>
            {#if canAccessFeatureReviews}
              <a
                href="/stewards/feature-reviews"
                onclick={(e) => { e.preventDefault(); navigate('/stewards/feature-reviews'); }}
                class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                  isActive('/stewards/feature-reviews') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
                }"
              >
                Feature Scoring
              </a>
            {/if}
            {#if canAccessDiscordXP}
              <a
                href="/stewards/discord-xp"
                onclick={(e) => { e.preventDefault(); navigate('/stewards/discord-xp'); }}
                class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                  isActive('/stewards/discord-xp') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
                }"
              >
                Discord XP
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

      <!-- Genesis (Foundations documents) -->
      <div>
        <button
          onclick={() => changeCategory('foundations', '/genesis')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px] {getActiveSection() === 'foundations' ? '' : 'hover:bg-[#eeedfb]'}"
          style={getActiveSection() === 'foundations' ? 'background: #eeedfb;' : ''}
          title={collapsed ? 'Genesis' : ''}
        >
          <!-- GenLayer symbol (from /assets/gl-symbol-black.svg) -->
          <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 34.0294 32" fill={getActiveSection() === 'foundations' ? '#6D5DD3' : '#1a1a1a'}>
            <path d="M15.4065 11.2607L9.64908 23.3639L15.0689 26.072L0 32L15.4065 0V11.2607Z" />
            <path d="M18.6229 11.2607L24.3803 23.3639L18.9605 26.072L34.0294 32L18.6229 0V11.2607Z" />
            <path d="M16.9311 15.2394L20.3041 21.9088L16.9311 23.5623L13.7392 21.9019L16.9311 15.2394Z" />
          </svg>
          {#if !collapsed}
            <span>Genesis</span>
          {/if}
        </button>
      </div>

      <!-- Ecosystem -->
      <div>
        <button
          onclick={() => changeCategory('partners', '/ecosystem-partners')}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px] {getActiveSection() === 'partners' ? '' : 'hover:bg-[#eeedfb]'}"
          style={getActiveSection() === 'partners' ? 'background: #eeedfb;' : ''}
          title={collapsed ? 'Ecosystem' : ''}
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
            <span>Ecosystem</span>
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
  <div class="flex-shrink-0 space-y-2 pt-2">
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
        {#if sidebarUser}
          <Avatar user={sidebarUser} size="sm" className="flex-shrink-0" />
        {:else}
          <div class="w-8 h-8 rounded-full bg-[#f5f5f5] flex items-center justify-center flex-shrink-0">
            <span class="text-xs font-semibold text-gray-700">?</span>
          </div>
        {/if}
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
<aside
  class="md:hidden fixed left-0 right-0 bottom-0 z-40 bg-white border-r border-[#e6e6e6] transform transition-[transform,visibility] duration-300 ease-in-out flex flex-col overflow-hidden {isOpen ? 'translate-y-0' : '-translate-y-full invisible'}"
  style="top: var(--mobile-navbar-height, 49px);"
>
  <div class="min-h-0 flex-1 overflow-y-auto p-3">
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

      {#if getActiveSection() === 'builder' && $authState.isAuthenticated}
        <div class="pl-5">
          <a
            href="/builders/contributions"
            onclick={(e) => { e.preventDefault(); openRoleSection('/builders/contributions', 'builder'); }}
            class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
              isActive('/builders/contributions') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
            } {isRoleLocked('builder') ? 'text-gray-400' : 'text-black'}"
            title={isRoleLocked('builder') ? 'Become a builder to unlock' : ''}
          >
            <span>Contributions</span>
            {#if isRoleLocked('builder')}
              <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            {/if}
          </a>
          <a
            href="/builders/leaderboard"
            onclick={() => trackSidebarNav('/builders/leaderboard', { roleContext: 'builder' })}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/builders/leaderboard') ? 'border-[#EE8D24]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
          </a>
          <a
            href="/builders/resources"
            onclick={() => trackSidebarNav('/builders/resources', { roleContext: 'builder' })}
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

      {#if getActiveSection() === 'validator' && $authState.isAuthenticated}
        <div class="pl-5">
          <a
            href="/validators/contributions"
            onclick={(e) => { e.preventDefault(); openRoleSection('/validators/contributions', 'validator'); }}
            class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
              isActive('/validators/contributions') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            } {isRoleLocked('validator') ? 'text-gray-400' : 'text-black'}"
            title={isRoleLocked('validator') ? 'Become a validator to unlock' : ''}
          >
            <span>Contributions</span>
            {#if isRoleLocked('validator')}
              <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            {/if}
          </a>
          <a
            href="/validators/leaderboard"
            onclick={() => trackSidebarNav('/validators/leaderboard', { roleContext: 'validator' })}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/leaderboard') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
          </a>
          <a
            href="/validators/participants"
            onclick={() => trackSidebarNav('/validators/participants', { roleContext: 'validator' })}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/validators/participants') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            }"
          >
            Participants
          </a>
          <a
            href="/validators/wall-of-shame"
            onclick={(e) => { e.preventDefault(); openRoleSection('/validators/wall-of-shame', 'validator'); }}
            class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
              isActive('/validators/wall-of-shame') ? 'border-[#387DE8]' : 'border-[#f5f5f5]'
            } {isRoleLocked('validator') ? 'text-gray-400' : 'text-black'}"
            title={isRoleLocked('validator') ? 'Become a validator to unlock' : ''}
          >
            <span>Wall of Shame</span>
            {#if isRoleLocked('validator')}
              <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            {/if}
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

      {#if getActiveSection() === 'community' && $authState.isAuthenticated}
        <div class="pl-5">
          <a
            href="/community/contributions"
            onclick={(e) => { e.preventDefault(); openRoleSection('/community/contributions', 'community'); }}
            class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
              isActive('/community/contributions') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            } {isRoleLocked('community') ? 'text-gray-400' : 'text-black'}"
            title={isRoleLocked('community') ? 'Join the community to unlock' : ''}
          >
            <span>Contributions</span>
            {#if isRoleLocked('community')}
              <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            {/if}
          </a>
          <a
            href="/community/leaderboard"
            onclick={() => trackSidebarNav('/community/leaderboard', { roleContext: 'community' })}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/community/leaderboard') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            }"
          >
            Leaderboard
          </a>
          <a
            href="/community/poaps"
            onclick={(e) => { e.preventDefault(); openRoleSection('/community/poaps', 'community'); }}
            class="flex items-center justify-between border-l-[1.5px] px-3 py-2 text-[14px] font-medium tracking-[0.28px] {
              isActive('/community/poaps') ? 'border-[#8D81E1]' : 'border-[#f5f5f5]'
            } {isRoleLocked('community') ? 'text-gray-400' : 'text-black'}"
            title={isRoleLocked('community') ? 'Join the community to unlock' : ''}
          >
            <span>POAPs</span>
            {#if isRoleLocked('community')}
              <svg class="h-3.5 w-3.5 flex-shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            {/if}
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
            href="/stewards/submissions"
            onclick={(e) => { e.preventDefault(); navigate('/stewards/submissions'); }}
            class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
              isActive('/stewards/submissions') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
            }"
          >
            Contribution Submissions
          </a>
          {#if canAccessFeatureReviews}
              <a
                href="/stewards/feature-reviews"
                onclick={(e) => { e.preventDefault(); navigate('/stewards/feature-reviews'); }}
                class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                  isActive('/stewards/feature-reviews') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Feature Scoring
            </a>
          {/if}
          {#if canAccessDiscordXP}
            <a
              href="/stewards/discord-xp"
              onclick={(e) => { e.preventDefault(); navigate('/stewards/discord-xp'); }}
              class="flex items-center border-l-[1.5px] px-3 py-2 text-[14px] font-medium text-black tracking-[0.28px] {
                isActive('/stewards/discord-xp') ? 'border-[#19A663]' : 'border-[#f5f5f5]'
              }"
            >
              Discord XP
            </a>
          {/if}
        </div>
      {/if}

      <!-- Discover header (mobile) -->
      <div class="pt-2 pb-1 px-3">
        <span class="text-[12px] font-normal text-[#6b6b6b] tracking-[0.24px]">Discover</span>
      </div>

      <!-- Genesis (mobile) -->
      <button
        onclick={() => changeCategory('foundations', '/genesis')}
        class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-[14px] font-medium text-black tracking-[0.28px]"
        style={getActiveSection() === 'foundations' ? 'background: #eeedfb;' : ''}
      >
        <!-- GenLayer symbol (from /assets/gl-symbol-black.svg) -->
        <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 34.0294 32" fill={getActiveSection() === 'foundations' ? '#6D5DD3' : '#1a1a1a'}>
          <path d="M15.4065 11.2607L9.64908 23.3639L15.0689 26.072L0 32L15.4065 0V11.2607Z" />
          <path d="M18.6229 11.2607L24.3803 23.3639L18.9605 26.072L34.0294 32L18.6229 0V11.2607Z" />
          <path d="M16.9311 15.2394L20.3041 21.9088L16.9311 23.5623L13.7392 21.9019L16.9311 15.2394Z" />
        </svg>
        <span>Genesis</span>
      </button>

      <!-- Ecosystem (mobile) -->
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
        <span>Ecosystem</span>
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
  <div class="flex-shrink-0 p-3 space-y-2">
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
      class="w-full flex items-center gap-2 px-3 py-2 rounded-[8px] transition-colors text-left {isActive('/submit-contribution') ? 'bg-[#eeedfb]' : 'hover:bg-[#f5f5f5]'}"
    >
      <img src="/assets/icons/add-line-sidebar.svg" alt="" class="w-4 h-4 flex-shrink-0">
      <span class="text-[14px] font-medium tracking-[0.28px] {isActive('/submit-contribution') ? 'text-[#6D5DD3]' : 'text-[#656567]'}">Submit Contribution</span>
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
        {#if sidebarUser}
          <Avatar user={sidebarUser} size="sm" className="flex-shrink-0" />
        {:else}
          <div class="w-8 h-8 rounded-full bg-[#f5f5f5] flex items-center justify-center flex-shrink-0">
            <span class="text-xs font-semibold text-gray-700">?</span>
          </div>
        {/if}
        <span class="text-[14px] font-medium text-black tracking-[0.28px] truncate text-left">
          {displayName || 'Connect wallet'}
        </span>
      </div>
      <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
    </button>
  </div>
</aside>
