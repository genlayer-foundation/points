<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Avatar from '../components/Avatar.svelte';
  import Podium from '../components/ui/Podium.svelte';
  import { leaderboardAPI } from '../lib/api';
  import { getCategoryGradientStyle } from '../lib/categoryPresentation.js';

  const PAGE_SIZE = 10;
  const PODIUM_SIZE = 3;
  const REQUEST_SIZE = PAGE_SIZE + 1;
  const SEARCH_LIMIT = 100;

  let podiumEntries = $state([]);
  let referrals = $state([]);
  let loading = $state(true);
  let pageLoading = $state(false);
  let error = $state(null);
  let searchQuery = $state('');
  let activeSearch = $state('');
  let currentPage = $state(1);
  let pendingPage = $state(null);
  let hasNextPage = $state(false);
  let totalCount = $state(0);
  let searchTimer;
  let requestSequence = 0;

  const pageConfig = {
    title: 'Referral leaderboard',
    description: 'Top referrers ranked by eligible referral points.',
    icon: '/assets/icons/link-m.svg',
    iconClass: 'bg-[#111827]',
    accentColor: '#7f52e1',
    valueLabel: 'RP',
    podiumCategory: 'referral',
  };

  const gradientStyle = getCategoryGradientStyle('community', pageConfig.accentColor);

  let isSearching = $derived(searchQuery.trim().length > 0 || activeSearch.length > 0);
  let selectedPage = $derived(pendingPage || currentPage);
  let paginationPages = $derived((() => {
    const pages = new Set([1, selectedPage]);
    const start = Math.max(2, currentPage - 2);
    const end = currentPage + (hasNextPage ? 1 : 0);

    for (let page = start; page <= end; page += 1) {
      pages.add(page);
    }

    return [...pages].filter((page) => page >= 1).sort((a, b) => a - b);
  })());

  function shortAddress(address) {
    if (!address) return '';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  }

  function displayName(entry) {
    const user = entry.user_details || {};
    return user.name || shortAddress(user.address) || 'Unknown';
  }

  function getRankClass(rank) {
    if (rank === 1) return 'bg-[#f8b93d] text-white';
    if (rank === 2) return 'bg-[#f1f3f7] text-[#333]';
    if (rank === 3) return 'bg-[#c9956b] text-white';
    return 'bg-[#f8fafc] text-[#506078]';
  }

  function userMatchesSearch(entry, query) {
    const user = entry.user_details || {};
    const name = (user.name || '').toLowerCase();
    const address = (user.address || '').toLowerCase();
    return name.includes(query) || address.includes(query);
  }

  function normalizeReferral(member, fallbackRank) {
    const totalPoints = member.total_referral_points ?? member.total_points ?? 0;

    return {
      id: member.id,
      rank: member.rank ?? fallbackRank,
      total_points: totalPoints,
      points: totalPoints,
      referral_builder_points: member.referral_builder_points ?? 0,
      referral_validator_points: member.referral_validator_points ?? 0,
      user_details: {
        id: member.id,
        name: member.name,
        address: member.address,
        profile_image_url: member.profile_image_url,
        builder: member.builder,
        validator: member.validator,
        steward: member.steward,
      },
    };
  }

  async function fetchReferralLeaderboard(page = 1, { reset = false } = {}) {
    const requestId = ++requestSequence;
    const query = activeSearch.trim().toLowerCase();
    const shouldShowFullLoader = reset || (podiumEntries.length === 0 && referrals.length === 0);

    try {
      loading = shouldShowFullLoader;
      pageLoading = !shouldShowFullLoader;
      error = null;

      if (query) {
        const response = await leaderboardAPI.getReferrals({ limit: SEARCH_LIMIT, offset: 0 });
        if (requestId !== requestSequence) return;

        const entries = (response.data?.results || [])
          .map((member, index) => normalizeReferral(member, index + 1))
          .filter((entry) => userMatchesSearch(entry, query));

        podiumEntries = [];
        referrals = entries.slice(0, PAGE_SIZE);
        totalCount = entries.length;
        currentPage = 1;
        hasNextPage = false;
        return;
      }

      const podiumResponse = await leaderboardAPI.getReferrals({ limit: PODIUM_SIZE, offset: 0 });
      if (requestId !== requestSequence) return;

      const topEntries = (podiumResponse.data?.results || []).map((member, index) => normalizeReferral(member, index + 1));
      const count = podiumResponse.data?.count ?? topEntries.length;
      const tableOffset = count >= PODIUM_SIZE
        ? PODIUM_SIZE + ((page - 1) * PAGE_SIZE)
        : ((page - 1) * PAGE_SIZE);

      const tableResponse = await leaderboardAPI.getReferrals({ limit: REQUEST_SIZE, offset: tableOffset });
      if (requestId !== requestSequence) return;

      const tableData = (tableResponse.data?.results || []).map((member, index) => normalizeReferral(member, tableOffset + index + 1));

      podiumEntries = topEntries;
      referrals = tableData.slice(0, PAGE_SIZE);
      totalCount = tableResponse.data?.count ?? count;
      currentPage = page;
      hasNextPage = tableOffset + tableData.length < totalCount;
    } catch (err) {
      if (requestId !== requestSequence) return;
      error = err.message || 'Failed to load referral leaderboard';
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
    fetchReferralLeaderboard(page);
  }

  onMount(() => {
    fetchReferralLeaderboard(1, { reset: true });
  });

  $effect(() => {
    const query = searchQuery.trim();
    clearTimeout(searchTimer);

    searchTimer = setTimeout(() => {
      if (query !== activeSearch) {
        activeSearch = query;
        pendingPage = null;
        fetchReferralLeaderboard(1, { reset: false });
      }
    }, 250);

    return () => clearTimeout(searchTimer);
  });
</script>

<div class="relative -mx-3 -my-3 min-h-[calc(100vh-64px)] overflow-hidden bg-white px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[320px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0" style={gradientStyle}></div>
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div class="space-y-2">
        <div class="flex items-start gap-3">
          <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] {pageConfig.iconClass} shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
            <img src={pageConfig.icon} alt="" class="h-5 w-5 brightness-0 invert" />
          </div>
          <h1
            class="min-w-0 break-words text-[34px] font-semibold leading-none text-black sm:text-[40px] md:text-[46px] font-display"
            style="letter-spacing: -1px;"
          >
            {pageConfig.title}
          </h1>
        </div>
        <p class="max-w-2xl text-[14px] text-[#3f4b5f] sm:text-[15px]" style="letter-spacing: 0.2px;">
          {pageConfig.description}
        </p>
      </div>

      {#if !loading && !error && (referrals.length > 0 || podiumEntries.length > 0 || searchQuery)}
        <div class="flex w-full flex-col gap-2 md:w-[320px]">
          <label for="referral-search" class="sr-only">Search referrers</label>
          <div class="relative">
            <img
              src="/assets/icons/search-line.svg"
              alt=""
              class="pointer-events-none absolute left-3 top-1/2 z-10 h-5 w-5 -translate-y-1/2 opacity-70"
            />
            <input
              id="referral-search"
              bind:value={searchQuery}
              type="search"
              class="relative z-0 block h-[42px] w-full rounded-[8px] border border-white/70 bg-white/82 pl-11 pr-3 text-[14px] text-[#111827] shadow-[0_8px_22px_rgba(31,42,68,0.08)] outline-none backdrop-blur-md placeholder:text-[#7b8798] focus:border-black focus:ring-2 focus:ring-black/10"
              placeholder="Search by name or address"
            />
          </div>
          <button
            type="button"
            onclick={() => push('/referral-program')}
            class="inline-flex h-10 items-center justify-center gap-1.5 rounded-[8px] border border-[#dfe4ee] bg-white/82 px-3 text-[13px] font-semibold text-[#111827] shadow-[0_8px_18px_rgba(31,42,68,0.06)] backdrop-blur-md transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)]"
          >
            Referral Program
            <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4" />
          </button>
        </div>
      {/if}
    </header>

    <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
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
          <h3 class="text-[14px] font-semibold text-red-800">Error loading referral leaderboard</h3>
          <p class="mt-1 text-[13px] text-red-700">{error}</p>
        </div>
      {:else if totalCount === 0 && !searchQuery}
        <div class="rounded-[8px] border border-dashed border-[#dfe4ee] bg-white/70 p-10 text-center">
          <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-[12px] bg-[#111827] shadow-[0_8px_18px_rgba(31,42,68,0.12)]">
            <img src={pageConfig.icon} alt="" class="h-6 w-6 brightness-0 invert" />
          </div>
          <h2 class="text-[18px] font-semibold text-black">No referral points yet</h2>
          <p class="mx-auto mt-2 max-w-md text-[14px] text-[#66708a]">
            Referrers will appear here once referred users earn eligible builder or validator points.
          </p>
        </div>
      {:else}
        <div class="space-y-8 md:space-y-10">
          {#if !isSearching}
            <section>
              <Podium
                entries={podiumEntries}
                loading={false}
                accentColor={pageConfig.accentColor}
                valueLabel={pageConfig.valueLabel}
                category={pageConfig.podiumCategory}
              />
            </section>
          {/if}

          {#if referrals.length > 0 || isSearching}
            <section class={!isSearching ? 'border-t border-[#e9ecf3] pt-6 md:pt-8' : ''}>
              <div class={`overflow-hidden rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)] transition-opacity duration-200 ${pageLoading ? 'opacity-60' : 'opacity-100'}`}>
                {#if searchQuery && referrals.length === 0}
                  <div class="p-8 text-center text-[14px] text-[#6b6b6b]">
                    No referrers found matching "{searchQuery.trim()}"
                  </div>
                {:else}
                <div class="overflow-hidden">
                  <table class="w-full table-fixed divide-y divide-[#eef1f6]">
                    <thead class="bg-[#f8fafc]">
                      <tr>
                        <th scope="col" class="w-[56px] px-2 py-3 text-left text-[11px] font-semibold uppercase text-[#7b8798] sm:w-[88px] sm:px-6" style="letter-spacing: 0.8px;">
                          Rank
                        </th>
                        <th scope="col" class="px-2 py-3 text-left text-[11px] font-semibold uppercase text-[#7b8798] sm:px-6" style="letter-spacing: 0.8px;">
                          Referrer
                        </th>
                        <th scope="col" class="w-[96px] px-2 py-3 text-right text-[11px] font-semibold uppercase text-[#7b8798] sm:w-[150px] sm:px-6 sm:text-left" style="letter-spacing: 0.8px;">
                          Referral Points
                        </th>
                        <th scope="col" class="hidden w-[220px] px-3 py-3 text-left text-[11px] font-semibold uppercase text-[#7b8798] lg:table-cell lg:px-6" style="letter-spacing: 0.8px;">
                          Breakdown
                        </th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-[#eef1f6] bg-white">
                      {#each referrals as entry}
                        <tr class="bg-white transition-colors hover:bg-[#fbfcff]">
                          <td class="px-2 py-4 align-top sm:px-6">
                            <span class={`inline-flex h-8 w-8 items-center justify-center rounded-full text-[13px] font-semibold ${getRankClass(entry.rank)}`}>
                              {entry.rank}
                            </span>
                          </td>
                          <td class="min-w-0 px-2 py-4 align-top sm:px-6">
                            <div class="flex min-w-0 items-center">
                              <div class="mr-2 flex-shrink-0 sm:mr-3">
                                <Avatar user={entry.user_details} size="sm" clickable={true} />
                              </div>
                              <div class="min-w-0">
                                <button
                                  onclick={() => push(`/participant/${entry.user_details?.address || ''}`)}
                                  class="block max-w-full truncate text-left text-[14px] font-semibold text-[#111827] transition-colors hover:text-black"
                                >
                                  {displayName(entry)}
                                </button>
                                <div class="hidden text-[13px] text-[#7b8798] sm:block">
                                  {entry.user_details?.address || ''}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td class="px-2 py-4 text-right align-top sm:px-6 sm:text-left">
                            <div class="truncate text-[14px] font-semibold text-[#111827]">{entry.total_points}</div>
                          </td>
                          <td class="hidden px-3 py-4 align-top lg:table-cell lg:px-6">
                            <div class="flex flex-wrap gap-2">
                              <span class="inline-flex items-center rounded-full bg-[#fff5e8] px-2.5 py-1.5 text-[12px] font-semibold text-[#c66c13]">
                                Builder {entry.referral_builder_points}
                              </span>
                              <span class="inline-flex items-center rounded-full bg-[#eef4ff] px-2.5 py-1.5 text-[12px] font-semibold text-[#387de8]">
                                Validator {entry.referral_validator_points}
                              </span>
                            </div>
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
                {/if}
              </div>
            </section>
          {/if}
        </div>

        {#if !isSearching && (currentPage > 1 || hasNextPage)}
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
