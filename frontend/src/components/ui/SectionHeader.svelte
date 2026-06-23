<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../../lib/auth.js';

  let {
    title = '',
    subtitle = '',
    linkText = 'View all',
    linkPath = '',
    showLink = true,
    showArrow = true,
    requiresAuth = false,
  } = $props();

  function handleLinkClick() {
    if (requiresAuth && !$authState.isAuthenticated) {
      sessionStorage.setItem('redirectAfterLogin', linkPath);
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
      return;
    }
    push(linkPath);
  }
</script>

<div class="flex items-center justify-between mb-4">
  <div class="flex flex-col gap-1">
    <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">{title}</h2>
    {#if subtitle}
      <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">{subtitle}</p>
    {/if}
  </div>
  {#if showLink && linkPath}
    <button
      onclick={handleLinkClick}
      class="flex items-center gap-1 text-[14px] text-[#6b6b6b] hover:text-black transition-colors flex-shrink-0"
      style="letter-spacing: 0.28px;"
    >
      {linkText}
      {#if showArrow}
        <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
      {/if}
    </button>
  {/if}
</div>
