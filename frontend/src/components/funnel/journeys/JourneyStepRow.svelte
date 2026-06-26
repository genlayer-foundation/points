<script>
  // @ts-nocheck
  let {
    number = 1,
    title = '',
    detail = '',
    contributionLabel = '',
    points = null,
    pointsLabel = '',
    status = 'pending',
    actionLabel = '',
    actionHref = '',
    actionExternal = false,
    actionTone = 'secondary',
    disabled = false,
    busy = false,
    loading = false,
    onAction = () => {},
  } = $props();

  let statusLabel = $derived(
    status === 'done'
      ? 'Done'
      : status === 'active'
        ? 'Up next'
        : status === 'error'
          ? 'Error'
          : status === 'locked'
            ? 'Locked'
            : 'Pending'
  );

  function handleAction(event) {
    if (disabled || busy) {
      event.preventDefault();
      return;
    }
    onAction?.(event);
  }
</script>

<div
  class="step-row"
  class:step-active={status === 'active'}
  class:step-done={status === 'done'}
  class:step-locked={status === 'locked'}
  class:step-error={status === 'error'}
  class:step-loading={loading}
>
  {#if loading}
    <div class="step-index skeleton"></div>
    <div class="step-copy">
      <span class="skeleton skeleton-title"></span>
      <span class="skeleton skeleton-detail"></span>
    </div>
    <span class="skeleton skeleton-pill"></span>
  {:else}
    <div class="step-index" aria-hidden="true">
      {#if status === 'done'}
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.5 7.59a1 1 0 0 1-1.42.006L3.29 9.79a1 1 0 1 1 1.42-1.408l3.79 3.83 6.79-6.872a1 1 0 0 1 1.414-.06Z"
            clip-rule="evenodd"
          />
        </svg>
      {:else}
        {number}
      {/if}
    </div>

    <div class="step-copy">
      <p>
        <span>{title}</span>
        {#if contributionLabel}
          <em>{contributionLabel}</em>
        {/if}
        {#if detail}
          <small>{detail}</small>
        {/if}
      </p>
    </div>

    <div class="step-meta">
      {#if points !== null && points !== undefined}
        <span class="points-pill">+{points}{pointsLabel ? ` ${pointsLabel}` : ''}</span>
      {/if}

      {#if actionLabel}
        {#if actionHref}
          <a
            class="step-action"
            class:action-accent={actionTone === 'accent'}
            href={disabled ? undefined : actionHref}
            target={actionExternal ? '_blank' : undefined}
            rel={actionExternal ? 'noopener noreferrer' : undefined}
            onclick={handleAction}
            aria-disabled={disabled}
            tabindex={disabled ? -1 : 0}
          >
            <span>{busy ? 'Working...' : actionLabel}</span>
            <img src={actionTone === 'accent' ? '/assets/icons/arrow-right-line-white.svg' : '/assets/icons/arrow-right-line.svg'} alt="" />
          </a>
        {:else}
          <button
            type="button"
            class="step-action"
            class:action-accent={actionTone === 'accent'}
            onclick={handleAction}
            disabled={disabled || busy}
            aria-busy={busy}
          >
            <span>{busy ? 'Working...' : actionLabel}</span>
            <img src={actionTone === 'accent' ? '/assets/icons/arrow-right-line-white.svg' : '/assets/icons/arrow-right-line.svg'} alt="" />
          </button>
        {/if}
      {:else}
        <span class="status-label" class:status-error={status === 'error'}>{statusLabel}</span>
      {/if}
    </div>
  {/if}
</div>

<style>
  .step-row {
    align-items: center;
    background: #fff;
    border-top: 1px solid #f0f0f0;
    display: flex;
    gap: 14px;
    min-height: 64px;
    padding: 13px 18px;
    position: relative;
    width: 100%;
  }

  .step-row:first-child {
    border-top: 0;
  }

  .step-active {
    background: linear-gradient(90deg, var(--journey-active-bg, #fffaf3) 0%, #fff 70%);
  }

  .step-active::before {
    background: var(--role-accent, #ee8521);
    bottom: 0;
    content: '';
    left: 0;
    position: absolute;
    top: 0;
    width: 3px;
  }

  .step-locked {
    opacity: 0.74;
  }

  .step-error {
    background: #fffafa;
  }

  .step-index {
    align-items: center;
    background: #fff;
    border: 1px solid #e6e6e6;
    border-radius: 13px;
    color: #ababab;
    display: inline-flex;
    flex: 0 0 auto;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    height: 26px;
    justify-content: center;
    line-height: 17px;
    width: 26px;
  }

  .step-index svg {
    height: 14px;
    width: 14px;
  }

  .step-done .step-index {
    background: var(--journey-complete-gradient, var(--journey-black, #131214));
    border-color: var(--journey-complete-border, transparent);
    box-shadow: 0 7px 15px var(--journey-complete-shadow, rgba(19, 18, 20, 0.16));
    color: var(--journey-complete-color, #fff);
  }

  .step-active .step-index {
    border-color: var(--role-accent, #ee8521);
    color: var(--role-accent, #ee8521);
  }

  .step-error .step-index {
    border-color: #f4b8b8;
    color: #b42318;
  }

  .step-copy {
    flex: 1 1 auto;
    min-width: 0;
  }

  .step-copy p {
    align-items: baseline;
    color: var(--journey-black, #131214);
    display: flex;
    flex-wrap: wrap;
    font-family: var(--font-body);
    font-size: 14.5px;
    font-weight: 500;
    gap: 5px;
    line-height: 22px;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .step-copy em {
    background: var(--journey-active-bg, #fff4e5);
    border-radius: 999px;
    color: var(--role-accent, #ee8521);
    font-family: var(--font-mono);
    font-size: 9px;
    font-style: normal;
    letter-spacing: 1px;
    line-height: 15px;
    padding: 2px 6px;
    text-transform: uppercase;
  }

  .step-copy small {
    color: #ababab;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 400;
    line-height: 17px;
  }

  .step-meta {
    align-items: center;
    display: flex;
    flex: 0 0 auto;
    gap: 13px;
    justify-content: flex-end;
  }

  .points-pill {
    align-items: center;
    background: var(--journey-points-bg, #fdf3e6);
    border-radius: 999px;
    color: var(--role-accent, #ee8521);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    height: 27px;
    justify-content: center;
    line-height: 18px;
    min-width: 64px;
    padding: 0 10px;
  }

  .status-label {
    color: #ababab;
    font-family: var(--font-mono);
    font-size: 11px;
    line-height: 17px;
    min-width: 54px;
    text-align: right;
  }

  .status-error {
    color: #b42318;
  }

  .step-action {
    align-items: center;
    background: #fff;
    border: 1px solid #e6e6e6;
    border-radius: 999px;
    color: var(--journey-black, #131214);
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    gap: 8px;
    height: 38px;
    justify-content: center;
    line-height: 18px;
    padding: 0 16px;
    transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, opacity 160ms ease;
    white-space: nowrap;
  }

  .step-action img {
    height: 14px;
    width: 14px;
  }

  .step-action:hover:not(:disabled) {
    background: #f7f7f7;
  }

  .step-action[aria-disabled='true'],
  .step-action:disabled {
    cursor: default;
    opacity: 0.62;
  }

  .action-accent {
    background: var(--role-accent, #ee8521);
    border-color: transparent;
    color: #fff;
  }

  .action-accent:hover:not(:disabled) {
    background: var(--role-accent-hover, #d97518);
  }

  .skeleton {
    animation: pulse 1.2s ease-in-out infinite;
    background: #f1f1f1;
    border-radius: 999px;
    display: block;
  }

  .skeleton-title {
    height: 14px;
    max-width: 280px;
    width: 55%;
  }

  .skeleton-detail {
    height: 10px;
    margin-top: 8px;
    max-width: 170px;
    width: 35%;
  }

  .skeleton-pill {
    height: 27px;
    width: 64px;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 0.55;
    }
    50% {
      opacity: 1;
    }
  }

  @media (max-width: 900px) {
    .step-row {
      align-items: flex-start;
      gap: 12px;
    }

    .step-meta {
      align-items: flex-end;
      flex-direction: column;
      gap: 8px;
    }
  }

  @media (max-width: 640px) {
    .step-row {
      flex-wrap: wrap;
      padding: 14px;
    }

    .step-copy {
      flex-basis: calc(100% - 40px);
    }

    .step-meta {
      align-items: center;
      flex-basis: 100%;
      flex-direction: row;
      justify-content: space-between;
      padding-left: 40px;
    }

    .step-action {
      flex: 0 1 auto;
      min-width: 0;
    }
  }
</style>
