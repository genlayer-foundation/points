<script>
  import { onMount } from 'svelte';

  let {
    value = $bindable(''),
    id = undefined,
    placeholder = '',
    debounceMs = 0,
    onChange = () => {},
    onClear = () => {},
    helpTitle = 'Search syntax',
    helpBody = undefined,
  } = $props();

  let showHelp = $state(false);
  let triggerEl = $state(null);
  let panelEl = $state(null);
  let debounceTimer = null;

  function fire() {
    onChange(value);
  }

  function handleInput() {
    if (debounceTimer) clearTimeout(debounceTimer);
    if (debounceMs > 0) {
      debounceTimer = setTimeout(fire, debounceMs);
    } else {
      fire();
    }
  }

  function handleClear() {
    value = '';
    if (debounceTimer) clearTimeout(debounceTimer);
    onClear();
  }

  function handleClickOutside(event) {
    if (!showHelp) return;
    if (panelEl?.contains(event.target) || triggerEl?.contains(event.target)) return;
    showHelp = false;
  }

  onMount(() => {
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  });
</script>

<div class="relative">
  <img src="/assets/icons/search-line.svg" alt="" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 opacity-50 pointer-events-none" />
  <input
    {id}
    type="text"
    bind:value
    oninput={handleInput}
    {placeholder}
    class="w-full pl-9 pr-16 py-2 border border-[#e6e6e6] rounded-[8px] bg-white text-[14px] text-black placeholder-[#bababa] focus:outline-none focus:border-[#8D81E1] transition-colors font-mono"
  />
  {#if value}
    <button
      type="button"
      onclick={handleClear}
      class="absolute right-9 top-1/2 -translate-y-1/2 w-5 h-5 flex items-center justify-center rounded-full text-[#6b6b6b] hover:bg-[#f0f0f0] hover:text-black transition-colors text-[14px] leading-none"
      aria-label="Clear search"
    >×</button>
  {/if}
  {#if helpBody}
    <button
      bind:this={triggerEl}
      type="button"
      onclick={() => (showHelp = !showHelp)}
      class="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center rounded-full text-[#6b6b6b] hover:bg-[#f0f0f0] hover:text-black transition-colors"
      aria-label={helpTitle}
      title={helpTitle}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    </button>
    {#if showHelp}
      <div
        bind:this={panelEl}
        role="dialog"
        aria-label={helpTitle}
        class="absolute right-0 top-[calc(100%+8px)] z-30 w-[340px] bg-white border border-[#e6e6e6] rounded-[12px] shadow-lg p-4"
      >
        <h4 class="text-[13px] font-semibold text-black mb-2" style="letter-spacing: -0.1px;">{helpTitle}</h4>
        {@render helpBody()}
      </div>
    {/if}
  {/if}
</div>
