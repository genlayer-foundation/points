<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { leaderboardAPI } from '../../lib/api';
  import Avatar from '../Avatar.svelte';

  const LIMIT = 5;
  const RANK_OPACITY = [1, 0.85, 0.7, 0.6, 0.5];

  const categoryConfig = {
    builder:   { icon: '/assets/icons/terminal-line.svg',        color: '#EE8521', hexagon: '/assets/icons/hexagon-builder-light.svg' },
    validator: { icon: '/assets/icons/folder-shield-line.svg',   color: '#387DE8', hexagon: '/assets/icons/hexagon-validator-light.svg' },
    community: { icon: '/assets/icons/group-3-line.svg',         color: '#7F52E1', hexagon: '/assets/icons/hexagon-community-light.svg' },
  };

  let builders = $state([]);
  let validators = $state([]);
  let community = $state([]);
  let loading = $state(true);
  let error = $state(null);

  onMount(async () => {
    try {
      const [bRes, vRes, cRes] = await Promise.all([
        leaderboardAPI.getLeaderboard({ type: 'builder', limit: LIMIT }),
        leaderboardAPI.getLeaderboard({ type: 'validator', limit: LIMIT }),
        leaderboardAPI.getCommunity({ limit: LIMIT }),
      ]);
      builders = extractEntries(bRes.data);
      validators = extractEntries(vRes.data);
      community = (cRes.data?.results ?? []).slice(0, LIMIT);
    } catch (err) {
      error = err.message || 'Failed to load leaderboard';
    } finally {
      loading = false;
    }
  });

  function extractEntries(data) {
    const arr = Array.isArray(data) ? data : (data?.results ?? []);
    return arr.slice(0, LIMIT);
  }

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
    if (pts == null) return '—';
    if (pts >= 1000) return (pts / 1000).toFixed(1) + 'K';
    return pts.toString();
  }
</script>

