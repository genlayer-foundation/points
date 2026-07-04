<script>
  import { push } from 'svelte-spa-router';
  import { format } from '../../lib/dates.js';
  import { poapsAPI } from '../../lib/api.js';
  import { authState } from '../../lib/auth.js';
  import PoapCollectionWall from './PoapCollectionWall.svelte';

  /** @type {{ userId?: string | null, limit?: number }} */
  let { userId = null, limit = 120 } = $props();

  const PREVIEW_LIMIT = 10;
  let loading = $state(true);
  let loadingMore = $state(false);
  /** @type {any[]} */
  let claims = $state([]);
  let count = $state(0);
  let page = $state(1);
  let error = $state('');
  let loadedUserId = $state('');
  let viewAll = $state(false);

  /** @param {number} [nextPage] */
  async function loadPoaps(nextPage = 1, mode = viewAll ? 'all' : 'preview') {
    if (!userId) {
      loading = false;
      return;
    }
    const append = nextPage > 1;
    if (append) {
      loadingMore = true;
    } else {
      loading = true;
    }
    error = '';
    try {
      const pageSize = mode === 'preview' ? PREVIEW_LIMIT : limit;
      const response = await poapsAPI.getUserPoaps(userId, { page: nextPage, page_size: pageSize });
      const nextClaims = response.data?.results || response.data || [];
      claims = append ? [...claims, ...nextClaims] : nextClaims;
      count = response.data?.count ?? claims.length;
      page = nextPage;
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      error = requestError.response?.data?.error || 'Unable to load POAPs.';
      if (!append) claims = [];
      count = 0;
    } finally {
      loading = false;
      loadingMore = false;
    }
  }

  /** @param {any} item */
  function normalizePoap(item) {
    const drop = item?.drop || {};
    return {
      key: `profile-poap-${item.id || drop.id || drop.slug}`,
      slug: drop.slug,
      title: drop.title || 'POAP',
      artworkUrl: drop.artwork_url || '',
      eventStartAt: drop.event_start_at || item?.claimed_at || null,
      claimedAt: item?.claimed_at || null,
    };
  }

  /** @param {string | Date | null | undefined} value */
  function toDate(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  /** @param {string | Date | null | undefined} value */
  function dateMs(value) {
    return toDate(value)?.getTime() || 0;
  }

  /** @param {string | Date | null | undefined} value */
  function monthLabel(value) {
    const date = toDate(value);
    if (!date) return 'Unknown';
    return format(date, 'MMM yyyy');
  }

  /** @param {string} value */
  function initials(value) {
    return (value || 'POAP').slice(0, 2).toUpperCase();
  }

  /** @param {string} slug */
  function openPoap(slug) {
    if (!slug) return;
    push(`/community/poaps/${slug}`);
  }

  async function showAllPoaps() {
    viewAll = true;
    await loadPoaps(1, 'all');
  }

  function showRecentPoaps() {
    viewAll = false;
  }

  let normalizedClaims = $derived(claims.map(normalizePoap).filter((item) => item.slug));
  let recentClaims = $derived(
    [...normalizedClaims]
      .sort((left, right) => dateMs(right.claimedAt || right.eventStartAt) - dateMs(left.claimedAt || left.eventStartAt))
      .slice(0, PREVIEW_LIMIT)
  );
  let hasMore = $derived(viewAll && count > claims.length);
  let canViewAll = $derived(count > 0);
  let canRecover = $derived(Boolean(
    userId &&
    $authState.isAuthenticated &&
    $authState.address &&
    String(userId).toLowerCase() === String($authState.address).toLowerCase()
  ));

  $effect(() => {
    if (userId && userId !== loadedUserId) {
      loadedUserId = userId;
      claims = [];
      page = 1;
      viewAll = false;
      loadPoaps(1, 'preview');
    }
  });
</script>

<section class="w-full">
  <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
    <div>
      <h3 class="text-[20px] font-semibold text-black">POAPs</h3>
      <p class="mt-1 text-[14px] text-[#999]">Collected GenLayer community badges.</p>
    </div>
    {#if canViewAll || canRecover}
      <div class="flex items-center gap-2">
        {#if canRecover}
          <button
            class="h-8 rounded-full border border-[#d9d2ff] bg-white px-3 text-[12px] font-semibold text-[#6b5bd6] transition-colors hover:bg-[#f7f4ff]"
            onclick={() => push('/community/poaps/recover')}
          >
            Recover
          </button>
        {/if}
        {#if canViewAll}
          <button
            class="h-8 rounded-full border border-[#d9d2ff] bg-white px-3 text-[12px] font-semibold text-[#6b5bd6] transition-colors hover:bg-[#f7f4ff]"
            onclick={viewAll ? showRecentPoaps : showAllPoaps}
          >
            {viewAll ? 'Show recent' : 'View all'}
          </button>
        {/if}
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="grid grid-cols-2 gap-5 sm:grid-cols-4 lg:grid-cols-6 animate-pulse">
      {#each Array(6) as _}
        <div class="flex flex-col items-center gap-3">
          <div class="h-24 w-24 rounded-full bg-white shadow-[0_14px_30px_rgba(38,48,75,0.08)]"></div>
          <div class="h-3 w-20 rounded bg-[#eee]"></div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="rounded-[8px] border border-[#f0d2d2] bg-[#fff7f7] p-4 text-[14px] text-[#9f2f2f]">{error}</div>
  {:else if claims.length === 0}
    <div class="rounded-[8px] border border-[#f0f0f0] bg-white p-8 text-center">
      <p class="text-[14px] font-medium text-black">No POAPs yet</p>
      <p class="mt-1 text-[13px] text-[#7a7a7a]">Claimed community badges will appear here.</p>
    </div>
  {:else}
    <div class="space-y-6">
      {#if viewAll}
        <PoapCollectionWall items={claims} density="compact" />
      {:else}
        <div class="poap-recent-shell">
          <div class="poap-recent-slider">
            {#each recentClaims as poap (poap.key)}
              <button
                type="button"
                class="poap-recent-card"
                title={poap.title}
                aria-label={`Open ${poap.title}`}
                onclick={() => openPoap(poap.slug)}
              >
                <span class="poap-recent-disc">
                  <span class="poap-month-badge">{monthLabel(poap.eventStartAt)}</span>
                  <span class="poap-recent-core">
                    {#if poap.artworkUrl}
                      <img src={poap.artworkUrl} alt="" class="poap-recent-art" loading="lazy" />
                    {:else}
                      <span class="poap-recent-fallback">{initials(poap.title)}</span>
                    {/if}
                  </span>
                </span>
              </button>
            {/each}
          </div>
        </div>
      {/if}

      {#if hasMore}
        <div class="flex justify-center">
          <button
            class="h-10 rounded-[24px] border border-[#d9d2ff] bg-white px-4 text-[14px] font-medium text-[#6b5bd6] transition-colors hover:bg-[#f7f4ff] disabled:opacity-50"
            disabled={loadingMore}
            onclick={() => loadPoaps(page + 1)}
          >
            {loadingMore ? 'Loading...' : 'Load more POAPs'}
          </button>
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .poap-recent-shell {
    position: relative;
  }

  .poap-recent-slider {
    display: flex;
    gap: 22px;
    overflow-x: auto;
    padding: 4px 2px 10px;
    scroll-behavior: smooth;
    scroll-snap-type: x mandatory;
    scrollbar-width: none;
  }

  .poap-recent-slider::-webkit-scrollbar {
    display: none;
  }

  .poap-recent-card {
    align-items: center;
    background: transparent;
    border: 0;
    cursor: pointer;
    display: flex;
    flex: 0 0 176px;
    flex-direction: column;
    min-width: 0;
    padding: 0 2px 6px;
    scroll-snap-align: start;
    text-align: center;
  }

  .poap-recent-card:focus-visible {
    border-radius: 18px;
    outline: 2px solid #7f52e1;
    outline-offset: 6px;
  }

  .poap-recent-disc {
    align-items: center;
    background:
      linear-gradient(#fff, #fff) padding-box,
      conic-gradient(from 135deg, rgba(127, 82, 225, 0.85), rgba(202, 190, 255, 0.42), rgba(25, 166, 99, 0.34), rgba(127, 82, 225, 0.85)) border-box;
    border: 1px solid transparent;
    border-radius: 999px;
    box-shadow:
      0 14px 30px rgba(38, 48, 75, 0.12),
      inset 0 0 0 1px rgba(127, 82, 225, 0.14);
    display: inline-flex;
    height: 158px;
    justify-content: center;
    padding: 7px;
    position: relative;
    transition: transform 160ms ease, box-shadow 160ms ease;
    width: 158px;
  }

  .poap-recent-card:hover .poap-recent-disc {
    box-shadow:
      0 18px 36px rgba(80, 64, 150, 0.18),
      inset 0 0 0 1px rgba(127, 82, 225, 0.2);
    transform: translateY(-4px) scale(1.025);
  }

  .poap-month-badge {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid rgba(127, 82, 225, 0.2);
    border-radius: 999px;
    box-shadow: 0 8px 18px rgba(80, 64, 150, 0.12);
    color: #51658d;
    font-size: 10px;
    font-weight: 850;
    left: 50%;
    letter-spacing: 0;
    line-height: 1;
    padding: 5px 8px;
    position: absolute;
    text-transform: uppercase;
    top: -5px;
    transform: translateX(-50%);
    white-space: nowrap;
    z-index: 2;
  }

  .poap-recent-core {
    background: #fff;
    border-radius: 999px;
    box-shadow: inset 0 0 0 2px #fff;
    display: block;
    height: 100%;
    overflow: hidden;
    width: 100%;
  }

  .poap-recent-art,
  .poap-recent-fallback {
    border-radius: inherit;
    display: block;
    height: 100%;
    width: 100%;
  }

  .poap-recent-art {
    background: #fff;
    object-fit: cover;
  }

  .poap-recent-fallback {
    align-items: center;
    background:
      radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.9), transparent 34%),
      linear-gradient(135deg, #7f52e1, #2f426a 58%, #19a663);
    color: #fff;
    display: flex;
    font-size: 20px;
    font-weight: 800;
    justify-content: center;
  }

  @media (max-width: 640px) {
    .poap-recent-card {
      flex-basis: 142px;
    }

    .poap-recent-disc {
      height: 130px;
      width: 130px;
    }
  }
</style>
