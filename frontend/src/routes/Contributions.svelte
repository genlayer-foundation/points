<script>
  import ContributionTypeStats from '../components/ContributionTypeStats.svelte';
  import Missions from '../components/Missions.svelte';
  import StartupRequests from '../components/StartupRequests.svelte';
  import RecentContributions from '../components/RecentContributions.svelte';
  import { currentCategory } from '../stores/category.js';

  // Derive title and view all URL from current category
  let title = $derived($currentCategory === 'global' ? 'Recent Contributions' :
                     $currentCategory === 'validator' ? 'Recent Validator Contributions' :
                     $currentCategory === 'builder' ? 'Recent Builder Contributions' :
                     'Recent Contributions');
  let viewAllUrl = $derived($currentCategory === 'global' ? '/all-contributions' :
                           `/all-contributions?category=${$currentCategory}`);
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900">Contributions</h1>
  </div>

  <!-- Request for Startups (only for builders) -->
  {#if $currentCategory === 'builder'}
    <StartupRequests />
  {/if}

  <Missions />

  <!-- Contribution Type Statistics -->
  <ContributionTypeStats />

  <!-- Recent Contributions -->
  <div>
    <RecentContributions
      {title}
      limit={5}
      userId={null}
      showHeader={true}
      showViewAll={true}
      viewAllPath={viewAllUrl}
      viewAllText="View All →"
      className="px-4"
    />
  </div>
</div>