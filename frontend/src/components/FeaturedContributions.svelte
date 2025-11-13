<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { contributionsAPI, usersAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import Avatar from './Avatar.svelte';
  import Badge from './Badge.svelte';
  import ContributionCard from './ContributionCard.svelte';

  let {
    title = 'Featured Contributions',
    subtitle = null,
    limit = 3,
    userId = null,
    contributionTypeId = null,
    category = null, // Can be passed in or will use currentCategory
    showViewAll = true,
    viewAllPath = '/highlights',
    viewAllText = 'View All →',
    showHeader = true,
    cardStyle = 'default', // 'default', 'compact', 'highlight'
    className = '',
    isOwnProfile = false,
    hideWhenEmpty = false,
    colorTheme = null // 'orange' for builder, 'sky' for validator, null for default
  } = $props();

  let highlights = $state([]);
  let loading = $state(true);
  let error = $state(null);

  // Determine button colors based on theme
  const buttonClasses = $derived(
    colorTheme === 'orange'
      ? 'border-orange-300 text-orange-700 bg-orange-100 hover:bg-orange-200 hover:border-orange-400'
      : colorTheme === 'sky'
      ? 'border-sky-300 text-sky-700 bg-sky-100 hover:bg-sky-200 hover:border-sky-400'
      : 'border-primary-200 text-primary-700 bg-primary-50 hover:bg-primary-100 hover:border-primary-300'
  );

  // Determine contribution type badge colors based on theme
  const contributionTypeBadgeClasses = $derived(
    colorTheme === 'orange'
      ? 'bg-orange-100 text-orange-800'
      : colorTheme === 'sky'
      ? 'bg-sky-100 text-sky-800'
      : 'bg-primary-100 text-primary-800'
  );

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };

  async function fetchHighlights() {
    try {
      loading = true;
      let response;
      
      // Use passed category or current category
      const filterCategory = category || $currentCategory;
      
      if (userId) {
        // Fetch user-specific highlights
        const params = { limit };
        if (filterCategory && filterCategory !== 'global') {
          params.category = filterCategory;
        }
        response = await usersAPI.getUserHighlights(userId, params);
      } else if (contributionTypeId) {
        // Fetch contribution type specific highlights
        response = await contributionsAPI.getContributionTypeHighlights(contributionTypeId);
      } else {
        // Fetch all highlights with category filter
        const params = { limit: limit || 10 };
        if (filterCategory && filterCategory !== 'global') {
          params.category = filterCategory;
        }
        response = await contributionsAPI.getAllHighlights(params);
      }
      
      highlights = response.data || [];
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load featured contributions';
      loading = false;
    }
  }

  // Compute the correct view all path based on category
  function getViewAllPath() {
    const cat = category || $currentCategory;
    if (cat === 'builder') {
      return '/builders/contributions/highlights';
    } else if (cat === 'validator') {
      return '/validators/contributions/highlights';
    } else {
      return '/contributions/highlights';
    }
  }

  // Fetch highlights when category changes (including initial mount)
  let previousCategory = $state(null);
  
  $effect(() => {
    const filterCategory = category || $currentCategory;
    if (filterCategory && filterCategory !== previousCategory) {
      previousCategory = filterCategory;
      fetchHighlights();
    }
  });
</script>

