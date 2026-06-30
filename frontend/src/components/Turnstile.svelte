<script>
  import { onDestroy, onMount } from 'svelte';
  import { TURNSTILE_SITE_KEY } from '../lib/config.js';

  let {
    onVerify = () => {},
    onExpire = () => {},
    disabled = false,
  } = $props();

  let container = $state(null);
  let widgetId = $state(null);

  function emitDebugToken() {
    onVerify('debug-pass');
  }

  function renderWidget() {
    if (!container || disabled || !TURNSTILE_SITE_KEY) return;
    if (!window.turnstile) return;
    widgetId = window.turnstile.render(container, {
      sitekey: TURNSTILE_SITE_KEY,
      callback: (token) => onVerify(token),
      'expired-callback': () => onExpire(),
      'error-callback': () => onExpire(),
    });
  }

  onMount(() => {
    if (!TURNSTILE_SITE_KEY) {
      emitDebugToken();
      return;
    }

    if (window.turnstile) {
      renderWidget();
      return;
    }

    const existing = document.querySelector('script[data-turnstile-api]');
    if (existing) {
      existing.addEventListener('load', renderWidget, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.dataset.turnstileApi = 'true';
    script.addEventListener('load', renderWidget, { once: true });
    document.head.appendChild(script);
  });

  onDestroy(() => {
    if (widgetId !== null && window.turnstile) {
      window.turnstile.remove(widgetId);
    }
  });
</script>

{#if TURNSTILE_SITE_KEY}
  <div class="turnstile-frame" bind:this={container}></div>
{:else}
  <div class="turnstile-debug">Local verification enabled</div>
{/if}

<style>
  .turnstile-frame {
    min-height: 65px;
  }

  .turnstile-debug {
    align-items: center;
    background: #f7faf8;
    border: 1px solid #d6eadc;
    border-radius: 8px;
    color: #247342;
    display: flex;
    font-size: 13px;
    font-weight: 700;
    min-height: 44px;
    padding: 0 12px;
  }
</style>
