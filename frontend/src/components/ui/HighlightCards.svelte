<script>
  import Avatar from '../Avatar.svelte';

  let { highlights = [], loading = false, layout = 'grid', category = 'builder' } = $props();

  const categoryColors = {
    builder:   { bg: '#FFF3E8', text: '#EE8521' },
    validator: { bg: '#E8F0FF', text: '#387DE8' },
    community: { bg: '#F3EDFF', text: '#7F52E1' },
    steward:   { bg: '#E8FFF0', text: '#19A663' },
  };

  let containerClass = $derived(
    layout === 'scroll'
      ? 'flex gap-2.5 overflow-x-auto pb-2'
      : 'grid grid-cols-1 md:grid-cols-3 gap-2.5'
  );

  let cardWidthClass = $derived(
    layout === 'scroll' ? 'w-[300px] flex-shrink-0' : ''
  );

  function getUserObj(h) {
    return {
      name: h.user_name,
      address: h.user_address,
      profile_image_url: h.user_profile_image_url,
    };
  }

  function formatDate(dateString) {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateString;
    }
  }

  function getColors(cat) {
    return categoryColors[cat] || categoryColors.builder;
  }

  function formatPoints(pts) {
    if (pts == null) return '0';
    if (pts >= 1000000) return (pts / 1000000).toFixed(1) + 'M';
    if (pts >= 1000) return (pts / 1000).toFixed(1) + 'K';
    return pts.toString();
  }
</script>

{#if loading}
  <div class={containerClass} style="-ms-overflow-style: none; scrollbar-width: none;">
    {#each [1, 2, 3] as _}
      <div class="{cardWidthClass} h-[160px] rounded-[8px] bg-gray-100 animate-pulse"></div>
    {/each}
  </div>
{:else if highlights.length === 0}
  <div class={containerClass}>
    <div class="{cardWidthClass} h-[160px] rounded-[8px] bg-gray-50 flex items-center justify-center">
      <span class="text-sm text-gray-400">No highlights yet</span>
    </div>
  </div>
{:else}
  <div class={containerClass} style="-ms-overflow-style: none; scrollbar-width: none;">
    {#each highlights as highlight}
      {@const cat = highlight.contribution_type_category || category}
      {@const colors = getColors(cat)}
      <div class="{cardWidthClass} h-[160px] rounded-[8px] p-4 flex flex-col gap-2"
        style="background: {colors.bg};"
      >
        <!-- Top: avatar + username | points pill + highlight star -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Avatar user={getUserObj(highlight)} size="xs" clickable={false} />
            <span class="text-[12px] font-medium text-[#bbb]">
              {highlight.user_name || `${highlight.user_address?.slice(0, 6)}...`}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span
              class="text-xs font-medium px-2 py-0.5 rounded-full"
              style="background: rgba(255,255,255,0.6); color: {colors.text};"
            >
              {formatPoints(highlight.contribution_points)} pts
            </span>
            <div class="relative w-[32px] h-[32px] flex-shrink-0">
              <img src="/assets/icons/hexagon-highlight.svg" alt="" class="w-full h-full" />
              <div
                class="absolute inset-0 m-auto w-[16px] h-[16px]"
                style="background-color: #FFFFFF; -webkit-mask-image: url(/assets/icons/star-line.svg); mask-image: url(/assets/icons/star-line.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
              ></div>
            </div>
          </div>
        </div>

        <!-- Middle: title + description -->
        <div class="flex-1 min-h-0 overflow-hidden">
          <h3 class="text-[14px] font-semibold text-black line-clamp-1">
            {highlight.title || highlight.contribution_type_name || 'Contribution'}
          </h3>
          <p class="text-[12px] mt-1 text-[#6b6b6b] line-clamp-2">
            {highlight.description || ''}
          </p>
        </div>

        <!-- Bottom: category pill + date -->
        <div class="flex items-center justify-between">
          <span
            class="text-xs px-2 py-0.5 rounded-full"
            style="border: 1px solid {colors.text}; color: {colors.text};"
          >
            {highlight.contribution_type_name || cat}
          </span>
          <span class="text-[12px] text-[#999]">
            {formatDate(highlight.contribution_date)}
          </span>
        </div>
      </div>
    {/each}
  </div>
{/if}
