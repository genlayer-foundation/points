<script>
  import { authState } from '../lib/auth.js';
  import { openWhatsNew, whatsNewStore } from '../lib/whatsNewStore.js';

  let unseenCount = $derived($whatsNewStore.unseenCount || 0);
</script>

{#if $authState.isAuthenticated}
  <button
    type="button"
    class="whats-new-trigger"
    aria-label="Open What's New"
    title="What's New"
    onclick={openWhatsNew}
  >
    <svg class="spark-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 4.25l1.55 4.3 4.2 1.45-4.2 1.45L12 15.75l-1.55-4.3-4.2-1.45 4.2-1.45L12 4.25Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
      <path d="M18 15.5l.65 1.85 1.85.65-1.85.65L18 20.5l-.65-1.85-1.85-.65 1.85-.65L18 15.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
    </svg>
    <span class="trigger-label">What's New</span>
    {#if unseenCount > 0}
      <span class="trigger-dot" aria-hidden="true">{unseenCount > 9 ? '9+' : unseenCount}</span>
    {/if}
  </button>
{/if}

<style>
  .whats-new-trigger {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.42rem;
    min-width: 0;
    max-width: 100%;
    height: 2.5rem;
    padding: 0 0.78rem;
    border: 1px solid #e0e5ef;
    border-radius: 20px;
    color: #374151;
    background: #fff;
    box-shadow: 0 6px 16px rgba(31, 42, 68, 0.06);
    font-size: 0.86rem;
    font-weight: 650;
    line-height: 1;
    transition:
      transform 160ms ease,
      border-color 160ms ease,
      box-shadow 160ms ease,
      color 160ms ease;
  }

  .whats-new-trigger:hover {
    transform: translateY(-1px);
    border-color: #cdd5e3;
    color: #000;
    background: #f7f8fb;
    box-shadow: 0 10px 22px rgba(31, 42, 68, 0.1);
  }

  .whats-new-trigger:focus-visible {
    outline: 2px solid #0284c7;
    outline-offset: 2px;
  }

  .spark-icon {
    width: 1.05rem;
    height: 1.05rem;
    color: #0284c7;
    flex: 0 0 auto;
  }

  .trigger-label {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .trigger-dot {
    position: absolute;
    top: -0.22rem;
    right: -0.18rem;
    display: inline-flex;
    min-width: 1.05rem;
    height: 1.05rem;
    align-items: center;
    justify-content: center;
    padding: 0 0.22rem;
    border-radius: 999px;
    background: #0284c7;
    border: 2px solid #fff;
    color: #fff;
    font-size: 0.62rem;
    font-weight: 750;
    line-height: 1;
  }

  @media (max-width: 1023px) {
    .whats-new-trigger {
      padding: 0;
      width: 2.5rem;
    }

    .trigger-label {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
  }

  @media (max-width: 767px) {
    .whats-new-trigger {
      width: 2.25rem;
      height: 2.25rem;
      box-shadow: none;
    }

    .spark-icon {
      width: 1rem;
      height: 1rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .whats-new-trigger {
      transition: none;
    }

    .whats-new-trigger:hover {
      transform: none;
    }
  }
</style>
