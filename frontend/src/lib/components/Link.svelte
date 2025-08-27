<script>
  import { push } from 'svelte-spa-router';
  
  let { 
    href = '', 
    class: className = '',
    ...restProps
  } = $props();
  
  // Ensure href starts with #/
  let fullHref = $derived(href.startsWith('#') ? href : `#${href}`);
  
  function handleClick(e) {
    // Don't interfere with modified clicks - let browser handle them naturally
    if (
      e.button !== 0 || // Not left click
      e.metaKey ||      // Cmd key (Mac)
      e.ctrlKey ||      // Ctrl key (Windows/Linux)
      e.shiftKey ||     // Shift key
      e.altKey          // Alt key
    ) {
      // Let the browser handle it - this will open in new tab/window
      return;
    }
    
    // For regular left clicks, prevent default and use SPA navigation
    e.preventDefault();
    const route = href.startsWith('#') ? href.substring(1) : href;
    push(route);
  }
</script>

<a 
  href={fullHref}
  class={className}
  onclick={handleClick}
  {...restProps}
>
  <slot />
</a>