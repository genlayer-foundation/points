<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../../lib/api.js';
  import HighlightsSlider from './HighlightsSlider.svelte';

  let { category = null, limit = 10, showHeader = true } = $props();

  let highlights = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      const params = {};
      if (category) params.category = category;
      const response = await contributionsAPI.getAllHighlights(params);
      const all = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      // Sort newest first and cap to `limit` so the slider always shows the latest highlights
      highlights = [...all]
        .sort((a, b) => new Date(b.contribution_date) - new Date(a.contribution_date))
        .slice(0, limit);
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
  <HighlightsSlider {highlights} {loading} />
</div>
