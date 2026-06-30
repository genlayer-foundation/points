<script>
  import { authState, startPendingSignupEmail } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { journeyAPI, updateUserProfile } from '../lib/api.js';
  import { push, location } from 'svelte-spa-router';
  import { detectCategoryFromRoute } from '../stores/category.js';
  import { journeyPath, roleForCategory } from '../lib/roleState.js';
  import {
    getAnalyticsContext,
    getFunnelDurationMs,
    markLifecycleTime,
    markFunnelTime,
    templateRoute,
    trackEvent,
  } from '../lib/analytics.js';
  import Turnstile from './Turnstile.svelte';

  // Form state
  let email = $state('');
  let name = $state('');
  let submittingProfile = $state(false);
  let profileError = $state('');
  let pendingLinkSent = $state(false);
  let turnstileToken = $state('');
  let turnstileWidget = $state(null);

  // Track which fields were pre-filled
  let hasExistingName = $state(false);
  let hasExistingEmail = $state(false);

  // Role selection. Preselected from the entry route; once the user clicks a
  // role we stop overriding it. Drives the post-completion journey start and
  // redirect only; the role itself is earned later via the journey.
  const ROLE_OPTIONS = [
    {
      value: 'builder',
      label: 'Builder',
      eyebrow: 'Build',
      description: 'Ship Intelligent Contracts and ecosystem projects.',
      icon: '/assets/illustrations/builder-badge-small.svg',
      accent: '#ee8521',
      accentRgb: '238, 133, 33',
    },
    {
      value: 'validator',
      label: 'Validator',
      eyebrow: 'Reason',
      description: 'Run infrastructure and adjudicate protocol decisions.',
      icon: '/assets/illustrations/validator-badge-small.svg',
      accent: '#387de8',
      accentRgb: '56, 125, 232',
    },
    {
      value: 'community',
      label: 'Community',
      eyebrow: 'Connect',
      description: 'Create content, test flows, and expand the network.',
      icon: '/assets/illustrations/community-badge-small.svg',
      accent: '#7f52e1',
      accentRgb: '127, 82, 225',
    },
  ];
  const ROLE_VALUES = new Set(ROLE_OPTIONS.map((option) => option.value));
  let selectedRole = $state('community');
  let roleTouched = $state(false);
  let preselectedRole = $state('community');
  let preselectedSource = $state('route');
  let lastProfileViewKey = $state('');

  function selectRole(value) {
    trackEvent('onboarding_role_selected', getAnalyticsContext({
      selected_role: value,
      preselected_role: preselectedRole,
      selection_source: 'user',
      source_route: templateRoute($location),
    }));
    selectedRole = value;
    roleTouched = true;
  }

  // Determine if profile is incomplete
  let showGuard = $derived.by(() => {
    // Don't show while loading
    if ($authState.loading || $userStore.loading) return false;

    if ($authState.pendingSignup) return true;

    // Only show if authenticated
    if (!$authState.isAuthenticated) return false;

    // Only show if we have user data
    const user = $userStore.user;
    if (!user) return false;

    // Check if profile is incomplete
    const needsName = !user.name || user.name.trim() === '';

    return needsName;
  });

  // Preselect the role from where the user started auth (captured at sign-in,
  // before the post-login redirect), falling back to the current route. Holds
  // until the user picks one.
  $effect(() => {
    if (showGuard && !roleTouched) {
      let stored = null;
      try { stored = sessionStorage.getItem('onboardingRole'); } catch {}
      // The stored value is untrusted (may be stale/invalid) — only honor it
      // when it's a known role, otherwise fall back to the current route.
      const nextRole = ROLE_VALUES.has(stored)
        ? stored
        : roleForCategory(detectCategoryFromRoute($location));
      selectedRole = nextRole;
      preselectedRole = nextRole;
      preselectedSource = ROLE_VALUES.has(stored) ? 'session' : 'route';
    }
  });

  $effect(() => {
    if (!showGuard) {
      lastProfileViewKey = '';
      return;
    }
    const viewKey = `${preselectedRole}:${$location}`;
    if (viewKey === lastProfileViewKey) return;
    lastProfileViewKey = viewKey;
    trackEvent('profile_completion_view', getAnalyticsContext({
      preselected_role: preselectedRole,
      selected_role: selectedRole,
      selection_source: preselectedSource,
      source_route: templateRoute($location),
    }));
  });

  // Pre-fill form fields when user data is available
  $effect(() => {
    const user = $userStore.user;
    if (user && showGuard) {
      // Pre-fill name if it exists
      if (user.name && user.name.trim() !== '') {
        name = user.name;
        hasExistingName = true;
      } else {
        name = '';
        hasExistingName = false;
      }

      // Pre-fill email if it exists and is not auto-generated
      if (user.email && user.email.trim() !== '' && !user.email.endsWith('@ethereum.address')) {
        email = user.email;
        hasExistingEmail = true;
      } else {
        email = '';
        hasExistingEmail = false;
      }
    }
  });

  async function handleProfileSubmit() {
    trackEvent('profile_completion_submit', getAnalyticsContext({
      selected_role: selectedRole,
      preselected_role: preselectedRole,
    }));

    // Validate inputs
    if (!name || ($authState.pendingSignup && !email)) {
      trackEvent('profile_completion_error', getAnalyticsContext({
        selected_role: selectedRole,
        error_stage: 'validation',
      }));
      profileError = $authState.pendingSignup
        ? 'Please provide both email and display name'
        : 'Please provide a display name';
      return;
    }

    if ($authState.pendingSignup && !isValidEmail(email)) {
      trackEvent('profile_completion_error', getAnalyticsContext({
        selected_role: selectedRole,
        error_stage: 'validation',
      }));
      profileError = 'Please enter a valid email address';
      return;
    }

    submittingProfile = true;
    profileError = '';

    try {
      if ($authState.pendingSignup) {
        if (pendingLinkSent) {
          return;
        }

        if (!turnstileToken) {
          profileError = 'Please complete verification first';
          return;
        }

        await startPendingSignupEmail({
          email,
          name,
          selected_role: ROLE_VALUES.has(selectedRole) ? selectedRole : roleForCategory(detectCategoryFromRoute($location)),
          turnstile_token: turnstileToken,
        });
        pendingLinkSent = true;
        profileError = '';
        return;
      } else {
      // Prepare update data
      const updateData = {};
      if (name) updateData.name = name;

      // Submit to backend
      await updateUserProfile(updateData);

      // Update the user store
      userStore.updateUser(updateData);
      }

      // Start the selected journey immediately, then send first-time users
      // straight to it. If the marker request fails, the route will retry on
      // mount so a transient error does not strand the user after saving.
      const targetRole = ROLE_VALUES.has(selectedRole)
        ? selectedRole
        : roleForCategory(detectCategoryFromRoute($location));
      markFunnelTime('profile_completion');
      markLifecycleTime('first_profile_completion');
      trackEvent('profile_completion_success', getAnalyticsContext({
        selected_role: targetRole,
        preselected_role: preselectedRole,
        time_from_wallet_click_ms: getFunnelDurationMs('wallet_click'),
        time_from_wallet_auth_success_ms: getFunnelDurationMs('wallet_auth_success'),
      }));

      trackEvent('journey_start_attempt', getAnalyticsContext({
        role_context: targetRole,
        selected_role: targetRole,
        surface: 'profile_completion',
      }));
      try {
        const startRes = targetRole === 'builder'
          ? await journeyAPI.startBuilderJourney()
          : await journeyAPI.startRoleJourney(targetRole);
        if (startRes.data?.user) userStore.updateUser(startRes.data.user);
        markFunnelTime(`journey_start:${targetRole}`);
        markLifecycleTime(`first_journey_start:${targetRole}`);
        trackEvent('journey_started', getAnalyticsContext({
          role_context: targetRole,
          selected_role: targetRole,
          surface: 'profile_completion',
          journey_state: 'started',
          time_from_wallet_click_ms: getFunnelDurationMs('wallet_click'),
          time_from_wallet_auth_success_ms: getFunnelDurationMs('wallet_auth_success'),
          time_from_profile_completion_ms: getFunnelDurationMs('profile_completion'),
        }));
      } catch (startErr) {
        trackEvent('journey_start_error', getAnalyticsContext({
          role_context: targetRole,
          selected_role: targetRole,
          surface: 'profile_completion',
          error_stage: startErr.response?.status ? 'backend' : 'network',
        }));
        // Best-effort; each journey route also marks itself started.
      }

      // Reload user data to ensure we have the latest.
      await userStore.loadUser();

      try { sessionStorage.removeItem('onboardingRole'); } catch {}
      push(journeyPath(targetRole));
    } catch (err) {
      trackEvent('profile_completion_error', getAnalyticsContext({
        selected_role: selectedRole,
        error_stage: err.response?.status ? 'backend' : 'network',
      }));
      // Handle field-specific errors from Django REST Framework
      if (err.response?.data) {
        const data = err.response.data;
        if (data.email) {
          profileError = data.email;
        } else if (data.name) {
          profileError = data.name;
        } else if (data.error) {
          profileError = data.error;
        } else {
          profileError = err.message || 'Failed to update profile';
        }
      } else {
        profileError = err.message || 'Failed to update profile';
      }
      if ($authState.pendingSignup) {
        turnstileToken = '';
        turnstileWidget?.reset?.();
      }
    } finally {
      submittingProfile = false;
    }
  }

  function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
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

