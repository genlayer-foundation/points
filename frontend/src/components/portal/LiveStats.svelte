<script>
  import { onMount } from 'svelte';
  import { statsAPI } from '../../lib/api';
  import CategoryIcon from './CategoryIcon.svelte';

  let stats = $state(null);
  let loading = $state(true);
  let error = $state(null);

  onMount(async () => {
    try {
      const response = await statsAPI.getDashboardStats();
      stats = response.data;
    } catch (err) {
      error = err.message || 'Failed to load stats';
    } finally {
      loading = false;
    }
  });

  function formatNumber(n) {
    if (n == null) return '—';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
  }

  const statConfigs = $derived([
    {
      key: 'contribution_count',
      label: 'Contributions Submitted',
      value: stats ? formatNumber(stats.contribution_count) : '—',
      delta: '+12%',
      category: 'genlayer',
    },
    {
      key: 'builder_count',
      label: 'Builders',
      value: stats ? formatNumber(stats.builder_count) : '—',
      delta: '+8%',
      category: 'builder',
    },
    {
      key: 'validator_count',
      label: 'Validators',
      value: stats ? formatNumber(stats.validator_count) : '—',
      delta: '+5%',
      category: 'validator',
    },
    {
      key: 'creator_count',
      label: 'Community Members',
      value: stats ? formatNumber(stats.creator_count ?? stats.participant_count) : '—',
      delta: '+15%',
      category: 'community',
    },
  ]);
</script>

<div>
  <div class="flex flex-col gap-1 mb-4">
    <div class="flex items-center gap-2">
      <h2 class="text-[20px] font-semibold text-gray-900" style="letter-spacing: 0.4px;">GenLayer Live</h2>
      <span class="w-2 h-2 rounded-full bg-[#3eb359]"></span>
    </div>
    <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">What's going on today in GenLayer?</p>
  </div>

  {#if loading}
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      {#each [1, 2, 3, 4] as _}
        <div class="bg-white rounded-[8px] border border-[#f0f0f0] h-[80px] flex items-center px-4 gap-3 animate-pulse">
          <div class="w-12 h-12 bg-gray-200 rounded-lg flex-shrink-0"></div>
          <div class="space-y-2 flex-1">
            <div class="h-8 bg-gray-200 rounded w-16"></div>
            <div class="h-3 bg-gray-100 rounded w-24"></div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
      Failed to load stats
    </div>
  {:else}
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      {#each statConfigs as stat}
        <div class="bg-white rounded-[8px] border border-[#f0f0f0] h-[80px] flex items-start justify-between overflow-hidden pr-4">
          <!-- Left: icon + value/label -->
          <div class="flex items-center h-full">
            <div class="flex items-center p-4">
              <CategoryIcon category={stat.category} mode="hexagon" size={48} />
            </div>
            <div class="flex flex-col justify-between h-full py-4 min-w-0">
              <p class="text-[32px] font-medium font-display text-black leading-[25px]" style="letter-spacing: -0.96px;">{stat.value}</p>
              <p class="text-[12px] text-[#6b6b6b] leading-[15px]" style="letter-spacing: 0.24px;">{stat.label}</p>
            </div>
          </div>

          <!-- Right: delta (top-aligned) -->
          <div class="flex items-center py-4">
            <img src="/assets/icons/arrow-up-s-line.svg" alt="" class="w-4 h-4">
            <span class="text-[14px] text-[#3eb359] leading-[16px]" style="letter-spacing: 0.28px;">{stat.delta}</span>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
