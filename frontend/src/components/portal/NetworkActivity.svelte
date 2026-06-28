<script>
  import { onMount } from 'svelte';
  import { metricsAPI } from '../../lib/api.js';
  import ActivityHeatmap from './ActivityHeatmap.svelte';
  import DecisionsChart from './DecisionsChart.svelte';
  import PortalStats from './PortalStats.svelte';

  let data = $state(null);
  let loading = $state(true);
  let activeView = $state('graph');

  onMount(async () => {
    try {
      const response = await metricsAPI.getNetworkActivity();
      data = response.data;
    } catch (err) {
      data = null;
    } finally {
      loading = false;
    }
  });

  function formatNumber(value) {
    if (value == null || value === '') return '—';
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    if (n >= 1000000000) return `${(n / 1000000000).toFixed(1)}B`;
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toLocaleString();
  }

  function formatTps(value) {
    if (value == null || value === '') return '—';
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    if (n > 0 && n < 0.01) return '<0.01';
    return n.toLocaleString(undefined, {
      maximumFractionDigits: 2,
      minimumFractionDigits: n < 1 ? 2 : 0,
    });
  }

  let kpis = $derived([
    {
      label: 'Decisions',
      value: data ? formatNumber(data.totals?.daily_decisions_made) : '—',
      unit: 'per day',
    },
    {
      label: 'Transactions',
      value: data ? formatNumber(data.totals?.daily_chain_transactions) : '—',
      unit: 'per day',
    },
    {
      label: 'Transactions',
      value: data ? formatTps(data.totals?.transactions_per_second) : '—',
      unit: 'per second',
    },
  ]);

  const viewCopy = $derived(
    activeView === 'activity'
      ? 'Daily decisions and transactions across Studio and the testnets'
      : 'Decisions/week across Studio and the testnets · last 12 aligned weeks',
  );
</script>

<section class="network-activity" aria-busy={loading}>
  <!-- Left — portal contributors -->
  <PortalStats />

  <!-- Right — network activity (decisions over time + headline KPIs) -->
  <div class="panel chart-panel">
    <div class="panel-head">
      <div>
        <h2>Network activity</h2>
        <p>{viewCopy}</p>
      </div>
      <div class="view-tabs" aria-label="Network activity view">
        <button type="button" class:active={activeView === 'graph'} onclick={() => (activeView = 'graph')}>
          Graph
        </button>
        <button type="button" class:active={activeView === 'activity'} onclick={() => (activeView = 'activity')}>
          Activity
        </button>
      </div>
    </div>

    <div class="kpi-strip">
      {#each kpis as kpi}
        <div class:loading class="kpi">
          {#if loading}
            <span class="kpi-value-skeleton" aria-hidden="true"></span>
          {:else}
            <strong>{kpi.value}</strong>
          {/if}
          <div class="kpi-meta">
            <span>{kpi.label}</span>
            <small>{kpi.unit}</small>
          </div>
        </div>
      {/each}
    </div>

    {#if activeView === 'activity'}
      <ActivityHeatmap activity={data?.activity || []} {loading} />
    {:else}
      <DecisionsChart labels={data?.labels || []} series={data?.series || []} {loading} />
    {/if}
  </div>
</section>

<style>
  .network-activity {
    align-items: stretch;
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(280px, 1fr) minmax(0, 2fr);
  }

  .panel {
    background: #fff;
    border: 1px solid #ececf0;
    border-radius: 8px;
    box-shadow: 0 8px 18px rgba(31, 42, 68, 0.04);
    padding: 18px;
  }

  .chart-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
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

  .chart-panel .panel-head {
    align-items: flex-start;
    display: flex;
    gap: 14px;
    justify-content: space-between;
  }

  .view-tabs {
    background: #f4f5f7;
    border: 1px solid #ececf0;
    border-radius: 8px;
    display: inline-flex;
    flex: 0 0 auto;
    gap: 2px;
    padding: 3px;
  }

  .view-tabs button {
    appearance: none;
    background: transparent;
    border: 0;
    border-radius: 6px;
    color: #6b7280;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    line-height: 16px;
    padding: 6px 10px;
    transition: background 160ms ease, box-shadow 160ms ease, color 160ms ease;
  }

  .view-tabs button.active {
    background: #fff;
    box-shadow: 0 1px 3px rgba(31, 42, 68, 0.1);
    color: #101010;
  }

  .view-tabs button:focus-visible {
    outline: 2px solid rgba(56, 125, 232, 0.55);
    outline-offset: 2px;
  }

  /* KPI strip */
  .kpi-strip {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .kpi {
    align-items: center;
    background: #fbfbfc;
    border: 1px solid #eeeeef;
    border-radius: 8px;
    display: flex;
    gap: 12px;
    overflow: hidden;
    padding: 14px;
    position: relative;
  }

  .kpi strong {
    color: #101010;
    flex-shrink: 0;
    font-family: var(--font-display, inherit);
    font-size: clamp(28px, 3.1vw, 40px);
    font-weight: 600;
    letter-spacing: -0.8px;
    line-height: 1;
  }

  .kpi-meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .kpi-meta span {
    color: #303846;
    font-size: 15px;
    font-weight: 600;
    line-height: 19px;
  }

  .kpi-meta small {
    color: #9aa1ad;
    font-size: 11px;
    line-height: 14px;
    margin-top: 2px;
  }

  .kpi.loading {
    min-height: 78px;
  }

  .kpi-value-skeleton {
    animation: kpi-shimmer 1.4s ease-in-out infinite;
    background: linear-gradient(90deg, #eef0f3 0%, #fbfbfc 48%, #eef0f3 100%);
    background-size: 220% 100%;
    border-radius: 8px;
    display: block;
    flex: 0 0 auto;
    height: clamp(28px, 3.1vw, 40px);
    width: clamp(70px, 8vw, 104px);
  }

  @keyframes kpi-shimmer {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .kpi-value-skeleton {
      animation: none;
    }
  }

  @media (max-width: 1024px) {
    .network-activity {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 620px) {
    .panel {
      padding: 14px;
    }

    .kpi-strip {
      grid-template-columns: 1fr;
    }

    .chart-panel .panel-head {
      align-items: stretch;
      flex-direction: column;
    }

    .view-tabs {
      width: fit-content;
    }
  }
</style>
