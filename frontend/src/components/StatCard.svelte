<script>
  export let title;
  export let value;
  export let icon = null;
  export let color = 'blue';
  
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-500',
    green: 'bg-green-50 text-green-500',
    purple: 'bg-purple-50 text-purple-500',
    amber: 'bg-amber-50 text-amber-500',
    red: 'bg-red-50 text-red-500',
  };
  
  const iconBgClass = colorClasses[color] || colorClasses.blue;
</script>

<div class="bg-white overflow-hidden shadow rounded-lg">
  <div class="p-5">
    <div class="flex items-center">
      {#if icon}
        <div class={`flex-shrink-0 rounded-md p-3 ${iconBgClass}`}>
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icon} />
          </svg>
        </div>
      {/if}
      <div class={icon ? 'ml-5' : ''}>
        <p class="text-sm font-medium text-gray-500 truncate">
          {title}
        </p>
        <p class="mt-1 text-3xl font-semibold text-gray-900">
          {value}
        </p>
      </div>
    </div>
  </div>
</div>