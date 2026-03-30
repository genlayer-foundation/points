<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { leaderboardAPI } from '../../lib/api';
  import Avatar from '../Avatar.svelte';

  let contributors = $state([]);
  let loading = $state(true);
  let error = $state(null);

  onMount(async () => {
    try {
      const response = await leaderboardAPI.getTrending(10);
      contributors = response.data;
    } catch (err) {
      error = err.message || 'Failed to load contributors';
    } finally {
      loading = false;
    }
  });

  function getUserObj(entry) {
    return {
      name: entry.user_name || entry.name,
      address: entry.user_address || entry.address,
      profile_image_url: entry.profile_image_url,
      builder: entry.builder ?? false,
      validator: entry.validator ?? false,
      steward: entry.steward ?? false,
      has_validator_waitlist: entry.has_validator_waitlist ?? false,
      has_builder_welcome: entry.has_builder_welcome ?? false,
    };
  }

  function getDisplayName(entry) {
    const name = entry.user_name || entry.name;
    const addr = entry.user_address || entry.address;
    if (name) return name.length > 12 ? name.slice(0, 12) + '...' : name;
    if (addr) return addr.slice(0, 6) + '...' + addr.slice(-4);
    return 'Unknown';
  }

  function formatPoints(pts) {
    if (pts == null) return '0';
    if (pts >= 1000) return (pts / 1000).toFixed(1) + 'K';
    return pts.toString();
  }

  // Priority: steward > validator > builder > community
  function getCategoryType(entry) {
    if (entry.steward) return 'steward';
    if (entry.validator) return 'validator';
    if (entry.builder) return 'builder';
    return 'community';
  }

  const categoryConfig = {
    steward:   { icon: '/assets/icons/seedling-line.svg',        color: '#19A663' },
    validator: { icon: '/assets/icons/folder-shield-line.svg',   color: '#387DE8' },
    builder:   { icon: '/assets/icons/terminal-line.svg',        color: '#EE8521' },
    community: { icon: '/assets/icons/group-3-line.svg',         color: '#7F52E1' },
  };
</script>

<div class="flex flex-col gap-[12px]">
  <!-- Section header -->
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Trending Contributors</h2>
      <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">Highest GenLayer Portal contributions this week</p>
    </div>
  </div>

  <!-- Cards -->
  {#if loading}
    <div class="flex gap-[10px] overflow-x-auto" style="-ms-overflow-style: none; scrollbar-width: none;">
      {#each [1, 2, 3, 4, 5, 6] as _}
        <div class="flex items-center flex-shrink-0 border border-[#f5f5f5] rounded-[8px] overflow-clip pr-[16px] animate-pulse">
          <div class="w-[80px] h-[80px] flex items-center justify-center">
            <div class="w-[48px] h-[48px] rounded-full bg-gray-200"></div>
          </div>
          <div class="w-[120px] flex flex-col gap-2">
            <div class="h-3 bg-gray-200 rounded w-16"></div>
            <div class="h-3 bg-gray-200 rounded w-12"></div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="text-sm text-gray-500 py-4">Could not load contributors</div>
  {:else if contributors.length === 0}
    <div class="text-sm text-gray-500 py-4">No contributors yet</div>
  {:else}
    <div class="flex gap-[10px] overflow-x-auto" style="-ms-overflow-style: none; scrollbar-width: none;">
      {#each contributors as entry}
        <button
          onclick={() => push(`/participant/${entry.user_address || entry.address}`)}
          class="flex items-center flex-shrink-0 border border-[#f5f5f5] rounded-[8px] overflow-clip pr-[16px] hover:border-[#e0e0e0] transition-colors"
        >
          <!-- Avatar container -->
          <div class="w-[80px] h-[80px] flex items-center justify-center">
            <Avatar
              user={getUserObj(entry)}
              size="lg"
              showBorder={false}
              clickable={false}
            />
          </div>

          <!-- Name and points -->
          <div class="w-[120px] flex flex-col justify-center">
            <span class="text-[14px] font-medium text-black text-left truncate" style="letter-spacing: 0.28px;">
              {getDisplayName(entry)}
            </span>
            <span class="flex items-center gap-0.5">
              <svg class="w-4 h-4 text-[#3eb359]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
              </svg>
              <span class="text-[14px] text-[#3eb359]" style="letter-spacing: 0.28px;">{formatPoints(entry.total_points)}</span>
            </span>
          </div>

          <!-- Category label: light hexagon + colored icon -->
          <div class="pt-[16px] self-start ml-auto">
            <div class="relative w-6 h-6">
              <img src="/assets/icons/hexagon-light.svg" alt="" class="w-full h-full" />
              <div
                class="absolute inset-0 m-auto w-3 h-3"
                style="background-color: {categoryConfig[getCategoryType(entry)].color}; -webkit-mask-image: url({categoryConfig[getCategoryType(entry)].icon}); mask-image: url({categoryConfig[getCategoryType(entry)].icon}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
              ></div>
            </div>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>
