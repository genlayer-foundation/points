<script>
  import { onMount } from 'svelte';
  import Turnstile from './Turnstile.svelte';
  import { confirmEmailVerification, startEmailVerification } from '../lib/auth';
  import { showError } from '../lib/toastStore';
  import { userStore } from '../lib/userStore';

  const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  let {
    initialEmail = '',
    onClose = () => {},
    onVerified = () => {},
  } = $props();

  let email = $state('');
  let code = $state('');
  let error = $state('');
  let codeSent = $state(false);
  let verified = $state(false);
  let sending = $state(false);
  let verifying = $state(false);
  let turnstileToken = $state('');
  let turnstileWidget = $state(null);
  let modalElement = $state(null);
  let emailInput = $state(null);
  let codeInput = $state(null);
  let doneButton = $state(null);
  let cooldownEndsAt = $state(0);
  let cooldownRemaining = $state(0);

  $effect(() => {
    if (!codeSent && !verified) {
      email = cleanEmail(initialEmail);
    }
  });

  $effect(() => {
    codeSent;
    verified;
    focusInitialControl();
  });

  onMount(() => {
    const previousActiveElement = document.activeElement;
    const cooldownTimer = window.setInterval(updateCooldown, 1000);
    focusInitialControl();
    return () => {
      window.clearInterval(cooldownTimer);
      if (previousActiveElement && typeof previousActiveElement.focus === 'function') {
        previousActiveElement.focus();
      }
    };
  });

  function cleanEmail(value) {
    const next = String(value || '').trim();
    return next.endsWith('@ethereum.address') ? '' : next;
  }

  function isValidEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || '').trim());
  }

  function normalizeCode(value) {
    return String(value || '').replace(/\D/g, '').slice(0, 6);
  }

  function handleCodeInput(event) {
    code = normalizeCode(event.target.value);
  }

  function extractError(err, fallback) {
    const data = err?.response?.data;
    return data?.email || data?.code || data?.token || data?.detail || data?.turnstile_token || fallback;
  }

  function startCooldown(seconds) {
    const duration = Number(seconds) || 0;
    cooldownEndsAt = duration > 0 ? Date.now() + duration * 1000 : 0;
    updateCooldown();
  }

  function startCooldownFromData(data) {
    if (Number(data?.cooldown_seconds) > 0) {
      startCooldown(data.cooldown_seconds);
    }
  }

  function updateCooldown() {
    if (!cooldownEndsAt) {
      cooldownRemaining = 0;
      return;
    }
    cooldownRemaining = Math.max(0, Math.ceil((cooldownEndsAt - Date.now()) / 1000));
    if (cooldownRemaining === 0) cooldownEndsAt = 0;
  }

  function formatCooldown(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`;
  }

  function focusInitialControl() {
    if (typeof window === 'undefined') return;
    window.setTimeout(() => {
      if (verified) {
        doneButton?.focus?.();
      } else if (codeSent) {
        codeInput?.focus?.();
      } else {
        emailInput?.focus?.();
      }
    }, 0);
  }

  function getFocusableElements() {
    if (!modalElement) return [];
    return Array.from(modalElement.querySelectorAll(FOCUSABLE_SELECTOR))
      .filter((element) => element.offsetParent !== null || element === document.activeElement);
  }

  function handleModalKeydown(event) {
    if (event.key === 'Escape' && !sending && !verifying) {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;

    const focusable = getFocusableElements();
    if (focusable.length === 0) {
      event.preventDefault();
      modalElement?.focus?.();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  async function sendCode() {
    if (!isValidEmail(email)) {
      error = 'Enter a valid email address';
      return;
    }
    if (!turnstileToken) {
      error = 'Complete verification first';
      return;
    }

    sending = true;
    error = '';
    try {
      const response = await startEmailVerification({
        email: email.trim(),
        turnstile_token: turnstileToken,
      });
      startCooldownFromData(response.data);
      codeSent = true;
      code = '';
    } catch (err) {
      startCooldownFromData(err.response?.data);
      error = extractError(err, 'Failed to send verification code');
      showError(error);
      turnstileToken = '';
      turnstileWidget?.reset?.();
    } finally {
      sending = false;
    }
  }

  async function verifyCode() {
    const normalized = normalizeCode(code);
    if (normalized.length !== 6) {
      error = 'Enter the 6-digit code from your email';
      return;
    }

    verifying = true;
    error = '';
    try {
      const response = await confirmEmailVerification(normalized);
      const updated = {
        email: response.data?.email || email.trim(),
        is_email_verified: true,
        email_verified_at: response.data?.email_verified_at || new Date().toISOString(),
      };
      verified = true;
      userStore.updateUser(updated);
      try {
        onVerified(await userStore.loadUser());
      } catch {
        onVerified(updated);
      }
    } catch (err) {
      error = extractError(err, 'Invalid or expired verification code');
      showError(error);
    } finally {
      verifying = false;
    }
  }

  function useDifferentEmail() {
    codeSent = false;
    code = '';
    error = '';
    turnstileToken = '';
    turnstileWidget?.reset?.();
  }
</script>

<div class="email-modal-backdrop" role="presentation">
  <div
    bind:this={modalElement}
    class="email-modal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="email-verification-title"
    tabindex="-1"
    onkeydown={handleModalKeydown}
  >
    <div class="email-modal-hero">
      <div class="hero-topline">
        <span class="hero-badge" aria-hidden="true">G</span>
        <span>GenLayer Portal</span>
      </div>
      <button
        type="button"
        class="modal-close"
        aria-label="Close email verification"
        onclick={onClose}
        disabled={sending || verifying}
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
      </button>
      <h2 id="email-verification-title">
        {verified ? 'Email verified' : codeSent ? 'Enter your code' : 'Verify your email'}
      </h2>
      <p>
        {#if verified}
          Your Portal identity now has a verified email.
        {:else if codeSent}
          Paste the one-time code we sent to keep this flow in the Portal.
        {:else}
          Add the email address you want tied to your Portal account.
        {/if}
      </p>
    </div>

    <div class="email-modal-body">
      {#if error}
        <div class="modal-error">
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M10 6v5M10 14.5h.01M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
          </svg>
          <span>{error}</span>
        </div>
      {/if}

      {#if verified}
        <div class="success-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="m5 12.5 4.2 4.2L19 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <button bind:this={doneButton} type="button" class="primary-action" onclick={onClose}>Done</button>
      {:else if codeSent}
        <div class="code-sent">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 6.5h16v11H4v-11ZM5 8l7 5 7-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span>Code sent to {email.trim()}.</span>
        </div>
        {#if cooldownRemaining > 0}
          <p class="cooldown-copy">You can request another code in {formatCooldown(cooldownRemaining)}.</p>
        {/if}

        <label for="email-verification-code">Verification code</label>
        <input
          id="email-verification-code"
          bind:this={codeInput}
          class="code-input"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          maxlength="6"
          value={code}
          oninput={handleCodeInput}
          placeholder="000000"
          disabled={verifying}
        />

        <button
          type="button"
          class="primary-action"
          onclick={verifyCode}
          disabled={verifying || code.length !== 6}
        >
          {verifying ? 'Verifying...' : 'Verify code'}
        </button>
        <button type="button" class="secondary-action" onclick={useDifferentEmail} disabled={verifying}>
          Change email or resend code
        </button>
      {:else}
        <label for="email-verification-email">Email address</label>
        <input
          id="email-verification-email"
          bind:this={emailInput}
          class="email-input"
          type="email"
          bind:value={email}
          placeholder="you@example.com"
          disabled={sending}
        />

        <div class="turnstile-slot">
          <Turnstile
            bind:this={turnstileWidget}
            disabled={sending}
            onVerify={(token) => (turnstileToken = token)}
            onExpire={() => (turnstileToken = '')}
          />
        </div>

        <button
          type="button"
          class="primary-action"
          onclick={sendCode}
          disabled={sending || cooldownRemaining > 0 || !email.trim() || !turnstileToken}
        >
          {#if sending}
            Sending...
          {:else if cooldownRemaining > 0}
            Send in {formatCooldown(cooldownRemaining)}
          {:else}
            Send verification code
          {/if}
        </button>
        {#if cooldownRemaining > 0}
          <p class="cooldown-copy">You can request another code in {formatCooldown(cooldownRemaining)}.</p>
        {/if}
      {/if}
    </div>
  </div>
</div>

<style>
  .email-modal-backdrop {
    align-items: center;
    backdrop-filter: blur(4px);
    background:
      linear-gradient(135deg, rgba(238, 133, 33, 0.18), rgba(91, 190, 238, 0.14) 48%, rgba(151, 132, 238, 0.16)),
      rgba(14, 14, 16, 0.54);
    display: flex;
    inset: 0;
    justify-content: center;
    padding: 20px;
    position: fixed;
    z-index: 10000;
  }

  .email-modal {
    background: #fff;
    border: 1px solid rgba(19, 18, 20, 0.08);
    border-radius: 16px;
    box-shadow:
      0 34px 70px rgba(15, 15, 15, 0.22),
      0 1px 0 rgba(255, 255, 255, 0.85) inset;
    max-height: min(90vh, 720px);
    max-width: 92vw;
    overflow: hidden auto;
    width: 470px;
  }

  .email-modal-hero {
    background: #fff;
    color: #131214;
    overflow: hidden;
    padding: 24px;
    position: relative;
  }

  .email-modal-hero::before {
    background: linear-gradient(90deg, rgba(238, 133, 33, 0.34) 0%, rgba(255, 230, 132, 0.28) 18%, rgba(95, 213, 165, 0.3) 38%, rgba(91, 190, 238, 0.3) 58%, rgba(151, 132, 238, 0.28) 78%, rgba(245, 151, 194, 0.3) 100%);
    content: '';
    filter: blur(18px);
    height: 116px;
    inset: 28px -20px auto;
    opacity: 0.95;
    position: absolute;
  }

  .hero-topline,
  .email-modal-hero h2,
  .email-modal-hero p,
  .modal-close {
    position: relative;
    z-index: 1;
  }

  .hero-topline {
    align-items: center;
    color: #5d5d64;
    display: flex;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    gap: 10px;
    letter-spacing: 0;
    text-transform: uppercase;
  }

  .hero-badge {
    align-items: center;
    background: #131214;
    border-radius: 14px;
    color: #fff;
    display: inline-flex;
    font-size: 14px;
    font-weight: 900;
    height: 42px;
    justify-content: center;
    width: 42px;
  }

  .modal-close {
    align-items: center;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(19, 18, 20, 0.08);
    border-radius: 999px;
    color: #5f6068;
    cursor: pointer;
    display: flex;
    height: 40px;
    justify-content: center;
    position: absolute;
    right: 18px;
    top: 18px;
    transition-duration: 160ms;
    transition-property: background-color, color, transform, box-shadow;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    width: 40px;
  }

  .modal-close svg {
    height: 20px;
    width: 20px;
  }

  .modal-close:hover:not(:disabled) {
    background: #fff;
    color: #131214;
    box-shadow: 0 10px 22px rgba(19, 18, 20, 0.14);
  }

  .modal-close:active:not(:disabled) {
    transform: scale(0.96);
  }

  .email-modal-hero h2 {
    color: #131214;
    font-family: var(--font-heading);
    font-size: 27px;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 1.12;
    margin: 22px 0 0;
    text-wrap: balance;
  }

  .email-modal-hero p {
    color: #606068;
    font-size: 14px;
    line-height: 1.55;
    margin: 10px 0 0;
    max-width: 25rem;
    text-wrap: pretty;
  }

  .email-modal-body {
    padding: 24px;
  }

  label {
    color: #131214;
    display: block;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0;
    margin-bottom: 8px;
  }

  .email-input,
  .code-input {
    background: #fafafa;
    border: 1px solid #ededed;
    border-radius: 8px;
    color: #111827;
    font-size: 15px;
    min-height: 48px;
    padding: 0 12px;
    transition-duration: 160ms;
    transition-property: background-color, border-color, box-shadow;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    width: 100%;
  }

  .email-input:focus,
  .code-input:focus {
    background: #fff;
    border-color: #131214;
    box-shadow: 0 0 0 3px rgba(19, 18, 20, 0.08);
    outline: none;
  }

  .code-input {
    font-family: var(--font-mono);
    font-size: 24px;
    font-variant-numeric: tabular-nums;
    font-weight: 800;
    letter-spacing: 10px;
    padding: 0 15px 0 22px;
    text-align: center;
  }

  .email-input::placeholder,
  .code-input::placeholder {
    color: #b6b6bc;
  }

  .turnstile-slot {
    margin-top: 14px;
  }

  .primary-action,
  .secondary-action {
    align-items: center;
    border: 0;
    border-radius: 999px;
    cursor: pointer;
    display: flex;
    font-size: 15px;
    font-weight: 800;
    justify-content: center;
    min-height: 48px;
    transition-duration: 160ms;
    transition-property: background-color, box-shadow, color, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    width: 100%;
  }

  .primary-action {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), transparent 34%), #131214;
    box-shadow: 0 14px 28px rgba(19, 18, 20, 0.18);
    color: #fff;
    margin-top: 16px;
  }

  .primary-action:hover:not(:disabled) {
    background-color: #1a1a1f;
    box-shadow: 0 18px 34px rgba(19, 18, 20, 0.22);
    transform: translateY(-1px);
  }

  .primary-action:active:not(:disabled),
  .secondary-action:active:not(:disabled) {
    transform: scale(0.96);
  }

  .primary-action:disabled,
  .secondary-action:disabled,
  .modal-close:disabled {
    cursor: default;
    opacity: 0.55;
    transform: none;
  }

  .secondary-action {
    background: #f4f4f5;
    color: #4f5057;
    margin-top: 10px;
  }

  .secondary-action:hover:not(:disabled) {
    background: #ededee;
    color: #131214;
  }

  .modal-error {
    align-items: flex-start;
    background: #fff1f1;
    border: 1px solid #ffc9c9;
    border-radius: 8px;
    color: #9f1d1d;
    display: flex;
    font-size: 14px;
    gap: 10px;
    line-height: 1.45;
    margin-bottom: 16px;
    padding: 12px 14px;
  }

  .modal-error svg {
    flex: none;
    height: 18px;
    margin-top: 1px;
    width: 18px;
  }

  .code-sent {
    align-items: center;
    background: #f6fbf8;
    border: 1px solid #ccebd8;
    border-radius: 8px;
    color: #19683a;
    display: flex;
    font-size: 13px;
    font-weight: 650;
    gap: 10px;
    line-height: 1.45;
    margin-bottom: 16px;
    min-height: 48px;
    padding: 12px;
  }

  .code-sent svg {
    flex: none;
    height: 20px;
    width: 20px;
  }

  .cooldown-copy {
    color: #696970;
    font-size: 12px;
    font-weight: 650;
    line-height: 1.45;
    margin: -6px 0 16px;
  }

  .success-mark {
    align-items: center;
    background: #edf9f1;
    border-radius: 999px;
    color: #17743d;
    display: flex;
    height: 66px;
    justify-content: center;
    margin: 2px auto 6px;
    width: 66px;
  }

  .success-mark svg {
    height: 32px;
    width: 32px;
  }

  @media (max-width: 560px) {
    .email-modal-backdrop {
      padding: 16px;
    }

    .email-modal {
      max-width: 100%;
      width: 100%;
    }

    .email-modal-hero,
    .email-modal-body {
      padding: 20px;
    }
  }
</style>
