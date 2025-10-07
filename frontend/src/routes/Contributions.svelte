<script>
  import ContributionTypeStats from '../components/ContributionTypeStats.svelte';
  import Missions from '../components/Missions.svelte';
  import ContributionsTable from '../components/ContributionsTable.svelte';
  import { currentCategory } from '../stores/category.js';

  // Derive category and view all URL from current category
  let category = $derived($currentCategory === 'global' ? null : $currentCategory);
  let title = $derived($currentCategory === 'global' ? 'Recent Contributions' :
                     $currentCategory === 'validator' ? 'Recent Validator Contributions' :
                     $currentCategory === 'builder' ? 'Recent Builder Contributions' :
                     'Recent Contributions');
  let subtitle = $derived($currentCategory === 'global' ? 'Latest 5 contributions' :
                         `Latest 5 ${$currentCategory} contributions`);
  let viewAllUrl = $derived($currentCategory === 'global' ? '/all-contributions' :
                           `/all-contributions?category=${$currentCategory}`);
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900">Contributions</h1>
  </div>

  <Missions />

  <!-- Contribution Type Statistics -->
  <ContributionTypeStats />

  <!-- Recent Contributions Table -->
  <ContributionsTable
    title={title}
    subtitle={subtitle}
    category={category}
    limit={5}
    showParticipantColumn={true}
    viewAllUrl={viewAllUrl}
  />
</div>