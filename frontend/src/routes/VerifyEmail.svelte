<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import {
    authState,
    confirmEmailVerification,
    confirmPendingSignupEmail,
    verifyAuth,
  } from '../lib/auth.js';
  import { journeyAPI } from '../lib/api.js';
  import { journeyPath } from '../lib/roleState.js';
  import { userStore } from '../lib/userStore.js';
  import EmailVerificationModal from '../components/EmailVerificationModal.svelte';

  const ROLE_VALUES = new Set(['builder', 'validator', 'community']);

  let status = $state('loading');
  let title = $state('Verifying email');
  let message = $state('Checking your verification link...');
  let destination = $state('/profile');
  let pendingFlow = $state(false);
  let recoveryLabel = $state('Go to profile');
  let recoveryPath = $state('/profile');
  let showEmailModal = $state(false);
  let modalEmail = $state('');
  let modalDestination = $state('/');

  function extractError(err) {
    const data = err?.response?.data;
    return data?.code || data?.token || data?.detail || data?.email || 'This verification link is invalid or has expired.';
  }

  function consumeAuthenticatedDestination(address) {
    try {
      const redirectPath = sessionStorage.getItem('redirectAfterLogin');
      if (redirectPath) {
        sessionStorage.removeItem('redirectAfterLogin');
        return redirectPath;
      }
    } catch {}
    return address ? `/participant/${address}` : '/';
  }

  function getPostLoginDestination(role, address) {
    if (ROLE_VALUES.has(role)) return journeyPath(role);
    try {
      return sessionStorage.getItem('redirectAfterLogin') || (address ? `/participant/${address}` : '/');
    } catch {}
    return address ? `/participant/${address}` : '/';
  }

  function rememberPostLoginDestination(path) {
    if (!path || path === '/') return;
    try {
      sessionStorage.setItem('redirectAfterLogin', path);
    } catch {}
  }

  function goToRecovery() {
    push(recoveryPath);
  }

  function completeModalVerification(updatedUser) {
    userStore.updateUser(updatedUser);
    status = 'success';
    title = 'Email verified';
    message = 'Your Portal account now has a verified email.';
    destination = modalDestination;
  }

  function closeModalVerification() {
    showEmailModal = false;
    push(modalDestination);
  }

  async function startSelectedJourney(role) {
    if (!ROLE_VALUES.has(role)) return false;
    try {
      const response = role === 'builder'
        ? await journeyAPI.startBuilderJourney()
        : await journeyAPI.startRoleJourney(role);
      if (response.data?.user) userStore.updateUser(response.data.user);
    } catch {
      // Best-effort; journey routes also mark themselves started on mount.
    }
    destination = journeyPath(role);
    return true;
  }

  onMount(async () => {
    const token = new URLSearchParams(window.location.search).get('token');
    await verifyAuth();
    const state = authState.get();

    if (!token) {
      if (!state.isAuthenticated) {
        status = 'error';
        title = 'Sign in required';
        message = 'Sign in with your wallet, then verify your email from the Portal.';
        recoveryLabel = 'Go home';
        recoveryPath = '/';
        return;
      }

      let currentUser = userStore.getUser();
      try {
        currentUser = currentUser || await userStore.loadUser();
      } catch {}
      modalEmail = currentUser?.email || '';
      modalDestination = state.address ? `/participant/${state.address}` : '/';
      if (currentUser?.is_email_verified) {
        status = 'success';
        title = 'Email already verified';
        message = 'Your Portal account already has a verified email.';
        destination = modalDestination;
      } else {
        showEmailModal = true;
        status = 'modal';
        title = 'Verify your email';
        message = 'Complete verification with a one-time code.';
      }
      return;
    }

    try {
      if (state.pendingSignup || !state.isAuthenticated) {
        pendingFlow = true;
        const response = await confirmPendingSignupEmail(token);
        const address = response.data?.address || authState.get().address;
        if (response.data?.requires_wallet_login) {
          rememberPostLoginDestination(getPostLoginDestination(response.data?.selected_role, address));
          destination = '/';
          title = 'Email verified';
          message = 'Sign in with your wallet to continue.';
        } else {
          const roleStarted = await startSelectedJourney(response.data?.selected_role);
          if (!roleStarted) {
            destination = consumeAuthenticatedDestination(address);
          }
        }
      } else {
        await confirmEmailVerification(token);
        await userStore.loadUser();
        destination = '/profile';
      }

      status = 'success';
      title = 'Email verified';
      if (message === 'Checking your verification link...') {
        message = 'Redirecting...';
      }
      setTimeout(() => push(destination), 900);
    } catch (err) {
      status = 'error';
      title = 'Link could not be verified';
      message = extractError(err);
      recoveryLabel = pendingFlow ? 'Request a new link' : 'Go to profile';
      recoveryPath = pendingFlow ? '/' : '/profile';
    }
  });
</script>

