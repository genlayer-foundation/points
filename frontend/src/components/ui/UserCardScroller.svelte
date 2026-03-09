<script>
  import { push } from 'svelte-spa-router';
  import Avatar from '../Avatar.svelte';
  import CategoryIcon from '../portal/CategoryIcon.svelte';

  let { entries = [], loading = false, onCardClick = null } = $props();

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
    if (pts >= 1000000) return (pts / 1000000).toFixed(1) + 'M';
    if (pts >= 1000) return (pts / 1000).toFixed(1) + 'K';
    return pts.toString();
  }

  function getCategoryType(entry) {
    if (entry.steward) return 'steward';
    if (entry.validator) return 'validator';
    if (entry.builder) return 'builder';
    return 'community';
  }

  function handleCardClick(entry) {
    if (onCardClick) {
      onCardClick(entry);
    } else {
      const addr = entry.user_address || entry.address;
      if (addr) push(`/participant/${addr}`);
    }
  }
</script>

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
{:else if entries.length === 0}
  <div class="text-sm text-gray-500 py-4">No contributors yet</div>
{:else}
  <div class="flex gap-[10px] overflow-x-auto" style="-ms-overflow-style: none; scrollbar-width: none;">
    {#each entries as entry}
      <button
        onclick={() => handleCardClick(entry)}
        class="flex items-center flex-shrink-0 border border-[#f5f5f5] rounded-[8px] overflow-clip pr-[16px] hover:border-[#e0e0e0] transition-colors bg-white"
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
            <span class="text-[14px] text-[#3eb359]" style="letter-spacing: 0.28px;">{formatPoints(entry.total_points ?? entry.points)}</span>
          </span>
        </div>

        <!-- Category icon: small hexagon -->
        <div class="pt-[16px] self-start ml-auto">
          <CategoryIcon category={getCategoryType(entry)} mode="hexagon" size={24} light={true} />
        </div>
      </button>
    {/each}
  </div>
{/if}
