<script>
  import { toastStore } from '../lib/toastStore';
  import Toast from './Toast.svelte';
</script>

<!-- Toast container - fixed position at top-right -->
<div
  class="fixed top-4 right-4 z-50 pointer-events-none"
  aria-live="polite"
  aria-atomic="true"
>
  <div class="pointer-events-auto">
    {#each $toastStore as toast (toast.id)}
      <Toast
        id={toast.id}
        type={toast.type}
        message={toast.message}
        duration={toast.duration}
      />
    {/each}
  </div>
</div>