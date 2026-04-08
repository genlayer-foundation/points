<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { contributionsAPI } from '../lib/api.js';
  import { parseMarkdown } from '../lib/markdownLoader.js';
  import Avatar from '../components/Avatar.svelte';

  let { params = {} } = $props();

  let contribution = $state(null);
  let userContributions = $state([]);
  let topContributors = $state([]);
  let loading = $state(true);
  let error = $state(null);

  // Category color config matching portal design system
  const categoryConfig = {
    builder:   { color: '#EE8521', light: 'rgba(238,133,33,0.08)', pillBg: 'rgba(238,141,36,0.1)', text: '#ee8d24', icon: '/assets/icons/terminal-line.svg', hexagon: '/assets/icons/hexagon-builder-light.svg' },
    validator: { color: '#387DE8', light: 'rgba(79,118,246,0.08)', pillBg: 'rgba(79,118,246,0.1)', text: '#4f76f6', icon: '/assets/icons/folder-shield-line.svg', hexagon: '/assets/icons/hexagon-validator-light.svg' },
    community: { color: '#7F52E1', light: '#f4f2fc',              pillBg: 'rgba(143,70,233,0.1)', text: '#8d81e1', icon: '/assets/icons/group-3-line.svg', hexagon: '/assets/icons/hexagon-community-light.svg' },
    steward:   { color: '#19A663', light: 'rgba(25,166,99,0.08)', pillBg: 'rgba(25,166,99,0.1)',  text: '#19A663', icon: '/assets/icons/seedling-line.svg', hexagon: '/assets/icons/hexagon-community-light.svg' },
    global:    { color: '#7F52E1', light: '#f4f2fc',              pillBg: 'rgba(143,70,233,0.1)', text: '#8d81e1', icon: '/assets/icons/group-3-line.svg', hexagon: '/assets/icons/hexagon-community-light.svg' },
  };

  // Highlight icon config (gold hexagon + white star)
  const highlightIcon = {
    hexagon: '/assets/icons/hexagon-highlight.svg',
    icon: '/assets/icons/star-line.svg',
    iconColor: '#FFFFFF',
  };

  let category = $derived(contribution?.contribution_type_details?.category || 'global');
  let colors = $derived(categoryConfig[category] || categoryConfig.global);
  let isHighlighted = $derived(!!contribution?.highlight);
  let typeName = $derived(contribution?.contribution_type_details?.name || contribution?.contribution_type_name || 'Contribution');

  // Get the user's role label
  let userRole = $derived.by(() => {
    const ud = contribution?.user_details;
    if (!ud) return 'community';
    if (ud.steward) return 'steward';
    if (ud.validator) return 'validator';
    if (ud.builder) return 'builder';
    return 'community';
  });

  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch {
      return dateString || 'N/A';
    }
  }

  function formatPoints(pts) {
    if (pts == null) return '0';
    if (pts >= 1000) return (pts / 1000).toFixed(1) + 'K';
    return pts.toString();
  }

  function getDisplayName(user) {
    if (!user) return 'Unknown';
    if (user.name) return user.name.length > 16 ? user.name.slice(0, 16) + '...' : user.name;
    if (user.address) return user.address.slice(0, 6) + '...' + user.address.slice(-4);
    return 'Unknown';
  }

  function getUserObj(c) {
    const ud = c.user_details || {};
    return {
      name: ud.name,
      address: ud.address,
      profile_image_url: ud.profile_image_url,
      builder: ud.builder ?? false,
      validator: ud.validator ?? false,
      steward: ud.steward ?? false,
      has_validator_waitlist: ud.has_validator_waitlist ?? false,
      has_builder_welcome: ud.has_builder_welcome ?? false,
    };
  }

  function getContributionCategory(c) {
    return c?.contribution_type_details?.category || 'global';
  }

  onMount(async () => {
    try {
      const res = await contributionsAPI.getContribution(params.id);
      contribution = res.data;

      // Fetch related data in parallel
      const promises = [];

      // More from this user
      if (contribution.user_details?.address) {
        promises.push(
          contributionsAPI.getContributions({
            user_address: contribution.user_details.address,
            page_size: 7,
            group_consecutive: false,
          }).then(r => {
            const results = r.data?.results || r.data || [];
            userContributions = results.filter(c => c.id !== contribution.id).slice(0, 6);
          }).catch(() => {})
        );
      }

      // Top contributors in this category type
      if (contribution.contribution_type_details?.id) {
        promises.push(
          contributionsAPI.getContributionTypeTopContributors(contribution.contribution_type_details.id)
            .then(r => {
              topContributors = (r.data || []).slice(0, 1);
            }).catch(() => {})
        );
      }

      await Promise.all(promises);
    } catch (err) {
      error = err.message || 'Failed to load contribution';
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="max-w-[1200px] mx-auto animate-pulse">
    <!-- Back link skeleton -->
    <div class="h-[20px] w-[140px] rounded bg-gray-200 mb-[24px]"></div>

    <div class="flex gap-[40px]">
      <!-- Article skeleton -->
      <div class="flex-1 min-w-0 max-w-[688px]">
        <!-- Type name -->
        <div class="h-[38px] w-[200px] rounded bg-gray-200 mb-[24px]"></div>

        <!-- Showcase links -->
        <div class="mb-[24px]">
          <div class="h-[24px] w-[100px] rounded bg-gray-200 mb-[16px]"></div>
          <div class="flex flex-col gap-[8px]">
            <div class="h-[44px] rounded-[8px] bg-gray-100" style="border: 1px solid #f5f5f5;"></div>
            <div class="h-[44px] rounded-[8px] bg-gray-100" style="border: 1px solid #f5f5f5;"></div>
          </div>
        </div>

        <!-- Notes block -->
        <div class="rounded-[8px] p-[20px] mb-[24px]" style="background: #fafafa;">
          <div class="h-[16px] w-[60px] rounded bg-gray-200 mb-[12px]"></div>
          <div class="space-y-[8px]">
            <div class="h-[14px] w-full rounded bg-gray-200"></div>
            <div class="h-[14px] w-3/4 rounded bg-gray-200"></div>
            <div class="h-[14px] w-1/2 rounded bg-gray-200"></div>
          </div>
        </div>

        <!-- HR -->
        <div class="border-t mb-[40px]" style="border-color: #f0f0f0;"></div>

        <!-- More from user -->
        <div class="mb-[40px]">
          <div class="h-[24px] w-[180px] rounded bg-gray-200 mb-[8px]"></div>
          <div class="h-[16px] w-[240px] rounded bg-gray-100 mb-[16px]"></div>
          <div class="flex gap-[10px]">
            {#each [1, 2, 3] as _}
              <div class="flex-shrink-0 w-[260px] h-[156px] rounded-[8px] bg-gray-100" style="border: 1px solid #f5f5f5;"></div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Sidebar skeleton -->
      <div class="w-[240px] flex-shrink-0 flex flex-col gap-[16px]">
        <!-- Contributor card -->
        <div class="rounded-[8px] pl-[17px] pr-[4px] py-[17px]" style="border: 1px solid #f5f5f5;">
          <div class="h-[14px] w-[80px] rounded bg-gray-200 mb-[12px]"></div>
          <div class="flex items-center gap-[12px]">
            <div class="w-[40px] h-[40px] rounded-full bg-gray-200"></div>
            <div class="flex flex-col gap-[6px]">
              <div class="h-[14px] w-[100px] rounded bg-gray-200"></div>
              <div class="h-[12px] w-[60px] rounded bg-gray-100"></div>
            </div>
          </div>
        </div>

        <!-- Details card -->
        <div class="rounded-[8px] pl-[17px] pr-[17px] py-[17px] flex flex-col gap-[12px]" style="border: 1px solid #f5f5f5;">
          {#each [1, 2, 3, 4] as _}
            <div class="flex items-center justify-between">
              <div class="h-[12px] w-[50px] rounded bg-gray-200"></div>
              <div class="h-[24px] w-[70px] rounded-full bg-gray-100"></div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>
{:else if error}
  <div class="text-center py-20">
    <p class="text-[14px]" style="color: #6b6b6b;">Could not load contribution</p>
    <button onclick={() => push('/')} class="mt-4 text-[14px] text-black hover:opacity-70 transition-opacity">
      ← Back to dashboard
    </button>
  </div>
{:else if contribution}
  <div class="max-w-[1200px] mx-auto">
    <!-- Back link -->
    <button
      onclick={() => window.history.length > 1 ? window.history.back() : push('/')}
      class="flex items-center gap-[6px] mb-[24px] text-[14px] hover:opacity-70 transition-opacity"
      style="color: #ababab; letter-spacing: 0.28px;"
    >
      <span>←</span>
      <span>Back to dashboard</span>
    </button>

    <!-- Main layout: article + sidebar -->
    <div class="flex gap-[40px]">
      <!-- Article -->
      <div class="flex-1 min-w-0 max-w-[688px]">

        {#if isHighlighted}
          <!-- Highlighted hero box -->
          <div class="rounded-[8px] p-[20px] mb-[24px]" style="background: {colors.light};">
            <!-- Type name with highlight icon -->
            <div class="flex items-center gap-[12px] mb-[12px]">
              <div class="relative w-[48px] h-[48px] flex-shrink-0">
                <img src={highlightIcon.hexagon} alt="" class="w-full h-full" />
                <div
                  class="absolute inset-0 m-auto w-6 h-6"
                  style="background-color: {highlightIcon.iconColor}; -webkit-mask-image: url({highlightIcon.icon}); mask-image: url({highlightIcon.icon}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
                ></div>
              </div>
              <span class="font-display font-medium text-[32px]" style="color: {colors.text}; letter-spacing: -1.28px;">
                {typeName}
              </span>
            </div>
            <!-- Title (optional) -->
            {#if contribution.highlight.title}
              <h1 class="font-display font-medium text-[48px] text-black leading-[56px] mb-[8px]" style="letter-spacing: -0.96px;">
                {contribution.highlight.title}
              </h1>
            {/if}
            <!-- Full article body from highlight.description -->
            {#if contribution.highlight.description}
              <div class="article-body">
                {@html parseMarkdown(contribution.highlight.description)}
              </div>
            {/if}
          </div>

        {:else}
          <!-- Normal/Basic header -->
          <div class="mb-[24px]">
            <span class="font-display font-medium text-[32px] block" style="color: {colors.text}; letter-spacing: -1.28px;">
              {typeName}
            </span>
            {#if contribution.title}
              <h1 class="font-display font-medium text-[48px] text-black leading-[56px] mt-[8px]" style="letter-spacing: -0.96px;">
                {contribution.title}
              </h1>
            {/if}
          </div>
        {/if}

        <!-- Showcase section: evidence URLs as clickable links -->
        {#if contribution.evidence_items?.length > 0}
          {@const urlEvidence = contribution.evidence_items.filter(e => e.url)}
          {#if urlEvidence.length > 0}
            <div class="mb-[24px]">
              <h2 class="text-[20px] font-semibold text-black mb-[16px]" style="letter-spacing: 0.4px;">Showcase</h2>
              <div class="flex flex-col gap-[8px]">
                {#each urlEvidence as evidence}
                  <a
                    href={evidence.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center justify-between px-[17px] py-[12px] bg-white rounded-[8px] hover:shadow-sm transition-shadow"
                    style="border: 1px solid #f0f0f0;"
                  >
                    <span class="text-[14px] font-medium text-black truncate" style="letter-spacing: 0.28px;">
                      {evidence.description || evidence.url}
                    </span>
                    <svg class="w-4 h-4 flex-shrink-0 ml-[12px]" style="color: #ababab;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17L17 7M17 7H7M17 7V17"/>
                    </svg>
                  </a>
                {/each}
              </div>
            </div>
          {/if}
        {/if}

        <!-- Notes block (user's original submission) -->
        {#if contribution.notes}
          <div class="rounded-[8px] pt-[20px] px-[20px] pb-[20px] mb-[24px]" style="background: #fafafa;">
            <h3 class="text-[14px] font-semibold text-black mb-[12px]" style="letter-spacing: 0.28px;">
              Notes
            </h3>
            <div class="text-[14px] leading-[21px]" style="color: #3f3f3f; letter-spacing: 0.28px;">
              {@html parseMarkdown(contribution.notes)}
            </div>
          </div>
        {/if}

        <!-- HR -->
        <div class="border-t mb-[40px]" style="border-color: #f0f0f0;"></div>

        <!-- More from user -->
        {#if userContributions.length > 0}
          <div class="mb-[40px]">
            <div class="mb-[16px]">
              <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">
                More from {getDisplayName(contribution.user_details)}
              </h2>
              <p class="text-[14px]" style="color: #6b6b6b; letter-spacing: 0.28px;">
                Other contributions by this contributor
              </p>
            </div>
            <div class="flex gap-[10px] overflow-x-auto pb-[4px]" style="-ms-overflow-style: none; scrollbar-width: none;">
              {#each userContributions as uc}
                {@const ucCategory = getContributionCategory(uc)}
                {@const ucColors = categoryConfig[ucCategory] || categoryConfig.global}
                <button
                  onclick={() => push(`/contribution/${uc.id}`)}
                  class="flex-shrink-0 w-[260px] h-[156px] rounded-[8px] flex flex-col justify-between pl-[17px] pr-[4px] py-[17px] text-left hover:shadow-sm transition-shadow"
                  style="border: 1px solid #f0f0f0;"
                >
                  <!-- Top: avatar + name + points -->
                  <div class="flex items-center gap-[8px]">
                    {#if uc.user_details?.profile_image_url}
                      <img src={uc.user_details.profile_image_url} alt="" class="w-[20px] h-[20px] rounded-full flex-shrink-0" />
                    {:else}
                      <div class="w-[20px] h-[20px] rounded-full flex-shrink-0" style="background: #e6e6e6;"></div>
                    {/if}
                    <span class="text-[12px] font-medium text-black flex-1 truncate" style="letter-spacing: 0.24px;">
                      {getDisplayName(uc.user_details)}
                    </span>
                    <span class="text-[12px] px-[8px] py-[4px] rounded-full flex-shrink-0" style="background: #f3f3f3; color: #6b6b6b; letter-spacing: 0.24px;">
                      {uc.frozen_global_points || 0} pts
                    </span>
                  </div>
                  <!-- Middle: title + description -->
                  <div class="flex flex-col gap-[4px] overflow-hidden">
                    <span class="text-[14px] font-medium text-black truncate" style="letter-spacing: 0.28px;">
                      {uc.title || uc.contribution_type_details?.name || uc.contribution_type_name || 'Contribution'}
                    </span>
                    {#if uc.notes}
                      <span class="text-[12px] leading-[20px] line-clamp-2" style="color: #6b6b6b; letter-spacing: 0.24px;">
                        {uc.notes.slice(0, 120)}
                      </span>
                    {/if}
                  </div>
                  <!-- Bottom: category pill + date -->
                  <div class="flex items-center justify-between">
                    <span class="text-[12px] font-medium px-[8px] py-[4px] rounded-full" style="background: {ucColors.pillBg}; color: {ucColors.text};">
                      {uc.contribution_type_details?.name || uc.contribution_type_name || 'Contribution'}
                    </span>
                    <span class="text-[12px]" style="color: #ababab; letter-spacing: 0.24px;">
                      {formatDate(uc.contribution_date)}
                    </span>
                  </div>
                </button>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Top in category type -->
        {#if topContributors.length > 0}
          <div class="mb-[24px]">
            <h2 class="text-[20px] font-semibold text-black mb-[16px]" style="letter-spacing: 0.4px;">
              Top in {typeName}
            </h2>
            <div class="rounded-[8px] overflow-clip" style="border: 1px solid #f0f0f0;">
              {#each topContributors as tc, i}
                <button
                  onclick={() => tc.address && push(`/participant/${tc.address}`)}
                  class="w-full flex items-center gap-[12px] px-[16px] py-[12px] hover:opacity-80 transition-opacity"
                  style="background: #fafafa;"
                >
                  <span class="text-[12px] font-medium w-[20px]" style="color: #ababab; letter-spacing: 0.24px;">
                    #{i + 1}
                  </span>
                  {#if tc.profile_image_url}
                    <img src={tc.profile_image_url} alt="" class="w-[20px] h-[20px] rounded-full" />
                  {:else}
                    <div class="w-[20px] h-[20px] rounded-full" style="background: #e6e6e6;"></div>
                  {/if}
                  <span class="text-[14px] font-medium text-black flex-1 text-left" style="letter-spacing: 0.28px;">
                    {tc.name || (tc.address ? tc.address.slice(0, 6) + '...' + tc.address.slice(-4) : 'Unknown')}
                  </span>
                  <span class="text-[12px] font-medium" style="color: #6b6b6b; letter-spacing: 0.24px;">
                    {formatPoints(tc.total_points)} pts
                  </span>
                </button>
              {/each}
            </div>
          </div>
        {/if}
      </div>

      <!-- Sidebar -->
      <div class="w-[240px] flex-shrink-0 flex flex-col gap-[16px]">
        <!-- Contributor card -->
        <div class="bg-white rounded-[8px] pl-[17px] pr-[4px] py-[17px]" style="border: 1px solid #f0f0f0;">
          <div class="text-[12px] mb-[12px]" style="color: #ababab; letter-spacing: 0.24px;">Contributor</div>
          <button
            onclick={() => contribution.user_details?.address && push(`/participant/${contribution.user_details.address}`)}
            class="flex items-center gap-[12px] hover:opacity-80 transition-opacity"
          >
            <Avatar user={getUserObj(contribution)} size="md" clickable={false} />
            <div class="flex flex-col">
              <span class="text-[14px] font-medium text-black text-left" style="letter-spacing: 0.28px;">
                {getDisplayName(contribution.user_details)}
              </span>
              <span class="text-[12px] capitalize text-left" style="color: #6b6b6b; letter-spacing: 0.24px;">
                {userRole}
              </span>
            </div>
          </button>
        </div>

        <!-- Details card -->
        <div class="bg-white rounded-[8px] pl-[17px] pr-[4px] py-[17px] flex flex-col gap-[12px]" style="border: 1px solid #f0f0f0;">
          <!-- Points -->
          <div class="flex items-center justify-between pr-[13px]">
            <span class="text-[12px]" style="color: #ababab; letter-spacing: 0.24px;">Points</span>
            <span class="text-[12px] font-medium px-[8px] py-[4px] rounded-full" style="background: #f3f3f3; color: #6b6b6b;">
              {contribution.frozen_global_points || 0} pts
            </span>
          </div>

          <!-- Category -->
          <div class="flex items-center justify-between pr-[13px]">
            <span class="text-[12px]" style="color: #ababab; letter-spacing: 0.24px;">Category</span>
            <span class="text-[12px] font-medium px-[8px] py-[4px] rounded-full" style="background: {colors.pillBg}; color: {colors.text};">
              {typeName}
            </span>
          </div>

          <!-- Date -->
          <div class="flex items-center justify-between pr-[13px]">
            <span class="text-[12px]" style="color: #ababab; letter-spacing: 0.24px;">Date</span>
            <span class="text-[12px] font-medium" style="color: #3f3f3f; letter-spacing: 0.24px;">
              {formatDate(contribution.contribution_date)}
            </span>
          </div>

          <!-- Status -->
          <div class="flex items-center justify-between pr-[13px]">
            <span class="text-[12px]" style="color: #ababab; letter-spacing: 0.24px;">Status</span>
            <div class="flex items-center gap-[6px]">
              <div class="w-[6px] h-[6px] rounded-full" style="background: #169941;"></div>
              <span class="text-[12px] font-medium" style="color: #169941; letter-spacing: 0.24px;">Accepted</span>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Article body typography for highlighted descriptions */
  .article-body :global(h1),
  .article-body :global(h2),
  .article-body :global(h3) {
    font-family: var(--font-display);
    font-weight: 500;
    color: black;
    margin-top: 40px;
    margin-bottom: 20px;
  }

  .article-body :global(h2) {
    font-size: 24px;
    letter-spacing: -0.48px;
    line-height: 40px;
  }

  .article-body :global(h3) {
    font-size: 20px;
    letter-spacing: -0.4px;
    line-height: 32px;
  }

  .article-body :global(p) {
    font-size: 17px;
    line-height: 28px;
    color: #3f3f3f;
    letter-spacing: 0.34px;
    margin-bottom: 16px;
  }

  .article-body :global(ul),
  .article-body :global(ol) {
    padding-left: 20px;
    margin-bottom: 16px;
  }

  .article-body :global(li) {
    font-size: 17px;
    line-height: 28px;
    color: #3f3f3f;
    letter-spacing: 0.34px;
    margin-bottom: 8px;
  }

  .article-body :global(strong) {
    font-weight: 600;
    color: black;
  }

  .article-body :global(a) {
    color: #4f76f6;
    text-decoration: underline;
  }

  /* Line clamp utility */
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
