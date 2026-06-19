<script>
  import { onMount } from 'svelte';
  import { metricsAPI } from '../../lib/api.js';
  import DecisionsChart from './DecisionsChart.svelte';
  import PortalStats from './PortalStats.svelte';

  let data = $state(null);
  let loading = $state(true);

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

  function formatFeesTier(value) {
    if (value == null || value === '') return '—';
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    return `Top ${Math.round(n)}`;
  }

  let kpis = $derived([
    { label: 'Decisions made', value: data ? formatNumber(data.totals?.decisions_made) : '—', caption: 'All-time' },
    { label: 'Chain TXs', value: data ? formatNumber(data.totals?.chain_transactions) : '—', caption: 'All-time' },
    {
      label: 'Chains by fees',
      value: data ? formatFeesTier(data.totals?.defillama_fees_rank) : '—',
      caption: 'if GenLayer were mainnet',
      accent: true,
    },
  ]);
</script>

<section class="network-activity">
  <!-- Left — portal contributors -->
  <PortalStats />

  <!-- Right — network activity (decisions over time + headline KPIs) -->
  <div class="panel chart-panel">
    <div class="panel-head">
      <div>
        <h2>Network activity</h2>
        <p>Decisions made across Studio and the testnets · last 12 weeks</p>
      </div>
    </div>

    <div class="kpi-strip">
      {#each kpis as kpi}
        <div class:accent={kpi.accent} class="kpi">
          <strong>{kpi.value}</strong>
          <div class="kpi-meta">
            <span>{kpi.label}</span>
            <small>{kpi.caption}</small>
          </div>
        </div>
      {/each}
    </div>

    <DecisionsChart labels={data?.labels || []} series={data?.series || []} {loading} />
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

  .kpi.accent {
    background:
      linear-gradient(135deg, rgba(34, 28, 76, 0.88), rgba(115, 68, 177, 0.74) 45%, rgba(232, 119, 47, 0.76)),
      url('/assets/illustrations/welcome-gradient.png') center / cover;
    border-color: rgba(127, 82, 225, 0.32);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18), 0 10px 20px rgba(69, 47, 132, 0.1);
  }

  .kpi.accent::after {
    background: radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.2), transparent 32%);
    content: '';
    inset: 0;
    pointer-events: none;
    position: absolute;
  }

  .kpi.accent > :global(*) {
    position: relative;
    z-index: 1;
  }

  .kpi.accent strong {
    color: #fff;
    font-size: clamp(28px, 2.4vw, 34px);
    letter-spacing: -0.5px;
  }

  .kpi.accent .kpi-meta span {
    color: rgba(255, 255, 255, 0.9);
  }

  .kpi.accent .kpi-meta small {
    color: rgba(255, 255, 255, 0.6);
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
  }
</style>
