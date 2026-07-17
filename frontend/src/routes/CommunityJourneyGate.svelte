<script>
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';
  import { userStore } from '../lib/userStore.js';
  import CommunityJourney from './CommunityJourney.svelte';

  let verificationState = $state('loading');
  let requestId = 0;

  async function verifyProfile() {
    const currentRequestId = ++requestId;
    verificationState = 'loading';

    try {
      const user = await userStore.loadUser();
      if (currentRequestId !== requestId) return;

      if (!user) {
        verificationState = 'error';
        return;
      }

      if (user.creator) {
        verificationState = 'redirecting';
        replace('/community');
        return;
      }

      verificationState = 'ready';
    } catch {
      if (currentRequestId === requestId) verificationState = 'error';
    }
  }

  onMount(() => {
    verifyProfile();
    return () => {
      requestId += 1;
    };
  });
</script>

<svelte:head>
  <title>Community Journey | GenLayer Portal</title>
</svelte:head>

{#if verificationState === 'ready'}
  <CommunityJourney />
{:else}
  <div class="flex min-h-[420px] items-center justify-center px-4 py-12">
    {#if verificationState === 'error'}
      <section class="w-full max-w-lg rounded-[8px] border border-[#e6e6e6] bg-white p-8 text-center" aria-labelledby="journey-profile-error-title" role="status">
        <h1 id="journey-profile-error-title" class="text-xl font-semibold text-black">We couldn't verify your profile</h1>
        <p class="mt-2 text-sm leading-6 text-[#666]">Your journey has not been changed. Try again when the connection is available.</p>
        <button
          type="button"
          class="mt-5 h-10 rounded-[8px] bg-[#8d81e1] px-5 text-sm font-semibold text-white transition-colors hover:bg-[#7669d4]"
          onclick={verifyProfile}
        >
          Retry
        </button>
      </section>
    {:else}
      <div class="flex items-center gap-3 text-sm text-[#666]" role="status">
        <span class="h-5 w-5 animate-spin rounded-full border-2 border-[#d9d2ff] border-t-[#8d81e1]" aria-hidden="true"></span>
        <span>{verificationState === 'redirecting' ? 'Taking you back to Community...' : 'Verifying your profile...'}</span>
      </div>
    {/if}
  </div>
{/if}
