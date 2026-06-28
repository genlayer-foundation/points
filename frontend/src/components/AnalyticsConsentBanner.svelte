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
  <section class="analytics-consent" aria-label="Analytics consent">
    <div class="consent-copy">
      <strong>Analytics</strong>
      <span>Help us understand Portal usage with Google Analytics. It only runs if you accept.</span>
    </div>
    <div class="consent-actions">
      <button type="button" class="consent-button consent-button-secondary" onclick={decline}>
        Decline
      </button>
      <button type="button" class="consent-button consent-button-primary" onclick={accept}>
        Accept
      </button>
    </div>
  </section>
{/if}

<style>
  .analytics-consent {
    position: fixed;
    right: 16px;
    bottom: 16px;
    z-index: 70;
    display: flex;
    align-items: center;
    gap: 16px;
    max-width: min(520px, calc(100vw - 32px));
    padding: 14px;
    border: 1px solid #e6e6e6;
    border-radius: 8px;
    background: #ffffff;
    box-shadow: 0 14px 40px rgba(19, 18, 20, 0.14);
  }

  .consent-copy {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
    color: #4f4f54;
    font-size: 13px;
    line-height: 1.35;
  }

  .consent-copy strong {
    color: #131214;
    font-size: 14px;
    line-height: 1.2;
  }

  .consent-actions {
    display: flex;
    flex-shrink: 0;
    gap: 8px;
  }

  .consent-button {
    min-width: 76px;
    height: 34px;
    padding: 0 12px;
    border: 1px solid transparent;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
  }

  .consent-button-primary {
    background: #131214;
    color: #ffffff;
  }

  .consent-button-primary:hover {
    background: #242326;
  }

  .consent-button-secondary {
    border-color: #dedee2;
    background: #ffffff;
    color: #4f4f54;
  }

  .consent-button-secondary:hover {
    border-color: #c9c9cf;
    color: #131214;
  }

  @media (max-width: 640px) {
    .analytics-consent {
      right: 12px;
      bottom: 12px;
      left: 12px;
      max-width: none;
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
    }

    .consent-actions {
      justify-content: flex-end;
    }
  }
</style>
