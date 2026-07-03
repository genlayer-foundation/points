<script>
  import { userStore } from '../../../lib/userStore.js';
  import { authState } from '../../../lib/auth.js';

  let storeValue = $state({ user: null });
  userStore.subscribe(value => { storeValue = value; });

  let authValue = $state({ isAuthenticated: false });
  authState.subscribe(value => { authValue = value; });

  let userName = $derived(storeValue.user?.name || storeValue.user?.address?.slice(0, 8) || '');
  let isLoggedIn = $derived(authValue.isAuthenticated && !!storeValue.user);
</script>

<div class="relative overflow-hidden rounded-[8px]">
  <div class="px-[16px] py-[72px] sm:py-[96px] md:px-[20px] md:py-[128px] flex items-center justify-center">
    <div class="flex flex-col gap-[18px] md:gap-[24px] items-center text-center">
      <h1 class="text-[40px] sm:text-[52px] md:text-[64px] font-medium text-black font-display leading-[42px] sm:leading-[54px] md:leading-[64px] w-full max-w-[542px]" style="letter-spacing: -0.02em;">
        {isLoggedIn ? `Welcome, ${userName}` : 'Welcome to GenLayer Portal'}
      </h1>
      <p class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] max-w-[560px]" style="letter-spacing: 0.02em;">
        {isLoggedIn
          ? 'Continue earning points and climbing the leaderboard.'
          : 'Join professional validators and builders in testing the trust infrastructure for the AI age.'}
      </p>
    </div>
  </div>
</div>
