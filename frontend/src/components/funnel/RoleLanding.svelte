<script>
  // @ts-ignore svelte-spa-router does not ship type declarations in this app.
  import { push } from 'svelte-spa-router';
  import { journeyPath } from '../../lib/roleState.js';
  import { journeyAPI } from '../../lib/api.js';
  import { userStore } from '../../lib/userStore.js';
  import { showError } from '../../lib/toastStore.js';
  import BuilderLanding from './BuilderLanding.svelte';
  import ValidatorLanding from './ValidatorLanding.svelte';
  import CommunityLanding from './CommunityLanding.svelte';

  let { category = 'community', state: roleState = 'unauthenticated' } = $props();

  let starting = $state(false);

  async function handleStart(role = category) {
    if (roleState === 'unauthenticated') {
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton instanceof HTMLElement) authButton.click();
      return;
    }

    if (starting) return;
    starting = true;
    try {
      await journeyAPI.startRoleJourney(role);
      await userStore.loadUser?.();
      push(journeyPath(role));
    } catch {
      showError('Could not start this journey. Please try again.');
    } finally {
      starting = false;
    }
  }
</script>

{#if category === 'builder'}
  <BuilderLanding state={roleState} {starting} onStart={() => handleStart('builder')} />
{:else if category === 'validator'}
  <ValidatorLanding state={roleState} {starting} onStart={() => handleStart('validator')} />
{:else}
  <CommunityLanding state={roleState} {starting} onStart={() => handleStart('community')} />
{/if}
