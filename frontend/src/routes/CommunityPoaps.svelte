<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { poapsAPI } from '../lib/api.js';
  import { showError } from '../lib/toastStore.js';
  import PoapCollectionWall from '../components/poaps/PoapCollectionWall.svelte';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';
  import { getCategoryGradientStyle } from '../lib/categoryPresentation.js';

  let loading = $state(true);
  /** @type {any[]} */
  let poaps = $state([]);
  let count = $state(0);
  let search = $state('');
  let monthFilter = $state('');
  let appliedSearch = $state('');
  let appliedMonthFilter = $state('');
  let page = $state(1);
  let hasMore = $state(false);
  let loadingMore = $state(false);
  let latestPoapsRequestId = 0;

  const PAGE_SIZE = 48;
  const poapGradientStyle = getCategoryGradientStyle('community', '#7f52e1');

  /** @param {number} [nextPage] @param {boolean} [append] */
  async function loadPoaps(nextPage = 1, append = false) {
    const requestId = ++latestPoapsRequestId;
    if (append) {
      loadingMore = true;
    } else {
      loading = true;
      loadingMore = false;
      appliedSearch = search.trim();
      appliedMonthFilter = monthFilter;
      hasMore = false;
    }

    try {
      const nextSearch = append ? appliedSearch : search.trim();
      const nextMonthFilter = append ? appliedMonthFilter : monthFilter;
      /** @type {Record<string, any>} */
      const params = {
        page: nextPage,
        page_size: PAGE_SIZE,
        ordering: '-event_start_at',
      };
      if (nextSearch) params.search = nextSearch;
      if (nextMonthFilter) params.month = nextMonthFilter;
      const response = await poapsAPI.list(params);
      if (requestId !== latestPoapsRequestId) return;
      const data = response.data || {};
      if (Array.isArray(data)) {
        poaps = append ? [...poaps, ...data] : data;
        count = poaps.length;
        page = nextPage;
        hasMore = false;
        return;
      }

      const results = data.results || [];
      poaps = append ? [...poaps, ...results] : results;
      count = data.count ?? poaps.length;
      page = nextPage;
      hasMore = Boolean(data.next);
    } catch (err) {
      if (requestId !== latestPoapsRequestId) return;
      const error = /** @type {any} */ (err);
      showError(error.response?.data?.error || 'Unable to load POAPs');
      if (!append) {
        poaps = [];
        count = 0;
        page = 1;
        hasMore = false;
      }
    } finally {
      if (requestId !== latestPoapsRequestId) return;
      if (append) {
        loadingMore = false;
      } else {
        loading = false;
      }
    }
  }

  function clearFilters() {
    search = '';
    monthFilter = '';
    loadPoaps(1);
  }

  onMount(() => {
    loadPoaps(1);
  });
</script>

<div class="relative -mx-3 -my-3 min-h-[calc(100vh-64px)] overflow-hidden bg-white px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[220px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0" style={poapGradientStyle}></div>
    <div class="absolute inset-0 bg-white/55"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
      <div class="flex min-w-0 items-start gap-3">
        <div class="mt-1 shrink-0">
          <CategoryIcon category="community" mode="hexagon" />
        </div>
        <div class="min-w-0">
          <h1 class="font-display text-[34px] font-semibold leading-none text-black sm:text-[40px] md:text-[46px]" style="letter-spacing: -1px;">POAPs</h1>
          <p class="mt-2 text-[14px] text-[#3f4b5f] sm:text-[15px]">Browse GenLayer POAPs.</p>
        </div>
      </div>

      <div class="flex w-full flex-col gap-3 xl:w-auto xl:items-end">
        <button
          class="inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-[#d9d2ff] bg-white px-4 text-[13px] font-semibold text-[#6b5bd6] transition-colors hover:bg-[#f7f4ff] xl:self-end"
          onclick={() => push('/community/poaps/recover')}
        >
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M20 12v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5" />
            <path d="m8 10 4-4 4 4" />
            <path d="M12 6v10" />
          </svg>
          Recover POAPs
        </button>
        <div class="flex w-full flex-col gap-2 md:flex-row xl:justify-end">
          <label class="relative md:w-[300px]">
            <span class="sr-only">Search POAPs</span>
            <input
              bind:value={search}
              class="h-10 w-full rounded-[8px] border border-[#e6e6e6] bg-white px-4 pr-10 text-[14px] text-black outline-none transition-colors placeholder:text-[#999] focus:border-[#8d81e1]"
              placeholder="Search POAPs"
              onkeydown={(event) => event.key === 'Enter' && loadPoaps(1)}
            />
            <button
              class="absolute right-1.5 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-[6px] text-[#8d81e1] hover:bg-[#f4ecfd]"
              onclick={() => loadPoaps(1)}
              aria-label="Search POAPs"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
              </svg>
            </button>
          </label>

          <input
            bind:value={monthFilter}
            type="month"
            class="h-10 rounded-[8px] border border-[#e6e6e6] bg-white px-3 text-[14px] outline-none focus:border-[#8d81e1] md:w-[150px]"
            onchange={() => loadPoaps(1)}
          />

          {#if search || monthFilter}
            <button
              class="h-10 rounded-[8px] border border-[#e6e6e6] bg-white px-3 text-[13px] font-medium text-[#555] transition-colors hover:bg-[#f7f7f7]"
              onclick={clearFilters}
            >
              Reset
            </button>
          {/if}

        </div>
      </div>
    </header>

    <section class="space-y-6">
      {#if loading}
        <div class="space-y-8 animate-pulse">
          <div class="h-8 w-56 rounded bg-[#eee8ff]"></div>
          <div class="grid grid-cols-2 gap-5 sm:grid-cols-4 lg:grid-cols-6">
            {#each Array(12) as _}
              <div class="flex flex-col items-center gap-3">
                <div class="h-28 w-28 rounded-full bg-white shadow-[0_14px_30px_rgba(38,48,75,0.08)] sm:h-36 sm:w-36"></div>
                <div class="h-3 w-24 rounded bg-[#eee]"></div>
              </div>
            {/each}
          </div>
        </div>
      {:else if poaps.length === 0}
        <div class="rounded-[8px] border border-[#f0f0f0] bg-white p-12 text-center">
          <p class="text-[15px] font-medium text-black">No POAPs found</p>
          <p class="mt-1 text-[14px] text-[#7a7a7a]">Try changing the filters or check back after the next community event.</p>
        </div>
      {:else}
        <PoapCollectionWall items={poaps} density="large" showCaptions={false} showOpenBadge={true} />
        {#if hasMore}
          <div class="flex justify-center pt-2">
            <button
              class="h-10 rounded-[8px] border border-[#d9d2ff] bg-white px-4 text-[13px] font-semibold text-[#6b5bd6] transition-colors hover:bg-[#f7f4ff] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loadingMore}
              onclick={() => loadPoaps(page + 1, true)}
            >
              {loadingMore ? 'Loading...' : `Load more POAPs (${poaps.length} of ${count})`}
            </button>
          </div>
        {/if}
      {/if}
    </section>
  </div>
</div>
