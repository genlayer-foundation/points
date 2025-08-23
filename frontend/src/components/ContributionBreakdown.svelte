<script>
  import { push } from 'svelte-spa-router';
  
  let {
    contributionTypes = [],
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

  const getPointsBgColor = $derived(
    colorTheme === 'orange' ? 'bg-orange-100 text-orange-800' :
    colorTheme === 'green' ? 'bg-green-100 text-green-800' :
    'bg-sky-100 text-sky-800'
  );

  const getDotColor = $derived(
    colorTheme === 'orange' ? 'bg-orange-500' :
    colorTheme === 'green' ? 'bg-green-500' :
    'bg-sky-500'
  );

  const getHoverColor = $derived(
    colorTheme === 'orange' ? 'hover:text-orange-600' :
    colorTheme === 'green' ? 'hover:text-green-600' :
    'hover:text-sky-600'
  );
</script>

{#if contributionTypes && contributionTypes.length > 0}
  <div>
    <div class="mb-4">
      <h3 class="text-lg leading-6 font-medium text-gray-900">
        Contribution Breakdown
      </h3>
      <p class="mt-1 text-sm text-gray-500">
        Points distribution across contribution types
      </p>
    </div>
    
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each contributionTypes as type}
        <div class="{getBgColor} border {getBorderColor} rounded-lg p-4 hover:shadow-md transition-shadow">
          <div class="flex flex-col h-full">
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <div class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 {getDotColor}">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 6v12m6-6H6"></path>
                  </svg>
                </div>
                <h3 class="text-sm font-semibold text-gray-900 truncate">
                  <button
                    class="{getHoverColor} transition-colors"
                    onclick={() => push(`/contribution-type/${type.id}`)}
                  >
                    {type.name}
                  </button>
                </h3>
              </div>
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {getPointsBgColor} ml-2 flex-shrink-0">
                {type.total_points} pts
              </span>
            </div>
            
            <div class="text-xs text-gray-500 mb-2">
              {#if type.count > 1}
                × {type.count} contributions
              {:else}
                × 1 contribution
              {/if}
            </div>
            
            <div class="flex items-center gap-2 mt-auto">
              <div class="flex-1 bg-gray-200 rounded-full h-2">
                <div 
                  class="h-2 rounded-full transition-all duration-300"
                  class:bg-purple-500={type.percentage >= 40}
                  class:bg-blue-500={type.percentage >= 25 && type.percentage < 40}
                  class:bg-green-500={type.percentage >= 10 && type.percentage < 25}
                  class:bg-gray-400={type.percentage < 10}
                  style={`width: ${type.percentage || 0}%`}
                ></div>
              </div>
              <span class="text-xs text-gray-600 font-medium min-w-[2.5rem] text-right">
                {type.percentage != null ? type.percentage.toFixed(0) : 0}%
              </span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  </div>
{/if}