{#snippet genlayerHexMark()}
  <svg class="genlayer-hex-mark" viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M21.75 2.304c1.393-.804 3.107-.804 4.5 0l15.535 8.968c1.393.804 2.25 2.29 2.25 3.897v17.937c0 1.607-.857 3.092-2.25 3.897L26.25 45.971c-1.393.804-3.107.804-4.5 0L6.215 37.003c-1.393-.805-2.25-2.29-2.25-3.897V15.169c0-1.607.857-3.093 2.25-3.897L21.75 2.304Z" fill="#131214" />
    <g transform="translate(10.75 8.5) scale(0.78)" fill="#fff">
      <path d="M15.4065 11.2607L9.64908 23.3639L15.0689 26.072L0 32L15.4065 0V11.2607Z" />
      <path d="M18.6229 11.2607L24.3803 23.3639L18.9605 26.072L34.0294 32L18.6229 0V11.2607Z" />
      <path d="M16.9311 15.2394L20.3041 21.9088L16.9311 23.5623L13.7392 21.9019L16.9311 15.2394Z" />
    </g>
  </svg>
{/snippet}

<section class="verify-email-page">
  <div class="verify-email-panel" aria-live="polite">
    <div class="verify-email-hero">
      <div class="hero-topline">
        <span class="hero-badge" aria-hidden="true">
          {@render genlayerHexMark()}
        </span>
        <span>GenLayer Portal</span>
      </div>
      <div class="status-mark {status}">
        {#if status === 'loading'}
          <span class="spinner" aria-hidden="true"></span>
        {:else if status === 'success'}
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="m5 12.5 4.2 4.2L19 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        {:else if status === 'modal'}
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 6.5h16v11H4v-11ZM5 8l7 5 7-5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        {:else}
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 7v6M12 17h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        {/if}
      </div>
    </div>

    <div class="verify-email-copy">
      <h1>{title}</h1>
      <p>{message}</p>
    </div>

    {#if status === 'success'}
      <button type="button" onclick={() => push(destination)}>Continue</button>
    {:else if status === 'error'}
      <button type="button" onclick={goToRecovery}>{recoveryLabel}</button>
    {/if}
  </div>
</section>

{#if showEmailModal}
  <EmailVerificationModal
    initialEmail={modalEmail}
    onClose={closeModalVerification}
    onVerified={completeModalVerification}
  />
{/if}

<style>
  .verify-email-page {
    align-items: center;
    background:
      linear-gradient(135deg, rgba(255, 247, 237, 0.92), rgba(245, 248, 255, 0.96) 48%, rgba(249, 246, 255, 0.94)),
      #f6f6f4;
    display: flex;
    justify-content: center;
    min-height: calc(100vh - 5rem);
    padding: 24px;
  }

  .verify-email-panel {
    align-items: center;
    background: #fff;
    border: 1px solid rgba(19, 18, 20, 0.08);
    border-radius: 16px;
    box-shadow:
      0 34px 70px rgba(15, 15, 15, 0.14),
      0 1px 0 rgba(255, 255, 255, 0.85) inset;
    display: flex;
    flex-direction: column;
    max-width: 470px;
    overflow: hidden;
    text-align: center;
    width: 100%;
  }

  .verify-email-hero {
    align-items: center;
    background:
      linear-gradient(90deg,
        rgba(238, 133, 33, 0.22) 0%,
        rgba(255, 230, 132, 0.18) 18%,
        rgba(95, 213, 165, 0.2) 38%,
        rgba(91, 190, 238, 0.2) 58%,
        rgba(151, 132, 238, 0.18) 78%,
        rgba(245, 151, 194, 0.2) 100%
      ),
      #ffffff;
    display: flex;
    flex-direction: column;
    padding: 24px 24px 22px;
    width: 100%;
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
    margin-bottom: 20px;
    text-transform: uppercase;
  }

  .hero-badge {
    align-items: center;
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.92);
    border-radius: 14px;
    box-shadow: 0 12px 26px rgba(19, 18, 20, 0.1);
    display: inline-flex;
    height: 42px;
    justify-content: center;
    width: 42px;
  }

  .genlayer-hex-mark {
    display: block;
    height: 34px;
    width: 34px;
  }

  .status-mark {
    align-items: center;
    border-radius: 999px;
    display: flex;
    height: 62px;
    justify-content: center;
    width: 62px;
  }

  .status-mark.loading {
    background: rgba(255, 255, 255, 0.76);
    color: #4b5563;
    box-shadow: 0 12px 28px rgba(19, 18, 20, 0.1);
  }

  .status-mark.success {
    background: #edf9f1;
    color: #17743d;
  }

  .status-mark.modal {
    background: #f4f4f5;
    color: #4f5057;
  }

  .status-mark.error {
    background: #fff2f2;
    color: #b42318;
  }

  .status-mark svg {
    height: 30px;
    width: 30px;
  }

  .spinner {
    animation: spin 0.8s linear infinite;
    border: 2px solid #d1d5db;
    border-top-color: #111827;
    border-radius: 999px;
    height: 27px;
    width: 27px;
  }

  .verify-email-copy {
    padding: 26px 30px 0;
  }

  h1 {
    color: #131214;
    font-family: var(--font-heading);
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 1.12;
    margin: 0;
    text-wrap: balance;
  }

  p {
    color: #606068;
    font-size: 14px;
    line-height: 1.55;
    margin: 10px 0 0;
    text-wrap: pretty;
  }

  button {
    background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.12), transparent 34%),
      #131214;
    border: 0;
    border-radius: 999px;
    box-shadow: 0 14px 28px rgba(19, 18, 20, 0.18);
    color: #fff;
    cursor: pointer;
    font-size: 14px;
    font-weight: 800;
    margin: 24px 30px 30px;
    min-height: 46px;
    min-width: 148px;
    padding: 0 22px;
    transition-duration: 160ms;
    transition-property: background-color, box-shadow, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  button:hover {
    background-color: #1a1a1f;
    box-shadow: 0 18px 34px rgba(19, 18, 20, 0.22);
    transform: translateY(-1px);
  }

  button:active {
    transform: scale(0.96);
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 560px) {
    .verify-email-page {
      padding: 16px;
    }

    .verify-email-copy {
      padding: 24px 22px 0;
    }

    button {
      margin: 22px 22px 26px;
      width: calc(100% - 44px);
    }
  }
</style>
