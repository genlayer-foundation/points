<script>
  // @ts-nocheck
  let {
    role = 'builder',
    title = '',
    message = '',
    chips = [],
    alert = '',
    alertTone = 'error',
  } = $props();
</script>

<header class="journey-welcome" data-role={role}>
  <div class="welcome-copy">
    <p class="welcome-eyebrow">GenLayer Portal</p>
    <h2>{title}</h2>
    {#if message}
      <p class="welcome-message">{message}</p>
    {/if}
    {#if alert}
      <p class="welcome-alert" class:welcome-alert-error={alertTone === 'error'} role={alertTone === 'error' ? 'alert' : 'status'}>
        {alert}
      </p>
    {/if}
  </div>

  {#if chips.length}
    <div class="welcome-chips" aria-label="Journey summary">
      {#each chips as chip}
        <span class="welcome-chip">
          <small>{chip.label}</small>
          <strong>{chip.value}</strong>
        </span>
      {/each}
    </div>
  {/if}
</header>

<style>
  .journey-welcome {
    align-items: start;
    display: grid;
    gap: 18px;
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 4px 4px 0;
    width: 100%;
  }

  .welcome-copy {
    min-width: 0;
  }

  .welcome-eyebrow {
    color: var(--role-accent, #ee8521);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0 !important;
    line-height: 17px;
    margin: 0 0 6px;
    text-transform: uppercase;
  }

  h2 {
    color: var(--journey-black, #131214);
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 30px;
    margin: 0;
    text-wrap: balance;
  }

  .welcome-message {
    color: #565656;
    font-family: var(--font-body);
    font-size: 14.5px;
    line-height: 23px;
    margin: 7px 0 0;
    max-width: 720px;
  }

  .welcome-alert {
    align-items: center;
    background: #fff7f7;
    border-left: 3px solid #d92d20;
    color: #b42318;
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 13.5px;
    line-height: 21px;
    margin: 12px 0 0;
    max-width: 720px;
    padding: 4px 0 4px 10px;
  }

  .welcome-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
    min-width: min(100%, 320px);
  }

  .welcome-chip {
    background: color-mix(in srgb, var(--role-accent, #ee8521) 8%, #fff);
    border: 1px solid color-mix(in srgb, var(--role-accent, #ee8521) 20%, #ededed);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 108px;
    padding: 8px 10px;
  }

  .welcome-chip small {
    color: #767676;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0 !important;
    line-height: 14px;
    text-transform: uppercase;
  }

  .welcome-chip strong {
    color: var(--journey-black, #131214);
    font-family: var(--font-body);
    font-size: 13.5px;
    font-weight: 600;
    line-height: 18px;
    overflow-wrap: anywhere;
  }

  @media (max-width: 760px) {
    .journey-welcome {
      grid-template-columns: 1fr;
    }

    .welcome-chips {
      justify-content: flex-start;
      min-width: 0;
    }
  }

  @media (max-width: 640px) {
    .journey-welcome {
      padding: 4px 12px 0;
    }

    h2 {
      font-size: 21px;
      line-height: 27px;
    }

    .welcome-chip {
      flex: 1 1 132px;
    }
  }
</style>
