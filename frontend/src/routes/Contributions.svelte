<script>
  import ContributionTypeStats from '../components/ContributionTypeStats.svelte';
  import Missions from '../components/Missions.svelte';
  import StartupRequests from '../components/StartupRequests.svelte';
  import PortalContributionCard from '../components/portal/PortalContributionCard.svelte';
  import SocialTasksSection from '../components/social-tasks/SocialTasksSection.svelte';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { push } from 'svelte-spa-router';
  import { getCategoryButtonStyle, getCategoryGradientStyle } from '../lib/categoryPresentation.js';

  const RECENT_LIMIT = 5;
  const COMMUNITY_SOCIAL_LINK_SLUGS = new Set(['community-link-x', 'community-link-discord']);

  /** @type {Record<string, { title: string, recentTitle: string, description: string, icon: string, iconClass: string, accentColor: string }>} */
  const categoryConfig = {
    global: {
      title: 'Contributions',
      recentTitle: 'Recent Contributions',
      description: 'Open calls, missions, and recent work from across the GenLayer ecosystem.',
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-black',
      accentColor: '#7f52e1',
    },
    builder: {
      title: 'Builder Contributions',
      recentTitle: 'Recent Builder Contributions',
      description: 'Build, ship, and document high-signal work for the GenLayer ecosystem.',
      icon: '/assets/icons/terminal-fill-white.svg',
      iconClass: 'bg-orange-500',
      accentColor: '#ee8521',
    },
    validator: {
      title: 'Validator Contributions',
      recentTitle: 'Recent Validator Contributions',
      description: 'Support the network with validator operations, testing, and ecosystem reliability.',
      icon: '/assets/icons/shield-white.svg',
      iconClass: 'bg-gradient-to-br from-[#8f7bff] to-[#6f8cff]',
      accentColor: '#387de8',
    },
    community: {
      title: 'Community Contributions',
      recentTitle: 'Recent Community Contributions',
      description: 'Create, teach, gather feedback, and help the community understand GenLayer.',
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-[#7f52e1]',
      accentColor: '#7f52e1',
    },
    steward: {
      title: 'Steward Contributions',
      recentTitle: 'Recent Steward Contributions',
      description: 'Recognize, curate, and sustain high-quality ecosystem participation.',
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-emerald-500',
      accentColor: '#3eb359',
    },
  };

  let recentContributions = $state(/** @type {any[]} */ ([]));
  let recentLoading = $state(true);
  let recentError = $state(/** @type {string | null} */ (null));
  let recentRequestSequence = 0;
  let recentSlider = $state(/** @type {HTMLElement | null} */ (null));

  let activeCategory = $derived($currentCategory || 'global');
  let pageConfig = $derived(categoryConfig[activeCategory] || categoryConfig.global);
  let gradientStyle = $derived(getCategoryGradientStyle(activeCategory, pageConfig.accentColor));
  let pageGradientStyle = $derived(
    gradientStyle || getCategoryGradientStyle('community', categoryConfig.community.accentColor)
  );
  let submitButtonStyle = $derived(getCategoryButtonStyle(pageConfig.accentColor));
  let viewAllUrl = $derived(
    activeCategory === 'global' ? '/all-contributions' : `/all-contributions?category=${activeCategory}`
  );
  let recentCardCategory = $derived(activeCategory === 'global' ? null : activeCategory);

  function getContributionTypeSlug(contribution) {
    return contribution?.contribution_type_details?.slug || contribution?.contribution_type_slug || contribution?.contribution_type?.slug || '';
  }

  function isCommunitySocialLinkContribution(contribution) {
    return COMMUNITY_SOCIAL_LINK_SLUGS.has(getContributionTypeSlug(contribution));
  }

  function filterRecentContributions(contributions, category) {
    if (category !== 'community') return contributions;
    return contributions.filter((contribution) => !isCommunitySocialLinkContribution(contribution));
  }

  /**
   * @param {string} category
   */
  async function fetchRecentContributions(category) {
    const requestId = ++recentRequestSequence;

    try {
      recentLoading = true;
      recentError = null;

      /** @type {Record<string, string | number>} */
      const params = {
        limit: category === 'community' ? RECENT_LIMIT * 4 : RECENT_LIMIT,
        ordering: '-created_at',
      };

      if (category !== 'global') {
        params.category = category;
      }

      if (category === 'community') {
        params.exclude_onboarding = 'true';
      }

      const response = await contributionsAPI.getContributions(params);
      if (requestId !== recentRequestSequence) return;
      recentContributions = filterRecentContributions(response.data?.results || [], category).slice(0, RECENT_LIMIT);
    } catch (err) {
      if (requestId !== recentRequestSequence) return;
      recentError = err instanceof Error ? err.message : 'Failed to load recent contributions';
      recentContributions = [];
    } finally {
      if (requestId === recentRequestSequence) {
        recentLoading = false;
      }
    }
  }

  $effect(() => {
    fetchRecentContributions(activeCategory);
  });

  /**
   * @param {-1 | 1} direction
   */
  function scrollRecent(direction) {
    recentSlider?.scrollBy({
      left: direction * 320,
      behavior: 'smooth',
    });
  }
</script>

{#snippet contributionSkeleton()}
  <div class="rounded-[8px] bg-white border border-[#f0f0f0] p-4 flex h-[180px] flex-col gap-2 overflow-hidden">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="h-6 w-6 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
        <div class="h-3 w-20 rounded bg-[#f1f1f1] sk-shimmer"></div>
      </div>
      <div class="h-4 w-12 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
    </div>
    <div class="flex flex-1 flex-col gap-1.5 pt-1">
      <div class="h-3 w-2/3 rounded bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-2.5 w-full rounded bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-2.5 w-5/6 rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
    <div class="flex items-center justify-between">
      <div class="h-4 w-20 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-3 w-14 rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
  </div>
{/snippet}

<div class="relative -mx-3 -my-3 overflow-hidden bg-white px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[320px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0" style={pageGradientStyle}></div>
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

      <button
        type="button"
        onclick={() => push('/submit-contribution')}
        class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[8px] border border-black bg-black px-4 text-[13px] font-semibold text-white shadow-[0_8px_22px_rgba(31,42,68,0.12)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.16)] sm:w-auto"
        style={submitButtonStyle}
      >
        Submit contribution
        <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="h-4 w-4" />
      </button>
    </header>

    {#if activeCategory === 'builder'}
      <StartupRequests />
    {/if}

    <SocialTasksSection />

    <Missions />

    <ContributionTypeStats />

    <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
      <div class="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="flex items-start gap-3">
          <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] {pageConfig.iconClass} shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
            <img src={pageConfig.icon} alt="" class="h-5 w-5" />
          </div>
          <div>
            <div class="flex flex-wrap items-center gap-3">
              <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
                {pageConfig.recentTitle}
              </h2>
              {#if !recentLoading && !recentError}
                <span class="inline-flex h-[25px] items-center rounded-full border border-[#e8ebf2] bg-white px-3 text-[12px] font-semibold text-[#506078]">
                  {recentContributions.length} latest
                </span>
              {/if}
            </div>
            <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
              Latest accepted contributions for the selected category.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          {#if !recentLoading && !recentError && recentContributions.length > 1}
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
            onclick={() => push(viewAllUrl)}
            class="inline-flex h-11 items-center justify-center gap-1.5 rounded-[8px] border border-[#dfe4ee] bg-white px-3 text-[13px] font-semibold text-[#111827] shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)]"
          >
            View all
            <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4" />
          </button>
        </div>
      </div>

      {#if recentLoading}
        <div class="slider-scroll flex gap-3 overflow-x-auto pb-2">
          {#each Array(RECENT_LIMIT) as _}
            <div class="w-[300px] flex-shrink-0">
              {@render contributionSkeleton()}
            </div>
          {/each}
        </div>
      {:else if recentError}
        <div class="rounded-[8px] border border-red-100 bg-red-50 p-5">
          <h3 class="text-[14px] font-semibold text-red-800">Error loading contributions</h3>
          <p class="mt-1 text-[13px] text-red-700">{recentError}</p>
        </div>
      {:else if recentContributions.length === 0}
        <div class="rounded-[8px] border border-dashed border-[#dfe4ee] bg-white/70 p-8 text-center">
          <h3 class="text-[15px] font-semibold text-black">No contributions yet</h3>
          <p class="mt-1 text-[13px] text-[#6b6b6b]">Submitted work will appear here once it is accepted.</p>
        </div>
      {:else}
        <div
          bind:this={recentSlider}
          class="slider-scroll flex snap-x gap-3 overflow-x-auto pb-2"
        >
          {#each recentContributions as contribution (contribution.id)}
            <div class="w-[300px] max-w-[82vw] flex-shrink-0 snap-start">
              <PortalContributionCard {contribution} category={recentCardCategory} />
            </div>
          {/each}
        </div>
      {/if}
    </section>
  </div>
</div>

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

  .slider-scroll {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  .slider-scroll::-webkit-scrollbar {
    display: none;
  }
</style>
