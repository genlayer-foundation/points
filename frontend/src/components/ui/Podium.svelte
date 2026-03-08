<script>
  import Avatar from '../Avatar.svelte';
  import { push } from 'svelte-spa-router';

  let {
    entries = [],
    loading = false,
    accentColor = '#ee8521',
    valueLabel = 'BP',
    category = 'builder',
  } = $props();

  // Color schemes per category
  const schemes = {
    builder: {
      firstGradient: 'linear-gradient(to bottom, #f8b93d, #ee8d24)',
      glow: 'rgba(248, 185, 61, 0.25)',
    },
    validator: {
      firstGradient: 'linear-gradient(135deg, #6da7f3 15%, #387de8 50%, #2159d2 85%)',
      glow: 'rgba(56, 125, 232, 0.25)',
    },
  };

  let scheme = $derived(schemes[category] || schemes.builder);

  // Reorder entries: [2nd, 1st, 3rd] for podium layout
  let podiumEntries = $derived((() => {
    if (entries.length < 3) return entries;
    return [entries[1], entries[0], entries[2]];
  })());

  function getUserObj(entry) {
    const ud = entry.user_details || {};
    return {
      name: entry.user_name || ud.name || entry.name,
      address: entry.user_address || ud.address || entry.address,
      profile_image_url: entry.profile_image_url || ud.profile_image_url,
      builder: entry.builder ?? false,
      validator: entry.validator ?? false,
      steward: entry.steward ?? false,
    };
  }

  function getDisplayName(entry) {
    const ud = entry.user_details || {};
    const name = entry.user_name || ud.name || entry.name;
    const addr = entry.user_address || ud.address || entry.address;
    if (name) return name.length > 12 ? name.slice(0, 12) + '...' : name;
    if (addr) return addr.slice(0, 6) + '...' + addr.slice(-4);
    return 'Unknown';
  }

  function getAddress(entry) {
    const ud = entry.user_details || {};
    return entry.user_address || ud.address || entry.address;
  }

  function navigateToUser(entry) {
    const addr = getAddress(entry);
    if (addr) push(`/participant/${addr}`);
  }
</script>

<div class="bg-white border border-[#f5f5f5] rounded-[8px] overflow-clip relative flex flex-col items-center justify-end" style="min-height: 304px;">
  {#if loading}
    <!-- Loading skeleton -->
    <div class="flex gap-[8px] items-end justify-center pb-0">
      {#each [120, 160, 80] as height}
        <div class="flex flex-col gap-[12px] items-center">
          <div class="flex flex-col gap-[4px] items-center">
            <div class="rounded-full bg-gray-200 animate-pulse" style="width: {height === 160 ? 64 : 48}px; height: {height === 160 ? 64 : 48}px;"></div>
            <div class="h-4 w-20 rounded bg-gray-200 animate-pulse"></div>
            <div class="h-4 w-12 rounded bg-gray-100 animate-pulse"></div>
          </div>
          <div class="rounded-t-[8px] bg-gray-100 animate-pulse" style="width: 140px; height: {height}px;"></div>
        </div>
      {/each}
    </div>
  {:else if podiumEntries.length < 3}
    <!-- Not enough data -->
    <div class="flex-1 flex items-center justify-center">
      <p class="text-[14px] text-[#999]">Not enough participants yet</p>
    </div>
  {:else}
    <!-- Decorative glow -->
    <div class="absolute top-[-53px] left-1/2 -translate-x-1/2 w-[612px] h-[104px] pointer-events-none" style="filter: blur(40px);">
      <div class="w-full h-full rounded-full" style="background: radial-gradient(ellipse at center, {scheme.glow} 0%, transparent 70%);"></div>
    </div>

    <!-- Podium -->
    <div class="flex gap-[8px] items-end justify-center relative z-10 px-[16px]">
      {#each podiumEntries as entry, i}
        {@const rank = i === 0 ? 2 : i === 1 ? 1 : 3}
        {@const isFirst = rank === 1}
        {@const pedestalHeight = rank === 1 ? 160 : rank === 2 ? 120 : 80}

        <div class="flex flex-col gap-[12px] items-center">
          <!-- User info -->
          <button
            onclick={() => navigateToUser(entry)}
            class="flex flex-col gap-[4px] items-center justify-center hover:opacity-80 transition-opacity"
          >
            <span class="inline-block rounded-full" style="box-shadow: 0 0 0 2.5px {accentColor}; line-height: 0;">
              <Avatar user={getUserObj(entry)} size={isFirst ? 'xl' : 'lg'} clickable={false} />
            </span>
            <span class="text-[16px] font-medium text-black whitespace-nowrap" style="letter-spacing: 0.32px;">
              {getDisplayName(entry)}
            </span>
            <span class="whitespace-nowrap flex items-baseline gap-[2px]" style="color: {accentColor};">
              <span class="text-[14px] font-medium" style="letter-spacing: 0.28px;">{entry.total_points ?? entry.points ?? 0}</span>
              <span class="text-[12px] font-medium opacity-60" style="letter-spacing: 0.24px;">{valueLabel}</span>
            </span>
          </button>

          <!-- Pedestal -->
          <div
            class="flex flex-col items-center px-[24px] py-[12px] rounded-t-[8px] w-[140px] xl:w-[160px]"
            style="height: {pedestalHeight}px; {isFirst
              ? `background: ${scheme.firstGradient};`
              : 'background: linear-gradient(to bottom, #f5f5f5, #e6e6e6); border: 1px solid #ababab; border-bottom: none;'
            }"
          >
            <span
              class="text-[32px] font-medium font-display leading-[40px] whitespace-nowrap"
              style="letter-spacing: -1.28px; color: {isFirst ? 'rgba(245, 245, 245, 0.9)' : '#6b6b6b'};"
            >
              {rank}
            </span>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
