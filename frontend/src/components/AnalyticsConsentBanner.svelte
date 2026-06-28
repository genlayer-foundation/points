<script>
  import {
    analyticsConsent,
    isAnalyticsConfigured,
    setAnalyticsConsent,
  } from '../lib/analytics.js';

  let visible = $derived(isAnalyticsConfigured() && $analyticsConsent === 'unknown');

  function accept() {
    setAnalyticsConsent(true);
  }

  function decline() {
    setAnalyticsConsent(false);
  }
</script>

{#if visible}
  <section
    class="fixed bottom-3 left-3 right-3 z-[70] flex max-w-none flex-col items-stretch gap-3 rounded-[8px] border border-[#e6e6e6] bg-white p-3.5 shadow-[0_14px_40px_rgba(19,18,20,0.14)] sm:bottom-4 sm:left-auto sm:right-4 sm:max-w-[520px] sm:flex-row sm:items-center sm:gap-4"
    aria-label="Analytics consent"
  >
    <div class="min-w-0 space-y-[3px] text-[13px] leading-[1.35] text-[#4f4f54]">
      <strong class="block text-sm leading-tight text-[#131214]">Analytics</strong>
      <span>Help us understand Portal usage with Google Analytics. It only runs if you accept.</span>
    </div>
    <div class="flex shrink-0 justify-end gap-2">
      <button
        type="button"
        class="h-[34px] min-w-[76px] cursor-pointer rounded-md border border-[#dedee2] bg-white px-3 text-[13px] font-semibold text-[#4f4f54] transition-colors hover:border-[#c9c9cf] hover:text-[#131214]"
        onclick={decline}
      >
        Decline
      </button>
      <button
        type="button"
        class="h-[34px] min-w-[76px] cursor-pointer rounded-md border border-transparent bg-[#131214] px-3 text-[13px] font-semibold text-white transition-colors hover:bg-[#242326]"
        onclick={accept}
      >
        Accept
      </button>
    </div>
  </section>
{/if}
