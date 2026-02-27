<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI, statsAPI, leaderboardAPI, validatorsAPI, buildersAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';

  // Generic UI components
  import SectionHeader from '../components/ui/SectionHeader.svelte';
  import StatCardRow from '../components/ui/StatCardRow.svelte';
  import RankedList from '../components/ui/RankedList.svelte';
  import UserCardScroller from '../components/ui/UserCardScroller.svelte';
  import HighlightCards from '../components/ui/HighlightCards.svelte';
  import CTASection from '../components/ui/CTASection.svelte';
  import ChartPlaceholder from '../components/ui/ChartPlaceholder.svelte';

  // Portal components (self-fetching)
  import HeroBanner from '../components/portal/HeroBanner.svelte';
  import FeaturedBuilds from '../components/portal/FeaturedBuilds.svelte';

  // State
  let statsData = $state([]);
  let leaderboardEntries = $state([]);
  let newestMembers = $state([]);
  let highlights = $state([]);
  let waitlistEntries = $state([]);
  let trendingEntries = $state([]);
  let recentContributions = $state([]);

  let statsLoading = $state(true);
  let leaderboardLoading = $state(true);
  let membersLoading = $state(true);
  let highlightsLoading = $state(true);
  let waitlistLoading = $state(true);
  let trendingLoading = $state(true);
  let recentLoading = $state(true);

  let category = $derived($currentCategory);
  let isBuilder = $derived(category === 'builder');
  let isValidator = $derived(category === 'validator');

  // Map newest members data to UserCardScroller entry format
  let newestAsEntries = $derived(newestMembers.map(m => ({
    user_name: m.name || m.user_name,
    user_address: m.address || m.user_address,
    profile_image_url: m.profile_image_url,
    total_points: m.total_points || 0,
    builder: m.builder ?? false,
    validator: m.validator ?? false,
    steward: m.steward ?? false,
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
    // validator
    return [
      { value: data.validator_count ?? data.participant_count, label: 'Validators', delta: data.new_validators_count || '', category: 'validator' },
      { value: data.total_points, label: 'Total points earned', delta: data.new_points_count || '', iconSrc: '/assets/icons/gradient-icon-points.svg' },
      { value: data.contribution_count, label: 'Total Contributions', delta: data.new_contributions_count || '', iconSrc: '/assets/icons/gradient-icon-contributions.svg' },
    ];
  }

  onMount(async () => {
    const cat = $currentCategory;

    // All fetches in parallel
    const promises = [
      // Stats
      statsAPI.getDashboardStats(cat).then(res => {
        statsData = mapStats(res.data, cat);
        statsLoading = false;
      }).catch(() => { statsLoading = false; }),

      // Leaderboard top 5
      leaderboardAPI.getLeaderboardByType(cat, 'asc', { limit: 5 }).then(res => {
        leaderboardEntries = Array.isArray(res.data) ? res.data : (res.data?.results ?? []);
        leaderboardLoading = false;
      }).catch(() => { leaderboardLoading = false; }),

      // Newest members
      (cat === 'builder'
        ? buildersAPI.getNewestBuilders(5)
        : validatorsAPI.getNewestValidators(5)
      ).then(res => {
        newestMembers = res.data?.results ?? res.data ?? [];
        membersLoading = false;
      }).catch(() => { membersLoading = false; }),

      // Highlights
      contributionsAPI.getAllHighlights({ limit: 3, category: cat }).then(res => {
        highlights = res.data || [];
        highlightsLoading = false;
      }).catch(() => { highlightsLoading = false; }),
    ];

    // Validator-only fetches
    if (cat === 'validator') {
      promises.push(
        leaderboardAPI.getWaitlistTop(5).then(res => {
          waitlistEntries = Array.isArray(res.data) ? res.data : (res.data?.results ?? []);
          waitlistLoading = false;
        }).catch(() => { waitlistLoading = false; }),

        contributionsAPI.getContributions({ limit: 5, category: cat }).then(res => {
          recentContributions = res.data?.results ?? res.data ?? [];
          recentLoading = false;
        }).catch(() => { recentLoading = false; })
      );
    }

    // Builder-only fetches
    if (cat === 'builder') {
      promises.push(
        leaderboardAPI.getTrending(5).then(res => {
          trendingEntries = res.data || [];
          trendingLoading = false;
        }).catch(() => { trendingLoading = false; })
      );
    }

    await Promise.allSettled(promises);
  });

  // Helper: format date for recent contributions
  function formatContribDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
</script>

<div class="space-y-8">
  <!-- 1. Hero Banner -->
  <HeroBanner />

  <!-- 2. Live Dashboard Stats -->
  <div>
    <SectionHeader
      title={isBuilder ? "Builder's Live Dashboard" : "Validator's Live Dashboard"}
      subtitle=""
      showLink={false}
    />
    <StatCardRow stats={statsData} loading={statsLoading} columns={3} />
  </div>

  <!-- 3. Two-column: Top Contributors + Chart Placeholder -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div>
      <SectionHeader
        title="Top Contributors"
        subtitle="This month curated builds"
        linkText="View all"
        linkPath={isBuilder ? '/builders/leaderboard' : '/validators/leaderboard'}
      />
      <RankedList
        entries={leaderboardEntries}
        loading={leaderboardLoading}
        accentColor={isBuilder ? '#ee8521' : '#4f76f6'}
      />
    </div>
    <div>
      <SectionHeader
        title="This month's Podium"
        subtitle="Coming soon"
        showLink={false}
      />
      <ChartPlaceholder
        title={isBuilder ? 'Builder Activity Chart' : 'Validator Activity Chart'}
        subtitle="Coming soon"
      />
    </div>
  </div>

  <!-- 4. Newest Members -->
  <div>
    <SectionHeader
      title={isBuilder ? 'Newest Builders' : 'Newest Validators'}
      subtitle="New"
      linkText="View all"
      linkPath={isBuilder ? '/builders/leaderboard' : '/validators/participants'}
    />
    <UserCardScroller entries={newestAsEntries} loading={membersLoading} />
  </div>

  <!-- 5. Builder-only: Featured Builds -->
  {#if isBuilder}
    <FeaturedBuilds />
  {/if}

  <!-- 6. Builder-only: Trending Contributors -->
  {#if isBuilder}
    <div>
      <SectionHeader
        title="Trending Contributors"
        subtitle="Highest Builder Points Contributions this week"
        linkText="View all"
        linkPath="/leaderboard"
      />
      <UserCardScroller entries={trendingEntries} loading={trendingLoading} />
    </div>
  {/if}

  <!-- Bottom gradient area: Highlighted Contributions + CTA -->
  <div class="relative -mx-6 px-6">
    <!-- Gradient background -->
    <div
      class="absolute inset-0 pointer-events-none"
      style="background: radial-gradient(ellipse 80% 60% at 0% 100%, rgba(233, 147, 34, 0.25) 0%, transparent 70%), radial-gradient(ellipse 80% 60% at 100% 100%, rgba(233, 147, 34, 0.25) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 10% 0%, rgba(248, 185, 61, 0.12) 0%, transparent 60%);"
    ></div>

    <!-- 7. Highlighted Contributions -->
    <div class="relative z-10">
      <SectionHeader
        title="Highlighted Contributions"
        subtitle="This month curated builds"
        linkText="Explore all"
        linkPath={isBuilder ? '/builders/contributions/highlights' : '/validators/contributions/highlights'}
      />
      <HighlightCards
        {highlights}
        loading={highlightsLoading}
        layout="grid"
        category={category}
      />
    </div>

    <!-- 8. Validator-only: Waitlist + Recent Contributions -->
    {#if isValidator}
      <div class="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
        <div>
          <SectionHeader
            title="Waitlist"
            subtitle="Top waitlisted validators"
            linkText="View all"
            linkPath="/validators/waitlist/join"
          />
          <RankedList
            entries={waitlistEntries}
            loading={waitlistLoading}
            accentColor="#4f76f6"
            showDelta={false}
          />
        </div>
        <div>
          <SectionHeader
            title="Recent Contributions"
            subtitle="Latest validator contributions"
            linkText="View all"
            linkPath="/validators/contributions"
          />
          <div class="bg-white border border-[#f7f7f7] rounded-[8px] overflow-clip p-[16px]">
            {#if recentLoading}
              <div class="space-y-3 animate-pulse">
                {#each [1, 2, 3, 4, 5] as _}
                  <div class="h-[40px] flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-gray-200"></div>
                    <div class="flex-1 space-y-1">
                      <div class="h-3 bg-gray-200 rounded w-32"></div>
                      <div class="h-2.5 bg-gray-100 rounded w-20"></div>
                    </div>
                    <div class="h-3 bg-gray-100 rounded w-16"></div>
                  </div>
                {/each}
              </div>
            {:else if recentContributions.length === 0}
              <div class="py-6 text-center text-sm text-[#6b6b6b]">No recent contributions</div>
            {:else}
              <div class="space-y-2">
                {#each recentContributions as contrib}
                  <button
                    onclick={() => push(`/badge/${contrib.id}`)}
                    class="w-full flex items-center gap-3 py-2 px-1 hover:bg-gray-50 rounded transition-colors text-left"
                  >
                    {#if contrib.user_details?.profile_image_url}
                      <img src={contrib.user_details.profile_image_url} alt="" class="w-8 h-8 rounded-full">
                    {:else}
                      <div class="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-xs font-medium text-sky-600">
                        {(contrib.user_details?.name || contrib.user_name || '?')[0].toUpperCase()}
                      </div>
                    {/if}
                    <div class="flex-1 min-w-0">
                      <p class="text-[13px] font-medium text-black truncate">{contrib.contribution_type_name || 'Contribution'}</p>
                      <p class="text-[11px] text-[#999]">{contrib.user_details?.name || contrib.user_name || 'Anonymous'}</p>
                    </div>
                    <span class="text-[12px] text-[#bbb] flex-shrink-0">{formatContribDate(contrib.contribution_date)}</span>
                  </button>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      </div>
    {/if}

    <!-- 9. CTA Section -->
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
    {:else}
      <CTASection
        title="Join the validator network"
        description="Join professional validators and builders in testing the trust infrastructure for the AI age."
        primaryButtonText="Become a validator"
        primaryButtonPath="/validators/waitlist/join"
        secondaryLinkText="Visit the Studio"
        secondaryLinkPath="https://studio.genlayer.com"
        secondaryLinkExternal={true}
      />
    {/if}
  </div>
</div>
