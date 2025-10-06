<script>
  // Component props
  let { children, tooltipText, position = 'bottom' } = $props();

  let targetElement = $state(null);
  let showTooltip = $state(false);
  let tooltipPosition = $state({ top: 0, left: 0 });

  function updateTooltipPosition() {
    if (targetElement && showTooltip) {
      const rect = targetElement.getBoundingClientRect();

      if (position === 'bottom') {
        tooltipPosition = {
          top: rect.bottom + 8,
          left: rect.left + rect.width / 2
        };
      } else if (position === 'top') {
        tooltipPosition = {
          top: rect.top - 8,
          left: rect.left + rect.width / 2
        };
      }
    }
  }

  function handleMouseEnter() {
    showTooltip = true;
    updateTooltipPosition();
    // Add scroll listener to update position while tooltip is shown
    window.addEventListener('scroll', updateTooltipPosition, true);
  }

  function handleMouseLeave() {
    showTooltip = false;
    // Remove scroll listener when tooltip is hidden
    window.removeEventListener('scroll', updateTooltipPosition, true);
  }
</script>

<div
  bind:this={targetElement}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  class="relative inline-block"
>
  {@render children()}
</div>

<!-- Tooltip - Fixed position to avoid overflow clipping -->
{#if showTooltip}
  <div
    class="fixed px-4 py-2 bg-gray-800 text-white text-xs rounded-lg whitespace-normal transform -translate-x-1/2 pointer-events-none max-w-xs"
    style="top: {position === 'bottom' ? tooltipPosition.top : tooltipPosition.top}px; left: {tooltipPosition.left}px; z-index: 999999; {position === 'top' ? 'transform: translateX(-50%) translateY(-100%);' : ''}"
  >
    <p class="leading-relaxed whitespace-normal">{tooltipText}</p>
    <!-- Arrow -->
    {#if position === 'bottom'}
      <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-b-gray-800"></div>
    {:else if position === 'top'}
      <div class="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
    {/if}
  </div>
{/if}
