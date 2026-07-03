<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import HighlightsSlider from '../components/portal/HighlightsSlider.svelte';
  import PortalContributionCard from '../components/portal/PortalContributionCard.svelte';
  import { getCategoryButtonStyle, getCategoryGradientStyle } from '../lib/categoryPresentation.js';
  import { visibleContributions } from '../lib/hiddenContributions.js';
  import { parseMarkdown } from '../lib/markdownLoader.js';

  let { params = {} } = $props();

  const categoryConfig = {
    global: {
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-black',
      accent: '#7f52e1',
      label: 'Global',
    },
    builder: {
      icon: '/assets/icons/terminal-fill-white.svg',
      iconClass: 'bg-orange-500',
      accent: '#ee8521',
      label: 'Builder',
    },
    validator: {
      icon: '/assets/icons/shield-white.svg',
      iconClass: 'bg-gradient-to-br from-[#8f7bff] to-[#6f8cff]',
      accent: '#387de8',
      label: 'Validator',
    },
    community: {
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-[#7f52e1]',
      accent: '#7f52e1',
      label: 'Community',
    },
    steward: {
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-emerald-500',
      accent: '#3eb359',
      label: 'Steward',
    },
  };

  let contributionType = $state(null);
  let statistics = $state({});
  let missions = $state([]);
  let highlights = $state([]);
  let contributions = $state([]);
  let loading = $state(true);
  let error = $state(/** @type {string | null} */ (null));
  let recentSlider = $state(/** @type {HTMLElement | null} */ (null));
  let descriptionExpanded = $state(false);
  let descriptionOverflows = $state(false);
  let descriptionEl = $state(/** @type {HTMLElement | null} */ (null));

  let category = $derived(contributionType?.category || 'global');
  let config = $derived(categoryConfig[category] || categoryConfig.global);
  let pointsRange = $derived(formatPoints(statistics));
  let gradientStyle = $derived(getCategoryGradientStyle(category, config.accent));
  let submitButtonStyle = $derived(getCategoryButtonStyle(config.accent));
  let explorerCategory = $derived(category === 'global' ? 'all' : category);
  let allContributionsPath = $derived(
    `/all-contributions?category=${explorerCategory}&type=${params.id}`
  );

  function formatDate(dateString) {
    if (!dateString) return 'Never';
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch {
      return dateString;
    }
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString();
  }

  function formatPoints(stats) {
    if (stats?.min_points == null || stats?.max_points == null || stats?.current_multiplier == null) {
      return '0 pts';
    }

    const min = Math.round(stats.min_points * stats.current_multiplier);
    const max = Math.round(stats.max_points * stats.current_multiplier);
    return min === max ? `${min} pts` : `${min}-${max} pts`;
  }

  function scrollRecent(direction) {
    recentSlider?.scrollBy({
      left: direction * 320,
      behavior: 'smooth',
    });
  }

  async function loadContributionTypeDetail() {
    try {
      loading = true;
      error = null;

      const [typeRes, statsRes, missionsRes, highlightsRes, contributionsRes] = await Promise.all([
        contributionsAPI.getContributionType(params.id),
        contributionsAPI.getContributionTypeStatistics(),
        contributionsAPI.getMissions({ contribution_type: params.id }),
        contributionsAPI.getContributionTypeHighlights(params.id),
        contributionsAPI.getContributions({
          contribution_type: params.id,
          ordering: '-contribution_date',
          page_size: 10,
          exclude_onboarding: 'true',
        }),
      ]);

      contributionType = typeRes.data;
      const allStats = statsRes.data || [];
      statistics = allStats.find((stat) => String(stat.id) === String(params.id)) || {};
      missions = missionsRes.data?.results || missionsRes.data || [];
      highlights = visibleContributions(highlightsRes.data || []);
      contributions = visibleContributions(contributionsRes.data?.results || []);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load contribution type';
    } finally {
      loading = false;
    }
  }

  onMount(loadContributionTypeDetail);

  $effect(() => {
    // Track these so the effect re-runs when description loads.
    void contributionType?.description;
    if (!descriptionEl) return;
    if (descriptionExpanded) return; // Only measure while clamped.
    descriptionOverflows = descriptionEl.scrollHeight > descriptionEl.clientHeight + 1;
  });
</script>

{#snippet contributionSkeleton()}
  <div class="h-[180px] w-[300px] flex-shrink-0 rounded-[8px] border border-[#f0f0f0] bg-white p-4">
    <div class="mb-5 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="h-6 w-6 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
        <div class="h-3 w-20 rounded bg-[#f1f1f1] sk-shimmer"></div>
      </div>
      <div class="h-4 w-12 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
    </div>
    <div class="space-y-2">
      <div class="h-3 w-2/3 rounded bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-3 w-full rounded bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-3 w-5/6 rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
    <div class="mt-8 flex items-center justify-between">
      <div class="h-5 w-20 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-3 w-16 rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
  </div>
{/snippet}

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[320px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    {#if category === 'global'}
      <img
        src="/assets/illustrations/welcome-gradient.png"
        alt=""
        class="absolute inset-0 h-full w-full object-cover opacity-70"
      />
    {:else}
      <div class="absolute inset-0" style={gradientStyle}></div>
    {/if}
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <button
      type="button"
      onclick={() => window.history.length > 1 ? window.history.back() : push('/contributions')}
      class="inline-flex min-h-11 items-center gap-2 text-[13px] font-semibold text-[#667085] transition hover:text-black"
    >
      <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="h-4 w-4" />
      Back
    </button>

    {#if loading}
      <div class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
        <div class="h-10 w-64 rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="mt-4 h-4 w-full max-w-2xl rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {#each Array(4) as _}
            <div class="h-[110px] rounded-[8px] border border-[#e8ebf2] bg-white sk-shimmer"></div>
          {/each}
        </div>
      </div>
    {:else if error}
      <div class="rounded-[8px] border border-red-100 bg-red-50 p-5">
        <h3 class="text-[14px] font-semibold text-red-800">Error loading contribution type</h3>
        <p class="mt-1 text-[13px] text-red-700">{error}</p>
      </div>
    {:else if contributionType}
      <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
        <div class="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] {config.iconClass} shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
                <img src={config.icon} alt="" class="h-5 w-5" />
              </div>
              <div class="min-w-0">
                <span
                  class="inline-flex h-[24px] items-center rounded-full px-3 text-[12px] font-semibold"
                  style="background: {config.accent}14; color: {config.accent};"
                >
                  {config.label}
                </span>
              </div>
            </div>

            <h1
              class="mt-4 break-words text-[34px] sm:text-[40px] md:text-[46px] font-semibold font-display text-black leading-none"
              style="letter-spacing: -1px;"
            >
              {contributionType.name}
            </h1>

            {#if contributionType.description}
              <div class="mt-3 max-w-3xl">
                <div
                  bind:this={descriptionEl}
                  class="markdown-content text-[14px] sm:text-[15px] text-[#3f4b5f] leading-relaxed {descriptionExpanded ? '' : 'line-clamp-6'}"
                  style="letter-spacing: 0.2px;"
                >
                  {@html parseMarkdown(contributionType.description)}
                </div>
                {#if descriptionOverflows}
                  <button
                    type="button"
                    class="mt-2 text-[13px] font-medium text-primary-600 hover:text-primary-700 hover:underline"
                    onclick={() => (descriptionExpanded = !descriptionExpanded)}
                  >
                    {descriptionExpanded ? 'Show less' : 'Show more'}
                  </button>
                {/if}
              </div>
            {/if}
          </div>

          {#if contributionType.is_submittable}
            <button
              type="button"
              onclick={() => push(`/submit-contribution?type=${params.id}`)}
              class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[8px] border border-black bg-black px-4 text-[13px] font-semibold text-white shadow-[0_8px_22px_rgba(31,42,68,0.12)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.16)] sm:w-auto"
              style={submitButtonStyle}
            >
              Submit contribution
              <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="h-4 w-4" />
            </button>
          {/if}
        </div>

        <div class="mt-7 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Points</p>
            <p class="mt-2 font-display text-[28px] font-semibold leading-none text-black">{pointsRange}</p>
          </div>
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Contributions</p>
            <p class="mt-2 font-display text-[28px] font-semibold leading-none text-black">{formatNumber(statistics.count)}</p>
          </div>
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Contributors</p>
            <p class="mt-2 font-display text-[28px] font-semibold leading-none text-black">{formatNumber(statistics.participants_count)}</p>
          </div>
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Points Given</p>
            <p class="mt-2 font-display text-[28px] font-semibold leading-none text-black">{formatNumber(statistics.total_points_given)}</p>
          </div>
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Last Contribution</p>
            <p class="mt-2 text-[16px] font-semibold text-black">{statistics.count ? formatDate(statistics.last_earned) : 'Never'}</p>
          </div>
        </div>

        {#if Array.isArray(contributionType.examples) && contributionType.examples.length}
          <div class="mt-7 border-t border-[#e9ecf3] pt-6">
            <h2 class="text-[18px] font-semibold text-black">Ideas</h2>
            <div class="mt-3 flex flex-wrap gap-2">
              {#each contributionType.examples as example}
                <span class="inline-flex min-h-8 items-center rounded-full border border-[#e8ebf2] bg-[#fafafa] px-3 text-[13px] font-medium text-[#506078]">
                  {example}
                </span>
              {/each}
            </div>
          </div>
        {/if}
      </section>

      {#if missions.length > 0}
        <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
          <div class="mb-5 flex items-start gap-3">
            <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] {config.iconClass} shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
              <img src={config.icon} alt="" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
                Missions
              </h2>
              <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
                Time-limited missions for this contribution type.
              </p>
            </div>
          </div>

          <div class="overflow-hidden rounded-[8px] border border-[#e8ebf2] bg-white">
            {#each missions as mission (mission.id)}
              <button
                type="button"
                onclick={() => push(`/mission/${mission.id}`)}
                class="flex w-full items-center justify-between gap-4 border-b border-[#e8ebf2] px-4 py-4 text-left transition last:border-b-0 hover:bg-[#fafafa]"
              >
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-[15px] font-semibold text-black">{mission.name}</span>
                  <span class="mt-1 block text-[12px] text-[#7b8798]">
                    {mission.end_date ? `Ends ${formatDate(mission.end_date)}` : 'Ongoing'}
                  </span>
                </span>
                <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4 flex-shrink-0" />
              </button>
            {/each}
          </div>
        </section>
      {/if}

      <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
        <div class="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
              Highlighted Contributions
            </h2>
            <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
              Curated work for this contribution type.
            </p>
          </div>
        </div>
        <HighlightsSlider
          {highlights}
          loading={false}
          emptyTitle="No highlights yet"
          emptyMessage="Highlighted contributions for this type will appear here."
        />
      </section>

      <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
        <div class="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
              Recent Contributions
            </h2>
            <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
              Latest accepted contributions for this type.
            </p>
          </div>
          <div class="flex items-center gap-2">
            {#if contributions.length > 1}
              <button
                type="button"
                aria-label="Scroll recent contributions left"
                onclick={() => scrollRecent(-1)}
                class="hidden h-11 w-11 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] sm:inline-flex"
              >
                <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="h-5 w-5" />
              </button>
              <button
                type="button"
                aria-label="Scroll recent contributions right"
                onclick={() => scrollRecent(1)}
                class="hidden h-11 w-11 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] sm:inline-flex"
              >
                <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="h-5 w-5" />
              </button>
            {/if}
            <button
              type="button"
              onclick={() => push(allContributionsPath)}
              class="inline-flex h-11 items-center justify-center gap-1.5 rounded-[8px] border border-[#dfe4ee] bg-white px-3 text-[13px] font-semibold text-[#111827] shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)]"
            >
              View all
              <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4" />
            </button>
          </div>
        </div>

        {#if contributions.length === 0}
          <div class="rounded-[8px] border border-dashed border-[#dfe4ee] bg-white/70 p-8 text-center">
            <h3 class="text-[15px] font-semibold text-black">No contributions yet</h3>
            <p class="mt-1 text-[13px] text-[#6b6b6b]">Accepted contributions for this type will appear here.</p>
          </div>
        {:else}
          <div bind:this={recentSlider} class="slider-scroll flex snap-x gap-3 overflow-x-auto pb-2">
            {#each contributions as contribution (contribution.id)}
              <div class="w-[300px] max-w-[82vw] flex-shrink-0 snap-start">
                <PortalContributionCard {contribution} category={category} />
              </div>
            {/each}
          </div>
        {/if}
      </section>
    {:else}
      <div class="rounded-[8px] border border-amber-100 bg-amber-50 p-5 text-amber-800">
        Contribution type not found.
      </div>
    {/if}
  </div>
</div>

<style>
  .slider-scroll {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  .slider-scroll::-webkit-scrollbar {
    display: none;
  }

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

  .markdown-content :global(p) {
    margin: 0 0 0.6em;
  }
  .markdown-content :global(p:last-child) {
    margin-bottom: 0;
  }
  .markdown-content :global(ul) {
    list-style-type: disc;
    margin: 0 0 0.6em 1.25rem;
  }
  .markdown-content :global(ol) {
    list-style-type: decimal;
    margin: 0 0 0.6em 1.25rem;
  }
  .markdown-content :global(a) {
    color: #387de8;
    text-decoration: underline;
  }
  .markdown-content :global(strong) {
    font-weight: 600;
  }
  .markdown-content :global(code) {
    background: #f3f4f6;
    padding: 0 0.25rem;
    border-radius: 3px;
    font-size: 0.9em;
  }
</style>
