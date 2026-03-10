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
  <div class="px-[20px] py-[128px] flex items-center justify-center">
    <div class="flex flex-col gap-[24px] items-center text-center">
      <h1 class="text-[64px] font-medium text-black font-display leading-[64px] w-[542px]" style="letter-spacing: -1.28px;">
        {isLoggedIn ? `Welcome, ${userName}` : 'Welcome to GenLayer Points'}
      </h1>
      <p class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">
        {isLoggedIn
          ? 'Continue earning points and climbing the leaderboard.'
          : 'Join professional validators and builders in testing the trust infrastructure for the AI age.'}
      </p>
    </div>
  </div>
</div>
