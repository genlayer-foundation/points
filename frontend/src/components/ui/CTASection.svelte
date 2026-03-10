<script>
  import { push } from 'svelte-spa-router';

  let {
    title = 'Start contributing today',
    description = 'Join professional validators and builders in creating the trust infrastructure for the AI age.',
    primaryButtonText = 'Start building',
    primaryButtonPath = '/builders/contributions',
    primaryButtonColor = 'dark',
    secondaryLinkText = '',
    secondaryLinkPath = '',
    secondaryLinkExternal = false
  } = $props();

  function handlePrimaryClick() {
    push(primaryButtonPath);
  }

  function handleSecondaryClick() {
    if (secondaryLinkExternal) {
      window.open(secondaryLinkPath, '_blank');
    } else {
      push(secondaryLinkPath);
    }
  }
</script>

<div class="relative z-10 px-8 md:px-20 py-24 md:py-32 text-center">
  <h2 class="text-3xl md:text-[64px] font-medium text-gray-900 font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
    {title}
  </h2>
  <p class="text-[#6b6b6b] text-base max-w-2xl mx-auto mb-8 whitespace-nowrap">
    {description}
  </p>
  <div class="flex items-center justify-center gap-4">
    <button
      onclick={handlePrimaryClick}
      class="inline-flex items-center gap-2 h-12 px-8 text-white font-medium rounded-full text-base transition-colors hover:opacity-90"
      style="background-color: {primaryButtonColor === 'dark' ? '#131214' : primaryButtonColor};"
    >
      {primaryButtonText}
    </button>
    {#if secondaryLinkText && secondaryLinkPath}
      <button
        onclick={handleSecondaryClick}
        class="inline-flex items-center gap-2 h-12 px-8 font-medium rounded-full text-base transition-colors border border-[#e0e0e0] text-[#131214] hover:bg-gray-50"
      >
        {secondaryLinkText}
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
        </svg>
      </button>
    {/if}
  </div>
</div>
