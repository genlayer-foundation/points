<script>
  import { contributionsAPI, statsAPI, leaderboardAPI, validatorsAPI, buildersAPI } from '../lib/api';
  import { visibleContributions } from '../lib/hiddenContributions.js';
  import { hasReadOnlyRoleSectionAccess } from '../lib/roleState.js';
  import { userStore } from '../lib/userStore.js';
  import { currentCategory } from '../stores/category.js';

  // Generic UI components
  import SectionHeader from '../components/ui/SectionHeader.svelte';
  import StatCardRow from '../components/ui/StatCardRow.svelte';
  import RankedList from '../components/ui/RankedList.svelte';
  import UserCardScroller from '../components/ui/UserCardScroller.svelte';
  import PortalHighlights from '../components/portal/PortalHighlights.svelte';
  import PortalContributionCard from '../components/portal/PortalContributionCard.svelte';
  import CTASection from '../components/ui/CTASection.svelte';
  import Podium from '../components/ui/Podium.svelte';

  // Portal components (self-fetching)
  import HeroBanner from '../components/portal/HeroBanner.svelte';
  import FeaturedBuilds from '../components/portal/FeaturedBuilds.svelte';

  // State
  let statsData = $state([]);
  let leaderboardEntries = $state([]);
  let communityPodiumEntries = $state([]);
  let newestMembers = $state([]);
  let trendingEntries = $state([]);
  let recentContributions = $state([]);

  let statsLoading = $state(true);
  let leaderboardLoading = $state(true);
  let communityPodiumLoading = $state(true);
  let membersLoading = $state(true);
  let trendingLoading = $state(true);
  let recentLoading = $state(true);
  let recentSlider = $state(null);
  let canRecentLeft = $state(false);
  let canRecentRight = $state(false);
  let dashboardRequestSequence = 0;
  let activeLoadedCategory = $state(null);

  const COMMUNITY_SOCIAL_LINK_SLUGS = new Set(['community-link-x', 'community-link-discord']);

  let category = $derived($currentCategory);
  let isBuilder = $derived(category === 'builder');
  let isValidator = $derived(category === 'validator');
  let isCommunity = $derived(category === 'community');
  let isRoleSectionReadOnly = $derived(
    hasReadOnlyRoleSectionAccess($userStore.user, category)
  );
  let accentColor = $derived(isBuilder ? '#ee8521' : isCommunity ? '#7f52e1' : '#4f76f6');
  let valueLabel = $derived(isBuilder ? 'BP' : isCommunity ? 'CP' : 'VP');
  let dashboardTitle = $derived(
    isBuilder ? "Builder's Live Dashboard" : isCommunity ? "Community Live Dashboard" : "Validator's Live Dashboard"
  );
  let leaderboardTitle = $derived(isCommunity ? 'Top Community Contributors' : 'Top Contributors');
  let leaderboardSubtitle = $derived(
    isCommunity
      ? 'All-time XP and Community points'
      : isValidator
        ? 'All-time validator contributors'
        : 'Curated builds from the last 30 days'
  );
  let leaderboardPath = $derived(isBuilder ? '/builders/leaderboard' : isCommunity ? '/community/leaderboard' : '/validators/leaderboard');
  let podiumTitle = $derived(
    isCommunity ? 'Accepted Submissions Podium' : isValidator ? 'All-time Podium' : 'Last 30 Days Podium'
  );
  let podiumSubtitle = $derived(
    isCommunity
      ? 'Top Community contributors by points from accepted submissions'
      : isValidator
        ? "Who's contributed most to GenLayer?"
        : "Who's contributing more to GenLayer over the last 30 days?"
  );
  let podiumEntries = $derived(
    isCommunity ? communityPodiumEntries : leaderboardEntries.slice(0, 3)
  );
  let podiumLoading = $derived(
    isCommunity ? communityPodiumLoading : leaderboardLoading
  );
  let newestTitle = $derived(isBuilder ? 'Newest Builders' : isCommunity ? 'Newest Community Contributors' : 'Newest Validators');
  let newestPath = $derived(isBuilder ? '/builders/leaderboard' : isCommunity ? '/community/all-contributions' : '/validators/participants');
  let highlightsPath = $derived(
    isBuilder ? '/builders/all-contributions?view=highlights' : isCommunity ? '/community/all-contributions?view=highlights' : '/validators/all-contributions?view=highlights'
  );

  // Map newest members data to UserCardScroller entry format
  let newestAsEntries = $derived(newestMembers.map(m => ({
    // user_id is the profile link key: API addresses are truncated.
    user_id: m.user_details?.id ?? m.user_id ?? m.id,
    user_name: m.name || m.user_name || m.user_details?.name,
    user_address: m.address || m.user_address || m.user_details?.address,
    profile_image_url: m.profile_image_url || m.user_details?.profile_image_url,
    total_points: m.total_points || m.community_points || m.frozen_global_points || m.points || 0,
    builder: m.builder ?? m.user_details?.builder ?? false,
    validator: m.validator ?? m.user_details?.validator ?? false,
    steward: m.steward ?? m.user_details?.steward ?? false,
  })));

  // Map API stats response to StatCardRow format
  function mapStats(data, cat) {
    if (!data) return [];
    if (cat === 'builder') {
      return [
        { value: data.builder_count ?? data.participant_count, label: 'Builders', delta: data.new_builders_count || '', category: 'builder' },
        { value: data.total_points, label: 'Total points earned', delta: data.new_points_count || '', iconSrc: '/assets/icons/gradient-icon-points.svg' },
        { value: data.contribution_count, label: 'Total Contributions', delta: data.new_contributions_count || '', iconSrc: '/assets/icons/gradient-icon-contributions.svg' },
      ];
    }
    if (cat === 'community') {
      return [
        { value: data.community_member_count ?? data.creator_count ?? data.participant_count, label: 'Creators', delta: data.new_community_members_count || '', category: 'community' },
        { value: data.total_points, label: 'Community points earned', delta: data.new_points_count || '', category: 'genlayer', hexCategory: 'community' },
        { value: data.contribution_count, label: 'Community Contributions', delta: data.new_contributions_count || '', category: 'community' },
      ];
    }
    // validator
    return [
      { value: data.validator_count ?? data.participant_count, label: 'Validators', delta: data.new_validators_count || '', category: 'validator' },
      { value: data.total_points, label: 'Total points earned', delta: data.new_points_count || '', iconSrc: '/assets/icons/gradient-icon-points-blue.svg' },
      { value: data.contribution_count, label: 'Total Contributions', delta: data.new_contributions_count || '', iconSrc: '/assets/icons/gradient-icon-contributions-blue.svg' },
    ];
  }

  function getContributionTypeSlug(contribution) {
    return contribution?.contribution_type_details?.slug || contribution?.contribution_type_slug || contribution?.contribution_type?.slug || '';
  }

  function isCommunitySocialLinkContribution(contribution) {
    return COMMUNITY_SOCIAL_LINK_SLUGS.has(getContributionTypeSlug(contribution));
  }

  function filterRecentContributions(contributions, cat) {
    const visible = visibleContributions(contributions);
    if (cat !== 'community') return visible;
    return visible.filter((contribution) => !isCommunitySocialLinkContribution(contribution));
  }

  function formatDateParam(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function getLast30DaysParams() {
    const endDate = new Date();
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - 29);

    return {
      start_date: formatDateParam(startDate),
      end_date: formatDateParam(endDate),
    };
  }

  function resetDashboardState() {
    statsData = [];
    leaderboardEntries = [];
    communityPodiumEntries = [];
    newestMembers = [];
    trendingEntries = [];
    recentContributions = [];
    statsLoading = true;
    leaderboardLoading = true;
    communityPodiumLoading = true;
    membersLoading = true;
    trendingLoading = true;
    recentLoading = true;
    canRecentLeft = false;
    canRecentRight = false;
  }

  async function fetchDashboardData(cat) {
    const requestId = ++dashboardRequestSequence;
    resetDashboardState();

    // All fetches in parallel
    const promises = [
      // Stats
      statsAPI.getDashboardStats(cat).then(res => {
        if (requestId !== dashboardRequestSequence) return;
        statsData = mapStats(res.data, cat);
        statsLoading = false;
      }).catch(() => {
        if (requestId === dashboardRequestSequence) statsLoading = false;
      }),

      // Top contributors. Community and Validator use their all-time
      // leaderboards; Builder keeps its rolling 30-day view.
      (cat === 'builder'
          ? leaderboardAPI.getMonthlyLeaderboardByType(cat, 5, getLast30DaysParams())
          : leaderboardAPI.getLeaderboard({ type: cat, order: 'asc', limit: 5 })
      ).then(res => {
        if (requestId !== dashboardRequestSequence) return;
        leaderboardEntries = Array.isArray(res.data) ? res.data : (res.data?.results ?? []);
        leaderboardLoading = false;
      }).catch(() => {
        if (requestId === dashboardRequestSequence) leaderboardLoading = false;
      }),

    ];

    if (cat === 'community') {
      promises.push(
        leaderboardAPI.getCommunityPodium().then(res => {
          if (requestId !== dashboardRequestSequence) return;
          communityPodiumEntries = Array.isArray(res.data) ? res.data : (res.data?.results ?? []);
          communityPodiumLoading = false;
        }).catch(() => {
          if (requestId === dashboardRequestSequence) communityPodiumLoading = false;
        })
      );
    } else {
      communityPodiumLoading = false;
    }

    if (cat === 'community') {
      promises.push(
        contributionsAPI.getContributions({ limit: 20, category: cat, exclude_onboarding: 'true' }).then(res => {
          if (requestId !== dashboardRequestSequence) return;
          const contributions = filterRecentContributions(res.data?.results ?? res.data ?? [], cat);
          recentContributions = contributions.slice(0, 5);

          const seen = new Set();
          newestMembers = contributions.filter((contrib) => {
            const address = contrib.user_details?.address || contrib.user_address || contrib.address;
            if (!address || seen.has(address)) return false;
            seen.add(address);
            return true;
          }).slice(0, 10);

          membersLoading = false;
          recentLoading = false;
        }).catch(() => {
          if (requestId === dashboardRequestSequence) {
            membersLoading = false;
            recentLoading = false;
          }
        })
      );
    } else {
      promises.push(
        (cat === 'builder'
          ? buildersAPI.getNewestBuilders(10)
          : validatorsAPI.getNewestValidators(10)
        ).then(res => {
          if (requestId !== dashboardRequestSequence) return;
          newestMembers = res.data?.results ?? res.data ?? [];
          membersLoading = false;
        }).catch(() => {
          if (requestId === dashboardRequestSequence) membersLoading = false;
        })
      );
    }

    // Builder-only fetches
    if (cat === 'builder') {
      promises.push(
        leaderboardAPI.getTrending(10, { category: cat }).then(res => {
          if (requestId !== dashboardRequestSequence) return;
          trendingEntries = res.data || [];
          trendingLoading = false;
        }).catch(() => {
          if (requestId === dashboardRequestSequence) trendingLoading = false;
        })
      );
    }

    await Promise.allSettled(promises);
  }

  $effect(() => {
    const cat = $currentCategory;
    if (!cat || cat === activeLoadedCategory) return;
    activeLoadedCategory = cat;
    fetchDashboardData(cat);
  });

  function updateRecentArrows() {
    if (!recentSlider) return;
    const { scrollLeft, scrollWidth, clientWidth } = recentSlider;
    canRecentLeft = scrollLeft > 4;
    canRecentRight = scrollLeft + clientWidth < scrollWidth - 4;
  }

  function scrollRecent(direction) {
    if (!recentSlider) return;
    recentSlider.scrollBy({
      left: direction * Math.round(recentSlider.clientWidth * 0.8),
      behavior: 'smooth',
    });
  }

  $effect(() => {
    if (!recentSlider) return;
    void recentContributions.length;
    requestAnimationFrame(updateRecentArrows);
  });
