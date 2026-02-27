<script>
  import { push } from 'svelte-spa-router';
  import Avatar from '../Avatar.svelte';

  let { entries = [], loading = false, accentColor = '#3eb359', valueLabel = 'GP', showDelta = true, onRowClick = null } = $props();

  const RANK_OPACITY = [1, 0.85, 0.7, 0.6, 0.5];

  function getUserObj(entry) {
    const ud = entry.user_details || {};
    return {
      name: entry.user_name || ud.name || entry.name,
      address: entry.user_address || ud.address || entry.address,
      profile_image_url: entry.profile_image_url || ud.profile_image_url,
      builder: entry.builder ?? false,
      validator: entry.validator ?? false,
      steward: entry.steward ?? false,
      has_validator_waitlist: entry.has_validator_waitlist ?? false,
      has_builder_welcome: entry.has_builder_welcome ?? false,
    };
  }

  function getDisplayName(entry) {
    const ud = entry.user_details || {};
    const name = entry.user_name || ud.name || entry.name;
    const addr = entry.user_address || ud.address || entry.address;
    if (name) return name.length > 14 ? name.slice(0, 14) + '...' : name;
    if (addr) return addr.slice(0, 6) + '...' + addr.slice(-4);
    return 'Unknown';
  }

  function getAddress(entry) {
    const ud = entry.user_details || {};
    return entry.user_address || ud.address || entry.address;
  }

  function formatPoints(pts) {
    if (pts == null) return '\u2014';
    if (pts >= 1000000) return (pts / 1000000).toFixed(1) + 'M';
    if (pts >= 1000) return (pts / 1000).toFixed(1) + 'K';
    return pts.toString();
  }

  function handleRowClick(entry) {
    if (onRowClick) {
      onRowClick(entry);
    } else {
      const addr = getAddress(entry);
      if (addr) push(`/participant/${addr}`);
    }
  }
</script>

<div class="bg-white border border-[#f7f7f7] rounded-[8px] overflow-clip p-[16px]">
  {#if loading}
    <div class="flex items-start justify-between animate-pulse">
      <div class="flex gap-[24px]">
        <div class="flex flex-col gap-[8px]">
          {#each [1, 2, 3, 4, 5] as _}
            <div class="h-[48px] flex items-center">
              <div class="w-4 h-4 rounded bg-gray-200"></div>
            </div>
          {/each}
        </div>
        <div class="flex flex-col gap-[8px]">
          {#each [1, 2, 3, 4, 5] as _}
            <div class="h-[48px] flex items-center gap-[4px]">
              <div class="w-10 h-10 rounded-full bg-gray-200"></div>
              <div class="h-4 w-20 rounded bg-gray-100"></div>
            </div>
          {/each}
        </div>
      </div>
      <div class="flex flex-col gap-[8px]">
        {#each [1, 2, 3, 4, 5] as _}
          <div class="h-[48px] flex items-center">
            <div class="h-4 w-12 rounded bg-gray-100"></div>
          </div>
        {/each}
      </div>
    </div>
  {:else if entries.length === 0}
    <div class="py-6 text-center text-sm text-[#6b6b6b]">No data</div>
  {:else}
    <div class="flex items-start justify-between">
      <!-- Left: rank + user -->
      <div class="flex gap-[24px]">
        <!-- Rank numbers -->
        <div class="flex flex-col gap-[8px] w-[30px]">
          {#each entries as _, i}
            <div class="h-[48px] flex items-center justify-center">
              {#if i === 0}
                <!-- Gold hexagon -->
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="rankGold" x1="0" y1="0" x2="30" y2="30" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#f8b93d"/>
                      <stop offset="1" stop-color="#ee8d24"/>
                    </linearGradient>
                  </defs>
                  <path d="M15 1.5 L27.5 8.25 L27.5 21.75 L15 28.5 L2.5 21.75 L2.5 8.25 Z" fill="url(#rankGold)"/>
                  <text x="15" y="16" text-anchor="middle" dominant-baseline="central" fill="white" font-size="13" font-weight="600">1</text>
                </svg>
              {:else if i === 1}
                <!-- Silver hexagon -->
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="rankSilver" x1="0" y1="0" x2="30" y2="30" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#f5f5f5"/>
                      <stop offset="1" stop-color="#e6e6e6"/>
                    </linearGradient>
                  </defs>
                  <path d="M15 1.5 L27.5 8.25 L27.5 21.75 L15 28.5 L2.5 21.75 L2.5 8.25 Z" fill="url(#rankSilver)"/>
                  <text x="15" y="16" text-anchor="middle" dominant-baseline="central" fill="#333333" font-size="13" font-weight="600">2</text>
                </svg>
              {:else if i === 2}
                <!-- Bronze hexagon -->
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="rankBronze" x1="0" y1="0" x2="30" y2="30" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#e8c6a0"/>
                      <stop offset="1" stop-color="#c9956b"/>
                    </linearGradient>
                  </defs>
                  <path d="M15 1.5 L27.5 8.25 L27.5 21.75 L15 28.5 L2.5 21.75 L2.5 8.25 Z" fill="url(#rankBronze)"/>
                  <text x="15" y="16" text-anchor="middle" dominant-baseline="central" fill="white" font-size="13" font-weight="600">3</text>
                </svg>
              {:else}
                <span class="text-[16px] text-black text-center" style="letter-spacing: 0.32px; opacity: {RANK_OPACITY[i] ?? 0.5};">{i + 1}</span>
              {/if}
            </div>
          {/each}
        </div>
        <!-- User info -->
        <div class="flex flex-col gap-[8px]">
          {#each entries as entry}
            <button
              onclick={() => handleRowClick(entry)}
              class="h-[48px] flex items-center gap-[4px] hover:opacity-80 transition-opacity"
            >
              <div class="flex rounded-full ring-2 ring-[#f0f0f0]">
                <Avatar user={getUserObj(entry)} size="md" clickable={false} showBorder={false} />
              </div>
              <span class="text-[14px] font-medium text-black" style="letter-spacing: 0.28px;">{getDisplayName(entry)}</span>
            </button>
          {/each}
        </div>
      </div>

      <!-- Right: points -->
      <div class="flex flex-col gap-[8px]">
        {#each entries as entry}
          <div class="h-[48px] flex items-center gap-[2px]" style="color: {accentColor};">
            {#if showDelta}
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
              </svg>
            {/if}
            <span class="text-[14px] font-medium" style="letter-spacing: 0.28px;">{formatPoints(entry.total_points ?? entry.points)}</span>
            <span class="text-[12px] font-medium opacity-60" style="letter-spacing: 0.24px;">GP</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
