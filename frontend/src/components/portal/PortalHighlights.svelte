<script>
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../../lib/api.js';
  import HighlightsSlider from './HighlightsSlider.svelte';

  let { category = null, limit = 10, showHeader = true } = $props();

  let highlights = $state([]);
  let loading = $state(true);
  let requestSequence = 0;

  function getHighlightsPath() {
    const params = new URLSearchParams({ view: 'highlights' });
    if (category) params.set('category', category);
    return `/all-contributions?${params.toString()}`;
  }

  function getFeaturedSortTime(highlight) {
    const value = highlight?.featured_at || highlight?.created_at || highlight?.contribution_date;
    const time = value ? new Date(value).getTime() : 0;
    return Number.isNaN(time) ? 0 : time;
  }

  async function fetchHighlights() {
    const requestId = ++requestSequence;
    loading = true;
    try {
      const params = {};
      if (category) params.category = category;
      const response = await contributionsAPI.getAllHighlights(params);
      if (requestId !== requestSequence) return;
      const all = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      // Sort newest featured first and cap to `limit` so the slider always shows the latest highlights
      highlights = [...all]
        .sort((a, b) => getFeaturedSortTime(b) - getFeaturedSortTime(a))
        .slice(0, limit);
    } finally {
      if (requestId === requestSequence) loading = false;
    }
  }

  $effect(() => {
    void category;
    void limit;
    fetchHighlights();
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
        onclick={() => push(getHighlightsPath())}
        class="text-sm text-[#999] hover:text-black transition-colors"
      >Explore all →</button>
    </div>
  {/if}
  <HighlightsSlider {highlights} {loading} />
</div>
