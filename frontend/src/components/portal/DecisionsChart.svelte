<script>
  import { onDestroy } from 'svelte';
  import {
    Chart,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Filler,
    Tooltip,
    Legend,
  } from 'chart.js';

  Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip, Legend);

  let { labels = [], series = [], loading = false } = $props();

  const COLORS = {
    studio: '#7F52E1',
    asimov: '#EE8521',
    bradbury: '#387DE8',
  };

  let canvas;
  let chart;

  function rgba(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
  }

  function compact(v) {
    const n = Number(v);
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
    return n;
  }

  function render() {
    if (chart) {
      chart.destroy();
      chart = null;
    }
    if (!canvas || !series.length) return;

    // chart.js mutates the arrays it receives; hand it plain copies, not Svelte's reactive proxies.
    const plainLabels = labels.map((l) => l);
    const datasets = series.map((s) => {
      const color = COLORS[s.key] || '#8b93a1';
      const values = s.values.map((v) => (v == null ? null : Number(v)));
      return {
        label: s.label,
        data: values,
        borderColor: color,
        borderWidth: 2.5,
        tension: 0.4,
        cubicInterpolationMode: 'monotone',
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: color,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
        fill: true,
        spanGaps: true,
        backgroundColor: (c) => {
          const { ctx, chartArea } = c.chart;
          if (!chartArea) return 'transparent';
          const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
          g.addColorStop(0, rgba(color, 0.2));
          g.addColorStop(1, rgba(color, 0));
          return g;
        },
      };
    });

    chart = new Chart(canvas, {
      type: 'line',
      data: { labels: plainLabels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        layout: { padding: { top: 6, right: 4, bottom: 0, left: 0 } },
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
            labels: {
              usePointStyle: true,
              pointStyle: 'circle',
              boxWidth: 8,
              boxHeight: 8,
              padding: 16,
              color: '#6b6b6b',
              font: { size: 12 },
            },
          },
          tooltip: {
            backgroundColor: '#101010',
            padding: 10,
            cornerRadius: 8,
            usePointStyle: true,
            titleColor: '#ffffff',
            bodyColor: '#e5e5e5',
            callbacks: {
              title: (items) => `${items[0]?.label || ''} · decisions/week`,
              label: (i) => ` ${i.dataset.label}: ${Number(i.parsed.y).toLocaleString()}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: { color: '#9aa1ad', font: { size: 11 }, maxRotation: 0, autoSkipPadding: 12 },
          },
          y: {
            beginAtZero: true,
            grace: '8%',
            grid: { color: '#f0f0f2' },
            border: { display: false },
            ticks: { color: '#9aa1ad', font: { size: 11 }, maxTicksLimit: 5, callback: (v) => compact(v) },
          },
        },
      },
    });
  }

  $effect(() => {
    // re-run whenever the data changes
    void labels;
    void series;
    render();
  });

  onDestroy(() => {
    if (chart) chart.destroy();
  });
</script>

<div class="chart-wrap">
  <!-- canvas is always mounted so it's bound before data arrives (Svelte bind:this vs $effect timing) -->
  <canvas bind:this={canvas} style:opacity={!loading && series.length ? 1 : 0}></canvas>
  {#if loading}
    <div class="chart-overlay"><div class="chart-skeleton"></div></div>
  {:else if !series.length}
    <div class="chart-overlay chart-empty">Network activity will appear here shortly.</div>
  {/if}
</div>

<style>
  .chart-wrap {
    background: linear-gradient(180deg, rgba(127, 82, 225, 0.035), rgba(255, 255, 255, 0) 34%);
    border-radius: 8px;
    height: 280px;
    position: relative;
    width: 100%;
  }

  .chart-overlay {
    inset: 0;
    position: absolute;
  }

  .chart-skeleton {
    animation: shimmer 1.4s ease-in-out infinite;
    background: linear-gradient(90deg, #f2f3f5, #fbfbfc, #f2f3f5);
    background-size: 200% 100%;
    border-radius: 8px;
    height: 100%;
    width: 100%;
  }

  .chart-empty {
    align-items: center;
    color: #9aa1ad;
    display: flex;
    font-size: 13px;
    justify-content: center;
  }

  @keyframes shimmer {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }

  @media (max-width: 620px) {
    .chart-wrap {
      height: 240px;
    }
  }
</style>
