<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import Badge from '../components/Badge.svelte';
  import Avatar from '../components/Avatar.svelte';
  // Import route params from svelte-spa-router
  import { params } from 'svelte-spa-router';
  
  // State management
  let badge = $state(null);
  let loading = $state(true);
  let error = $state(null);
  
  // Mock badge data for development
  const mockBadges = {
    1: { 
      id: 1, 
      name: 'Node Runner', 
      description: 'Successfully ran a validator node for the GenLayer testnet with high uptime and good performance.',
      points: 100,
      actionId: 1,
      actionName: 'Node Runner',
      evidenceUrl: 'https://example.com/evidence/1',
      created_at: '2023-05-15T14:22:11Z',
      earners: [
        { id: 1, name: 'Alice Johnson', points: 100 },
        { id: 2, name: 'Bob Smith', points: 100 },
        { id: 3, name: 'Charlie Brown', points: 100 }
      ]
    },
    2: { 
      id: 2, 
      name: 'Bug Hunter', 
      description: 'Found and reported a critical bug in the GenLayer protocol, helping improve system security.',
      points: 150,
      actionId: 2,
      actionName: 'Bug Hunter',
      evidenceUrl: 'https://example.com/evidence/2',
      created_at: '2023-06-22T09:15:33Z',
      earners: [
        { id: 4, name: 'David Wang', points: 150 },
        { id: 5, name: 'Emily Chen', points: 150 }
      ]
    }
  };
  
  $effect(() => {
    const currentParams = $params;

    if (currentParams && currentParams.id) {
      fetchBadgeData(currentParams.id);
    } else {
      error = "Badge ID not provided";
      loading = false;
    }
  });

  async function fetchBadgeData(badgeId) {
    try {
      loading = true;
      error = null;
      
      // This would be a real API call in production
      // const res = await badgesAPI.getBadge(badgeId);
      // badge = res.data;
      
      // For now, use mock data
      setTimeout(() => {
        badge = mockBadges[badgeId] || null;
        if (!badge) {
          error = `Badge with ID ${badgeId} not found`;
        }
        loading = false;
      }, 500);
      
    } catch (err) {
      error = err.message || 'Failed to load badge data';
      loading = false;
    }
  }
  
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }
</script>

<div>
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if badge}
    <div class="bg-white shadow sm:rounded-lg mb-6">
      <div class="px-4 py-5 sm:px-6 flex flex-col sm:flex-row sm:justify-between sm:items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            Badge: {badge.name}
          </h1>
          <p class="mt-1 text-sm text-gray-500">
            Created on {formatDate(badge.created_at)}
          </p>
        </div>
        <div class="mt-4 sm:mt-0">
          <Badge 
            badge={badge} 
            size="lg" 
            color={badge.name === 'Bug Hunter' ? 'red' : badge.name === 'Node Runner' ? 'blue' : 'green'} 
            clickable={false} 
          />
        </div>
      </div>
      
      <div class="border-t border-gray-200 px-4 py-5 sm:p-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h2 class="text-lg font-medium text-gray-900 mb-3">Description</h2>
            <p class="text-gray-700">
              {badge.description}
            </p>
            
            <h2 class="text-lg font-medium text-gray-900 mt-6 mb-3">Details</h2>
            <dl class="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
              <div>
                <dt class="text-sm font-medium text-gray-500">Badge ID</dt>
                <dd class="mt-1 text-sm text-gray-900">{badge.id}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Points</dt>
                <dd class="mt-1 text-sm text-gray-900">{badge.points}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">Action Type</dt>
                <dd class="mt-1 text-sm text-gray-900">{badge.actionName}</dd>
              </div>
              {#if badge.evidenceUrl}
                <div>
                  <dt class="text-sm font-medium text-gray-500">Evidence</dt>
                  <dd class="mt-1 text-sm text-gray-900">
                    <a href={badge.evidenceUrl} target="_blank" rel="noopener noreferrer" class="text-primary-600 hover:text-primary-900">
                      View Evidence
                    </a>
                  </dd>
                </div>
              {/if}
            </dl>
          </div>
          
          <div>
            <h2 class="text-lg font-medium text-gray-900 mb-3">Badge Earners</h2>
            {#if badge.earners && badge.earners.length > 0}
              <div class="bg-white overflow-hidden rounded-md border border-gray-200">
                <ul class="divide-y divide-gray-200">
                  {#each badge.earners as earner}
                    <li class="px-4 py-3 flex items-center justify-between hover:bg-gray-50">
                      <div class="flex items-center gap-3">
                        <Avatar 
                          user={earner}
                          size="sm"
                          clickable={true}
                        />
                        <a 
                          href={`/participant/${earner.id}`} 
                          onclick={(e) => { e.preventDefault(); push(`/participant/${earner.id}`); }}
                          class="text-sm font-medium text-primary-600 hover:text-primary-900"
                        >
                          {earner.name}
                        </a>
                      </div>
                      <span class="text-sm text-gray-500">{earner.points} points</span>
                    </li>
                  {/each}
                </ul>
              </div>
            {:else}
              <p class="text-gray-500">No participants have earned this badge yet.</p>
            {/if}
          </div>
        </div>
      </div>
    </div>
  {:else}
    <div class="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
      Badge not found
    </div>
  {/if}
</div>