<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import { parseMarkdown } from '../lib/markdownLoader.js';
  import PortalContributionCard from '../components/portal/PortalContributionCard.svelte';
  import { getCategoryButtonStyle, getCategoryGradientStyle } from '../lib/categoryPresentation.js';

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

  let mission = $state(null);
  let contributionType = $state(null);
  let stats = $state({ unique_users: 0, contributions_count: 0, points_earned: 0 });
  let contributions = $state(/** @type {any[]} */ ([]));
  let loading = $state(true);
  let error = $state(/** @type {string | null} */ (null));
  let contributionSlider = $state(/** @type {HTMLElement | null} */ (null));

  let category = $derived(contributionType?.category || 'global');
  let config = $derived(categoryConfig[category] || categoryConfig.global);
  let gradientStyle = $derived(getCategoryGradientStyle(category, config.accent));
  let submitButtonStyle = $derived(getCategoryButtonStyle(config.accent));
  let explorerCategory = $derived(category === 'global' ? 'all' : category);
  let allContributionsPath = $derived(
    `/all-contributions?category=${explorerCategory}&mission=${params.id}`
  );
  let missionIsFull = $derived(
    mission?.user_is_full === true ||
      mission?.is_full === true ||
      (mission?.max_submissions != null &&
        mission?.submissions_remaining != null &&
        Number(mission.submissions_remaining) <= 0)
  );
  let contributionTypeIsFull = $derived(
    contributionType?.is_full === true ||
      (contributionType?.max_submissions != null &&
        contributionType?.submissions_remaining != null &&
        Number(contributionType.submissions_remaining) <= 0)
  );
  let submissionClosed = $derived(missionIsFull || contributionTypeIsFull);
  let submitButtonLabel = $derived(
    mission?.user_is_full === true
      ? 'Limit reached'
      : submissionClosed
        ? 'Submissions closed'
        : 'Submit to mission'
  );
  let capacityLabel = $derived.by(() => {
    if (mission?.user_is_full === true) return 'Your limit reached';
    if (mission?.max_submissions == null) {
      return contributionTypeIsFull ? 'Submissions closed' : 'Unlimited';
    }
    if (missionIsFull) return 'Full';
    if (contributionTypeIsFull) return 'Submissions closed';
    return `${formatNumber(mission.submissions_remaining)} left`;
  });

  function formatDate(dateString) {
    if (!dateString) return 'Ongoing';
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch {
      return dateString;
    }
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString();
  }

  // Mission descriptions come from the API; always sanitize before {@html}.
  function renderMarkdown(text) {
    if (!text) return '';
    return parseMarkdown(text);
  }

  function scrollContributions(direction) {
    contributionSlider?.scrollBy({
      left: direction * 320,
      behavior: 'smooth',
    });
  }

  async function loadMissionDetail() {
    try {
      loading = true;
      error = null;

      const [missionRes, statsRes, contributionsRes] = await Promise.all([
        contributionsAPI.getMission(params.id),
        contributionsAPI.getMissionStats(params.id).catch(() => null),
        contributionsAPI.getContributions({
          mission: params.id,
          ordering: '-contribution_date',
          page_size: 20,
        }),
      ]);

      mission = missionRes.data;
      stats = statsRes?.data || { unique_users: 0, contributions_count: 0, points_earned: 0 };
      contributions = contributionsRes.data?.results || [];

      if (mission?.contribution_type) {
        const typeRes = await contributionsAPI.getContributionType(mission.contribution_type);
        contributionType = typeRes.data;
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load mission';
    } finally {
      loading = false;
    }
  }

  onMount(loadMissionDetail);
</script>

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
      <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
        <div class="h-10 w-64 rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="mt-4 h-4 w-full max-w-2xl rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {#each Array(4) as _}
            <div class="h-[110px] rounded-[8px] border border-[#e8ebf2] bg-white sk-shimmer"></div>
          {/each}
        </div>
      </section>
    {:else if error}
      <div class="rounded-[8px] border border-red-100 bg-red-50 p-5">
        <h3 class="text-[14px] font-semibold text-red-800">Error loading mission</h3>
        <p class="mt-1 text-[13px] text-red-700">{error}</p>
      </div>
    {:else if mission}
      <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
        <div class="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-3">
              <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] {config.iconClass} shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
                <img src={config.icon} alt="" class="h-5 w-5" />
              </div>
              <span
                class="inline-flex h-[24px] items-center rounded-full px-3 text-[12px] font-semibold"
                style="background: {config.accent}14; color: {config.accent};"
              >
                Mission
              </span>
              {#if contributionType}
                <button
                  type="button"
                  onclick={() => push(`/contribution-type/${contributionType.id}`)}
                  class="inline-flex h-[24px] max-w-full items-center rounded-full border border-[#e8ebf2] bg-white px-3 text-[12px] font-semibold text-[#506078] transition hover:border-black hover:text-black"
                >
                  <span class="truncate">{contributionType.name}</span>
                </button>
              {/if}
            </div>

            <h1
              class="mt-4 break-words text-[34px] sm:text-[40px] md:text-[46px] font-semibold font-display text-black leading-none"
              style="letter-spacing: -1px;"
            >
              {mission.name}
            </h1>
          </div>

          <button
            type="button"
            onclick={() => !submissionClosed && push(`/submit-contribution?mission=${mission.id}`)}
            disabled={submissionClosed}
            class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[8px] border border-black bg-black px-4 text-[13px] font-semibold text-white shadow-[0_8px_22px_rgba(31,42,68,0.12)] transition sm:w-auto {submissionClosed ? 'cursor-not-allowed opacity-60' : 'hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.16)]'}"
            style={submissionClosed ? '' : submitButtonStyle}
          >
            {submitButtonLabel}
            {#if !submissionClosed}
              <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="h-4 w-4" />
            {/if}
          </button>
        </div>

        <div class="mt-7 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Unique Users</p>
            <p class="mt-2 font-display text-[28px] font-semibold leading-none text-black">{formatNumber(stats.unique_users)}</p>
          </div>
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Contributions</p>
            <p class="mt-2 font-display text-[28px] font-semibold leading-none text-black">{formatNumber(stats.contributions_count)}</p>
          </div>
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Points Earned</p>
            <p class="mt-2 font-display text-[28px] font-semibold leading-none text-black">{formatNumber(stats.points_earned)}</p>
          </div>
          <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            <p class="text-[12px] font-semibold uppercase text-[#7b8798]">Capacity</p>
            <p class="mt-2 text-[16px] font-semibold text-black">
              {capacityLabel}
            </p>
          </div>
        </div>
      </section>

      <section class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <aside class="space-y-3 lg:order-2">
          <div class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md">
            <h2 class="text-[16px] font-semibold text-black">Mission Info</h2>
            <div class="mt-4 space-y-3">
              <div class="flex items-center justify-between gap-4">
                <span class="text-[12px] font-semibold uppercase text-[#7b8798]">Status</span>
                <span class="text-[13px] font-semibold text-black">{mission.is_active ? 'Active' : 'Inactive'}</span>
              </div>
              <div class="flex items-center justify-between gap-4">
                <span class="text-[12px] font-semibold uppercase text-[#7b8798]">Start</span>
                <span class="text-[13px] font-semibold text-black">{mission.start_date ? formatDate(mission.start_date) : 'Anytime'}</span>
              </div>
              <div class="flex items-center justify-between gap-4">
                <span class="text-[12px] font-semibold uppercase text-[#7b8798]">End</span>
                <span class="text-[13px] font-semibold text-black">{formatDate(mission.end_date)}</span>
              </div>
              <div class="flex items-center justify-between gap-4">
                <span class="text-[12px] font-semibold uppercase text-[#7b8798]">Submissions</span>
                <span class="text-[13px] font-semibold text-black">
                  {mission.max_submissions == null
                    ? `${formatNumber(mission.submission_count)} / Unlimited`
                    : `${formatNumber(mission.submission_count)} / ${formatNumber(mission.max_submissions)}`}
                </span>
              </div>
            </div>
          </div>
        </aside>

        <article class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8 lg:order-1">
          <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
            Details
          </h2>
          <div class="mission-body mt-5 text-[#3f4b5f]">
            {@html renderMarkdown(mission.description)}
          </div>
        </article>

      </section>

      <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
        <div class="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
              Mission Contributions
            </h2>
            <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
              Accepted contributions submitted for this mission.
            </p>
          </div>
          <div class="flex items-center gap-2">
            {#if contributions.length > 1}
              <button
                type="button"
                aria-label="Scroll mission contributions left"
                onclick={() => scrollContributions(-1)}
                class="hidden h-11 w-11 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] sm:inline-flex"
              >
                <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="h-5 w-5" />
              </button>
              <button
                type="button"
                aria-label="Scroll mission contributions right"
                onclick={() => scrollContributions(1)}
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
            <p class="mt-1 text-[13px] text-[#6b6b6b]">Accepted mission contributions will appear here.</p>
          </div>
        {:else}
          <div bind:this={contributionSlider} class="slider-scroll flex snap-x gap-3 overflow-x-auto pb-2">
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
        Mission not found.
      </div>
    {/if}
  </div>
</div>

<style>
  .mission-body :global(p) {
    margin-bottom: 16px;
    font-size: 15px;
    line-height: 1.7;
  }

  .mission-body :global(p:last-child) {
    margin-bottom: 0;
  }

  .mission-body :global(ul),
  .mission-body :global(ol) {
    margin-bottom: 16px;
    padding-left: 20px;
  }

  .mission-body :global(li) {
    margin-bottom: 8px;
    line-height: 1.6;
  }

  .mission-body :global(a) {
    color: #4f76f6;
    text-decoration: underline;
  }

  .mission-body :global(strong) {
    color: black;
    font-weight: 600;
  }

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
</style>
