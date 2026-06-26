<script>
  // @ts-nocheck
  let { message = '', tone = 'default' } = $props();
</script>

<div class="journey-notice" class:notice-error={tone === 'error'} role={tone === 'error' ? 'alert' : 'status'}>
  <span class="notice-icon" aria-hidden="true">
    {#if tone === 'error'}
      <svg viewBox="0 0 20 20" fill="currentColor">
        <path
          fill-rule="evenodd"
          d="M8.485 2.495a1.75 1.75 0 0 1 3.03 0l6.28 10.875A1.75 1.75 0 0 1 16.28 16H3.72a1.75 1.75 0 0 1-1.515-2.63L8.485 2.495ZM10 6a.75.75 0 0 0-.75.75v3.5a.75.75 0 0 0 1.5 0v-3.5A.75.75 0 0 0 10 6Zm0 7.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
          clip-rule="evenodd"
        />
      </svg>
    {:else}
      <svg viewBox="0 0 20 20" fill="currentColor">
        <path
          fill-rule="evenodd"
          d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm.75 4.75a.75.75 0 0 0-1.5 0v3.5c0 .414.336.75.75.75h2.5a.75.75 0 0 0 0-1.5h-1.75V6.75Z"
          clip-rule="evenodd"
        />
      </svg>
    {/if}
  </span>
  <p>{message}</p>
</div>

<style>
  .journey-notice {
    align-items: center;
    background: #f7f7f7;
    border: 1px solid var(--journey-border, #ededed);
    border-radius: 10px;
    color: #3f3f3f;
    display: flex;
    gap: 11px;
    min-height: 48px;
    padding: 11px 14px;
    width: 100%;
  }

  .journey-notice p {
    flex: 1 1 auto;
    font-family: var(--font-body);
    font-size: 13.5px;
    line-height: 21px;
    margin: 0;
  }

  .notice-icon {
    color: var(--role-accent, #ee8521);
    display: inline-flex;
    flex: 0 0 auto;
    height: 16px;
    width: 16px;
  }

  .notice-icon svg {
    height: 16px;
    width: 16px;
  }

  .notice-error {
    background: #fff7f7;
    border-color: #f1c7c7;
  }

  .notice-error .notice-icon,
  .notice-error p {
    color: #b42318;
  }

  @media (max-width: 640px) {
    .journey-notice {
      align-items: flex-start;
      padding: 12px;
    }
  }
</style>
