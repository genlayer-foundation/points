<script>
  import CategoryIcon from '../portal/CategoryIcon.svelte';

  let { stats = [], loading = false, columns = 4 } = $props();

  let gridClass = $derived(
    columns === 3 ? 'grid grid-cols-2 md:grid-cols-3 gap-4' : 'grid grid-cols-2 md:grid-cols-4 gap-4'
  );

  function formatNumber(n) {
    if (n == null) return '\u2014';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
  }

  function formatDelta(d) {
    if (d == null || d === '') return '';
    const n = typeof d === 'number' ? d : parseInt(d);
    if (isNaN(n)) return d;
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
  }
</script>

{#if loading}
  <div class={gridClass}>
    {#each Array(columns) as _}
      <div class="bg-white rounded-[8px] border border-[#f0f0f0] h-[80px] flex items-center px-4 gap-3 animate-pulse">
        <div class="w-12 h-12 bg-gray-200 rounded-lg flex-shrink-0"></div>
        <div class="space-y-2 flex-1">
          <div class="h-8 bg-gray-200 rounded w-16"></div>
          <div class="h-3 bg-gray-100 rounded w-24"></div>
        </div>
      </div>
    {/each}
  </div>
{:else}
  <div class={gridClass}>
    {#each stats as stat}
      <div class="bg-white rounded-[8px] border border-[#f0f0f0] h-[80px] flex items-start justify-between pr-4">
        <div class="flex items-center h-full min-w-0 overflow-hidden">
          <div class="flex items-center p-4 flex-shrink-0">
            {#if stat.iconSrc}
              <img src={stat.iconSrc} alt="" class="flex-shrink-0" style="width: 48px; height: 48px;" />
            {:else}
              <CategoryIcon category={stat.category || 'genlayer'} hexCategory={stat.hexCategory} mode="hexagon" size={48} />
            {/if}
          </div>
          <div class="flex flex-col justify-between h-full py-4 min-w-0">
            <p class="text-[32px] font-medium font-display text-black leading-[25px] truncate" style="letter-spacing: -0.96px;">{formatNumber(stat.value)}</p>
            <p class="text-[12px] text-[#6b6b6b] leading-[15px] truncate" style="letter-spacing: 0.24px;">{stat.label}</p>
          </div>
        </div>
        {#if stat.delta}
          <div class="flex items-center py-4 flex-shrink-0">
            <img src="/assets/icons/arrow-up-s-line.svg" alt="" class="w-4 h-4 flex-shrink-0">
            <span class="text-[14px] text-[#3eb359] leading-[16px] whitespace-nowrap" style="letter-spacing: 0.28px;">{formatDelta(stat.delta)}</span>
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}
