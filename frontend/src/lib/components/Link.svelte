<script>
  import { push } from 'svelte-spa-router';
  
  let { 
    href = '', 
    class: className = '',
    ...restProps
  } = $props();
  
  // Normalize legacy '#/x' route hrefs to clean paths; new callers pass '/x'.
  // In-page anchors ('#section') are left untouched.
  let path = $derived(href.startsWith('#/') ? href.slice(1) : href);

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

    // In-page anchors keep native behavior — don't route them.
    if (path.startsWith('#')) return;

    // For regular left clicks, prevent default and use SPA navigation
    e.preventDefault();
    push(path);
  }
</script>

<a
  href={path}
  class={className}
  onclick={handleClick}
  {...restProps}
>
  <slot />
</a>