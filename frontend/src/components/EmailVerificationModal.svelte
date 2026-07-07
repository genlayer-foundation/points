<script>
  import { onMount } from 'svelte';
  import Turnstile from './Turnstile.svelte';
  import { confirmEmailVerification, resendEmailVerification, startEmailVerification } from '../lib/auth';
  import { showError } from '../lib/toastStore';
  import { userStore } from '../lib/userStore';
  import { m } from '../lib/paraglide/messages.js';

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
  let codeSent = $state(false);
  let verified = $state(false);
  let sending = $state(false);
  let verifying = $state(false);
  let resendRequested = $state(false);
  let resending = $state(false);
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
    if (event.key === 'Escape' && !sending && !verifying && !resending) {
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
    if (cooldownRemaining > 0 || sending) return;
    if (!isValidEmail(email)) {
      showError(m.everify_enter_valid_email());
      return;
    }
    if (!turnstileToken) {
      showError(m.everify_complete_verification_first());
      return;
    }

    sending = true;
    try {
      const response = await startEmailVerification({
        email: email.trim(),
        turnstile_token: turnstileToken,
      });
      startCooldownFromData(response.data);
      codeSent = true;
      code = '';
      resendRequested = false;
      turnstileToken = '';
      turnstileWidget?.reset?.();
    } catch (err) {
      startCooldownFromData(err.response?.data);
      showError(extractError(err, m.everify_failed_send_code()));
      turnstileToken = '';
      turnstileWidget?.reset?.();
    } finally {
      sending = false;
    }
  }

  async function resendCode(token = turnstileToken) {
    if (cooldownRemaining > 0 || sending || verifying || resending) return;
    if (!token) {
      resendRequested = true;
      return;
    }

    resending = true;
    try {
      const response = await resendEmailVerification({
        email: email.trim(),
        turnstile_token: token,
      });
      startCooldownFromData(response.data);
      code = '';
      resendRequested = false;
      turnstileToken = '';
      turnstileWidget?.reset?.();
    } catch (err) {
      startCooldownFromData(err.response?.data);
      showError(extractError(err, m.everify_could_not_resend_code()));
      turnstileToken = '';
      turnstileWidget?.reset?.();
    } finally {
      resending = false;
    }
  }

  function requestResendCode() {
    if (cooldownRemaining > 0 || sending || verifying || resending) return;
    resendRequested = true;
    turnstileToken = '';
    turnstileWidget?.reset?.();
  }

  function handleResendTurnstile(token) {
    turnstileToken = token;
    if (resendRequested) {
      resendCode(token);
    }
  }

  async function verifyCode() {
    const normalized = normalizeCode(code);
    if (normalized.length !== 6) {
      showError(m.everify_enter_six_digit_code());
      return;
    }

    verifying = true;
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
      showError(extractError(err, m.everify_invalid_or_expired_code()));
    } finally {
      verifying = false;
    }
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
      <button
        type="button"
        class="modal-close"
        aria-label={m.everify_close_aria()}
        onclick={onClose}
        disabled={sending || verifying || resending}
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
      </button>
      <h2 id="email-verification-title">
        {verified ? m.everify_title_verified() : codeSent ? m.everify_title_enter_code() : m.everify_title_verify_email()}
      </h2>
      <p>
        {#if verified}
          {m.everify_subtitle_verified()}
        {:else if codeSent}
          {m.everify_subtitle_code_sent()}
        {:else}
          {m.everify_subtitle_add_email()}
        {/if}
      </p>
    </div>

    <div class="email-modal-body">
      {#if verified}
        <div class="success-panel" role="status" aria-live="polite">
          <div class="success-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path class="success-check" pathLength="1" d="m5 12.5 4.2 4.2L19 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <p>{m.everify_email_now_verified({ email: email.trim() })}</p>
        </div>
        <button bind:this={doneButton} type="button" class="primary-action" onclick={onClose}>{m.common_done()}</button>
      {:else if codeSent}
        <label for="email-verification-code" class="code-label">
          <span>{m.everify_verification_code_label()}</span>
          <span class="sent-to">{m.everify_sent_to({ email: email.trim() })}</span>
        </label>
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
          disabled={verifying || resending}
        />
        <div class="resend-row" role="status" aria-live="polite">
          <span class="resend-hint">
            {#if cooldownRemaining > 0}
              {m.everify_new_code_in({ time: formatCooldown(cooldownRemaining) })}
            {:else if resendRequested && !resending}
              {m.everify_complete_verification_resend()}
            {:else}
              {m.everify_didnt_get_email()}
            {/if}
          </span>
          <button
            type="button"
            class="resend-button"
            onclick={requestResendCode}
            disabled={verifying || resending || cooldownRemaining > 0 || resendRequested}
          >
            {resending ? m.common_sending() : m.everify_resend_code()}
          </button>
        </div>
        {#if resendRequested}
          <div class="resend-turnstile">
            <Turnstile
              bind:this={turnstileWidget}
              disabled={resending}
              onVerify={handleResendTurnstile}
              onExpire={() => (turnstileToken = '')}
            />
          </div>
        {/if}

        <button
          type="button"
          class="primary-action"
          onclick={verifyCode}
          disabled={verifying || resending || code.length !== 6}
        >
          {verifying ? m.common_verifying() : m.everify_verify_code()}
        </button>
      {:else}
        <label for="email-verification-email">{m.everify_email_address_label()}</label>
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

        {#if cooldownRemaining > 0}
          <div class="cooldown-notice" role="status" aria-live="polite">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span>{m.everify_request_another_in({ time: formatCooldown(cooldownRemaining) })}</span>
          </div>
        {/if}

        <button
          type="button"
          class="primary-action"
          onclick={sendCode}
          disabled={sending || cooldownRemaining > 0 || !email.trim() || !turnstileToken}
        >
          {#if sending}
            {m.common_sending()}
          {:else if cooldownRemaining > 0}
            {m.everify_send_in({ time: formatCooldown(cooldownRemaining) })}
          {:else}
            {m.everify_send_verification_code()}
          {/if}
        </button>
      {/if}
    </div>
  </div>
</div>

<style>
  .email-modal-backdrop {
    align-items: center;
    backdrop-filter: blur(4px);
    background:
      radial-gradient(circle at 18% 12%, rgba(238, 133, 33, 0.24), transparent 25rem),
      radial-gradient(circle at 78% 18%, rgba(56, 125, 232, 0.19), transparent 24rem),
      radial-gradient(circle at 52% 84%, rgba(127, 82, 225, 0.22), transparent 24rem),
      rgba(14, 14, 16, 0.54);
    animation: emailFadeIn 150ms ease-out;
    display: flex;
    inset: 0;
    justify-content: center;
    padding: 20px;
    position: fixed;
    z-index: 10000;
  }

  @keyframes emailFadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .email-modal {
    animation: emailSlideUp 200ms ease-out;
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

  @keyframes emailSlideUp {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .email-modal-hero {
    background: #fff;
    color: #131214;
    overflow: hidden;
    padding: 28px 72px 22px 24px;
    position: relative;
  }

  .email-modal-hero h2,
  .email-modal-hero p,
  .modal-close {
    position: relative;
    z-index: 1;
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
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1.12;
    margin: 0;
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

  .code-label {
    align-items: center;
    display: flex;
    gap: 12px;
    justify-content: space-between;
  }

  .sent-to {
    color: #5d636f;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

  .primary-action {
    align-items: center;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), transparent 34%), #131214;
    border: 0;
    border-radius: 999px;
    box-shadow: 0 14px 28px rgba(19, 18, 20, 0.18);
    color: #fff;
    cursor: pointer;
    display: flex;
    font-size: 15px;
    font-weight: 800;
    justify-content: center;
    margin-top: 16px;
    min-height: 48px;
    transition-duration: 160ms;
    transition-property: background-color, box-shadow, color, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    width: 100%;
  }

  .primary-action:hover:not(:disabled) {
    background-color: #1a1a1f;
    box-shadow: 0 18px 34px rgba(19, 18, 20, 0.22);
    transform: translateY(-1px);
  }

  .primary-action:active:not(:disabled),
  .resend-button:active:not(:disabled) {
    transform: scale(0.96);
  }

  .primary-action:disabled,
  .resend-button:disabled,
  .modal-close:disabled {
    cursor: default;
    opacity: 0.55;
    transform: none;
  }

  .cooldown-notice {
    align-items: center;
    background: #fff8ed;
    border: 1px solid #f6d8ad;
    border-radius: 8px;
    color: #8a4d06;
    display: flex;
    font-size: 13px;
    font-weight: 750;
    gap: 9px;
    line-height: 1.35;
    margin-top: 14px;
    min-height: 42px;
    padding: 10px 12px;
  }

  .cooldown-notice svg {
    flex: 0 0 auto;
    height: 18px;
    width: 18px;
  }

  .resend-row {
    align-items: center;
    display: flex;
    gap: 12px;
    justify-content: space-between;
    margin-top: 10px;
  }

  .resend-hint {
    color: #737378;
    flex: 1 1 auto;
    font-size: 12px;
    font-weight: 650;
    line-height: 1.35;
    min-width: 0;
  }

  .resend-hint strong {
    color: #131214;
    font-variant-numeric: tabular-nums;
    font-weight: 800;
  }

  .resend-button {
    align-items: center;
    background: #fff;
    border: 1px solid #d8dbe2;
    border-radius: 999px;
    color: #363940;
    cursor: pointer;
    display: inline-flex;
    flex: 0 0 auto;
    font-size: 13px;
    font-weight: 800;
    justify-content: center;
    min-height: 40px;
    padding: 0 14px;
    transition-duration: 160ms;
    transition-property: background-color, border-color, color, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .resend-button:hover:not(:disabled) {
    background: #f7f7f8;
    border-color: #b8bdc8;
    color: #131214;
  }

  .resend-turnstile {
    margin-top: 10px;
  }

  .success-panel {
    align-items: center;
    display: flex;
    flex-direction: column;
    padding: 4px 0 2px;
    text-align: center;
  }

  .success-panel p {
    color: #5d636f;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.4;
    margin: 12px 0 0;
    max-width: 100%;
    overflow-wrap: anywhere;
  }

  .success-mark {
    align-items: center;
    animation: successPop 360ms cubic-bezier(0.2, 0, 0, 1) both;
    background: #edf9f1;
    border-radius: 999px;
    color: #17743d;
    display: flex;
    height: 66px;
    justify-content: center;
    margin: 2px auto 6px;
    position: relative;
    width: 66px;
  }

  .success-mark::after {
    animation: successRing 620ms 120ms cubic-bezier(0.2, 0, 0, 1) both;
    border: 1px solid rgba(23, 116, 61, 0.22);
    border-radius: inherit;
    content: '';
    inset: 0;
    position: absolute;
  }

  .success-mark svg {
    height: 32px;
    width: 32px;
  }

  .success-check {
    animation: successCheck 440ms 180ms cubic-bezier(0.2, 0, 0, 1) forwards;
    stroke-dasharray: 1;
    stroke-dashoffset: 1;
  }

  @keyframes successPop {
    from {
      opacity: 0;
      transform: scale(0.78);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  @keyframes successRing {
    from {
      opacity: 0.7;
      transform: scale(1);
    }
    to {
      opacity: 0;
      transform: scale(1.35);
    }
  }

  @keyframes successCheck {
    to {
      stroke-dashoffset: 0;
    }
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
