<script>
  let { id, alertType = 'info', text = '', icon = '', onDismiss } = $props();

  const typeStyles = {
    info: {
      bg: '#f3ecfc',
      border: '#8f46e9',
      iconColor: '#8f46e9',
    },
    warning: {
      bg: 'rgba(255, 165, 0, 0.1)',
      border: '#f59e0b',
      iconColor: '#f59e0b',
    },
    error: {
      bg: '#fef2f2',
      border: '#dc2626',
      iconColor: '#dc2626',
    },
    success: {
      bg: '#f0fdf4',
      border: '#16a34a',
      iconColor: '#16a34a',
    },
    blue: {
      bg: '#ebf0fe',
      border: '#387DE8',
      iconColor: '#387DE8',
    },
  };

  let styles = $derived(typeStyles[alertType] || typeStyles.info);
</script>

<div
  class="flex items-center gap-3 px-4 py-3 rounded-lg"
  style="background: {styles.bg}; border: 1px solid {styles.border};"
  role="alert"
>
  <!-- Icon -->
  <div class="flex-shrink-0">
    {#if alertType === 'info'}
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12Z" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 5.5V8M8 10.5h.007" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    {:else if alertType === 'warning'}
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6.86 2.57 1.21 12a1.33 1.33 0 0 0 1.15 2h11.29a1.33 1.33 0 0 0 1.15-2L9.14 2.57a1.33 1.33 0 0 0-2.28 0Z" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 6v2.67M8 11.33h.007" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    {:else if alertType === 'error'}
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12Z" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="m10 6-4 4M6 6l4 4" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    {:else if alertType === 'blue'}
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12Z" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M8 5.5V8M8 10.5h.007" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    {:else if alertType === 'success'}
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12Z" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="m5.5 8 1.5 1.5 3-3" stroke={styles.iconColor} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    {/if}
  </div>

  <!-- Text (supports HTML links since content is admin-managed) -->
  <p class="flex-1 text-sm font-medium alert-text" style="color: #1b1b1b; letter-spacing: 0.28px;">
    {@html text}
  </p>

  <!-- Close button -->
  <button
    onclick={() => onDismiss?.(id)}
    class="flex-shrink-0 p-0.5 rounded hover:bg-black/5 transition-colors cursor-pointer"
    aria-label="Dismiss alert"
  >
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="m11 5-6 6M5 5l6 6" stroke="#1b1b1b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </button>
</div>

<style>
  .alert-text :global(a) {
    text-decoration: underline;
    font-weight: 600;
  }
  .alert-text :global(a:hover) {
    opacity: 0.8;
  }
</style>
