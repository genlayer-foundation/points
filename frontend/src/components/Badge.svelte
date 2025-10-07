<script>
  import { push } from 'svelte-spa-router';
  
  export let badge = {
    id: null,
    name: 'Unknown',
    description: '',
    points: 0,
    actionId: null,
    actionName: '',
    evidenceUrl: ''
  };
  export let color = 'green'; // default color
  export let size = 'md'; // sm, md, lg
  export let clickable = true;
  export let bold = true; // whether to use bold font

  // Handle navigation to badge details
  function navigateToBadgeDetail() {
    if (clickable && badge.id) {
      // Hide any visible tooltips before navigation
      const tooltip = document.getElementById('custom-tooltip');
      const arrow = document.getElementById('custom-tooltip-arrow');
      
      if (tooltip) tooltip.style.opacity = '0';
      if (arrow) arrow.style.opacity = '0';
      
      if (badge.actionId && !badge.points) {
        // If this is an action type badge (like in ContributionsList)
        push(`/contribution-type/${badge.actionId}`);
      } else {
        // This is a real badge
        push(`/badge/${badge.id}`);
      }
    }
  }

  // Size classes
  const sizeClasses = {
    sm: 'px-2.5 py-1.5 text-xs',
    md: 'px-3.5 py-2 text-sm',
    lg: 'px-4 py-2.5 text-base'
  };

  // Color classes for different badge types
  const colorClasses = {
    green: 'bg-green-100 text-green-800 hover:bg-green-200',
    blue: 'bg-blue-100 text-blue-800 hover:bg-blue-200',
    purple: 'bg-purple-100 text-purple-800 hover:bg-purple-200',
    red: 'bg-red-100 text-red-800 hover:bg-red-200',
    yellow: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
    indigo: 'bg-indigo-100 text-indigo-800 hover:bg-indigo-200',
    pink: 'bg-pink-100 text-pink-800 hover:bg-pink-200',
    gray: 'bg-gray-100 text-gray-800 hover:bg-gray-200',
    orange: 'bg-orange-100 text-orange-800 hover:bg-orange-200',
  };
</script>

<a 
  href={clickable && badge.id ? (badge.actionId && !badge.points ? `/contribution-type/${badge.actionId}` : `/badge/${badge.id}`) : '#'}
  onclick={(e) => { 
    e.preventDefault(); 
    // Immediately hide any tooltips
    const tooltip = document.getElementById('custom-tooltip');
    const arrow = document.getElementById('custom-tooltip-arrow');
    if (tooltip) {
      tooltip.style.opacity = '0';
      tooltip.style.display = 'none';
    }
    if (arrow) {
      arrow.style.opacity = '0';
      arrow.style.display = 'none';
    }
    // Small delay to ensure tooltip is hidden before navigation
    setTimeout(() => navigateToBadgeDetail(), 50);
  }}
  class="inline-block {bold ? 'font-semibold' : 'font-normal'} rounded-lg {sizeClasses[size]} {colorClasses[color]} {clickable ? 'cursor-pointer transition-colors' : ''} {badge.description ? 'tooltip' : ''} whitespace-normal text-left max-w-[300px]"
  title={badge.description || ''}
>
  <span class="block">
    {badge.actionName || badge.name}
    {#if badge.points > 0}
      <span class="ml-1 font-normal">({badge.points}pts)</span>
    {/if}
  </span>
</a>