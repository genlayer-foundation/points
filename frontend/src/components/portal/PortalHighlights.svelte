<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { contributionsAPI } from '../../lib/api.js';

  let { category = null, limit = 10, showHeader = true } = $props();

  let highlights = $state([]);
  let loading = $state(true);
  let error = $state(null);

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };

  // Get colors based on category
  function getCategoryColors(category) {
    if (category === 'builder') {
      return {
        pillBg: 'rgba(238,141,36,0.1)',
        pillText: '#ee8d24',
        tagBorder: '#ee8d24',
        tagText: '#ee8d24',
      };
    }
    // validator, steward, or default
    return {
      pillBg: 'rgba(79,118,246,0.1)',
      pillText: '#4f76f6',
      tagBorder: '#4f76f6',
      tagText: '#4f76f6',
    };
  }

  onMount(async () => {
    try {
      const params = { limit };
      if (category) params.category = category;
      const response = await contributionsAPI.getAllHighlights(params);
      highlights = response.data || [];
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  });
</script>

<div>
  {#if showHeader}
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: -0.4px;">Highlighted Contributions</h2>
        <p class="text-sm text-[#999]">Outstanding community contributions</p>
      </div>
      <button
        onclick={() => push('/contributions/highlights')}
        class="text-sm text-[#999] hover:text-black transition-colors"
      >Explore all →</button>
    </div>
  {/if}

  {#if loading}
    <div class="flex gap-2.5 overflow-x-auto pb-2">
      {#each [1, 2, 3] as _}
        <div class="flex-shrink-0 w-[300px] h-[180px] rounded-[8px] bg-gray-100 animate-pulse"></div>
      {/each}
    </div>
  {:else if highlights.length === 0}
    <div class="flex gap-2.5 overflow-x-auto pb-2">
      <div class="flex-shrink-0 w-[300px] h-[180px] rounded-[8px] bg-gray-50 flex items-center justify-center">
        <span class="text-sm text-gray-400">No highlights yet</span>
      </div>
    </div>
  {:else}
    <div class="flex gap-2.5 overflow-x-auto pb-2" style="-ms-overflow-style: none; scrollbar-width: none;">
      {#each highlights as highlight}
        {@const category = highlight.contribution_type_category || 'validator'}
        {@const colors = getCategoryColors(category)}
        <button
          onclick={() => push(`/contribution/${highlight.contribution}`)}
          class="flex-shrink-0 w-[300px] h-[180px] rounded-[8px] p-4 flex flex-col gap-2 text-left hover:shadow-md transition-shadow cursor-pointer"
          style="border: 1px solid #f5f5f5;"
        >
          <!-- Top row: avatar + username | points pill -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              {#if highlight.user_profile_image_url}
                <img src={highlight.user_profile_image_url} alt="" class="w-6 h-6 rounded-full">
              {:else}
                <div class="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-medium text-gray-500">
                  {(highlight.user_name || '?')[0].toUpperCase()}
                </div>
              {/if}
              <span class="text-sm font-medium text-black">
                {highlight.user_name || `${highlight.user_address?.slice(0, 6)}...`}
              </span>
            </div>
            <span
              class="text-xs font-medium px-2 py-0.5 rounded-full"
              style="background: {colors.pillBg}; color: {colors.pillText};"
            >
              {highlight.contribution_points} pts
            </span>
          </div>

          <!-- Middle: title + description -->
          <div class="flex-1 min-h-0 overflow-hidden">
            <h3 class="text-sm font-medium text-black truncate">{highlight.title}</h3>
            <p class="text-xs mt-1 line-clamp-3" style="color: #6b6b6b;">
              {highlight.description}
            </p>
          </div>

          <!-- Bottom row: category tag + date -->
          <div class="flex items-center justify-between">
            <span
              class="text-xs px-2 py-0.5 rounded-full"
              style="border: 1px solid {colors.tagBorder}; color: {colors.tagText};"
            >
              {highlight.contribution_type_name || 'Contribution'}
            </span>
            <span class="text-xs" style="color: #bababa;">
              {formatDate(highlight.contribution_date)}
            </span>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>
