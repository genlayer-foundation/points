<script>
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';

  onMount(() => {
    replace('/referrals');
  });
</script>

<div class="flex min-h-[240px] items-center justify-center text-[14px] text-[#66708a]">
  Redirecting to referrals...
</div>
