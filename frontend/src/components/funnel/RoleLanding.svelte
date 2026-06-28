<script>
  // @ts-ignore svelte-spa-router does not ship type declarations in this app.
  import { push } from 'svelte-spa-router';
  import { journeyPath } from '../../lib/roleState.js';
  import { journeyAPI } from '../../lib/api.js';
  import { userStore } from '../../lib/userStore.js';
  import { showError } from '../../lib/toastStore.js';
  import {
    getAnalyticsContext,
    getFunnelDurationMs,
    markLifecycleTime,
    markFunnelTime,
    setConnectWalletIntent,
    trackEvent,
  } from '../../lib/analytics.js';
  import BuilderLanding from './BuilderLanding.svelte';
  import ValidatorLanding from './ValidatorLanding.svelte';
  import CommunityLanding from './CommunityLanding.svelte';
  import AuthenticatedRoleLanding from './AuthenticatedRoleLanding.svelte';

  let { category = 'community', state: roleState = 'unauthenticated' } = $props();

  let starting = $state(false);
  let lastViewKey = $state('');

  let ctaId = $derived(roleState === 'unauthenticated' ? `${category}_connect_wallet` : `${category}_start_journey`);

  $effect(() => {
    const viewKey = `${category}:${roleState}`;
    if (viewKey === lastViewKey) return;
    lastViewKey = viewKey;
    markFunnelTime(`role_landing:${category}`);
    trackEvent('role_landing_view', getAnalyticsContext({
      role_context: category,
      selected_role: category,
      role_funnel_state: roleState,
      journey_state: roleState === 'waitlisted' ? 'waitlisted' : undefined,
      surface: 'role_landing',
      cta_id: ctaId,
    }));
    if (category === 'validator' && roleState === 'waitlisted') {
      trackEvent('validator_waitlist_status_view', getAnalyticsContext({
        role_context: 'validator',
        role_funnel_state: 'waitlisted',
        journey_state: 'waitlisted',
        surface: 'role_landing',
      }));
    }
  });

  async function handleStart(role = category) {
    trackEvent('role_cta_click', getAnalyticsContext({
      role_context: role,
      selected_role: role,
      role_funnel_state: roleState,
      surface: 'role_landing',
      cta_id: ctaId,
    }));

    if (roleState === 'unauthenticated') {
      setConnectWalletIntent({
        surface: 'role_landing',
        cta_id: ctaId,
        selected_role: role,
      });
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton instanceof HTMLElement) authButton.click();
      return;
    }

    if (starting) return;
    starting = true;
    trackEvent('journey_start_attempt', getAnalyticsContext({
      role_context: role,
      selected_role: role,
      surface: 'role_landing',
    }));
    try {
      const response = await journeyAPI.startRoleJourney(role);
      // Journey marker created server-side — navigate now. The user refresh is
      // best-effort and must not block (or fail) entering the journey.
      if (response.data?.user) {
        userStore.setUser(response.data.user);
      } else {
        userStore.loadUser?.()?.catch(() => {});
      }
      markFunnelTime(`journey_start:${role}`);
      markLifecycleTime(`first_journey_start:${role}`);
      trackEvent('journey_started', getAnalyticsContext({
        role_context: role,
        selected_role: role,
        surface: 'role_landing',
        journey_state: 'started',
        time_from_role_landing_ms: getFunnelDurationMs(`role_landing:${role}`),
        time_from_wallet_click_ms: getFunnelDurationMs('wallet_click'),
        time_from_wallet_auth_success_ms: getFunnelDurationMs('wallet_auth_success'),
        time_from_profile_completion_ms: getFunnelDurationMs('profile_completion'),
      }));
      push(journeyPath(role));
    } catch (err) {
      trackEvent('journey_start_error', getAnalyticsContext({
        role_context: role,
        selected_role: role,
        surface: 'role_landing',
        error_stage: err.response?.status ? 'backend' : 'network',
      }));
      showError('Could not start this journey. Please try again.');
    } finally {
      starting = false;
    }
  }
</script>

{#if roleState !== 'unauthenticated'}
  <AuthenticatedRoleLanding {category} state={roleState} {starting} onStart={() => handleStart(category)} />
{:else if category === 'builder'}
  <BuilderLanding state={roleState} {starting} onStart={() => handleStart('builder')} />
{:else if category === 'validator'}
  <ValidatorLanding state={roleState} {starting} onStart={() => handleStart('validator')} />
{:else}
  <CommunityLanding state={roleState} {starting} onStart={() => handleStart('community')} />
{/if}