{#if showGuard}
  <div class="profile-guard-backdrop">
    <div class="profile-guard-modal" role="dialog" aria-modal="true" aria-labelledby="profile-guard-title">
      <div class="profile-guard-hero">
        <div class="hero-topline">
          <span class="hero-badge" aria-hidden="true">
            {@render genlayerHexMark()}
          </span>
          <span>GenLayer Portal</span>
        </div>
        <h2 id="profile-guard-title" class="profile-guard-title">Set up your Portal identity</h2>
        <p>Choose how creators, builders, and validators will recognize you across the Portal.</p>
      </div>

      <div class="profile-guard-body">
        <div class="profile-completion-form">
          {#if profileError}
            <div class="profile-error">
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M10 6v5M10 14.5h.01M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
              </svg>
              {profileError}
            </div>
          {/if}

          <div class="identity-grid">
            <div class="form-group">
              <label for="name" class="form-label">
                <span>Username</span>
                {#if hasExistingName}
                  <span class="field-state">Already set</span>
                {/if}
              </label>
              <div class="input-shell" class:is-complete={hasExistingName}>
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
                <input
                  id="name"
                  type="text"
                  bind:value={name}
                  placeholder="Your public name"
                  class="form-input"
                  disabled={submittingProfile || pendingLinkSent}
                />
              </div>
              <p>Shown on your profile, submissions, and contribution history.</p>
            </div>

            {#if $authState.pendingSignup}
            <div class="form-group">
              <label for="email" class="form-label">
                <span>Email</span>
                {#if hasExistingEmail}
                  <span class="field-state">Already set</span>
                {/if}
              </label>
              <div class="input-shell" class:is-complete={hasExistingEmail}>
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M4 6.5h16v11H4v-11ZM5 8l7 5 7-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <input
                  id="email"
                  type="email"
                  bind:value={email}
                  placeholder="you@example.com"
                  class="form-input"
                  disabled={submittingProfile || pendingLinkSent}
                />
              </div>
              <p>Used for important updates about submissions and rewards.</p>
            </div>
            {/if}
          </div>

          {#if $authState.pendingSignup}
            <div class="form-group">
              {#if pendingLinkSent}
                <div class="form-label">
                  <span>Verification link</span>
                  <span class="field-state">Sent</span>
                </div>
                <div class="verification-link-status">
                  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M4 6.5h16v11H4v-11ZM5 8l7 5 7-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                  <span>Open the verification link sent to {email.trim()} to finish creating your account.</span>
                </div>
              {:else}
                <Turnstile
                  bind:this={turnstileWidget}
                  disabled={submittingProfile}
                  onVerify={(token) => (turnstileToken = token)}
                  onExpire={() => (turnstileToken = '')}
                />
              {/if}
            </div>
          {/if}

          <div class="form-group">
            <span class="form-label role-label">Choose your first journey</span>
            <div class="role-options">
              {#each ROLE_OPTIONS as option}
                <button
                  type="button"
                  class="role-option {selectedRole === option.value ? 'role-option-selected' : ''}"
                  style={`--role-accent: ${option.accent}; --role-accent-rgb: ${option.accentRgb};`}
                  onclick={() => selectRole(option.value)}
                  disabled={submittingProfile}
                  aria-pressed={selectedRole === option.value}
                >
                  <span class="role-card-bg" aria-hidden="true"></span>
                  <span class="role-icon" aria-hidden="true">
                    <img src={option.icon} alt="" />
                  </span>
                  <span class="role-copy">
                    <span class="role-eyebrow">{option.eyebrow}</span>
                    <span class="role-title">{option.label}</span>
                    <span class="role-description">{option.description}</span>
                  </span>
                  <span class="role-check" aria-hidden="true">
                    <svg viewBox="0 0 18 18" fill="none">
                      <path d="m4.25 9.25 3 3 6.5-6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </span>
                </button>
              {/each}
            </div>
          </div>

          <button
            onclick={handleProfileSubmit}
            disabled={submittingProfile || !name.trim() || ($authState.pendingSignup && (pendingLinkSent || !email.trim() || !turnstileToken))}
            class="profile-submit-button"
          >
            {#if submittingProfile}
              <div class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Sending...
            {:else}
              {#if $authState.pendingSignup}
                {pendingLinkSent ? 'Verification link sent' : 'Send verification link'}
              {:else}
                Continue
              {/if}
            {/if}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .profile-guard-backdrop {
    position: fixed;
    inset: 0;
    background:
      radial-gradient(circle at 18% 12%, rgba(238, 133, 33, 0.24), transparent 25rem),
      radial-gradient(circle at 78% 18%, rgba(56, 125, 232, 0.19), transparent 24rem),
      radial-gradient(circle at 52% 84%, rgba(127, 82, 225, 0.22), transparent 24rem),
      rgba(14, 14, 16, 0.54);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    animation: fadeIn 0.15s ease-out;
    backdrop-filter: blur(4px);
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .profile-guard-modal {
    background: #fff;
    border-radius: 16px;
    box-shadow:
      0 34px 70px rgba(15, 15, 15, 0.22),
      0 1px 0 rgba(255, 255, 255, 0.85) inset;
    width: 620px;
    max-width: 90vw;
    max-height: min(88vh, 780px);
    overflow-y: auto;
    scroll-behavior: smooth;
    animation: slideUp 0.2s ease-out;
    border: 1px solid rgba(19, 18, 20, 0.08);
  }

  @keyframes slideUp {
    from {
      transform: translateY(10px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .profile-guard-hero {
    background: #ffffff;
    color: #131214;
    padding: 24px;
    position: relative;
    overflow: hidden;
  }

  .profile-guard-hero::before {
    background:
      linear-gradient(90deg,
        rgba(238, 133, 33, 0.34) 0%,
        rgba(255, 230, 132, 0.28) 18%,
        rgba(95, 213, 165, 0.3) 38%,
        rgba(91, 190, 238, 0.3) 58%,
        rgba(151, 132, 238, 0.28) 78%,
        rgba(245, 151, 194, 0.3) 100%
      );
    content: '';
    filter: blur(18px);
    height: 122px;
    left: -20px;
    opacity: 0.95;
    position: absolute;
    right: -20px;
    top: 46%;
    transform: translateY(-50%);
  }

  .profile-guard-hero::after {
    background: linear-gradient(180deg, transparent, rgba(255, 255, 255, 0.36));
    bottom: 0;
    content: '';
    height: 46px;
    left: 0;
    pointer-events: none;
    position: absolute;
    right: 0;
  }

  .hero-topline {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #5d5d64;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0;
    text-transform: uppercase;
    margin-bottom: 16px;
  }

  .hero-badge {
    width: 42px;
    height: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.74);
    border: 1px solid rgba(255, 255, 255, 0.92);
    border-radius: 14px;
    box-shadow: 0 12px 26px rgba(19, 18, 20, 0.1);
  }

  .genlayer-hex-mark {
    display: block;
    width: 34px;
    height: 34px;
  }

  .profile-guard-title {
    color: #131214;
    font-family: var(--font-heading);
    font-size: 26px;
    font-weight: 700;
    line-height: 1.12;
    letter-spacing: 0;
    margin: 0;
    text-wrap: balance;
    position: relative;
    z-index: 1;
  }

  .profile-guard-hero p {
    color: #606068;
    font-size: 14px;
    line-height: 1.55;
    margin: 10px 0 0;
    max-width: 31rem;
    text-wrap: pretty;
    position: relative;
    z-index: 1;
  }

  .profile-guard-body {
    padding: 24px;
  }

  .profile-error {
    align-items: flex-start;
    background-color: #fff1f1;
    border: 1px solid #ffc9c9;
    color: #9f1d1d;
    display: flex;
    gap: 10px;
    padding: 12px 14px;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.45;
    margin-bottom: 18px;
  }

  .profile-error svg {
    flex: 0 0 auto;
    height: 18px;
    margin-top: 1px;
    width: 18px;
  }

  .identity-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .form-group {
    margin-bottom: 18px;
  }

  .form-label {
    align-items: center;
    color: #131214;
    display: flex;
    font-size: 13px;
    font-weight: 700;
    justify-content: space-between;
    letter-spacing: 0;
    margin-bottom: 8px;
  }

  .role-label {
    margin-bottom: 10px;
  }

  .field-state {
    color: #16894d;
    font-size: 11px;
    font-weight: 700;
  }

  .input-shell {
    align-items: center;
    background-color: #fafafa;
    border: 1px solid #ededed;
    border-radius: 8px;
    display: flex;
    gap: 10px;
    min-height: 48px;
    padding: 0 12px;
    transition-duration: 160ms;
    transition-property: background-color, border-color, box-shadow;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .input-shell:focus-within {
    background-color: #fff;
    border-color: #131214;
    box-shadow: 0 0 0 3px rgba(19, 18, 20, 0.08);
  }

  .input-shell.is-complete {
    background-color: #f6fbf8;
    border-color: #ccebd8;
  }

  .input-shell svg {
    color: #8d8d92;
    flex: 0 0 auto;
    height: 20px;
    width: 20px;
  }

  .form-input {
    width: 100%;
    padding: 0;
    font-size: 15px;
    color: #111827;
    background-color: transparent;
    border: 0;
    min-width: 0;
  }

  .form-input:focus {
    outline: none;
  }

  .form-input:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .form-input::placeholder {
    color: #9CA3AF;
  }

  .form-group p {
    color: #737378;
    font-size: 12px;
    line-height: 1.45;
    margin: 7px 0 0;
    text-wrap: pretty;
  }

  .verification-link-status {
    align-items: center;
    background: #f6fbf8;
    border: 1px solid #ccebd8;
    border-radius: 8px;
    color: #19683a;
    display: flex;
    gap: 10px;
    font-size: 13px;
    font-weight: 650;
    line-height: 1.45;
    min-height: 48px;
    padding: 12px;
  }

  .verification-link-status svg {
    flex: 0 0 auto;
    height: 20px;
    width: 20px;
  }

  .role-options {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .role-option {
    background:
      linear-gradient(180deg, rgba(var(--role-accent-rgb), 0.08), rgba(255, 255, 255, 0) 62%),
      #fff;
    border: 1px solid #ededed;
    border-radius: 8px;
    color: #131214;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 9px;
    min-height: 172px;
    min-width: 0;
    overflow: hidden;
    padding: 13px;
    position: relative;
    text-align: left;
    transition-duration: 160ms;
    transition-property: border-color, box-shadow, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .role-option:hover:not(:disabled) {
    border-color: rgba(var(--role-accent-rgb), 0.42);
    box-shadow: 0 14px 28px rgba(var(--role-accent-rgb), 0.12);
    transform: translateY(-1px);
  }

  .role-option:active:not(:disabled) {
    transform: scale(0.96);
  }

  .role-option-selected {
    border-color: rgba(var(--role-accent-rgb), 0.88);
    box-shadow:
      0 0 0 3px rgba(var(--role-accent-rgb), 0.14),
      0 14px 30px rgba(var(--role-accent-rgb), 0.14);
  }

  .role-option:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .role-card-bg {
    background: radial-gradient(circle at 50% 0%, rgba(var(--role-accent-rgb), 0.2), transparent 58%);
    inset: 0;
    opacity: 0;
    pointer-events: none;
    position: absolute;
    transition: opacity 160ms cubic-bezier(0.2, 0, 0, 1);
  }

  .role-option-selected .role-card-bg,
  .role-option:hover .role-card-bg {
    opacity: 1;
  }

  .role-icon {
    display: block;
    height: 44px;
    position: relative;
    width: 44px;
  }

  .role-icon img {
    display: block;
    height: 100%;
    width: 100%;
  }

  .role-copy {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
    position: relative;
  }

  .role-eyebrow {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1.2;
    text-transform: uppercase;
  }

  .role-title {
    color: #131214;
    font-size: 16px;
    font-weight: 800;
    line-height: 1.25;
    margin-top: 4px;
  }

  .role-description {
    color: #6f6f75;
    font-size: 12px;
    line-height: 1.38;
    margin-top: 6px;
    text-wrap: pretty;
  }

  .role-check {
    align-items: center;
    background: var(--role-accent);
    border-radius: 999px;
    color: #fff;
    display: flex;
    height: 22px;
    justify-content: center;
    opacity: 0;
    position: absolute;
    right: 12px;
    scale: 0.25;
    top: 12px;
    transform-origin: center;
    transition-duration: 180ms;
    transition-property: opacity, scale, filter;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    filter: blur(4px);
    width: 22px;
  }

  .role-option-selected .role-check {
    opacity: 1;
    scale: 1;
    filter: blur(0);
  }

  .role-check svg {
    height: 14px;
    width: 14px;
  }

  .profile-submit-button {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 48px;
    padding: 0.875rem 1rem;
    font-size: 15px;
    font-weight: 800;
    color: white;
    background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.12), transparent 34%),
      #131214;
    border: none;
    border-radius: 999px;
    cursor: pointer;
    transition-duration: 160ms;
    transition-property: background-color, box-shadow, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    margin-top: 4px;
    box-shadow: 0 14px 28px rgba(19, 18, 20, 0.18);
  }

  .profile-submit-button:hover:not(:disabled) {
    background-color: #1a1a1f;
    box-shadow: 0 18px 34px rgba(19, 18, 20, 0.22);
    transform: translateY(-1px);
  }

  .profile-submit-button:active:not(:disabled) {
    transform: scale(0.96);
  }

  .profile-submit-button:disabled {
    opacity: 0.6;
    cursor: default;
    transform: none;
  }

  /* Responsive design */
  @media (max-width: 640px) {
    .profile-guard-modal {
      width: calc(100vw - 2rem);
      max-height: 90vh;
    }

    .profile-guard-hero {
      padding: 20px;
    }

    .profile-guard-body {
      padding: 18px;
    }

    .identity-grid,
    .role-options {
      grid-template-columns: 1fr;
    }

    .role-option {
      min-height: 0;
      flex-direction: row;
      align-items: center;
      padding-right: 42px;
    }

    .role-icon {
      flex: 0 0 auto;
    }
  }
</style>
