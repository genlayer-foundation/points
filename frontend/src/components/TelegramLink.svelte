<script>
  import { onDestroy } from "svelte";
  import { getCurrentUser, telegramAPI } from "../lib/api";
  import { showSuccess, showError } from "../lib/toastStore";

  // Private connection: this component must only ever be rendered on the
  // user's OWN profile (the API returns telegram_connection to owners only).
  let { connection = null, onLinked = () => {} } = $props();

  let isLinking = $state(false);
  let isDisconnecting = $state(false);

  // Plain let (not $state): imperative timer bookkeeping.
  /** @type {ReturnType<typeof setInterval> | null} */
  let pollTimer = null;
  let pollAttempts = 0;

  const MAX_POLL_ATTEMPTS = 40; // 40 x 3s = 2 minutes
  const TELEGRAM_COLOR = "#229ED9";
  const icon = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>`;

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  onDestroy(stopPolling);

  function startPolling() {
    stopPolling();
    pollAttempts = 0;
    pollTimer = setInterval(async () => {
      pollAttempts += 1;
      try {
        const user = await getCurrentUser();
        if (user?.telegram_connection) {
          stopPolling();
          isLinking = false;
          showSuccess("Telegram account linked!");
          onLinked(user);
          return;
        }
      } catch {
        // Transient fetch error; keep polling until the attempt cap.
      }
      if (pollAttempts >= MAX_POLL_ATTEMPTS) {
        stopPolling();
        isLinking = false;
      }
    }, 3000);
  }

  async function linkTelegram() {
    if (isLinking) return;
    isLinking = true;

    // Open the tab synchronously inside the click gesture; an await before
    // window.open gets popup-blocked in Safari.
    const telegramTab = window.open("", "_blank");
    try {
      const response = await telegramAPI.getLinkToken();
      const deepLink = response.data.deep_link;
      if (telegramTab) {
        telegramTab.location = deepLink;
      } else {
        // Popup blocked (common on mobile): navigate this tab instead.
        // Reset the state first so a bfcache-restored return doesn't show
        // a stuck disabled "Waiting for Telegram" button.
        isLinking = false;
        window.location.assign(deepLink);
        return;
      }
      startPolling();
    } catch (error) {
      telegramTab?.close();
      isLinking = false;
      const code = /** @type {any} */ (error)?.response?.data?.error;
      showError(
        code === "telegram_not_configured"
          ? "Telegram linking isn't available right now."
          : "Failed to start Telegram linking. Please try again.",
      );
    }
  }

  /** @param {PageTransitionEvent} event */
  async function handlePageShow(event) {
    // Returning from Telegram via back button / bfcache (same-tab flow):
    // check once whether the link completed while we were away.
    if (!event.persisted || connection || isLinking) return;
    try {
      const user = await getCurrentUser();
      if (user?.telegram_connection) {
        showSuccess("Telegram account linked!");
        onLinked(user);
      }
    } catch {
      // Not linked or fetch failed; the button stays usable either way.
    }
  }

  async function disconnectTelegram() {
    if (isDisconnecting) return;
    if (!confirm("Unlink your Telegram account? You'll stop receiving portal notifications there.")) {
      return;
    }
    isDisconnecting = true;
    try {
      await telegramAPI.disconnect();
      const user = await getCurrentUser();
      showSuccess("Telegram account unlinked.");
      onLinked(user);
    } catch {
      showError("Failed to unlink Telegram. Please try again.");
    } finally {
      isDisconnecting = false;
    }
  }
</script>

<svelte:window onpageshow={handlePageShow} />

{#if connection}
  <span
    class="telegram-pill"
    style="--brand-color: {TELEGRAM_COLOR};"
    title={connection.linked_at
      ? `Linked on ${new Date(connection.linked_at).toLocaleDateString()}. Only you can see this.`
      : "Only you can see this."}
  >
    <span class="telegram-pill-icon">{@html icon}</span>
    <span class="telegram-pill-name">
      {connection.platform_username ? `@${connection.platform_username}` : "Telegram"}
    </span>
    <button
      type="button"
      class="telegram-unlink-btn"
      onclick={disconnectTelegram}
      disabled={isDisconnecting}
      title="Unlink Telegram"
      aria-label="Unlink Telegram"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
        <path d="M6 6l12 12M18 6L6 18" />
      </svg>
    </button>
  </span>
{:else}
  <button
    onclick={linkTelegram}
    disabled={isLinking}
    class="telegram-pill telegram-pill-link"
    style="--brand-color: {TELEGRAM_COLOR};"
    title="Get portal notifications and check your stats from Telegram. Private: never shown on your public profile."
  >
    {#if isLinking}
      <svg class="animate-spin telegram-spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span class="telegram-pill-name">Waiting for Telegram…</span>
    {:else}
      <span class="telegram-pill-icon">{@html icon}</span>
      <span class="telegram-pill-prefix">Link</span>
      <span class="telegram-pill-name">Telegram</span>
    {/if}
  </button>
{/if}

<style>
  /* Matches SocialLink's compact .social-pill styling */
  .telegram-pill {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 6px;
    background: white;
    border: 1px solid #f0f0f0;
    font-size: 13px;
    font-weight: 500;
    color: #1a1a1a;
    transition: background-color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }

  .telegram-pill-link {
    cursor: pointer;
    color: #888;
    border: 1px dashed #d0d0d0;
    background: #fafafa;
  }

  .telegram-pill-link:hover:not(:disabled) {
    border-color: var(--brand-color);
    color: var(--brand-color);
    background: white;
  }

  .telegram-pill-link:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .telegram-pill-icon {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .telegram-pill-icon :global(svg) {
    width: 14px;
    height: 14px;
  }

  .telegram-spinner {
    width: 14px;
    height: 14px;
  }

  .telegram-pill-name {
    letter-spacing: 0.28px;
    line-height: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .telegram-unlink-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    margin-left: 2px;
    padding: 0;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #b0b0b0;
    cursor: pointer;
    transition: color 0.15s, background-color 0.15s;
  }

  .telegram-unlink-btn:hover:not(:disabled) {
    color: #d33;
    background: #f6f6f6;
  }

  .telegram-unlink-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .telegram-unlink-btn svg {
    width: 10px;
    height: 10px;
  }

  @media (max-width: 767px) {
    .telegram-pill {
      width: 100%;
      min-width: 0;
      min-height: 32px;
      justify-content: center;
      padding: 0.375rem 0.4375rem;
      font-size: 0.71875rem;
      gap: 3px;
    }

    .telegram-pill-prefix {
      display: none;
    }
  }
</style>
