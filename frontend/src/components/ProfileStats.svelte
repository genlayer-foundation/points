<script>
  let {
    contributions = 0,
    points = 0,
    rank = null,
    colorTheme = 'sky'
  } = $props();

  const getBgColor = $derived(
    colorTheme === 'orange' ? 'bg-orange-50' :
    colorTheme === 'green' ? 'bg-green-50' :
    'bg-sky-50'
  );

  const getBorderColor = $derived(
    colorTheme === 'orange' ? 'border-orange-200' :
    colorTheme === 'green' ? 'border-green-200' :
    'border-sky-200'
  );

  const getIconBgColor = $derived(
    colorTheme === 'orange' ? 'bg-orange-100' :
    colorTheme === 'green' ? 'bg-green-100' :
    'bg-sky-100'
  );

  const getIconColor = $derived(
    colorTheme === 'orange' ? 'text-orange-600' :
    colorTheme === 'green' ? 'text-green-600' :
    'text-sky-600'
  );
</script>

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  <div class="{getBgColor} rounded-lg p-4 border {getBorderColor}">
    <div class="flex items-center">
      <div class="p-3 {getIconBgColor} rounded-lg mr-4">
        <svg class="w-5 h-5 {getIconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
        </svg>
      </div>
      <div>
        <p class="text-xs text-gray-500">Total Contributions</p>
        <p class="text-2xl font-bold text-gray-900 font-heading">{contributions}</p>
      </div>
    </div>
  </div>
  
  <div class="{getBgColor} rounded-lg p-4 border {getBorderColor}">
    <div class="flex items-center">
      <div class="p-3 {getIconBgColor} rounded-lg mr-4">
        <svg class="w-5 h-5 {getIconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
        </svg>
      </div>
      <div>
        <p class="text-xs text-gray-500">Total Points</p>
        <p class="text-2xl font-bold text-gray-900 font-heading">{points}</p>
      </div>
    </div>
  </div>
  
  <div class="{getBgColor} rounded-lg p-4 border {getBorderColor} sm:col-span-2 lg:col-span-1">
    <div class="flex items-center">
      <div class="p-3 {getIconBgColor} rounded-lg mr-4">
        <svg class="w-5 h-5 {getIconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
        </svg>
      </div>
      <div>
        <p class="text-xs text-gray-500">Current Rank</p>
        <p class="text-2xl font-bold text-gray-900 font-heading">#{rank || 'N/A'}</p>
      </div>
    </div>
  </div>
</div>