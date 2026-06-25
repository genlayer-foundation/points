<script>
  // @ts-nocheck
  // Role "main route" shell for /builders, /validators, /community.
  //   earned role        -> the existing category Dashboard
  //   everything else    -> an informative landing with the right CTA
  // Category comes from the route (currentCategory), like Dashboard itself.
  import { authState } from '../../lib/auth.js';
  import { journeyAPI } from '../../lib/api.js';
  import { userStore } from '../../lib/userStore.js';
  import { currentCategory } from '../../stores/category.js';
  import { roleFunnelState, hasEarnedRole, hasStartedJourney } from '../../lib/roleState.js';
  import Dashboard from '../../routes/Dashboard.svelte';
  import RoleLanding from './RoleLanding.svelte';
  import BuilderJourney from '../../routes/BuilderJourney.svelte';
  import ValidatorWaitlist from '../../routes/ValidatorWaitlist.svelte';
  import CommunityJourney from '../../routes/CommunityJourney.svelte';

  let category = $derived($currentCategory);
  let isAuth = $derived($authState.isAuthenticated);
  let user = $derived($userStore.user);
  let baseState = $derived(roleFunnelState(isAuth, user, category));
  let communityJourney = $state(null);
  let communityJourneyLoading = $state(false);
  let communityJourneyKey = $state('');
  let communityJourneyFailed = $state(false);
  let shouldCheckCommunityJourney = $derived(
    category === 'community' &&
      isAuth &&
      Boolean(user) &&
      (hasEarnedRole(user, 'community') || hasStartedJourney(user, 'community')),
  );
  let funnelState = $derived.by(() => {
    if (category !== 'community') return baseState;
    if (!isAuth) return 'unauthenticated';
    if (!user) return baseState;
    if (!shouldCheckCommunityJourney) return baseState;

    if (communityJourneyLoading && !communityJourney && !communityJourneyFailed) {
      return 'checking';
    }

    if (communityJourney?.is_member && communityJourney?.complete) {
      return 'earned';
    }

    // Fail closed for Community: never show the Dashboard unless the status
    // endpoint confirms that the role was claimed after all journey steps.
    return 'started';
  });

  $effect(() => {
    const key = shouldCheckCommunityJourney
      ? [
          user?.id || user?.address || '',
          user?.creator ? 1 : 0,
          user?.has_community_welcome ? 1 : 0,
          user?.has_community_link_x ? 1 : 0,
          user?.has_community_link_discord ? 1 : 0,
        ].join(':')
      : '';

    if (key === communityJourneyKey) return;
    communityJourneyKey = key;
    communityJourney = null;
    communityJourneyFailed = false;

    if (key) loadCommunityJourney(key);
  });

  async function loadCommunityJourney(key) {
    communityJourneyLoading = true;
    try {
      const res = await journeyAPI.communityJourney();
      if (key !== communityJourneyKey) return;
      communityJourney = res.data || null;
    } catch {
      if (key === communityJourneyKey) communityJourneyFailed = true;
    } finally {
      if (key === communityJourneyKey) communityJourneyLoading = false;
    }
  }
</script>

{#if isAuth && !user}
  <!-- Authenticated but user not loaded yet: avoid flashing the landing for an
       earned-role user before /users/me/ resolves. -->
  <div class="flex justify-center p-16">
    <div class="h-8 w-8 animate-spin rounded-full border-b-2 border-gray-400"></div>
  </div>
{:else if funnelState === 'earned'}
  <Dashboard />
{:else if funnelState === 'checking'}
  <div class="flex justify-center p-16">
    <div class="h-8 w-8 animate-spin rounded-full border-b-2 border-gray-400"></div>
  </div>
{:else if funnelState === 'started'}
  <!-- Journey in progress: show the journey view (steps), not the landing. -->
  {#if category === 'builder'}
    <BuilderJourney />
  {:else if category === 'validator'}
    {#if user?.['has_validator_waitlist']}
      <!-- Already joined the waitlist: show the landing with a status CTA
           (awaiting admin graduation), not the join form again. -->
      <RoleLanding category="validator" state="waitlisted" />
    {:else}
      <ValidatorWaitlist />
    {/if}
  {:else}
    <CommunityJourney />
  {/if}
{:else}
  <RoleLanding {category} state={funnelState} />
{/if}
