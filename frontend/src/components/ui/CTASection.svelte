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

<div class="relative z-10 px-4 py-20 text-center sm:px-6 md:px-20 md:py-32">
  <h2 class="text-3xl md:text-[64px] font-medium text-gray-900 font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
    {title}
  </h2>
  <p class="mx-auto mb-8 max-w-2xl text-base leading-6 text-[#6b6b6b]">
    {description}
  </p>
  <div class="flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
    <button
      onclick={handlePrimaryClick}
      class="inline-flex h-12 w-full max-w-[280px] items-center justify-center gap-2 rounded-full px-8 text-base font-medium text-white transition-colors hover:opacity-90 sm:w-auto"
      style="background-color: {primaryButtonColor === 'dark' ? '#131214' : primaryButtonColor};"
    >
      {primaryButtonText}
    </button>
    {#if secondaryLinkText && secondaryLinkPath}
      <button
        onclick={handleSecondaryClick}
        class="inline-flex h-12 w-full max-w-[280px] items-center justify-center gap-2 rounded-full border border-[#e0e0e0] px-8 text-base font-medium text-[#131214] transition-colors hover:bg-gray-50 sm:w-auto"
      >
        {secondaryLinkText}
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
        </svg>
      </button>
    {/if}
  </div>
</div>