<!-- Section header -->
<div class="flex flex-col gap-[12px]">
  <div>
    <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Top Point Contributors</h2>
    <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">This month curated builds</p>
  </div>

  {#if loading}
    <!-- Loading skeleton -->
    <div class="flex flex-col md:flex-row gap-[12px]">
      {#each [1, 2, 3] as _}
        <div class="flex-1">
          <div class="flex items-center justify-between px-[4px] mb-[8px]">
            <div class="flex items-center gap-[8px]">
              <div class="w-6 h-6 rounded bg-gray-200 animate-pulse"></div>
              <div class="h-4 w-16 rounded bg-gray-200 animate-pulse"></div>
            </div>
            <div class="h-4 w-14 rounded bg-gray-200 animate-pulse"></div>
          </div>
          <div class="bg-white border border-[#f7f7f7] rounded-[8px] overflow-clip p-[16px] animate-pulse">
            <div class="flex items-start justify-between">
              <div class="flex gap-[24px]">
                <div class="flex flex-col gap-[8px]">
                  {#each [1, 2, 3, 4, 5] as __}
                    <div class="h-[48px] flex items-center">
                      <div class="w-4 h-4 rounded bg-gray-200"></div>
                    </div>
                  {/each}
                </div>
                <div class="flex flex-col gap-[8px]">
                  {#each [1, 2, 3, 4, 5] as __}
                    <div class="h-[48px] flex items-center gap-[4px]">
                      <div class="w-10 h-10 rounded-full bg-gray-200"></div>
                      <div class="h-4 w-20 rounded bg-gray-100"></div>
                    </div>
                  {/each}
                </div>
              </div>
              <div class="flex flex-col gap-[8px]">
                {#each [1, 2, 3, 4, 5] as __}
                  <div class="h-[48px] flex items-center">
                    <div class="h-4 w-12 rounded bg-gray-100"></div>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="text-sm text-gray-500 py-4">Could not load leaderboard</div>
  {:else}
    <!-- 3-column layout -->
    <div class="flex flex-col md:flex-row gap-[12px]">
      <!-- Builders column -->
      {@render column('Builders', builders, '/builders/leaderboard', 'builder')}
      <!-- Validators column -->
      {@render column('Validators', validators, '/validators/leaderboard', 'validator')}
      <!-- Community column -->
      {@render communityColumn()}
    </div>
  {/if}
</div>

{#snippet column(label, entries, viewPath, type)}
  <div class="flex-1">
    <!-- Column header -->
    <div class="flex items-center justify-between px-[4px] mb-[8px]">
      <div class="flex items-center gap-[4px]">
        {@render labelIcon(type)}
        <span class="text-[14px] font-medium text-black" style="letter-spacing: 0.28px;">{label}</span>
      </div>
      <button onclick={() => push(viewPath)} class="flex items-center gap-[4px] text-[14px] text-[#6b6b6b] hover:text-black transition-colors" style="letter-spacing: 0.28px;">
        View all
        <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
      </button>
    </div>

    <!-- Column card -->
    <div class="bg-white border border-[#f7f7f7] rounded-[8px] overflow-clip p-[16px]">
      {#if entries.length === 0}
        <div class="py-6 text-center text-sm text-[#6b6b6b]">No data</div>
      {:else}
        <div class="flex items-start justify-between">
          <!-- Left: rank + user -->
          <div class="flex gap-[24px]">
            <!-- Rank numbers -->
            <div class="flex flex-col gap-[8px]">
              {#each entries as _, i}
                <div class="h-[48px] flex items-center">
                  <span class="text-[16px] text-black" style="letter-spacing: 0.32px; opacity: {RANK_OPACITY[i] ?? 0.5};">{i + 1}</span>
                </div>
              {/each}
            </div>
            <!-- User info -->
            <div class="flex flex-col gap-[8px]">
              {#each entries as entry}
                <button
                  onclick={() => getAddress(entry) && push(`/participant/${getAddress(entry)}`)}
                  class="h-[48px] flex items-center gap-[4px] hover:opacity-80 transition-opacity"
                >
                  <Avatar user={getUserObj(entry)} size="md" clickable={false} />
                  <span class="text-[14px] font-medium text-black" style="letter-spacing: 0.28px;">{getDisplayName(entry)}</span>
                </button>
              {/each}
            </div>
          </div>

          <!-- Right: points -->
          <div class="flex gap-[16px]">
            <!-- Category points -->
            <div class="flex flex-col gap-[8px]">
              {#each entries as entry}
                <div class="h-[48px] flex items-center gap-[2px] {type === 'builder' ? 'text-[#ee8521]' : 'text-[#4f76f6]'}">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
                  </svg>
                  <span class="text-[14px]" style="letter-spacing: 0.28px;">{formatPoints(entry.total_points ?? entry.points)}</span>
                </div>
              {/each}
            </div>
            <!-- Total GP -->
            <div class="flex flex-col gap-[8px]">
              {#each entries as entry}
                <div class="h-[48px] flex items-center">
                  <span class="text-[14px] font-medium text-black" style="letter-spacing: 0.28px;">{formatPoints(entry.total_points ?? entry.points)}</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet communityColumn()}
  <div class="flex-1">
    <!-- Column header -->
    <div class="flex items-center justify-between px-[4px] mb-[8px]">
      <div class="flex items-center gap-[4px]">
        {@render labelIcon('community')}
        <span class="text-[14px] font-medium text-black" style="letter-spacing: 0.28px;">Community</span>
      </div>
      <button onclick={() => push('/community')} class="flex items-center gap-[4px] text-[14px] text-[#6b6b6b] hover:text-black transition-colors" style="letter-spacing: 0.28px;">
        View all
        <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
      </button>
    </div>

    <!-- Column card -->
    <div class="bg-white border border-[#f7f7f7] rounded-[8px] overflow-clip p-[16px]">
      {#if community.length === 0}
        <div class="py-6 text-center text-sm text-[#6b6b6b]">No data</div>
      {:else}
        <div class="flex items-start justify-between">
          <!-- Left: rank + user -->
          <div class="flex gap-[24px]">
            <!-- Rank numbers -->
            <div class="flex flex-col gap-[8px]">
              {#each community as _, i}
                <div class="h-[48px] flex items-center">
                  <span class="text-[16px] text-black" style="letter-spacing: 0.32px; opacity: {RANK_OPACITY[i] ?? 0.5};">{i + 1}</span>
                </div>
              {/each}
            </div>
            <!-- User info -->
            <div class="flex flex-col gap-[8px]">
              {#each community as entry}
                <button
                  onclick={() => getAddress(entry) && push(`/participant/${getAddress(entry)}`)}
                  class="h-[48px] flex items-center gap-[4px] hover:opacity-80 transition-opacity"
                >
                  <Avatar user={getUserObj(entry)} size="md" clickable={false} />
                  <span class="text-[14px] font-medium text-black" style="letter-spacing: 0.28px;">{getDisplayName(entry)}</span>
                </button>
              {/each}
            </div>
          </div>

          <!-- Right: community points columns -->
          <div class="flex gap-[16px]">
            <!-- Community points (purple) -->
            <div class="flex flex-col gap-[8px]">
              {#each community as entry}
                <div class="h-[48px] flex items-center gap-[2px] text-[#8f46e9]">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
                  </svg>
                  <span class="text-[14px]" style="letter-spacing: 0.28px;">{formatPoints(entry.total_points ?? entry.points)}</span>
                </div>
              {/each}
            </div>
            <!-- Builder points (orange) -->
            <div class="flex flex-col gap-[8px]">
              {#each community as entry}
                <div class="h-[48px] flex items-center">
                  <span class="text-[14px] font-medium text-[#ee8521]" style="letter-spacing: 0.28px;">{formatPoints(entry.builder_points ?? 0)}</span>
                </div>
              {/each}
            </div>
            <!-- Validator points (blue) -->
            <div class="flex flex-col gap-[8px]">
              {#each community as entry}
                <div class="h-[48px] flex items-center">
                  <span class="text-[14px] font-medium text-[#4f76f6]" style="letter-spacing: 0.28px;">{formatPoints(entry.validator_points ?? 0)}</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet labelIcon(type)}
  {@const cfg = categoryConfig[type]}
  <div class="relative w-6 h-6 flex-shrink-0">
    <img src={cfg.hexagon} alt="" class="w-full h-full" />
    <div
      class="absolute inset-0 m-auto w-3 h-3"
      style="background-color: {cfg.color}; -webkit-mask-image: url({cfg.icon}); mask-image: url({cfg.icon}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
    ></div>
  </div>
{/snippet}

