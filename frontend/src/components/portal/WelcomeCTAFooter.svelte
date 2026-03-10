<script>
  import { push } from 'svelte-spa-router';
  import { userStore } from '../../lib/userStore.js';
  import { authState } from '../../lib/auth.js';

  let storeValue = $state({ user: null });

  userStore.subscribe(value => {
    storeValue = value;
  });

  let authValue = $state({ isAuthenticated: false });

  authState.subscribe(value => {
    authValue = value;
  });

  let userName = $derived(storeValue.user?.name || storeValue.user?.address?.slice(0, 8) || '');
  let isLoggedIn = $derived(authValue.isAuthenticated && !!storeValue.user);
  let heading = $derived(isLoggedIn ? `Keep building, ${userName}` : 'Start contributing today');
</script>

<div class="relative overflow-hidden rounded-[8px]">
  <div class="px-[20px] pt-[160px] pb-[80px] flex items-center justify-center">
    <div class="flex flex-col gap-[24px] items-center text-center">
      <!-- Rank pill -->
      {#if isLoggedIn}
        <div class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px]" style="background: rgba(255,255,255,0.1);">
          <div class="relative w-[24px] h-[24px]">
            <img src="/assets/illustrations/gl-polygon.svg" alt="" class="absolute inset-[1.45%_6.7%] w-[86.6%] h-[97.1%]" />
            <img src="/assets/illustrations/gl-symbol-white.svg" alt="" class="absolute inset-[22.66%_24.69%_29.53%_24.69%] w-[50.62%] h-[47.81%]" />
          </div>
          <span class="text-[12px] font-medium text-black leading-[15px]" style="letter-spacing: 0.24px;">
            163 Points to Overall Rank #6
          </span>
        </div>
      {/if}

      <h2 class="text-[40px] md:text-[64px] font-medium font-display leading-[64px] text-black" style="letter-spacing: -1.28px;">
        {heading}
      </h2>
      <p class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">
        {#if isLoggedIn}
          Invite other builders to GenLayer and receive 10% of the points they make, forever.
        {:else}
          Join professional validators and builders in creating the trust infrastructure for the AI age.
        {/if}
      </p>

      <div class="flex gap-[8px] items-start">
        <button
          onclick={() => push(isLoggedIn ? '/submit-contribution' : '/builders/welcome')}
          class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] transition-colors hover:opacity-90"
          style="background-color: #9e4bf6;"
        >
          {#if isLoggedIn}
            <img src="/assets/icons/link-m.svg" alt="" class="w-4 h-4" />
          {/if}
          <span class="text-[14px] font-medium text-white leading-[21px]" style="letter-spacing: 0.28px;">
            {isLoggedIn ? 'Referral link' : 'Get started'}
          </span>
          {#if !isLoggedIn}
            <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="w-4 h-4" />
          {/if}
        </button>
        <a
          href="https://docs.genlayer.com"
          target="_blank"
          rel="noopener noreferrer"
          class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] border border-black transition-colors hover:bg-black/5"
        >
          <span class="text-[14px] font-medium text-black leading-[21px]" style="letter-spacing: 0.28px;">
            Read the Docs
          </span>
          <img src="/assets/icons/arrow-right-line-black.svg" alt="" class="w-4 h-4" />
        </a>
      </div>
    </div>
  </div>
</div>
