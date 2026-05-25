<script>
  // @ts-nocheck
  import LeaderboardTable from '../components/LeaderboardTable.svelte';
  import Podium from '../components/ui/Podium.svelte';
  import { leaderboardAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { getCategoryGradientStyle } from '../lib/categoryPresentation.js';
  
  const PAGE_SIZE = 10;
  const PODIUM_SIZE = 3;
  const REQUEST_SIZE = PAGE_SIZE + 1;

  // State management
  let leaderboard = $state([]);
  let loading = $state(true);
  let pageLoading = $state(false);
  let error = $state(null);
  let searchQuery = $state('');
  let activeSearch = $state('');
  let podiumEntries = $state([]);
  let currentPage = $state(1);
  let pendingPage = $state(null);
  let hasNextPage = $state(false);
  let activeCategory = $state(null);
  let searchTimer;
  let requestSequence = 0;

  const categoryConfig = {
    global: {
      title: 'Global Leaderboard',
      label: 'participants',
      description: 'All-time rankings across the GenLayer ecosystem.',
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-black',
      accentColor: '#7f52e1',
      valueLabel: 'GP',
      podiumCategory: 'global',
    },
    builder: {
      title: 'Builders Leaderboard',
      label: 'builders',
      description: 'All-time Builder Points rankings.',
      icon: '/assets/icons/terminal-fill-white.svg',
      iconClass: 'bg-orange-500',
      accentColor: '#ee8521',
      valueLabel: 'BP',
      podiumCategory: 'builder',
    },
    validator: {
      title: 'Validators Leaderboard',
      label: 'validators',
      description: 'All-time Validator Points rankings.',
      icon: '/assets/icons/shield-white.svg',
      iconClass: 'bg-gradient-to-br from-[#8f7bff] to-[#6f8cff]',
      accentColor: '#3a7ce7',
      valueLabel: 'VP',
      podiumCategory: 'validator',
    },
    steward: {
      title: 'Stewards Leaderboard',
      label: 'stewards',
      description: 'All-time steward contribution rankings.',
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-emerald-500',
      accentColor: '#3eb359',
      valueLabel: 'SP',
      podiumCategory: 'steward',
    },
    community: {
      title: 'Community Leaderboard',
      label: 'community',
      description: 'All-time Community Points rankings.',
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-[#7f52e1]',
      accentColor: '#7f52e1',
      valueLabel: 'CP',
      podiumCategory: 'community',
    },
  };

  let pageConfig = $derived(categoryConfig[$currentCategory] || categoryConfig.global);
  let activeGradientCategory = $derived($currentCategory || 'global');
  let gradientStyle = $derived(getCategoryGradientStyle(activeGradientCategory, pageConfig.accentColor));
  let topEntries = $derived(podiumEntries);
  let tableEntries = $derived(leaderboard);
  let isSearching = $derived(searchQuery.trim().length > 0 || activeSearch.length > 0);
  let selectedPage = $derived(pendingPage || currentPage);
  let paginationPages = $derived((() => {
    const pages = new Set([1, selectedPage]);
    const start = Math.max(2, currentPage - 2);
    const end = currentPage + (hasNextPage ? 1 : 0);

    for (let page = start; page <= end; page += 1) {
      pages.add(page);
    }

    return [...pages].filter(page => page >= 1).sort((a, b) => a - b);
  })());

  let filteredTableEntries = $derived(tableEntries);

  function fetchEntries(category, options) {
    const params = activeSearch ? { ...options, search: activeSearch } : options;

    if (category === 'global') {
      return leaderboardAPI.getLeaderboard(params);
    }

    return leaderboardAPI.getLeaderboard({ type: category, order: 'asc', ...params });
  }

  async function fetchLeaderboard(page = 1, { reset = false } = {}) {
    const category = $currentCategory || 'global';
    const shouldShowFullLoader = reset || (podiumEntries.length === 0 && leaderboard.length === 0);
    const requestId = ++requestSequence;

    try {
      loading = shouldShowFullLoader;
      pageLoading = !shouldShowFullLoader;
      error = null;

      const podiumResponse = await fetchEntries(category, { limit: PODIUM_SIZE, offset: 0 });

      if (requestId !== requestSequence) return;
      if (category !== ($currentCategory || 'global')) return;

      const podiumData = podiumResponse.data?.results || podiumResponse.data || [];
      const availableForPodium = podiumResponse.data?.count ?? podiumData.length;
      const tableOffset = activeSearch || availableForPodium < PODIUM_SIZE
        ? ((page - 1) * PAGE_SIZE)
        : PODIUM_SIZE + ((page - 1) * PAGE_SIZE);

      const tableResponse = await fetchEntries(category, { limit: REQUEST_SIZE, offset: tableOffset });

      if (requestId !== requestSequence) return;
      if (category !== ($currentCategory || 'global')) return;

      const tableData = tableResponse.data?.results || tableResponse.data || [];
      podiumEntries = podiumData;
      leaderboard = tableData.slice(0, PAGE_SIZE);
      currentPage = page;
      hasNextPage = tableData.length > PAGE_SIZE;
    } catch (err) {
      if (requestId !== requestSequence) return;
      error = err.message || 'Failed to load leaderboard';
    } finally {
      if (requestId === requestSequence) {
        loading = false;
        pageLoading = false;
        pendingPage = null;
      }
    }
  }

  function goToPage(page) {
    if (page === currentPage || page < 1 || loading || pageLoading) return;
    pendingPage = page;
    fetchLeaderboard(page);
  }

  // Re-fetch when category changes
  $effect(() => {
    const category = $currentCategory || 'global';
    if (category && category !== activeCategory) {
      activeCategory = category;
      searchQuery = '';
      activeSearch = '';
      pendingPage = null;
      fetchLeaderboard(1, { reset: true });
    }
  });

  $effect(() => {
    const query = searchQuery.trim();
    clearTimeout(searchTimer);

    searchTimer = setTimeout(() => {
      if (query !== activeSearch) {
        activeSearch = query;
        pendingPage = null;
        fetchLeaderboard(1);
      }
    }, 250);

    return () => clearTimeout(searchTimer);
  });
</script>

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[320px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    {#if activeGradientCategory === 'global'}
      <img
        src="/assets/illustrations/welcome-gradient.png"
        alt=""
        class="absolute inset-0 w-full h-full object-cover opacity-70"
      />
    {:else}
      <div class="absolute inset-0" style={gradientStyle}></div>
    {/if}
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div class="space-y-2">
        <div class="flex items-start gap-3">
          <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] {pageConfig.iconClass} shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
            <img src={pageConfig.icon} alt="" class="h-5 w-5" />
          </div>
          <h1
            class="min-w-0 break-words text-[34px] sm:text-[40px] md:text-[46px] font-semibold font-display text-black leading-none"
            style="letter-spacing: -1px;"
          >
            {pageConfig.title}
          </h1>
        </div>
        <p class="max-w-2xl text-[14px] sm:text-[15px] text-[#3f4b5f]" style="letter-spacing: 0.2px;">
          {pageConfig.description}
        </p>
      </div>

      {#if !loading && !error && (leaderboard.length > 0 || podiumEntries.length > 0)}
        <div class="w-full md:w-[320px]">
          <label for="search" class="sr-only">Search participants</label>
          <div class="relative">
            <img
              src="/assets/icons/search-line.svg"
              alt=""
              class="pointer-events-none absolute left-3 top-1/2 z-10 h-5 w-5 -translate-y-1/2 opacity-70"
            />
            <input
              id="search"
              bind:value={searchQuery}
              type="search"
              class="relative z-0 block h-[42px] w-full rounded-[8px] border border-white/70 bg-white/82 pl-11 pr-3 text-[14px] text-[#111827] shadow-[0_8px_22px_rgba(31,42,68,0.08)] outline-none backdrop-blur-md placeholder:text-[#7b8798] focus:border-black focus:ring-2 focus:ring-black/10"
              placeholder="Search by name or address"
            />
          </div>
        </div>
      {/if}
    </header>

    <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 sm:p-7 md:p-8 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md">
      {#if loading}
        <div class="space-y-8">
          <div>
            <div class="mb-4 h-6 w-44 rounded-full bg-[#f2f3f7] animate-pulse"></div>
            <Podium
              entries={[]}
              loading={true}
              accentColor={pageConfig.accentColor}
              valueLabel={pageConfig.valueLabel}
              category={pageConfig.podiumCategory}
            />
          </div>
          <div class="h-[320px] rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)] animate-pulse"></div>
        </div>
      {:else if error}
        <div class="rounded-[8px] border border-red-100 bg-red-50 p-5">
          <h3 class="text-[14px] font-semibold text-red-800">Error loading leaderboard</h3>
          <p class="mt-1 text-[13px] text-red-700">{error}</p>
        </div>
      {:else}
        <div class="space-y-8 md:space-y-10">
          {#if !isSearching}
            <section>
              <Podium
                entries={topEntries}
                loading={false}
                accentColor={pageConfig.accentColor}
                valueLabel={pageConfig.valueLabel}
                category={pageConfig.podiumCategory}
              />
            </section>
          {/if}

          <section class={!isSearching ? 'border-t border-[#e9ecf3] pt-6 md:pt-8' : ''}>
            <div class={`overflow-hidden rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)] transition-opacity duration-200 ${pageLoading ? 'opacity-60' : 'opacity-100'}`}>
              {#if searchQuery && filteredTableEntries.length === 0}
                <div class="p-8 text-center text-[14px] text-[#6b6b6b]">
                  No participants found matching "{searchQuery.trim()}"
                </div>
              {:else}
                <LeaderboardTable
                  entries={filteredTableEntries}
                  loading={false}
                  error={null}
                  showHeader={false}
                  embedded={true}
                />
              {/if}
            </div>
          </section>
        </div>

        {#if currentPage > 1 || hasNextPage}
          <div class="mt-6 flex flex-wrap items-center justify-center gap-2">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage === 1 || loading || pageLoading}
              class="inline-flex min-h-11 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white px-4 text-[13px] font-semibold text-[#111827] shadow-[0_8px_18px_rgba(31,42,68,0.07)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] disabled:translate-y-0 disabled:opacity-45 disabled:shadow-none"
            >
              Previous
            </button>

            {#if paginationPages[1] && paginationPages[1] > 2}
              <span class="inline-flex min-h-11 min-w-11 items-center justify-center text-[13px] font-semibold text-[#7b8798]">...</span>
            {/if}

            {#each paginationPages as page}
              <button
                onclick={() => goToPage(page)}
                disabled={page === selectedPage || loading || pageLoading}
                class={`inline-flex min-h-11 min-w-11 items-center justify-center rounded-[8px] border px-3 text-[13px] font-semibold shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition ${
                  page === selectedPage
                    ? 'text-white'
                    : 'border-[#dfe4ee] bg-white text-[#111827] hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)]'
                } disabled:translate-y-0 disabled:shadow-none`}
                style={page === selectedPage ? `background-color: ${pageConfig.accentColor}; border-color: ${pageConfig.accentColor};` : ''}
                aria-current={page === selectedPage ? 'page' : undefined}
              >
                {page}
              </button>
            {/each}

            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={!hasNextPage || loading || pageLoading}
              class="inline-flex min-h-11 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white px-4 text-[13px] font-semibold text-[#111827] shadow-[0_8px_18px_rgba(31,42,68,0.07)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] disabled:translate-y-0 disabled:opacity-45 disabled:shadow-none"
            >
              Next
            </button>
          </div>
        {/if}
      {/if}
    </section>
  </div>
</div>

<style>
  /* Additional styles if needed */
</style>
