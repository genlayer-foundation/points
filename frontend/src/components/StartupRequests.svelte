<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import { showError } from '../lib/toastStore';
  import { currentCategory } from '../stores/category.js';
  import { getPioneerContributionsColors } from '../lib/categoryColors.js';
  import Icons from './Icons.svelte';

  // State
  let startupRequests = $state([]);
  let loading = $state(true);

  async function fetchStartupRequests() {
    try {
      loading = true;
      const response = await contributionsAPI.getStartupRequests();

      if (response.data?.results !== undefined) {
        startupRequests = response.data.results || [];
      } else {
        startupRequests = response.data || [];
      }
    } catch (err) {
      showError('Failed to load startup requests.');
      startupRequests = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchStartupRequests();
  });
</script>

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>

{#if !loading && startupRequests.length > 0}
  {@const colors = getPioneerContributionsColors($currentCategory)}

  <!-- Card container matching Missions style -->
  <div class="bg-white border border-gray-200 border-l-4 {colors.containerBorderLeft} shadow-sm overflow-hidden rounded-lg mb-6">
    <!-- Header -->
    <div class="px-4 py-5 sm:px-6 bg-white border-b border-gray-200">
      <div class="flex items-center">
        <Icons name="sparkle" size="md" className="{colors.headerIcon} mr-2" />
        <h2 class="text-xl font-bold text-gray-900">Request for Startups</h2>
      </div>
      <p class="mt-1 text-sm text-gray-600 leading-snug">
        Startup ideas we believe could thrive in the GenLayer ecosystem.<br>
        The GenLayer team is ready to support founders by opening doors and providing guidance.
      </p>
    </div>

    <!-- Startup requests list -->
    {#each startupRequests as request}
      <div class="px-4 py-3 border-b last:border-b-0 hover:bg-gray-50 transition-colors">
        <!-- Title row -->
        <div class="flex items-center gap-3 mb-2">
          <button
            onclick={() => push(`/builders/startup-requests/${request.id}`)}
            class="text-base font-bold font-heading text-gray-900 {colors.titleTextHover} transition-colors text-left"
          >
            {request.title}
          </button>

          <button
            onclick={() => push(`/builders/startup-requests/${request.id}`)}
            class="ml-auto flex-shrink-0 text-sm font-normal {colors.titleText} {colors.titleTextHover} transition-colors"
          >
            View Details →
          </button>
        </div>

        <!-- Description -->
        <p class="text-sm text-gray-600 line-clamp-2">
          {request.short_description}
        </p>
      </div>
    {/each}
  </div>
{:else if loading}
  <!-- Loading state matching Missions style -->
  <div class="mb-4">
    <div class="flex items-center">
      <div class="h-6 w-6 bg-gray-300 rounded animate-pulse mr-2"></div>
      <div class="h-6 w-40 bg-gray-300 rounded animate-pulse"></div>
    </div>
    <div class="mt-2 h-4 w-64 bg-gray-200 rounded animate-pulse"></div>
  </div>
  <div class="space-y-3">
    <div class="bg-white border border-gray-200 rounded-lg p-4">
      <div class="h-4 bg-gray-200 rounded animate-pulse mb-2"></div>
      <div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
    </div>
  </div>
{/if}
