<script>
  // @ts-nocheck
  let {
    title = '',
    body = '',
    label = '',
    icon = 'box',
  } = $props();
</script>

<article class="unlock-card">
  <span class="lock-badge">Locked</span>
  <div class="unlock-icon" aria-hidden="true">
    <img src="/assets/icons/hexagon-light.svg" alt="" />
    {#if icon === 'leaderboard'}
      <svg viewBox="0 0 24 24"><path d="M4 20V10h4v10H4Zm6 0V4h4v16h-4Zm6 0v-7h4v7h-4Z" /></svg>
    {:else if icon === 'resources'}
      <svg viewBox="0 0 24 24"><path d="M5 4h10a4 4 0 0 1 4 4v12H8a3 3 0 0 1-3-3V4Zm3 13h8M8 4v13" /></svg>
    {:else if icon === 'rewards'}
      <svg viewBox="0 0 24 24"><path d="M12 3 14.7 8.5l6 .9-4.3 4.2 1 5.9-5.4-2.9-5.4 2.9 1-5.9-4.3-4.2 6-.9L12 3Z" /></svg>
    {:else}
      <svg viewBox="0 0 24 24"><path d="M4 6h7l2 2h7v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6Z" /></svg>
    {/if}
  </div>
  <h3>{title}</h3>
  <p>{body}</p>
  <span class="unlock-label">{label}</span>
</article>

<style>
  .unlock-card {
    background: #fff;
    border: 1px solid var(--journey-border, #ededed);
    border-radius: 18px;
    min-height: 242px;
    opacity: 0.72;
    padding: 28px;
    position: relative;
  }

  .lock-badge {
    border: 1px solid #e6e6e6;
    border-radius: 6px;
    color: #ababab;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1px;
    line-height: 16px;
    padding: 2px 8px;
    position: absolute;
    right: 16px;
    text-transform: uppercase;
    top: 16px;
  }

  .unlock-icon {
    display: inline-flex;
    height: 48px;
    position: relative;
    width: 48px;
  }

  .unlock-icon img,
  .unlock-icon svg {
    height: 48px;
    width: 48px;
  }

  .unlock-icon svg {
    color: #ababab;
    fill: none;
    left: 50%;
    position: absolute;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.7;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 22px;
  }

  h3 {
    color: var(--journey-black, #131214);
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 500;
    letter-spacing: -0.22px;
    line-height: 28px;
    margin: 16px 0 0;
  }

  p {
    color: #3f3f3f;
    font-family: var(--font-body);
    font-size: 16px;
    line-height: 25.6px;
    margin: 8px 0 0;
  }

  .unlock-label {
    color: var(--role-accent, #ee8521);
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
    margin-top: 12px;
  }

  @media (max-width: 640px) {
    .unlock-card {
      min-height: 0;
      padding: 22px;
    }
  }
</style>
