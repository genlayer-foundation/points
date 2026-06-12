<script>
  // @ts-nocheck
  import { onMount, onDestroy } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import { parseMarkdown } from '../lib/markdownLoader.js';
  import { showError } from '../lib/toastStore';
  import { currentCategory } from '../stores/category.js';
  import { getCategoryAccent, getCategoryPillColors } from '../lib/categoryColors.js';
  import { rgbaFromHex } from '../lib/categoryPresentation.js';

  let missions = $state([]);
  let loading = $state(true);
  let countdowns = $state({});
  let countdownInterval = null;

  let activeCategory = $derived($currentCategory || 'global');
  let accentColor = $derived(getCategoryAccent(activeCategory));
  let pillColors = $derived(getCategoryPillColors(activeCategory));
  let cornerGlowStyle = $derived(
    `background: radial-gradient(circle at 100% 100%, ${rgbaFromHex(accentColor, 0.28)} 0%, ${rgbaFromHex(accentColor, 0.08)} 35%, transparent 65%);`
  );

  async function fetchMissions(category = activeCategory) {
    try {
      loading = true;
      const response = await contributionsAPI.getMissions({
        category: category !== 'global' ? category : undefined
      });

      if (response.data?.results !== undefined) {
        missions = response.data.results || [];
      } else {
        missions = response.data || [];
      }

      missions.sort((a, b) => {
        if (!a.end_date && !b.end_date) return 0;
        if (!a.end_date) return 1;
        if (!b.end_date) return -1;
        return new Date(a.end_date) - new Date(b.end_date);
      });

      updateCountdowns();
    } catch (err) {
      showError('Failed to load missions. Please refresh the page.');
      missions = [];
    } finally {
      loading = false;
    }
  }

  function updateCountdowns() {
    const newCountdowns = {};
    missions.forEach(mission => {
      if (mission.end_date) {
        newCountdowns[mission.id] = getCountdown(mission.end_date);
      }
    });
    countdowns = newCountdowns;
  }

  function getCountdown(endDate) {
    if (!endDate) return null;

    const now = new Date();
    const end = new Date(endDate);
    const diffMs = end - now;

    if (diffMs <= 0) return 'Ended';

    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      return `${days}d ${hours}h`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  }

  function spotsLeftLabel(count) {
    return `${count} ${Number(count) === 1 ? 'spot' : 'spots'} left`;
  }

  function isFull(entity) {
    if (!entity) return false;
    if (entity.is_full === true) return true;
    return (
      entity.max_submissions !== null &&
      entity.max_submissions !== undefined &&
      entity.submissions_remaining !== null &&
      entity.submissions_remaining !== undefined &&
      Number(entity.submissions_remaining) <= 0
    );
  }

  function missionCapacityLabel(mission, parentType) {
    if (mission?.user_is_full === true) return 'Your limit reached';
    if (isFull(mission)) return 'Full';
    if (isFull(parentType)) return 'Submissions closed';
    if (mission?.max_submissions != null && mission?.submissions_remaining != null) {
      return spotsLeftLabel(mission.submissions_remaining);
    }
    if (parentType?.max_submissions != null && parentType?.submissions_remaining != null) {
      return spotsLeftLabel(parentType.submissions_remaining);
    }
    return null;
  }

  function formatPoints(type) {
    if (!type?.min_points && !type?.max_points) return null;
    const min = Number(type.min_points || 0);
    const max = Number(type.max_points || 0);
    return min === max ? `${min} pts` : `${min}-${max} pts`;
  }

  function renderMarkdown(text) {
    if (!text) return '';
    return parseMarkdown(text);
  }

  function submitLabel(mission, parentType) {
    if (mission?.user_is_full === true) return 'Limit reached';
    if (isFull(mission)) return 'Full';
    if (isFull(parentType)) return 'Closed';
    return 'Submit';
  }

  function cardGradientStyle(category = activeCategory) {
    const color = getCategoryAccent(category || activeCategory);
    return `background: linear-gradient(180deg, ${rgbaFromHex(color, 0.95)} 0%, ${rgbaFromHex(color, 0.28)} 58%, ${rgbaFromHex(color, 0.06)} 100%);`;
  }

  function handleCardClick(event, mission) {
    if (event.target.closest('button') || event.target.closest('a')) return;
    push(`/mission/${mission.id}`);
  }

  function handleCardKeydown(event, mission) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleCardClick(event, mission);
    }
  }

  onMount(() => {
    countdownInterval = setInterval(updateCountdowns, 60000);
  });

  onDestroy(() => {
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
  });

  $effect(() => {
    fetchMissions(activeCategory);
  });
