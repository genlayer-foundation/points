<script>
  import { onMount, onDestroy } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { getCategoryColors } from '../lib/categoryColors.js';
  import Icons from './Icons.svelte';
  
  // State
  let highlights = $state([]);
  let loading = $state(true);
  let expandedHighlights = $state(new Set());
  let countdowns = $state({});
  let countdownInterval = null;

  async function fetchHighlights() {
    try {
      loading = true;
      const response = await contributionsAPI.getHighlights({
        category: $currentCategory !== 'global' ? $currentCategory : undefined
      });

      if (response.data?.results !== undefined) {
        highlights = response.data.results || [];
      } else {
        highlights = response.data || [];
      }

      // Sort by nearest end date
      highlights.sort((a, b) => {
        if (!a.end_date && !b.end_date) return 0;
        if (!a.end_date) return 1;
        if (!b.end_date) return -1;
        return new Date(a.end_date) - new Date(b.end_date);
      });

      // Initialize countdowns
      updateCountdowns();
    } catch (err) {
      console.error('Error loading highlights:', err);
      highlights = [];
    } finally {
      loading = false;
    }
  }

  function updateCountdowns() {
    const newCountdowns = {};
    highlights.forEach(highlight => {
      if (highlight.end_date) {
        newCountdowns[highlight.id] = getCountdown(highlight.end_date);
      }
    });
    countdowns = newCountdowns;
  }

  function getCountdown(endDate) {
    if (!endDate) return null;

    const now = new Date();
    const end = new Date(endDate);
    const diffMs = end - now;

    if (diffMs <= 0) return 'Ended';

    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);

    if (days > 0) {
      return `Ends in ${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `Ends in ${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `Ends in ${minutes}m ${seconds}s`;
    } else {
      return `Ends in ${seconds}s`;
    }
  }

  onMount(() => {
    fetchHighlights();
    // Update countdown every second
    countdownInterval = setInterval(updateCountdowns, 1000);
  });

  onDestroy(() => {
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
  });

  $effect(() => {
    if ($currentCategory) {
      fetchHighlights();
    }
  });

  function toggleExpanded(highlightId) {
    const newExpanded = new Set(expandedHighlights);
    if (newExpanded.has(highlightId)) {
      newExpanded.delete(highlightId);
    } else {
      newExpanded.add(highlightId);
    }
    expandedHighlights = newExpanded;
  }
</script>

