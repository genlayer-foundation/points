<script>
  import { validatorsAPI } from '../lib/api';
  import { DECKARD_BOT_USERNAME } from '../lib/config';
  import { showSuccess, showError } from '../lib/toastStore';

  let codes = $state([]);
  let loading = $state(true);
  /** @type {string | null} */
  let error = $state(null);
  let isIssuing = $state(false);
  /** @type {string | null} Plaintext of the code issued in this session — shown once. */
  let freshCode = $state(null);
  /** @type {string | null} */
  let freshCodeExpiresAt = $state(null);
  /** @type {number | null} */
  let revokingId = $state(null);
  let copied = $state(false);

  const botLabel = DECKARD_BOT_USERNAME
    ? `@${DECKARD_BOT_USERNAME}`
    : 'the Deckard support bot';

  const STATUS_STYLES = {
    issued: 'bg-[#EEF6F1] text-[#2E7D46]',
    redeemed: 'bg-[#EAF1FC] text-[#2757A5]',
    expired: 'bg-[#F3F1EC] text-[#7A766F]',
    revoked: 'bg-[#FBEDEB] text-[#B4433A]',
  };

  const STATUS_LABELS = {
    issued: 'Active',
    redeemed: 'Redeemed',
    expired: 'Expired',
    revoked: 'Revoked',
  };

  $effect(() => {
    loadCodes();
  });

  async function loadCodes() {
    try {
      const response = await validatorsAPI.getMyTelegramBindCodes();
      codes = response.data || [];
      error = null;
    } catch (err) {
      if (err.response?.status === 403) {
        error = 'Only validators can link Telegram groups.';
      } else {
        error = 'Failed to load your codes. Please try again.';
      }
    } finally {
      loading = false;
    }
  }

  async function issueCode() {
    isIssuing = true;
    try {
      const response = await validatorsAPI.issueTelegramBindCode();
      freshCode = response.data.code;
      freshCodeExpiresAt = response.data.expires_at;
      copied = false;
      showSuccess('Code generated. It is shown only once — use it within 48 hours.');
      await loadCodes();
    } catch (err) {
      if (err.response?.status === 429) {
        showError('Too many codes generated recently. Please try again later.');
      } else if (err.response?.status === 403) {
        showError('Only validators can generate Telegram group codes.');
      } else {
        showError('Failed to generate a code. Please try again.');
      }
    } finally {
      isIssuing = false;
    }
  }

  async function copyCode() {
    if (!freshCode) return;
    try {
      await navigator.clipboard.writeText(`/bindcode ${freshCode}`);
      copied = true;
      showSuccess('Command copied to clipboard.');
    } catch (err) {
      showError('Could not copy — select and copy the code manually.');
    }
  }

  async function revokeCode(id) {
    revokingId = id;
    try {
      await validatorsAPI.revokeTelegramBindCode(id);
      showSuccess('Code revoked.');
      await loadCodes();
    } catch (err) {
      if (err.response?.status === 409) {
        showError('This code was already redeemed and cannot be revoked.');
        await loadCodes();
      } else {
        showError('Failed to revoke the code. Please try again.');
      }
    } finally {
      revokingId = null;
    }
  }

  function formatDate(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
</script>

<div class="mx-auto max-w-3xl space-y-6 px-4 py-6 sm:px-6">
  <div class="space-y-2">
    <h1 class="text-[34px] font-semibold font-display leading-none text-black sm:text-[40px]">
      Link a Telegram group
    </h1>
    <p class="max-w-2xl text-[14px] text-[#3f4b5f] sm:text-[15px]">
      Connect a Telegram group to your validator so {botLabel} can support you
      there. You can link as many groups as you need — each one uses its own
      one-time code. Direct messages are not supported: the bot only binds
      groups.
    </p>
  </div>

  <!-- How it works -->
  <div class="rounded-[12px] border border-[#E6E3DD] bg-[#FBFAF7] p-4 shadow-[0_1px_0_rgba(0,0,0,0.04)]">
    <p class="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#7A766F]">
      How it works
    </p>
    <ol class="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-[#3f4b5f]">
      <li>Create a new Telegram group for your validator.</li>
      <li>Add {botLabel} to that group.</li>
      <li>Generate a code below, then run <code class="rounded bg-[#F3F1EC] px-1.5 py-0.5 font-mono text-[13px] text-black">/bindcode &lt;code&gt;</code> in the group.</li>
    </ol>
    <p class="mt-2 text-xs text-gray-500">
      Each code binds one group, works once, and expires after 48 hours.
    </p>
  </div>

  {#if error}
    <div class="rounded-[8px] border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      {error}
    </div>
  {:else}
    <!-- Issue a code -->
    <div class="rounded-[12px] border border-[#EAEAEA] p-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="min-w-0">
          <h2 class="text-[16px] font-semibold tracking-[-0.2px] text-black">
            Generate a group code
          </h2>
          <p class="mt-1 text-sm text-gray-500">
            The code is shown only once — paste it in your group right away.
          </p>
        </div>
        <button
          onclick={issueCode}
          disabled={isIssuing}
          class="min-h-[44px] shrink-0 rounded-[8px] bg-black px-4 py-2.5 text-sm font-medium text-white transition-[background-color,color,transform] hover:bg-gray-800 active:scale-[0.96] disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400 disabled:active:scale-100"
        >
          {isIssuing ? 'Generating...' : 'Generate code'}
        </button>
      </div>

      {#if freshCode}
        <div class="mt-4 rounded-[8px] border border-[#CFE3D6] bg-[#F2FAF5] p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#2E7D46]">
            Your one-time code
          </p>
          <div class="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center">
            <code class="min-w-0 flex-1 break-all rounded-[8px] bg-white px-3 py-2.5 font-mono text-sm text-black shadow-[0_0_0_1px_rgba(0,0,0,0.07)]">
              /bindcode {freshCode}
            </code>
            <button
              onclick={copyCode}
              class="min-h-[40px] shrink-0 rounded-[8px] border border-[#2E7D46] px-4 py-2 text-sm font-medium text-[#2E7D46] transition-colors hover:bg-[#E6F3EB]"
            >
              {copied ? 'Copied' : 'Copy command'}
            </button>
          </div>
          <p class="mt-2 text-xs text-[#2E7D46]">
            Run this command in your Telegram group. It will not be shown
            again{freshCodeExpiresAt ? ` and expires ${formatDate(freshCodeExpiresAt)}` : ''}.
          </p>
        </div>
      {/if}
    </div>

    <!-- Codes list -->
    <div class="rounded-[12px] border border-[#EAEAEA] p-4">
      <h2 class="text-[16px] font-semibold tracking-[-0.2px] text-black">
        Your codes
      </h2>
      {#if loading}
        <p class="mt-3 text-sm text-gray-500">Loading...</p>
      {:else if codes.length === 0}
        <p class="mt-3 text-sm text-gray-500">
          No codes yet. Generate one above to link your first group.
        </p>
      {:else}
        <div class="mt-3 space-y-2">
          {#each codes as code (code.id)}
            <div class="rounded-[8px] bg-white px-3 py-3 shadow-[0_0_0_1px_rgba(0,0,0,0.07),0_1px_2px_rgba(0,0,0,0.04)]">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-sm text-black">tgb_{code.identifier}_&hellip;</span>
                    <span class="rounded-full px-2 py-1 text-[11px] font-semibold {STATUS_STYLES[code.status] || 'bg-[#F3F1EC] text-[#5F5B54]'}">
                      {STATUS_LABELS[code.status] || code.status}
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-gray-500">
                    Created {formatDate(code.created_at)}
                    {#if code.status === 'issued'}
                      &middot; Expires {formatDate(code.expires_at)}
                    {:else if code.status === 'redeemed'}
                      &middot; Group linked {formatDate(code.redeemed_at)}
                      {#if code.redeemed_group_chat_id}
                        <span class="font-mono">(chat {code.redeemed_group_chat_id})</span>
                      {/if}
                    {/if}
                  </p>
                </div>
                {#if code.status === 'issued'}
                  <button
                    onclick={() => revokeCode(code.id)}
                    disabled={revokingId === code.id}
                    class="shrink-0 rounded-[8px] border border-[#E2DED6] px-3 py-1.5 text-xs font-medium text-[#B4433A] transition-colors hover:border-[#B4433A] hover:bg-[#FBEDEB] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {revokingId === code.id ? 'Revoking...' : 'Revoke'}
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
