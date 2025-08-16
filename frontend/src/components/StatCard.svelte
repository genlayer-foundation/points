<script>
  let { 
    title, 
    value, 
    icon = null, 
    color = 'blue',
    className = ''
  } = $props();
  
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-500',
    green: 'bg-green-50 text-green-500',
    purple: 'bg-purple-50 text-purple-500',
    amber: 'bg-amber-50 text-amber-500',
    red: 'bg-red-50 text-red-500',
  };
  
  const iconBgClass = colorClasses[color] || colorClasses.blue;
</script>

<div class="bg-white shadow rounded-lg p-4 {className}">
  <div class="flex items-center">
    {#if icon}
      <div class={`flex-shrink-0 p-3 rounded-lg mr-4 ${iconBgClass}`}>
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icon} />
        </svg>
      </div>
    {/if}
    <div>
      <p class="text-sm text-gray-500">
        {title}
      </p>
      <p class="text-2xl font-bold text-gray-900">
        {value}
      </p>
    </div>
  </div>
</div>