{#if !loading && highlights.length > 0}
  {@const containerColors = getCategoryColors($currentCategory)}

  <!-- Highlights Container -->
  <div class="w-full {containerColors.statBg} rounded-lg px-5 py-5 mb-6 border {containerColors.borderLight}">
      <!-- Section Header -->
      <div class="mb-4">
        <div class="flex items-center gap-2 mb-1">
          <!-- Sparkle Icon -->
          <Icons name="sparkle" size="md" className="text-yellow-500" />
          <h2 class="text-lg font-medium {containerColors.textDark}">Highlights</h2>
        </div>
        <p class="text-sm {containerColors.textMedium}">Active opportunities to contribute right now.</p>
      </div>

      <!-- Highlight Cards -->
      <div class="space-y-2">
        {#each highlights as highlight}
          {@const category = highlight.contribution_type_details?.category || $currentCategory}
          {@const colors = getCategoryColors(category)}
          {@const isExpanded = expandedHighlights.has(highlight.id)}

          <div class="w-full {colors.expandBg} border {colors.borderLight} rounded-lg transition-all duration-300 ease-in-out p-3">
              <!-- Top row with chips -->
              <div class="flex items-center gap-2  flex-wrap mb-2">
                <!-- Contribution type chip -->
                <button
                  onclick={() => push(`/contribution-type/${highlight.contribution_type}`)}
                  class="inline-flex items-center px-2.5 py-1 {colors.statBg} {colors.text} text-xs font-medium rounded-full transition-colors hover:opacity-80"
                >
                  {highlight.contribution_type_details?.name || 'Contribution'}
                </button>

                <!-- Countdown timer -->
                {#if highlight.end_date && countdowns[highlight.id]}
                  <span class="inline-flex items-center px-2.5 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-full font-mono">
                    {countdowns[highlight.id]}
                  </span>
                {/if}
              </div>

              <!-- Main content with button -->
              <div class="flex items-start gap-4">
                <!-- Left: Title and description -->
                <div class="flex-1">
                  <!-- Title -->
                  <h3 class="text-base font-semibold {colors.textDark} mb-1">
                    {highlight.name}
                  </h3>

                  <!-- Description section -->
                  {#if highlight.expanded_description && highlight.expanded_description !== highlight.short_description}
                    <!-- Clickable description with expand/collapse -->
                    <button
                      onclick={() => toggleExpanded(highlight.id)}
                      class="w-full text-left group"
                    >
                      <div class="overflow-hidden transition-all duration-300 ease-in-out" style="max-height: {isExpanded ? '500px' : '3.5rem'}">
                        {#if !isExpanded}
                          <p class="text-sm {colors.textMedium} leading-relaxed inline">
                            {highlight.short_description}
                            <svg class="w-4 h-4 inline-block ml-1 {colors.text} opacity-50 group-hover:opacity-100 transition-all duration-300 {isExpanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                            </svg>
                          </p>
                        {:else}
                          <p class="text-sm {colors.textMedium} leading-relaxed">
                            {highlight.expanded_description}
                            <svg class="w-4 h-4 inline-block ml-1 {colors.text} opacity-50 group-hover:opacity-100 transition-all duration-300 {isExpanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                            </svg>
                          </p>
                        {/if}
                      </div>
                    </button>
                  {:else}
                    <!-- Non-expandable description -->
                    <div class="overflow-hidden" style="max-height: 3.5rem">
                      <p class="text-sm {colors.textMedium} leading-relaxed line-clamp-2">
                        {highlight.short_description || ''}
                      </p>
                    </div>
                  {/if}
                </div>

                <!-- Right: Submit button -->
                <div class="flex items-center h-full">
                  <button
                    onclick={() => push(`/submit-contribution?type=${highlight.contribution_type}`)}
                    class="px-5 py-2 {colors.bg} text-white font-medium rounded-md transition-colors shadow-sm hover:shadow hover:opacity-90 whitespace-nowrap"
                  >
                    Submit Contribution
                  </button>
                </div>
              </div>
            </div>
        {/each}
      </div>
  </div>
{:else if loading}
  {@const loadingColors = getCategoryColors($currentCategory)}
  <!-- Loading state -->
  <div class="w-full {loadingColors.statBg} rounded-lg px-5 py-5 mb-6 border {loadingColors.borderLight}">
    <div class="mb-4">
      <div class="flex items-center gap-2 mb-1">
        <div class="h-5 w-5 bg-yellow-300 rounded animate-pulse"></div>
        <div class="h-6 w-24 {loadingColors.bg} opacity-30 rounded animate-pulse"></div>
      </div>
      <div class="h-4 w-64 {loadingColors.bg} opacity-30 rounded animate-pulse"></div>
    </div>
    <div class="{loadingColors.expandBg} border {loadingColors.borderLight} rounded-lg p-3">
      <div class="flex items-center gap-2 mb-2">
        <div class="h-6 w-20 {loadingColors.statBg} rounded-full animate-pulse"></div>
        <div class="h-6 w-24 bg-amber-100 rounded-full animate-pulse"></div>
      </div>
      <div class="flex items-start gap-4">
        <div class="flex-1">
          <div class="h-5 w-3/4 {loadingColors.bg} opacity-30 rounded animate-pulse mb-2"></div>
          <div class="space-y-2">
            <div class="h-4 w-full {loadingColors.bg} opacity-20 rounded animate-pulse"></div>
            <div class="h-4 w-2/3 {loadingColors.bg} opacity-20 rounded animate-pulse"></div>
          </div>
        </div>
        <div class="h-10 w-32 {loadingColors.bg} opacity-50 rounded-md animate-pulse"></div>
      </div>
    </div>
  </div>
{/if}

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>