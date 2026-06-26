<script>
  // @ts-nocheck
  // Role "main route" shell for /builders, /validators, /community.
  //   earned role        -> the existing category Dashboard
  //   started journey    -> the role's journey view (steps)
  //   everything else    -> an informative landing with the right CTA
  // "Earned" is role membership (user.builder/validator/creator), read straight
  // off /users/me/. Existing members are grandfathered to their Dashboard; the
  // journey only gates newcomers who do not hold the role yet.
  import { authState } from '../../lib/auth.js';
  import { userStore } from '../../lib/userStore.js';
  import { currentCategory } from '../../stores/category.js';
  import { roleFunnelState } from '../../lib/roleState.js';
  import Dashboard from '../../routes/Dashboard.svelte';
  import RoleLanding from './RoleLanding.svelte';
  import BuilderJourney from '../../routes/BuilderJourney.svelte';
  import ValidatorWaitlist from '../../routes/ValidatorWaitlist.svelte';
  import CommunityJourney from '../../routes/CommunityJourney.svelte';

  let category = $derived($currentCategory);
  let isAuth = $derived($authState.isAuthenticated);
  // authState defaults to unauthenticated and verifyAuth() is async, so until
  // the session is verified we must not render the signed-out landing or a
  // logged-in user briefly sees it flash before their dashboard loads.
  let isChecking = $derived(!$authState.hasVerified);
  let user = $derived($userStore.user);
  let funnelState = $derived(roleFunnelState(isAuth, user, category));
</script>

{#if isChecking || (isAuth && !user)}
  <!-- Session still verifying, or authenticated but /users/me/ not loaded yet:
       show a neutral spinner instead of flashing the signed-out landing. -->
  <div class="flex justify-center p-16">
    <div class="h-8 w-8 animate-spin rounded-full border-b-2 border-gray-400"></div>
  </div>
{:else if funnelState === 'earned'}
  <Dashboard />
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