</script>

{#snippet missionSkeleton()}
  <div class="relative overflow-hidden rounded-[8px] border border-[#eef1f6] bg-white p-4 pl-6 shadow-[0_8px_18px_rgba(31,42,68,0.05)]">
    <div class="absolute inset-y-0 left-0 w-1.5 bg-[#f1f1f1] sk-shimmer"></div>
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap gap-2">
          <div class="h-5 w-16 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
          <div class="h-5 w-20 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
        </div>
        <div class="mt-4 h-5 w-3/5 rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="mt-4 space-y-2">
          <div class="h-3 w-full rounded bg-[#f1f1f1] sk-shimmer"></div>
          <div class="h-3 w-11/12 rounded bg-[#f1f1f1] sk-shimmer"></div>
        </div>
      </div>
      <div class="flex flex-shrink-0 items-center justify-between gap-4 sm:w-[180px] sm:flex-col sm:items-end">
        <div class="h-4 w-24 rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="h-9 w-24 rounded-[8px] bg-[#f1f1f1] sk-shimmer"></div>
      </div>
    </div>
  </div>
{/snippet}

{#if !loading && missions.length > 0}
  <section
    class="relative overflow-hidden rounded-[10px] border border-white/70 bg-white/78 p-4 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-6 lg:p-8"
  >
    <div
      class="pointer-events-none absolute bottom-0 right-0 h-[260px] w-[280px]"
      style={cornerGlowStyle}
      aria-hidden="true"
    ></div>

    <div class="relative mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
            Missions
          </h2>
          <span class="inline-flex h-6 items-center rounded-full border border-[#e8ebf2] bg-white px-4 text-[12px] font-semibold text-[#506078]">
            {missions.length} {missions.length === 1 ? 'mission' : 'missions'}
          </span>
        </div>
        <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
          Time-limited opportunities to earn extra points and climb the leaderboard.
        </p>
      </div>

    </div>

    <div class="relative space-y-4">
      {#each missions as mission (mission.id)}
        {@const parentType = mission.contribution_type_details}
        {@const submissionClosed = mission.user_is_full === true || isFull(mission) || isFull(parentType)}
        {@const capacityLabel = missionCapacityLabel(mission, parentType)}
        {@const pointsLabel = formatPoints(parentType)}
        {@const countdownLabel = mission.end_date && countdowns[mission.id] ? countdowns[mission.id] : 'Ongoing'}
        {@const missionAccentStyle = cardGradientStyle(parentType?.category)}

        <div
          class="group relative flex w-full cursor-pointer flex-col gap-4 overflow-hidden rounded-[8px] border border-[#eef1f6] bg-white p-4 pl-6 shadow-[0_8px_18px_rgba(31,42,68,0.05)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_28px_rgba(31,42,68,0.10)] sm:flex-row sm:items-stretch sm:justify-between"
          onclick={(event) => handleCardClick(event, mission)}
          onkeydown={(event) => handleCardKeydown(event, mission)}
          role="link"
          tabindex="0"
        >
          <div class="absolute inset-y-0 left-0 w-1.5" style={missionAccentStyle} aria-hidden="true"></div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="inline-flex h-6 items-center rounded-full bg-[#f7f8fb] px-2 text-[11px] font-semibold uppercase text-[#667085]">
                Mission
              </span>
              <span
                class="inline-flex h-6 items-center rounded-full px-2 text-[12px] font-semibold"
                style="background: {countdownLabel === 'Ended' ? '#f2f4f7' : pillColors.pillBg}; color: {countdownLabel === 'Ended' ? '#667085' : pillColors.pillText};"
              >
                {countdownLabel}
              </span>
              {#if capacityLabel}
                <span class="inline-flex h-6 items-center rounded-full border border-[#e8ebf2] bg-white px-2 text-[12px] font-semibold {submissionClosed ? 'text-[#98a2b3]' : 'text-[#506078]'}">
                  {capacityLabel}
                </span>
              {/if}
            </div>

            <div class="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
              <div class="min-w-0">
                <h3 class="line-clamp-2 text-[16px] font-semibold leading-snug text-black sm:text-[17px]">
                  {mission.name}
                </h3>

                {#if mission.description}
                  <div class="markdown-preview mt-2 text-[13px] leading-5 text-[#6b6b6b]">
                    {@html renderMarkdown(mission.description)}
                  </div>
                {:else}
                  <p class="mt-2 text-[13px] leading-5 text-[#98a2b3]">
                    No description available.
                  </p>
                {/if}
              </div>

              <div class="flex flex-wrap items-center gap-2 lg:justify-end">
                {#if pointsLabel}
                  <span
                    class="inline-flex h-8 items-center rounded-full px-4 text-[12px] font-semibold"
                    style="background: {pillColors.pillBg}; color: {pillColors.pillText};"
                  >
                    {pointsLabel}
                  </span>
                {/if}
                {#if parentType}
                  <button
                    type="button"
                    onclick={(event) => { event.stopPropagation(); push(`/contribution-type/${parentType.id}`); }}
                    class="inline-flex h-8 max-w-full items-center rounded-full border border-[#e8ebf2] bg-white px-4 text-[12px] font-semibold text-[#506078] transition hover:border-black hover:text-black"
                  >
                    <span class="truncate">{parentType.name}</span>
                  </button>
                {/if}
              </div>
            </div>
          </div>

          <div class="flex flex-shrink-0 items-center justify-between gap-2 border-t border-[#eef1f6] pt-4 sm:w-[142px] sm:flex-col sm:items-end sm:justify-between sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0">
            <span class="text-[12px] font-medium {submissionClosed ? 'text-[#98a2b3]' : 'text-[#506078]'}">
              {submissionClosed ? (capacityLabel || 'Submissions closed') : 'Ready to submit'}
            </span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                onclick={(event) => { event.stopPropagation(); push(`/mission/${mission.id}`); }}
                class="inline-flex h-8 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white px-2 text-[12px] font-semibold text-[#506078] transition hover:border-black hover:text-black"
              >
                Details
              </button>
              <button
                type="button"
                onclick={(event) => { event.stopPropagation(); !submissionClosed && push(`/submit-contribution?mission=${mission.id}`); }}
                disabled={submissionClosed}
                class="inline-flex h-8 items-center justify-center rounded-[8px] px-2 text-[12px] font-semibold transition {submissionClosed ? 'cursor-not-allowed bg-[#f2f4f7] text-[#98a2b3]' : 'bg-black text-white hover:-translate-y-0.5 hover:shadow-[0_10px_18px_rgba(31,42,68,0.14)]'}"
              >
                {submitLabel(mission, parentType)}
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  </section>
{:else if loading}
  <section class="rounded-[10px] border border-white/70 bg-white/78 p-4 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-6 lg:p-8">
    <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div class="h-7 w-32 rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="mt-2 h-4 w-64 max-w-full rounded bg-[#f1f1f1] sk-shimmer"></div>
      </div>
      <div class="hidden sm:block">
        <div class="h-11 w-40 rounded-[8px] bg-[#f1f1f1] sk-shimmer"></div>
      </div>
    </div>
    <div class="space-y-4">
      {#each Array(3) as _}
        {@render missionSkeleton()}
      {/each}
    </div>
  </section>
{/if}

<style>
  .sk-shimmer {
    background-image: linear-gradient(
      90deg,
      rgba(241, 241, 241, 1) 0%,
      rgba(228, 228, 228, 1) 50%,
      rgba(241, 241, 241, 1) 100%
    );
    background-size: 200% 100%;
    animation: sk-shimmer 1.4s ease-in-out infinite;
  }

  @keyframes sk-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  .markdown-preview {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .markdown-preview :global(p),
  .markdown-preview :global(ul),
  .markdown-preview :global(ol),
  .markdown-preview :global(blockquote),
  .markdown-preview :global(pre),
  .markdown-preview :global(table),
  .markdown-preview :global(thead),
  .markdown-preview :global(tbody),
  .markdown-preview :global(tr),
  .markdown-preview :global(th),
  .markdown-preview :global(td),
  .markdown-preview :global(h1),
  .markdown-preview :global(h2),
  .markdown-preview :global(h3),
  .markdown-preview :global(h4),
  .markdown-preview :global(h5),
  .markdown-preview :global(h6) {
    display: inline;
    margin: 0;
    padding: 0;
    font-size: inherit;
    line-height: inherit;
    font-weight: inherit;
  }

  .markdown-preview :global(li) {
    display: inline;
  }

  .markdown-preview :global(li + li)::before {
    content: ' / ';
  }

  .markdown-preview :global(img),
  .markdown-preview :global(hr) {
    display: none;
  }

  .markdown-preview :global(a) {
    color: inherit;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .markdown-preview :global(strong) {
    font-weight: 600;
  }

  .markdown-preview :global(code) {
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.06);
    padding: 0 4px;
    font-size: 0.95em;
  }
</style>