{#if loading || error || highlights.length > 0 || !hideWhenEmpty}
<div class={className}>
  {#if showHeader}
    <div class="flex justify-between items-center mb-4">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
        {#if subtitle}
          <p class="mt-1 text-sm text-gray-500">{subtitle}</p>
        {/if}
      </div>
      {#if showViewAll && highlights.length > 0}
        <button
          onclick={() => push(getViewAllPath())}
          class="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          {viewAllText}
        </button>
      {/if}
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      <p>{error}</p>
    </div>
  {:else if highlights.length === 0}
    {#if hideWhenEmpty}
      <!-- Don't render anything when empty and hideWhenEmpty is true -->
    {:else if isOwnProfile}
      <div class="py-4">
        <div>
          <p class="text-sm text-gray-700 mb-3">
            <span class="font-heading font-semibold text-gray-900">Get Highlighted!</span> Submit impactful or pioneering work to get featured.
          </p>
          <button
            onclick={() => push('/submit-contribution')}
            class="inline-flex items-center px-4 py-2 border {buttonClasses} text-sm font-medium rounded-lg transition-all duration-200 shadow-sm hover:shadow"
          >
            <svg class="w-5 h-5 mr-2 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
            </svg>
            Submit Contribution
          </button>
        </div>
      </div>
    {:else}
      <div class="py-4">
        <div class="flex items-center gap-2">
          <svg class="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
          <p class="text-sm text-gray-500">No featured contributions yet</p>
        </div>
      </div>
    {/if}
  {:else if cardStyle === 'default'}
    <!-- Default card style (used in Dashboard) - Use ContributionCard -->
    <div class="space-y-3">
      {#each highlights as highlight}
        <ContributionCard 
          contribution={{
            id: highlight.id,
            contribution_type: highlight.contribution_type,
            contribution_type_name: highlight.contribution_type_name,
            contribution_type_details: {
              id: highlight.contribution_type,
              name: highlight.contribution_type_name,
              category: highlight.category || category || $currentCategory
            },
            contribution_date: highlight.contribution_date,
            points: highlight.contribution_points,
            frozen_points: highlight.contribution_points,
            user_details: {
              name: highlight.user_name,
              address: highlight.user_address,
              profile_image_url: highlight.user_profile_image_url,
              validator: highlight.user_validator,
              builder: highlight.user_builder,
              steward: highlight.user_steward,
              has_validator_waitlist: highlight.user_has_validator_waitlist,
              has_builder_welcome: highlight.user_has_builder_welcome
            },
            users: [{
              name: highlight.user_name,
              address: highlight.user_address,
              profile_image_url: highlight.user_profile_image_url
            }],
            highlight: {
              title: highlight.title,
              description: highlight.description
            },
            mission: highlight.mission_name ? {
              id: highlight.mission_id,
              name: highlight.mission_name
            } : null,
            count: 1,
            category: highlight.category || category || $currentCategory
          }}
          showUser={true}
          showExpand={false}
          category={category || $currentCategory}
        />
      {/each}
    </div>
  {:else if cardStyle === 'compact'}
    <!-- Compact style (used in ContributionTypeDetail) -->
    {#if highlights.length > 0}
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex items-center mb-4">
          <svg class="w-5 h-5 text-yellow-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
          <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
        </div>
        <div class="space-y-3">
          {#each highlights as highlight}
          <div class="border-l-4 border-yellow-400 pl-4 py-2">
          <h3 class="font-semibold text-gray-900">{highlight.title}</h3>
          <p class="text-sm text-gray-600 mt-1">{highlight.description}</p>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <Avatar
              user={{
                name: highlight.user_name,
                address: highlight.user_address,
                profile_image_url: highlight.user_profile_image_url,
                validator: highlight.user_validator,
                builder: highlight.user_builder,
                steward: highlight.user_steward,
                has_validator_waitlist: highlight.user_has_validator_waitlist,
                has_builder_welcome: highlight.user_has_builder_welcome
              }}
              size="xs"
              clickable={true}
            />
            <button
              class="hover:text-purple-600"
              onclick={() => push(`/participant/${highlight.user_address}`)}
            >
              {highlight.user_name || `${highlight.user_address.slice(0, 6)}...${highlight.user_address.slice(-4)}`}
            </button>
            <span>•</span>
            <span>{formatDate(highlight.contribution_date)}</span>
            <span>•</span>
            <span class="font-semibold text-purple-600">{highlight.contribution_points} pts</span>
            <span>•</span>
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {contributionTypeBadgeClasses}">
              {highlight.contribution_type_name || 'Contribution'}
            </span>
            {#if highlight.mission_name}
              <span>•</span>
              <Badge
                badge={{
                  id: null,
                  name: highlight.mission_name,
                  description: '',
                  points: 0,
                  actionId: null,
                  actionName: '',
                  evidenceUrl: ''
                }}
                color="indigo"
                size="sm"
                clickable={false}
                bold={false}
              />
            {/if}
          </div>
        </div>
          {/each}
        </div>
      </div>
    {/if}
  {:else if cardStyle === 'highlight'}
    <!-- Highlight style (used in ParticipantProfile) -->
    <div class="space-y-4">
      {#each highlights as highlight}
        <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <h4 class="text-lg font-semibold text-gray-900">{highlight.title}</h4>
              <p class="mt-2 text-sm text-gray-700">{highlight.description}</p>
              <div class="mt-3 flex items-center gap-4 text-xs text-gray-600">
                <div class="flex items-center gap-2">
                  <Avatar
                    user={{
                      name: highlight.user_name,
                      address: highlight.user_address,
                      profile_image_url: highlight.user_profile_image_url,
                      validator: highlight.user_validator,
                      builder: highlight.user_builder,
                      steward: highlight.user_steward,
                      has_validator_waitlist: highlight.user_has_validator_waitlist,
                      has_builder_welcome: highlight.user_has_builder_welcome
                    }}
                    size="xs"
                    clickable={true}
                  />
                  <button 
                    class="text-primary-600 hover:text-primary-700 font-medium"
                    onclick={() => push(`/participant/${highlight.user_address}`)}
                  >
                    {highlight.user_name || `${highlight.user_address.slice(0, 6)}...${highlight.user_address.slice(-4)}`}
                  </button>
                </div>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {contributionTypeBadgeClasses}">
                  {highlight.contribution_type_name || 'Contribution'}
                </span>
                {#if highlight.mission_name}
                  <Badge
                    badge={{
                      id: null,
                      name: highlight.mission_name,
                      description: '',
                      points: 0,
                      actionId: null,
                      actionName: '',
                      evidenceUrl: ''
                    }}
                    color="indigo"
                    size="sm"
                    clickable={false}
                    bold={false}
                  />
                {/if}
                <span>{highlight.contribution_points} points</span>
                <span>{formatDate(highlight.contribution_date)}</span>
              </div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
{/if}