</script>

<div class="dashboard-page max-w-full overflow-x-hidden space-y-8">
  {#if isRoleSectionReadOnly}
    <div class="flex justify-end">
      <span class="inline-flex min-h-7 items-center rounded-full border border-[#cdddf8] bg-[#edf4ff] px-3 text-[11px] font-semibold text-[#245ca8]">
        View-only access
      </span>
    </div>
  {/if}

  <!-- 1. Hero Banner -->
  <HeroBanner category={category} compact={true} />

  <!-- 2. Live Dashboard Stats -->
  <div class="min-w-0">
    <SectionHeader
      title={dashboardTitle}
      subtitle=""
      showLink={false}
    />
    <StatCardRow stats={statsData} loading={statsLoading} columns={3} />
  </div>

  <!-- 3. Two-column: Top Contributors + Chart Placeholder -->
  <div class="grid min-w-0 grid-cols-1 gap-6 lg:grid-cols-2">
    <div class="min-w-0">
      <SectionHeader
        title={leaderboardTitle}
        subtitle={leaderboardSubtitle}
        linkText="View all"
        linkPath={leaderboardPath}
      />
      <RankedList
        entries={leaderboardEntries}
        loading={leaderboardLoading}
        accentColor={accentColor}
        valueLabel={valueLabel}
      />
    </div>
    <div class="min-w-0">
      <SectionHeader
        title={podiumTitle}
        subtitle={podiumSubtitle}
        showLink={false}
      />
      <Podium
        entries={podiumEntries}
        loading={podiumLoading}
        accentColor={accentColor}
        valueLabel={valueLabel}
        category={category}
      />
    </div>
  </div>

  <!-- 4. Newest Members -->
  <div class="min-w-0">
      <SectionHeader
        title={newestTitle}
        subtitle="New"
        linkText="View all"
        linkPath={newestPath}
        requiresAuth={isCommunity}
      />
    <UserCardScroller entries={newestAsEntries} loading={membersLoading} />
  </div>

  <!-- 5. Builder-only: Featured Builds -->
  {#if isBuilder}
    <FeaturedBuilds />
  {/if}

  <!-- 6. Builder-only: Trending Contributors -->
  {#if isBuilder}
    <div class="min-w-0">
      <SectionHeader
        title="Trending Contributors"
        subtitle="Highest Builder Points Contributions this week"
        linkText="View all"
        linkPath="/builders/leaderboard"
      />
      <UserCardScroller entries={trendingEntries} loading={trendingLoading} showPointIncrease={true} />
    </div>
  {/if}

  <!-- 7. Highlighted Contributions -->
  <div class="min-w-0">
    <SectionHeader
      title="Highlighted Contributions"
      subtitle="Latest standout contributions"
      linkText="Explore all"
      linkPath={highlightsPath}
      requiresAuth={true}
    />
    <PortalHighlights
      category={category}
      limit={10}
      showHeader={false}
    />
  </div>

  <!-- 8. Community Recent Contributions -->
  {#if isCommunity}
    <div class="grid min-w-0 grid-cols-1 gap-6">
      <div class="min-w-0">
        <SectionHeader
          title="Recent Community Contributions"
          subtitle="Latest accepted community work"
          linkText="View all"
          linkPath="/community/all-contributions"
          requiresAuth={true}
        />
        <div class="relative min-w-0 overflow-hidden">
          {#if recentLoading}
            <div class="flex max-w-full gap-3 overflow-hidden pb-2">
              {#each [1, 2, 3, 4, 5] as _}
                <div class="h-[180px] w-[300px] max-w-[82vw] flex-shrink-0 rounded-[8px] border border-[#f0f0f0] bg-white p-4 animate-pulse">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <div class="w-6 h-6 rounded-full bg-gray-200"></div>
                      <div class="h-3 w-20 rounded bg-gray-200"></div>
                    </div>
                    <div class="h-5 w-14 rounded-full bg-gray-100"></div>
                  </div>
                  <div class="mt-5 space-y-2">
                    <div class="h-3 w-3/4 rounded bg-gray-200"></div>
                    <div class="h-2.5 w-full rounded bg-gray-100"></div>
                    <div class="h-2.5 w-5/6 rounded bg-gray-100"></div>
                  </div>
                  <div class="mt-8 flex items-center justify-between">
                    <div class="h-5 w-24 rounded-full bg-gray-100"></div>
                    <div class="h-3 w-16 rounded bg-gray-100"></div>
                  </div>
                </div>
              {/each}
            </div>
          {:else if recentContributions.length === 0}
            <div class="rounded-[8px] border border-dashed border-[#e6e6e6] bg-[#fafafa] px-6 py-10 text-center text-sm text-[#6b6b6b]">
              No recent contributions
            </div>
          {:else}
            <div
              bind:this={recentSlider}
              onscroll={updateRecentArrows}
              class="hide-scrollbar flex max-w-full gap-3 overflow-x-auto px-1 pb-2 scroll-smooth"
            >
              {#each recentContributions as contribution (contribution.id)}
                <div class="w-[300px] max-w-[82vw] flex-shrink-0">
                  <PortalContributionCard
                    {contribution}
                    category="community"
                    pathPrefix="/community/contribution"
                  />
                </div>
              {/each}
            </div>
            {#if canRecentLeft}
              <button
                type="button"
                onclick={() => scrollRecent(-1)}
                aria-label="Scroll recent contributions left"
                class="absolute left-2 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-[#e6e6e6] bg-white shadow-md transition-all hover:bg-[#fafafa] hover:shadow-lg sm:flex"
              >
                <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="h-5 w-5" />
              </button>
            {/if}
            {#if canRecentRight}
              <button
                type="button"
                onclick={() => scrollRecent(1)}
                aria-label="Scroll recent contributions right"
                class="absolute right-2 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-[#e6e6e6] bg-white shadow-md transition-all hover:bg-[#fafafa] hover:shadow-lg sm:flex"
              >
                <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="h-5 w-5" />
              </button>
            {/if}
          {/if}
        </div>
      </div>
    </div>
  {/if}

  {#if !isRoleSectionReadOnly}
    <!-- 9. CTA Section with gradient background -->
    <div class="relative -mt-8 overflow-hidden pt-8">
      <!-- Gradient background — extends beyond container to cover main padding -->
      <div
        class="absolute -bottom-3 inset-x-0 top-0 pointer-events-none"
        style="background: {isBuilder
          ? 'radial-gradient(ellipse 80% 60% at 0% 100%, rgba(233, 147, 34, 0.25) 0%, transparent 70%), radial-gradient(ellipse 80% 60% at 100% 100%, rgba(233, 147, 34, 0.25) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 50% 0%, rgba(248, 185, 61, 0.12) 0%, transparent 60%)'
          : isCommunity
            ? 'radial-gradient(ellipse 80% 60% at 0% 100%, rgba(127, 82, 225, 0.20) 0%, transparent 70%), radial-gradient(ellipse 80% 60% at 100% 100%, rgba(127, 82, 225, 0.20) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 50% 0%, rgba(170, 141, 255, 0.12) 0%, transparent 60%)'
            : 'radial-gradient(ellipse 80% 60% at 0% 100%, rgba(56, 125, 232, 0.20) 0%, transparent 70%), radial-gradient(ellipse 80% 60% at 100% 100%, rgba(56, 125, 232, 0.20) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 50% 0%, rgba(109, 167, 243, 0.12) 0%, transparent 60%)'
        };"
      ></div>
      <!-- White fade at top for smooth transition -->
      <div
        class="absolute inset-x-0 top-0 h-40 pointer-events-none z-[1]"
        style="background: linear-gradient(to bottom, white 0%, transparent 100%);"
      ></div>
      {#if isBuilder}
        <CTASection
          title="Start building today"
          description="Join professional validators and builders in testing the trust infrastructure for the AI age."
          primaryButtonText="Become a builder"
          primaryButtonPath="/submit-contribution"
          secondaryLinkText="Visit the Studio"
          secondaryLinkPath="https://studio.genlayer.com"
          secondaryLinkExternal={true}
        />
      {:else if isCommunity}
        <CTASection
          title="Contribute to the community"
          description="Create content, share knowledge, and help more people understand GenLayer."
          primaryButtonText="Submit Contribution"
          primaryButtonPath="/submit-contribution"
          secondaryLinkText="Browse Contributions"
          secondaryLinkPath="/community/all-contributions"
        />
      {:else}
        <CTASection
          title="Become a Validator"
          description="Join professional validators and builders in testing the trust infrastructure for the AI age."
          primaryButtonText="Join the Waitlist"
          primaryButtonPath="/validators/waitlist/join"
          secondaryLinkText="Read the Docs"
          secondaryLinkPath="https://docs.genlayer.com"
          secondaryLinkExternal={true}
        />
      {/if}
    </div>
  {/if}
</div>

<style>
  @media (max-width: 767px) {
    .dashboard-page {
      padding-inline: 4px;
      padding-top: 10px;
    }
  }

  .hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
</style>
