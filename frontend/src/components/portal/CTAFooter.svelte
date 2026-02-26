<script>
  import { push } from 'svelte-spa-router';
</script>

<div class="bg-white border border-[#f0f0f0] rounded-[24px] px-8 md:px-20 py-24 md:py-32 text-center">
  <h2 class="text-3xl md:text-[64px] font-medium text-gray-900 font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
    Start contributing today
  </h2>
  <p class="text-[#6b6b6b] text-base max-w-xl mx-auto mb-8">
    Join professional validators and builders in creating the trust infrastructure for the AI age.
  </p>
  <div>
    <button
      onclick={() => push('/builders/contributions')}
      class="inline-flex items-center gap-2 h-12 px-8 text-white font-medium rounded-[20px] text-base transition-colors hover:opacity-90"
      style="background-color: #131214;"
    >
      Start building
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
      </svg>
    </button>
  </div>
</div>
