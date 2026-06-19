<script>
  import { onMount } from 'svelte';
  import { metricsAPI } from '../../lib/api.js';
  import CategoryIcon from './CategoryIcon.svelte';

  // Public overview metrics (no auth) — the leaderboard stats endpoint is auth-only.
  let metrics = $state(null);
  let loading = $state(true);

  onMount(async () => {
    try {
      const response = await metricsAPI.getOverview();
      metrics = response.data?.metrics || null;
    } catch (err) {
      // leave metrics null — rows render an em dash
    } finally {
      loading = false;
    }
  });

  function formatNumber(n) {
    if (n == null) return '—';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
  }

  const cards = $derived([
    { label: 'Builders', category: 'builder', value: metrics?.builders?.value },
    { label: 'Validators', category: 'validator', value: metrics?.validators?.value },
    { label: 'Community members', category: 'community', value: metrics?.community_members?.value },
    { label: 'Contributions', category: 'genlayer', value: metrics?.contributions?.value },
  ]);
</script>

<div class="panel portal-panel" aria-busy={loading}>
  <div class="panel-head">
    <h2>Portal contributors</h2>
    <p>Builders, validators and community on the portal</p>
  </div>

  <div class="metric-col">
    {#each cards as card}
      <div class="metric-row" data-category={card.category}>
        {#if loading}
          <div class="metric-icon-skeleton skeleton-shimmer" aria-hidden="true"></div>
        {:else}
          <CategoryIcon category={card.category} mode="hexagon" size={44} />
        {/if}
        <div class="metric-copy">
          {#if loading}
            <span class="metric-value-skeleton skeleton-shimmer" aria-hidden="true"></span>
          {:else}
            <strong>{formatNumber(card.value)}</strong>
          {/if}
          <span>{card.label}</span>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .panel {
    background: #fff;
    border: 1px solid #ececf0;
    border-radius: 8px;
    box-shadow: 0 8px 18px rgba(31, 42, 68, 0.04);
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-width: 0;
    padding: 18px;
  }

  h2,
  p {
    margin: 0;
  }

  .panel-head h2 {
    color: #101010;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.2px;
    line-height: 22px;
  }

  .panel-head p {
    color: #6b6b6b;
    font-size: 13px;
    line-height: 17px;
    margin-top: 3px;
  }

  .metric-col {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 12px;
  }

  .metric-row {
    align-items: center;
    background: #fbfbfc;
    border: 1px solid #eeeeef;
    border-radius: 10px;
    display: flex;
    flex: 1;
    gap: 14px;
    min-height: 72px;
    overflow: hidden;
    padding: 12px 16px;
    position: relative;
  }

  .metric-row::before {
    content: '';
    inset: 0;
    opacity: 0.7;
    pointer-events: none;
    position: absolute;
  }

  .metric-row > :global(*) {
    position: relative;
    z-index: 1;
  }

  .metric-row[data-category='builder'] {
    border-color: rgba(238, 133, 33, 0.18);
  }

  .metric-row[data-category='builder']::before {
    background: linear-gradient(135deg, rgba(238, 133, 33, 0.1), rgba(255, 209, 163, 0.04) 58%, transparent);
  }

  .metric-row[data-category='validator'] {
    border-color: rgba(56, 125, 232, 0.18);
  }

  .metric-row[data-category='validator']::before {
    background: linear-gradient(135deg, rgba(56, 125, 232, 0.1), rgba(184, 199, 255, 0.05) 58%, transparent);
  }

  .metric-row[data-category='community'] {
    border-color: rgba(127, 82, 225, 0.18);
  }

  .metric-row[data-category='community']::before {
    background: linear-gradient(135deg, rgba(127, 82, 225, 0.1), rgba(214, 195, 255, 0.05) 58%, transparent);
  }

  .metric-row[data-category='genlayer'] {
    background:
      linear-gradient(110deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.72)),
      url('/assets/illustrations/welcome-gradient.png') center / cover;
    border-color: rgba(127, 82, 225, 0.2);
  }

  .metric-row[data-category='genlayer']::before {
    background: linear-gradient(135deg, rgba(127, 82, 225, 0.08), rgba(238, 133, 33, 0.06) 46%, rgba(56, 125, 232, 0.06));
  }

  .metric-copy {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .metric-copy strong {
    color: #101010;
    font-family: var(--font-display, inherit);
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -0.8px;
    line-height: 1;
  }

  .metric-copy span {
    color: #6b6b6b;
    font-size: 13px;
    letter-spacing: 0.24px;
    line-height: 16px;
  }

  .skeleton-shimmer {
    animation: stat-shimmer 1.4s ease-in-out infinite;
    background: linear-gradient(90deg, #f0f1f4 0%, #fafafb 48%, #f0f1f4 100%);
    background-size: 220% 100%;
  }

  .metric-icon-skeleton {
    clip-path: polygon(50% 0, 92% 25%, 92% 75%, 50% 100%, 8% 75%, 8% 25%);
    flex: 0 0 44px;
    height: 44px;
    width: 44px;
  }

  .metric-value-skeleton {
    border-radius: 6px;
    display: block;
    height: 28px;
    width: 92px;
  }

  @keyframes stat-shimmer {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton-shimmer {
      animation: none;
    }
  }

  @media (max-width: 620px) {
    .panel {
      padding: 14px;
    }

    .metric-row {
      min-height: 64px;
    }
  }
</style>
