<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { Chart, registerables } from 'chart.js';
  import api from '../lib/api.js';

  Chart.register(...registerables);

  const EXPORT_WIDTH = 1920;
  const EXPORT_HEIGHT = 1080;
  const EXPORT_FORMAT = 'image/png';

  const exportBackgroundPlugin = {
    id: 'exportBackground',
    beforeDraw(chart, args, options) {
      const { ctx, width, height } = chart;
      ctx.save();
      ctx.fillStyle = options?.color || '#ffffff';
      ctx.fillRect(0, 0, width, height);
      ctx.restore();
    }
  };

  const CATEGORY_LABELS = {
    builder: 'Builder',
    creator: 'Community',
    steward: 'Steward',
    validator: 'Validator'
  };

  const participantPalette = {
    builders: {
      border: 'rgb(234, 88, 12)',
      fillTop: 'rgba(234, 88, 12, 0.24)',
      fillBottom: 'rgba(234, 88, 12, 0.03)',
      surface: 'from-orange-50 via-white to-orange-50/40',
      text: 'text-orange-600',
      track: 'bg-orange-100',
      bar: 'bg-orange-500'
    },
    validators: {
      border: 'rgb(37, 99, 235)',
      fillTop: 'rgba(37, 99, 235, 0.14)',
      fillBottom: 'rgba(37, 99, 235, 0.02)',
      surface: 'from-blue-50 via-white to-blue-50/40',
      text: 'text-blue-700',
      track: 'bg-blue-100',
      bar: 'bg-blue-600'
    }
  };

  const ecosystemPalette = {
    studio: {
      label: 'Studio',
      source: 'via Studio Pulse',
      surface: 'from-violet-50 via-white to-violet-50/40',
      text: 'text-violet-700',
      chip: 'bg-violet-100 text-violet-700',
      dot: 'bg-violet-500'
    },
    asimov: {
      label: 'Asimov',
      source: 'via GenScan',
      surface: 'from-sky-50 via-white to-sky-50/40',
      text: 'text-sky-700',
      chip: 'bg-sky-100 text-sky-700',
      dot: 'bg-sky-500'
    },
    bradbury: {
      label: 'Bradbury',
      source: 'via GenScan',
      surface: 'from-emerald-50 via-white to-emerald-50/40',
      text: 'text-emerald-700',
      chip: 'bg-emerald-100 text-emerald-700',
      dot: 'bg-emerald-500'
    },
    repository: {
      label: 'Repositories',
      source: 'via star-history.com',
      dot: 'bg-amber-500'
    },
    discord: {
      label: 'Discord',
      source: 'via Discord',
      surface: 'from-indigo-50 via-white to-indigo-50/40',
      text: 'text-indigo-700',
      dot: 'bg-indigo-500'
    },
    x: {
      label: 'X',
      source: 'via X',
      surface: 'from-slate-50 via-white to-slate-50/40',
      text: 'text-slate-900',
      dot: 'bg-slate-900'
    }
  };

  // Static social channel KPIs — refreshed manually until a live source is wired.
  const DISCORD_KPIS = [
    { label: 'Members', value: '86,319' },
    { label: 'MAU',     value: '44%'    },
    { label: 'DAU',     value: '30%'    }
  ];

  const X_KPIS = [
    { label: 'Followers',   value: '75.1K' },
    { label: 'Impressions', value: '432.4K', range: 'April' }
  ];

  const DISCORD_URL = 'https://discord.gg/A6jpkqrb';
  const DISCORD_HANDLE = 'discord.gg/A6jpkqrb';
  const X_URL = 'https://x.com/GenLayer';
  const X_HANDLE = '@GenLayer';

  const ONCHAIN_KPI_DEFS = [
    { label: 'Decisions',           range: 'Last 7 days', primaryKey: 'decisions7d',         secondaryKey: 'decisionsAllTime',         compact: true  },
    { label: 'Chain transactions',  range: 'Last 7 days', primaryKey: 'chainTx7d',           secondaryKey: 'chainTxAllTime',           compact: true  },
    { label: 'Deployed contracts',  range: 'Last 7 days', primaryKey: 'deployedContracts7d', secondaryKey: 'deployedContractsAllTime', compact: false },
    { label: 'Active contracts',                          primaryKey: 'activeContracts',                                               compact: false },
    { label: 'Monthly active users',                      primaryKey: 'mau',                                                           compact: false },
    { label: 'Daily active users',                        primaryKey: 'dau',                                                           compact: false }
  ];

  // GenScan exposes 7d for finalizations only — chain tx and contract counts
  // are all-time. The remaining cards (validators, stake, TPS) are testnet-
  // specific signals that don't have Studio equivalents.
  const TESTNET_KPI_DEFS = [
    { label: 'Decisions',          range: 'Last 7 days',  primaryKey: 'decisions7d',     secondaryKey: 'decisionsAllTime', compact: true  },
    { label: 'Chain transactions',                        primaryKey: 'chainTxAllTime',                                    compact: true  },
    { label: 'Contracts',                                 primaryKey: 'contractsAllTime',                                  compact: false },
    { label: 'Validators',                                primaryKey: 'validators',                                        compact: false },
    { label: 'GEN staked',                                primaryKey: 'genStaked',                                         compact: true  },
    { label: 'Avg TPS',            range: 'Last 24 hours', primaryKey: 'avgTps',                                            compact: false }
  ];

  const STUDIO_PULSE_URL = 'https://studio-metrics-dashboard.vercel.app';
  const BOILERPLATE_REPO = 'genlayerlabs/genlayer-project-boilerplate';

  // Testnet explorers don't return CORS headers, so the browser can't fetch
  // them directly. Django proxies and caches the aggregated KPIs at
  // /api/v1/metrics/testnet-kpis/?network=<asimov|bradbury>.
  const TESTNET_NETWORKS = ['asimov', 'bradbury'];

  const reviewPalette = {
    ingress: {
      bg: 'rgba(79, 70, 229, 0.24)',
      border: 'rgb(79, 70, 229)',
      text: 'text-indigo-600',
      surface: 'from-indigo-50 via-white to-indigo-50/40'
    },
    accepted: {
      bg: 'rgba(16, 185, 129, 0.78)',
      border: 'rgb(5, 150, 105)',
      text: 'text-emerald-600',
      surface: 'from-emerald-50 via-white to-emerald-50/40'
    },
    rejected: {
      bg: 'rgba(239, 68, 68, 0.74)',
      border: 'rgb(220, 38, 38)',
      text: 'text-rose-600',
      surface: 'from-rose-50 via-white to-rose-50/40'
    },
    moreInfo: {
      bg: 'rgba(245, 158, 11, 0.74)',
      border: 'rgb(217, 119, 6)',
      text: 'text-amber-600',
      surface: 'from-amber-50 via-white to-amber-50/40'
    },
    pending: {
      border: 'rgb(59, 130, 246)',
      text: 'text-blue-500',
      surface: 'from-blue-50 via-white to-blue-50/40'
    },
    points: {
      text: 'text-fuchsia-600',
      surface: 'from-fuchsia-50 via-white to-fuchsia-50/40'
    }
  };

  const emptyParticipantsSnapshot = {
    date: '',
    builders: 0,
    total: 0,
    validators: 0
  };

  let participantsChart;
  let submissionsChart;
  let submissionsTrendChart;

  let loading = $state(true);
  let submissionsLoading = $state(false);
  let pageError = $state(null);
  let submissionError = $state(null);

  let participantsData = $state([]);
  let submissionsData = $state({
    data: [],
    end_date: '',
    group_by: 'week',
    start_date: '',
    totals: {}
  });
  let contributionTypes = $state([]);

  let submissionGroupBy = $state('week');
  let submissionStartDate = $state('');
  let submissionEndDate = $state('');
  let selectedCategory = $state('');
  let selectedContributionType = $state('');
  let appliedSubmissionFilters = $state({
    category: '',
    contributionType: '',
    endDate: '',
    groupBy: 'week',
    startDate: ''
  });
  let chartExporting = $state('');
  let chartExportError = $state(null);

  let studioMetrics = $state(null);
  let studioLoading = $state(true);
  let studioError = $state(null);

  let asimovMetrics = $state(null);
  let asimovLoading = $state(true);
  let asimovError = $state(null);

  let bradburyMetrics = $state(null);
  let bradburyLoading = $state(true);
  let bradburyError = $state(null);

  let repoMetrics = $state(null);
  let repoLoading = $state(true);
  let repoError = $state(null);

  let activeTab = $state('portal');

  const TABS = [
    { id: 'portal',    label: 'Portal',    dot: 'bg-orange-500' },
    { id: 'networks',  label: 'Networks',  dot: 'bg-blue-500'   },
    { id: 'community', label: 'Community', dot: 'bg-purple-500' }
  ];

  let availableCategories = $derived.by(() =>
    Array.from(
      new Set(
        contributionTypes
          .map((type) => type.category)
          .filter(Boolean)
      )
    ).sort((left, right) =>
      getCategoryLabel(left).localeCompare(getCategoryLabel(right))
    )
  );

  let filteredContributionTypes = $derived.by(() => {
    const baseTypes = contributionTypes.filter((type) => type.is_submittable);
    if (!selectedCategory) {
      return baseTypes;
    }

    return baseTypes.filter((type) => type.category === selectedCategory);
  });

  let latestParticipantsSnapshot = $derived(
    participantsData.length > 0
      ? participantsData[participantsData.length - 1]
      : emptyParticipantsSnapshot
  );

  let submissionsSummary = $derived.by(() => {
    const totals = submissionsData.totals || {};
    const ingress = Number(totals.ingress || 0);
    const accepted = Number(totals.accepted || 0);
    const rejected = Number(totals.rejected || 0);
    const moreInfoRequested = Number(totals.more_info_requested || 0);
    const pointsAwarded = Number(totals.points_awarded || 0);
    const reviewed = accepted + rejected + moreInfoRequested;
    // Pending review comes from the backend: submissions created in the
    // selected range that are still in pending state. We can't derive it from
    // ingress - reviewed because ingress is bucketed by created_at and reviews
    // by reviewed_at, so they measure disjoint cohorts under any filter.
    const pendingReview = Number(totals.pending_review || 0);

    return {
      accepted,
      acceptanceRate: reviewed ? (accepted / reviewed) * 100 : 0,
      avgPointsPerAccepted: accepted ? pointsAwarded / accepted : 0,
      ingress,
      moreInfoRequested,
      pendingReview,
      pointsAwarded,
      rejected,
      reviewed
    };
  });

  let selectedContributionTypeLabel = $derived.by(() =>
    getContributionTypeLabel(selectedContributionType)
  );

  onMount(() => {
    fetchMetricsData();
    fetchStudioMetrics();
    fetchRepoMetrics();
    fetchTestnetMetrics('asimov');
    fetchTestnetMetrics('bradbury');

    return () => {
      destroyCharts();
    };
  });

  onDestroy(() => {
    destroyCharts();
  });

  async function fetchMetricsData() {
    try {
      loading = true;
      pageError = null;
      submissionError = null;

      const [participantsResponse, typesResponse] = await Promise.all([
        api.get('/metrics/participants-growth/'),
        api.get('/contribution-types/', { params: { page_size: 100 } })
      ]);

      participantsData = participantsResponse.data.data || [];
      contributionTypes = normalizeContributionTypes(
        typesResponse.data.results || typesResponse.data || []
      );

      await fetchSubmissionsData({ syncDates: true });

      loading = false;
      await tick();
      createCharts();
    } catch (err) {
      pageError = err.message || 'Failed to load metrics data';
      loading = false;
    }
  }

  async function fetchStudioMetrics() {
    try {
      studioLoading = true;
      studioError = null;

      const response = await fetch(`${STUDIO_PULSE_URL}/api/metrics/executive?range=week`, {
        headers: { Accept: 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`Studio Pulse responded with ${response.status}`);
      }

      const payload = await response.json();
      const byId = Object.fromEntries((payload?.metrics || []).map((entry) => [entry.id, entry]));

      studioMetrics = {
        decisions7d: Number(byId['total-decisions']?.value ?? 0),
        decisionsAllTime: Number(byId['total-decisions']?.allTimeValue ?? 0),
        chainTx7d: Number(byId['chain-transactions']?.value ?? 0),
        chainTxAllTime: Number(byId['chain-transactions']?.allTimeValue ?? 0),
        deployedContracts7d: Number(byId['deployed-contracts']?.value ?? 0),
        deployedContractsAllTime: Number(byId['deployed-contracts']?.allTimeValue ?? 0),
        activeContracts: Number(byId['active-contracts']?.value ?? 0),
        mau: Number(byId['mau']?.value ?? 0),
        dau: Number(byId['dau']?.value ?? 0)
      };
    } catch (err) {
      studioError = err.message || 'Failed to load Studio metrics';
    } finally {
      studioLoading = false;
    }
  }

  function setTestnetState(network, key, value) {
    if (network === 'asimov') {
      if (key === 'metrics') asimovMetrics = value;
      else if (key === 'loading') asimovLoading = value;
      else if (key === 'error') asimovError = value;
    } else if (network === 'bradbury') {
      if (key === 'metrics') bradburyMetrics = value;
      else if (key === 'loading') bradburyLoading = value;
      else if (key === 'error') bradburyError = value;
    }
  }

  async function fetchTestnetMetrics(network) {
    if (!TESTNET_NETWORKS.includes(network)) {
      return;
    }

    try {
      setTestnetState(network, 'loading', true);
      setTestnetState(network, 'error', null);

      const response = await api.get('/metrics/testnet-kpis/', { params: { network } });
      setTestnetState(network, 'metrics', response.data);
    } catch (err) {
      const detail = err.response?.data?.error || err.message || `Failed to load ${network} metrics`;
      setTestnetState(network, 'error', detail);
    } finally {
      setTestnetState(network, 'loading', false);
    }
  }

  async function fetchRepoMetrics() {
    try {
      repoLoading = true;
      repoError = null;

      const response = await fetch(`https://api.github.com/repos/${BOILERPLATE_REPO}`, {
        headers: { Accept: 'application/vnd.github+json' }
      });

      if (!response.ok) {
        throw new Error(`GitHub responded with ${response.status}`);
      }

      const payload = await response.json();

      repoMetrics = {
        boilerplate: {
          name: payload.name,
          fullName: payload.full_name,
          stars: Number(payload.stargazers_count ?? 0),
          forks: Number(payload.forks_count ?? 0),
          url: payload.html_url
        }
      };
    } catch (err) {
      repoError = err.message || 'Failed to load repository metrics';
    } finally {
      repoLoading = false;
    }
  }

  async function fetchSubmissionsData({ syncDates = false } = {}) {
    const params = {
      group_by: submissionGroupBy
    };

    if (submissionStartDate) {
      params.start_date = submissionStartDate;
    }

    if (submissionEndDate) {
      params.end_date = submissionEndDate;
    }

    if (selectedCategory) {
      params.category = selectedCategory;
    }

    if (selectedContributionType) {
      params.contribution_type = selectedContributionType;
    }

    const submissionsResponse = await api.get('/steward-submissions/daily-metrics/', {
      params
    });

    submissionsData = submissionsResponse.data || {
      data: [],
      totals: {}
    };

    if (syncDates) {
      submissionStartDate = submissionsData.start_date || '';
      submissionEndDate = submissionsData.end_date || '';
    }

    appliedSubmissionFilters = {
      category: selectedCategory,
      contributionType: selectedContributionType,
      endDate: submissionEndDate,
      groupBy: submissionGroupBy,
      startDate: submissionStartDate
    };
  }

  async function applySubmissionFilters() {
    try {
      submissionsLoading = true;
      submissionError = null;

      await fetchSubmissionsData();
      await tick();
      recreateSubmissionCharts();
    } catch (err) {
      submissionError = err.message || 'Failed to load submission analytics';
    } finally {
      submissionsLoading = false;
    }
  }

  async function clearSubmissionFilters() {
    selectedCategory = '';
    selectedContributionType = '';
    submissionGroupBy = 'week';
    submissionStartDate = '';
    submissionEndDate = '';

    await applyResetFilters();
  }

  async function applyResetFilters() {
    try {
      submissionsLoading = true;
      submissionError = null;

      await fetchSubmissionsData({ syncDates: true });
      await tick();
      recreateSubmissionCharts();
    } catch (err) {
      submissionError = err.message || 'Failed to reset submission analytics';
    } finally {
      submissionsLoading = false;
    }
  }

  function onCategoryChange() {
    selectedContributionType = '';
  }

  function normalizeContributionTypes(types) {
    return [...types]
      .filter((type) => type.is_submittable)
      .sort((left, right) => {
        const categoryCompare = getCategoryLabel(left.category).localeCompare(getCategoryLabel(right.category));
        if (categoryCompare !== 0) {
          return categoryCompare;
        }

        return left.name.localeCompare(right.name);
      });
  }

  function destroyCharts() {
    if (participantsChart) {
      participantsChart.destroy();
      participantsChart = null;
    }

    if (submissionsChart) {
      submissionsChart.destroy();
      submissionsChart = null;
    }

    if (submissionsTrendChart) {
      submissionsTrendChart.destroy();
      submissionsTrendChart = null;
    }
  }

  function recreateSubmissionCharts() {
    if (submissionsChart) {
      submissionsChart.destroy();
      submissionsChart = null;
    }

    if (submissionsTrendChart) {
      submissionsTrendChart.destroy();
      submissionsTrendChart = null;
    }

    createSubmissionsChart();
    createSubmissionsTrendChart();
  }

  function createCharts() {
    createParticipantsChart();
    createSubmissionsChart();
    createSubmissionsTrendChart();
  }

  function createParticipantsChart() {
    const participantsCanvas = document.getElementById('participantsChart');

    if (!participantsCanvas || participantsData.length === 0) {
      return;
    }

    const ctx = participantsCanvas.getContext('2d');
    const height = participantsCanvas.parentElement?.clientHeight || 320;

    participantsChart = new Chart(ctx, buildParticipantsChartConfig(ctx, height));
  }

  function createSubmissionsChart() {
    const submissionsCanvas = document.getElementById('submissionsChart');

    if (!submissionsCanvas || !submissionsData.data?.length) {
      return;
    }

    const ctx = submissionsCanvas.getContext('2d');

    submissionsChart = new Chart(ctx, buildSubmissionsChartConfig());
  }

  function createSubmissionsTrendChart() {
    const trendCanvas = document.getElementById('submissionsTrendChart');

    if (!trendCanvas || !submissionsData.data?.length) {
      return;
    }

    const ctx = trendCanvas.getContext('2d');

    submissionsTrendChart = new Chart(ctx, buildSubmissionsTrendChartConfig());
  }

  function handleLegendClick(event, legendItem, legend) {
    const index = legendItem.datasetIndex;
    const chart = legend.chart;
    const meta = chart.getDatasetMeta(index);

    meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
    chart.update();
  }

  function getLegendOptions({ interactive = true, fontSize = 12, padding = 18 } = {}) {
    const legend = {
      position: 'top',
      labels: {
        boxWidth: 10,
        boxHeight: 10,
        font: { size: fontSize },
        padding,
        usePointStyle: true
      }
    };

    if (interactive) {
      legend.onClick = handleLegendClick;
    }

    return legend;
  }

  function getHiddenDatasetLabels(chart) {
    if (!chart) {
      return new Set();
    }

    return new Set(
      chart.data.datasets
        .filter((_, index) => !chart.isDatasetVisible(index))
        .map((dataset) => dataset.label)
    );
  }

  function applyHiddenDatasets(datasets, hiddenLabels = new Set()) {
    return datasets.map((dataset) => ({
      ...dataset,
      hidden: hiddenLabels.has(dataset.label)
    }));
  }

  function getExportTitleOptions(title, subtitle, forExport) {
    return {
      title: {
        display: forExport,
        text: title,
        align: 'start',
        color: '#0f172a',
        font: {
          size: 34,
          weight: '600'
        },
        padding: {
          bottom: 10
        }
      },
      subtitle: {
        display: forExport && Boolean(subtitle),
        text: subtitle,
        align: 'start',
        color: '#64748b',
        font: {
          size: 18,
          weight: '500'
        },
        padding: {
          bottom: 24
        }
      }
    };
  }

  function getChartLayoutOptions(forExport) {
    if (!forExport) {
      return {};
    }

    return {
      padding: {
        top: 26,
        right: 40,
        bottom: 28,
        left: 18
      }
    };
  }

  function buildParticipantsChartConfig(ctx, height, { forExport = false, hiddenLabels = new Set() } = {}) {
    const exportTitle = getExportTitleOptions(
      'Portal participation growth',
      'Builders and validators over time',
      forExport
    );

    return {
      type: 'line',
      data: {
        labels: participantsData.map((point) => point.date),
        datasets: applyHiddenDatasets([
          {
            label: 'Builders',
            data: participantsData.map((point) => point.builders),
            borderColor: participantPalette.builders.border,
            backgroundColor: createGradient(
              ctx,
              height,
              participantPalette.builders.fillTop,
              participantPalette.builders.fillBottom
            ),
            borderWidth: 2.5,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.24,
            yAxisID: 'yBuilders'
          },
          {
            label: 'Validators',
            data: participantsData.map((point) => point.validators),
            borderColor: participantPalette.validators.border,
            backgroundColor: createGradient(
              ctx,
              height,
              participantPalette.validators.fillTop,
              participantPalette.validators.fillBottom
            ),
            borderWidth: 2.5,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.24,
            yAxisID: 'yValidators'
          }
        ], hiddenLabels)
      },
      options: {
        animation: forExport ? false : undefined,
        responsive: !forExport,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        layout: getChartLayoutOptions(forExport),
        plugins: {
          legend: getLegendOptions({
            interactive: !forExport,
            fontSize: forExport ? 20 : 12,
            padding: forExport ? 28 : 18
          }),
          ...exportTitle,
          tooltip: {
            enabled: !forExport,
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            bodyColor: '#0f172a',
            borderColor: 'rgba(148, 163, 184, 0.32)',
            borderWidth: 1,
            callbacks: {
              title: (items) => formatDate(items[0]?.label),
              label: (context) => `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            },
            titleColor: '#0f172a'
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#64748b',
              callback: function(value) {
                return formatParticipantAxisDate(this.getLabelForValue(value));
              },
              font: { size: forExport ? 18 : 12 },
              maxRotation: 0,
              maxTicksLimit: forExport ? 12 : 8
            }
          },
          yBuilders: {
            type: 'linear',
            position: 'left',
            beginAtZero: true,
            title: {
              display: true,
              text: 'Builders',
              color: participantPalette.builders.border,
              font: { size: forExport ? 18 : 11 }
            },
            grid: {
              color: 'rgba(148, 163, 184, 0.12)'
            },
            ticks: {
              color: participantPalette.builders.border,
              font: { size: forExport ? 18 : 12 },
              callback: (value) => formatNumber(value)
            }
          },
          yValidators: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            title: {
              display: true,
              text: 'Validators',
              color: participantPalette.validators.border,
              font: { size: forExport ? 18 : 11 }
            },
            grid: {
              drawOnChartArea: false
            },
            ticks: {
              color: participantPalette.validators.border,
              font: { size: forExport ? 18 : 12 },
              callback: (value) => formatNumber(value)
            }
          }
        }
      },
      plugins: forExport ? [exportBackgroundPlugin] : []
    };
  }

  function buildSubmissionsChartConfig({
    forExport = false,
    groupBy = submissionGroupBy,
    hiddenLabels = new Set()
  } = {}) {
    const exportTitle = getExportTitleOptions(
      'Submission intake vs reviewed outcomes',
      getSubmissionExportSubtitle(),
      forExport
    );

    return {
      type: 'bar',
      data: {
        labels: submissionsData.data.map((point) => formatPeriodLabel(point.period, groupBy)),
        datasets: applyHiddenDatasets([
          {
            label: 'Submitted',
            data: submissionsData.data.map((point) => point.ingress),
            backgroundColor: reviewPalette.ingress.bg,
            borderColor: reviewPalette.ingress.border,
            borderRadius: 10,
            borderWidth: 1,
            maxBarThickness: 22,
            stack: 'intake'
          },
          {
            label: 'Accepted',
            data: submissionsData.data.map((point) => point.accepted),
            backgroundColor: reviewPalette.accepted.bg,
            borderColor: reviewPalette.accepted.border,
            borderRadius: 10,
            borderWidth: 1,
            maxBarThickness: 22,
            stack: 'review'
          },
          {
            label: 'Rejected',
            data: submissionsData.data.map((point) => point.rejected),
            backgroundColor: reviewPalette.rejected.bg,
            borderColor: reviewPalette.rejected.border,
            borderRadius: 10,
            borderWidth: 1,
            maxBarThickness: 22,
            stack: 'review'
          },
          {
            label: 'More info requested',
            data: submissionsData.data.map((point) => point.more_info_requested),
            backgroundColor: reviewPalette.moreInfo.bg,
            borderColor: reviewPalette.moreInfo.border,
            borderRadius: 10,
            borderWidth: 1,
            maxBarThickness: 22,
            stack: 'review'
          }
        ], hiddenLabels)
      },
      options: {
        animation: forExport ? false : undefined,
        responsive: !forExport,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        layout: getChartLayoutOptions(forExport),
        plugins: {
          legend: getLegendOptions({
            interactive: !forExport,
            fontSize: forExport ? 20 : 12,
            padding: forExport ? 28 : 18
          }),
          ...exportTitle,
          tooltip: {
            enabled: !forExport,
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            bodyColor: '#0f172a',
            borderColor: 'rgba(148, 163, 184, 0.32)',
            borderWidth: 1,
            callbacks: {
              title: (items) => formatPeriodTooltip(submissionsData.data[items[0]?.dataIndex]?.period, groupBy),
              footer: (items) => {
                const point = submissionsData.data[items[0]?.dataIndex];
                const reviewed =
                  Number(point?.accepted || 0) +
                  Number(point?.rejected || 0) +
                  Number(point?.more_info_requested || 0);

                return `Reviewed decisions: ${formatNumber(reviewed)}`;
              },
              label: (context) => `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            },
            titleColor: '#0f172a'
          }
        },
        scales: {
          x: {
            stacked: true,
            grid: {
              display: false
            },
            ticks: {
              color: '#64748b',
              font: { size: forExport ? 18 : 12 },
              maxRotation: 0
            }
          },
          y: {
            beginAtZero: true,
            stacked: true,
            grid: {
              color: 'rgba(148, 163, 184, 0.12)'
            },
            ticks: {
              color: '#64748b',
              font: { size: forExport ? 18 : 12 },
              callback: (value) => formatNumber(value)
            }
          }
        }
      },
      plugins: forExport ? [exportBackgroundPlugin] : []
    };
  }

  function getSubmissionsCumulativeData() {
    let cumIngress = 0;
    let cumAccepted = 0;
    let cumRejected = 0;
    let cumMoreInfo = 0;
    let cumCanceled = 0;

    return submissionsData.data.map((point) => {
      cumIngress += Number(point.ingress || 0);
      cumAccepted += Number(point.accepted || 0);
      cumRejected += Number(point.rejected || 0);
      cumMoreInfo += Number(point.more_info_requested || 0);
      cumCanceled += Number(point.canceled || 0);
      const pending = Math.max(
        0,
        cumIngress - cumAccepted - cumRejected - cumMoreInfo - cumCanceled
      );
      return { pending, accepted: cumAccepted, rejected: cumRejected, moreInfo: cumMoreInfo };
    });
  }

  function buildSubmissionsTrendChartConfig({
    forExport = false,
    groupBy = submissionGroupBy,
    hiddenLabels = new Set()
  } = {}) {
    const isDaily = groupBy === 'day';
    const dotRadius = isDaily ? 0 : 3;
    const hoverRadius = isDaily ? 3 : 5;
    const cumData = getSubmissionsCumulativeData();
    const exportTitle = getExportTitleOptions(
      'Submission state trends',
      getSubmissionExportSubtitle(),
      forExport
    );

    return {
      type: 'line',
      data: {
        labels: submissionsData.data.map((point) => formatPeriodLabel(point.period, groupBy)),
        datasets: applyHiddenDatasets([
          {
            label: 'Pending review',
            data: cumData.map((point) => point.pending),
            borderColor: reviewPalette.pending.border,
            backgroundColor: 'rgba(59, 130, 246, 0.08)',
            borderWidth: isDaily ? 1.5 : 2.5,
            fill: true,
            pointRadius: dotRadius,
            pointHoverRadius: hoverRadius,
            pointBackgroundColor: reviewPalette.pending.border,
            tension: 0.3
          },
          {
            label: 'Accepted',
            data: cumData.map((point) => point.accepted),
            borderColor: reviewPalette.accepted.border,
            backgroundColor: 'rgba(5, 150, 105, 0.06)',
            borderWidth: isDaily ? 1.5 : 2.5,
            fill: false,
            pointRadius: dotRadius,
            pointHoverRadius: hoverRadius,
            pointBackgroundColor: reviewPalette.accepted.border,
            tension: 0.3
          },
          {
            label: 'Rejected',
            data: cumData.map((point) => point.rejected),
            borderColor: reviewPalette.rejected.border,
            backgroundColor: 'rgba(220, 38, 38, 0.06)',
            borderWidth: isDaily ? 1.5 : 2,
            fill: false,
            pointRadius: dotRadius,
            pointHoverRadius: hoverRadius,
            pointBackgroundColor: reviewPalette.rejected.border,
            tension: 0.3
          },
          {
            label: 'More info requested',
            data: cumData.map((point) => point.moreInfo),
            borderColor: reviewPalette.moreInfo.border,
            backgroundColor: 'rgba(217, 119, 6, 0.06)',
            borderWidth: isDaily ? 1.5 : 2,
            fill: false,
            pointRadius: dotRadius,
            pointHoverRadius: hoverRadius,
            pointBackgroundColor: reviewPalette.moreInfo.border,
            tension: 0.3
          }
        ], hiddenLabels)
      },
      options: {
        animation: forExport ? false : undefined,
        responsive: !forExport,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        layout: getChartLayoutOptions(forExport),
        plugins: {
          legend: getLegendOptions({
            interactive: !forExport,
            fontSize: forExport ? 20 : 12,
            padding: forExport ? 28 : 18
          }),
          ...exportTitle,
          tooltip: {
            enabled: !forExport,
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            bodyColor: '#0f172a',
            borderColor: 'rgba(148, 163, 184, 0.32)',
            borderWidth: 1,
            callbacks: {
              title: (items) => formatPeriodTooltip(submissionsData.data[items[0]?.dataIndex]?.period, groupBy),
              label: (context) => `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            },
            titleColor: '#0f172a'
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#64748b',
              font: { size: forExport ? 18 : 12 },
              maxRotation: 0
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(148, 163, 184, 0.12)'
            },
            ticks: {
              color: '#64748b',
              font: { size: forExport ? 18 : 12 },
              callback: (value) => formatNumber(value)
            }
          }
        }
      },
      plugins: forExport ? [exportBackgroundPlugin] : []
    };
  }

  function getContributionTypeLabel(typeId) {
    if (!typeId) {
      return 'All contribution types';
    }

    const matchedType = contributionTypes.find(
      (type) => String(type.id) === String(typeId)
    );

    return matchedType?.name || 'Custom type';
  }

  function getSubmissionExportSubtitle() {
    const filters = appliedSubmissionFilters;
    const startDate = filters.startDate ? formatDate(filters.startDate) : 'First available';
    const endDate = filters.endDate ? formatDate(filters.endDate) : 'Latest available';
    const category = filters.category ? getCategoryLabel(filters.category) : 'All categories';
    const contributionType = getContributionTypeLabel(filters.contributionType);

    return [
      `${startDate} - ${endDate}`,
      category,
      contributionType,
      getGroupingLabel(filters.groupBy)
    ].join(' | ');
  }

  function slugify(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'all';
  }

  function getSubmissionExportFilename(kind) {
    const filters = appliedSubmissionFilters;
    const parts = [
      'portal',
      kind,
      filters.groupBy,
      filters.category || 'all-categories',
      getContributionTypeLabel(filters.contributionType)
    ];

    return `${parts.map(slugify).join('-')}-16x9.png`;
  }

  function downloadCanvas(canvas, filename) {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error('Unable to export chart image'));
          return;
        }

        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        resolve();
      }, EXPORT_FORMAT);
    });
  }

  async function exportPortalChart(kind) {
    if (chartExporting) {
      return;
    }

    let exportChart = null;
    chartExporting = kind;
    chartExportError = null;

    try {
      const exportCanvas = document.createElement('canvas');
      exportCanvas.width = EXPORT_WIDTH;
      exportCanvas.height = EXPORT_HEIGHT;
      const ctx = exportCanvas.getContext('2d');

      if (!ctx) {
        throw new Error('Unable to create export canvas');
      }

      let config;
      let filename;

      if (kind === 'participants') {
        if (!participantsData.length) {
          throw new Error('No participant growth data available to export');
        }

        config = buildParticipantsChartConfig(ctx, EXPORT_HEIGHT, {
          forExport: true,
          hiddenLabels: getHiddenDatasetLabels(participantsChart)
        });
        filename = 'portal-participation-growth-16x9.png';
      } else if (kind === 'submissions') {
        if (!submissionsData.data?.length) {
          throw new Error('No submission analytics data available to export');
        }

        config = buildSubmissionsChartConfig({
          forExport: true,
          groupBy: appliedSubmissionFilters.groupBy,
          hiddenLabels: getHiddenDatasetLabels(submissionsChart)
        });
        filename = getSubmissionExportFilename('submissions');
      } else if (kind === 'submission-trends') {
        if (!submissionsData.data?.length) {
          throw new Error('No submission trend data available to export');
        }

        config = buildSubmissionsTrendChartConfig({
          forExport: true,
          groupBy: appliedSubmissionFilters.groupBy,
          hiddenLabels: getHiddenDatasetLabels(submissionsTrendChart)
        });
        filename = getSubmissionExportFilename('submission-trends');
      } else {
        throw new Error('Unknown chart export');
      }

      exportChart = new Chart(ctx, config);
      exportChart.update('none');
      await new Promise((resolve) => requestAnimationFrame(resolve));
      await downloadCanvas(exportCanvas, filename);
    } catch (err) {
      chartExportError = err.message || 'Failed to export chart';
    } finally {
      if (exportChart) {
        exportChart.destroy();
      }
      chartExporting = '';
    }
  }

  function createGradient(ctx, height, topColor, bottomColor) {
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, topColor);
    gradient.addColorStop(1, bottomColor);
    return gradient;
  }

  function formatParticipantAxisDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short'
    });
  }

  function formatPeriodLabel(dateStr, groupBy) {
    const date = new Date(dateStr);

    if (groupBy === 'month') {
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    }

    if (groupBy === 'week') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  function formatPeriodTooltip(dateStr, groupBy) {
    if (!dateStr) {
      return 'Unknown';
    }

    const date = new Date(dateStr);

    if (groupBy === 'day') {
      return date.toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' });
    }

    if (groupBy === 'week') {
      const end = new Date(date);
      end.setDate(end.getDate() + 6);
      const startStr = date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
      const endStr = end.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
      return `Week of ${startStr} – ${endStr}`;
    }

    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  function getCategoryLabel(slug) {
    return CATEGORY_LABELS[slug] || (slug ? slug[0].toUpperCase() + slug.slice(1) : 'Unknown');
  }

  function getGroupingLabel(groupBy) {
    if (groupBy === 'day') {
      return 'Daily';
    }

    if (groupBy === 'month') {
      return 'Monthly';
    }

    return 'Weekly';
  }

  function formatDate(dateStr) {
    if (!dateStr) {
      return 'Unknown';
    }

    return new Date(dateStr).toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString('en-US');
  }

  function formatCompact(value) {
    const number = Number(value || 0);
    if (Math.abs(number) < 10000) {
      return formatNumber(number);
    }
    return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(number);
  }

  function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
  }
</script>

<div class="mx-auto max-w-[1480px] px-4 py-8 lg:px-6">
  <div class="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="mb-2 text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Portal Metrics</p>
      <h1 class="text-3xl font-semibold tracking-tight text-slate-900">Metrics Dashboard</h1>
    </div>
    <nav>
      <ul class="flex flex-wrap gap-2">
        {#each TABS as tab (tab.id)}
          <li>
            <button
              type="button"
              onclick={() => (activeTab = tab.id)}
              class="flex items-center gap-3 whitespace-nowrap rounded-full px-5 py-3 text-sm font-medium transition {activeTab === tab.id
                ? 'bg-slate-900 text-white shadow-sm'
                : 'border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'}"
            >
              <span class="h-2 w-2 rounded-full {tab.dot}"></span>
              {tab.label}
            </button>
          </li>
        {/each}
      </ul>
    </nav>
  </div>

  {#if pageError}
    <div class="mb-6 rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700 shadow-sm">
      <span class="font-semibold">Error:</span> {pageError}
    </div>
  {/if}

  {#if chartExportError}
    <div class="mb-6 rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700 shadow-sm">
      <span class="font-semibold">Export error:</span> {chartExportError}
    </div>
  {/if}

  {#snippet kpiStrip(palette, defs, metrics, isLoading, isError)}
      <div class="rounded-[24px] border border-slate-200 bg-slate-50/60 p-5 sm:p-6">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="h-2.5 w-2.5 rounded-full {palette.dot}"></span>
            <h3 class="text-base font-semibold text-slate-900">{palette.label}</h3>
            {#if !metrics && !isLoading && !isError}
              <span class="rounded-full {palette.chip} px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em]">Coming soon</span>
            {/if}
          </div>
          <p class="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">{palette.source}</p>
        </div>

        {#if isLoading}
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
            {#each defs as _, i (i)}
              <div class="h-[112px] animate-pulse rounded-2xl border border-slate-200 bg-white"></div>
            {/each}
          </div>
        {:else if isError}
          <div class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <span class="font-semibold">Unavailable:</span> {isError}
          </div>
        {:else}
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
            {#each defs as def (def.primaryKey)}
              <div class="flex flex-col rounded-2xl border border-slate-200 bg-gradient-to-br {palette.surface} p-4">
                <p class="text-xs font-medium text-slate-600">{def.label}</p>
                {#if def.range}
                  <p class="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">{def.range}</p>
                {/if}
                <p class="mt-2 text-2xl font-semibold {metrics ? palette.text : 'text-slate-300'}">
                  {#if metrics}
                    {def.compact ? formatCompact(metrics[def.primaryKey]) : formatNumber(metrics[def.primaryKey])}
                  {:else}
                    —
                  {/if}
                </p>
                {#if def.secondaryKey}
                  <p class="mt-1 text-[11px] text-slate-400">
                    {#if metrics}
                      {def.compact ? formatCompact(metrics[def.secondaryKey]) : formatNumber(metrics[def.secondaryKey])} all time
                    {:else}
                      — all time
                    {/if}
                  </p>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/snippet}

    <div>
      <div class="min-w-0">

    <section class:hidden={activeTab !== 'community'} class="rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_20px_70px_rgba(15,23,42,0.06)] lg:p-8">
      <div class="mb-6">
        <p class="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Community</p>
        <h2 class="text-2xl font-semibold tracking-tight text-slate-900">Open source and channels</h2>
      </div>

      <div class="space-y-4">
        <div class="rounded-[24px] border border-slate-200 bg-slate-50/60 p-5 sm:p-6">
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap items-center gap-3">
              <span class="h-2.5 w-2.5 rounded-full {ecosystemPalette.repository.dot}"></span>
              <h3 class="text-base font-semibold text-slate-900">{ecosystemPalette.repository.label}</h3>
              {#if repoMetrics?.boilerplate}
                <span class="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-700">
                  <span aria-hidden="true">★</span>
                  {formatNumber(repoMetrics.boilerplate.stars)}
                </span>
                <span class="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-semibold text-slate-700">
                  <svg viewBox="0 0 16 16" aria-hidden="true" class="h-3.5 w-3.5" fill="currentColor">
                    <path d="M5 3.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm0 2.122a2.25 2.25 0 1 0-1.5 0v.878A2.25 2.25 0 0 0 5.75 8.5h1.5v2.128a2.251 2.251 0 1 0 1.5 0V8.5h1.5a2.25 2.25 0 0 0 2.25-2.25v-.878a2.25 2.25 0 1 0-1.5 0v.878a.75.75 0 0 1-.75.75h-4.5A.75.75 0 0 1 5 6.25v-.878Zm3.75 7.378a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm3-8.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"/>
                  </svg>
                  {formatNumber(repoMetrics.boilerplate.forks)}
                </span>
                <a
                  href={repoMetrics.boilerplate.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm font-medium text-slate-600 underline-offset-4 hover:text-amber-700 hover:underline"
                >
                  {repoMetrics.boilerplate.fullName} ↗
                </a>
              {/if}
            </div>
            <p class="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">{ecosystemPalette.repository.source}</p>
          </div>

          {#if repoLoading}
            <div class="h-[320px] animate-pulse rounded-[20px] border border-slate-200 bg-white"></div>
          {:else if repoError}
            <div class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <span class="font-semibold">Unavailable:</span> {repoError}
            </div>
          {:else if repoMetrics?.boilerplate}
            <div class="flex items-center justify-center rounded-[20px] border border-slate-200 bg-white p-3">
              <img
                src={`https://api.star-history.com/svg?repos=${BOILERPLATE_REPO}&type=Date`}
                alt={`Star history for ${BOILERPLATE_REPO}`}
                loading="lazy"
                class="block h-auto max-h-[320px] w-auto max-w-full"
              />
            </div>
          {/if}
        </div>

        <div class="grid gap-4 lg:grid-cols-5">
          <div class="rounded-[24px] border border-slate-200 bg-slate-50/60 p-5 sm:p-6 lg:col-span-3">
            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div class="flex flex-wrap items-center gap-3">
                <span class="h-2.5 w-2.5 rounded-full {ecosystemPalette.discord.dot}"></span>
                <h3 class="text-base font-semibold text-slate-900">
                  <a
                    href={DISCORD_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="underline-offset-4 hover:text-indigo-700 hover:underline"
                  >
                    GenLayer Discord ↗
                  </a>
                </h3>
              </div>
              <p class="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">{ecosystemPalette.discord.source}</p>
            </div>
            <div class="grid grid-cols-3 gap-3">
              {#each DISCORD_KPIS as kpi (kpi.label)}
                <div class="flex flex-col rounded-2xl border border-slate-200 bg-gradient-to-br {ecosystemPalette.discord.surface} p-4">
                  <p class="text-xs font-medium text-slate-600">{kpi.label}</p>
                  <p class="mt-2 text-2xl font-semibold {ecosystemPalette.discord.text}">{kpi.value}</p>
                </div>
              {/each}
            </div>
          </div>

          <div class="rounded-[24px] border border-slate-200 bg-slate-50/60 p-5 sm:p-6 lg:col-span-2">
            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div class="flex flex-wrap items-center gap-3">
                <span class="h-2.5 w-2.5 rounded-full {ecosystemPalette.x.dot}"></span>
                <h3 class="text-base font-semibold text-slate-900">
                  <a
                    href={X_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="underline-offset-4 hover:text-slate-700 hover:underline"
                  >
                    GenLayer X ↗
                  </a>
                </h3>
              </div>
              <p class="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">{ecosystemPalette.x.source}</p>
            </div>
            <div class="grid grid-cols-2 gap-3">
              {#each X_KPIS as kpi (kpi.label)}
                <div class="flex flex-col rounded-2xl border border-slate-200 bg-gradient-to-br {ecosystemPalette.x.surface} p-4">
                  <p class="text-xs font-medium text-slate-600">{kpi.label}</p>
                  {#if kpi.range}
                    <p class="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">{kpi.range}</p>
                  {/if}
                  <p class="mt-2 text-2xl font-semibold {ecosystemPalette.x.text}">{kpi.value}</p>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class:hidden={activeTab !== 'networks'} class="rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_20px_70px_rgba(15,23,42,0.06)] lg:p-8">
      <div class="mb-6 flex items-end justify-between gap-3">
        <div>
          <p class="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Networks</p>
          <h2 class="text-2xl font-semibold tracking-tight text-slate-900">Studio and testnets</h2>
        </div>
      </div>

      <div class="space-y-4">
        {@render kpiStrip(ecosystemPalette.studio, ONCHAIN_KPI_DEFS, studioMetrics, studioLoading, studioError)}
        {@render kpiStrip(ecosystemPalette.asimov, TESTNET_KPI_DEFS, asimovMetrics, asimovLoading, asimovError)}
        {@render kpiStrip(ecosystemPalette.bradbury, TESTNET_KPI_DEFS, bradburyMetrics, bradburyLoading, bradburyError)}
      </div>
    </section>

    <section class:hidden={activeTab !== 'portal'} class="mb-6 rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_20px_70px_rgba(15,23,42,0.06)] lg:p-8">
      <div class="mb-6">
        <p class="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Portal Participation</p>
        <h2 class="text-2xl font-semibold tracking-tight text-slate-900">Validators and active builders</h2>
      </div>

      <div class="mb-6 grid gap-4 md:grid-cols-2">
        {#if loading}
          {#each [0, 1] as _, i (i)}
            <div class="h-[110px] animate-pulse rounded-[24px] border border-slate-200 bg-slate-50"></div>
          {/each}
        {:else}
          <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {participantPalette.validators.surface} p-5">
            <p class="text-sm font-medium text-slate-500">Validators</p>
            <div class="mt-3 flex items-end justify-between gap-4">
              <p class="text-3xl font-semibold {participantPalette.validators.text}">
                {formatNumber(latestParticipantsSnapshot.validators)}
              </p>
              <p class="text-xs font-medium text-slate-500">Network operators</p>
            </div>
          </div>

          <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {participantPalette.builders.surface} p-5">
            <p class="text-sm font-medium text-slate-500">Builders</p>
            <div class="mt-3 flex items-end justify-between gap-4">
              <p class="text-3xl font-semibold {participantPalette.builders.text}">
                {formatNumber(latestParticipantsSnapshot.builders)}
              </p>
              <p class="text-xs font-medium text-slate-500">Contributors</p>
            </div>
          </div>
        {/if}
      </div>

      <div class="rounded-[28px] border border-slate-200 bg-slate-50/70 p-5 sm:p-6">
        <div class="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 class="text-lg font-semibold text-slate-900">Growth trajectory</h3>
            <p class="mt-1 text-sm text-slate-500">Builders on the left axis, validators on the right.</p>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <p class="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Daily points</p>
            <button
              type="button"
              title="Export 16:9 PNG"
              aria-label="Export growth trajectory as 16:9 PNG"
              onclick={() => exportPortalChart('participants')}
              disabled={loading || participantsData.length === 0 || Boolean(chartExporting)}
              class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-slate-400 transition hover:border-slate-200 hover:bg-white hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5"/>
                <path d="M4 13.5V16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2.5"/>
              </svg>
              <span class="sr-only">{chartExporting === 'participants' ? 'Exporting growth trajectory' : 'Export growth trajectory as 16:9 PNG'}</span>
            </button>
          </div>
        </div>

        {#if loading}
          <div class="h-[360px] animate-pulse rounded-2xl border border-slate-200 bg-white"></div>
        {:else if participantsData.length > 0}
          <div class="h-[360px]">
            <canvas id="participantsChart"></canvas>
          </div>
        {:else}
          <div class="flex h-[360px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white text-sm text-slate-500">
            No participant growth data available.
          </div>
        {/if}
      </div>
    </section>

    <section class:hidden={activeTab !== 'portal'} class="rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_20px_70px_rgba(15,23,42,0.06)] lg:p-8">
      <div class="mb-6 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Submission Analytics</p>
          <h2 class="text-2xl font-semibold tracking-tight text-slate-900">Review flow and trends</h2>
        </div>

        {#if submissionsLoading}
          <div class="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-600">
            Refreshing analytics...
          </div>
        {/if}
      </div>

      <div class="mb-6 rounded-[28px] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-slate-50/50 p-5 sm:p-6">
        <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_220px_260px_170px_auto]">
          <div>
            <label for="submission-start-date" class="mb-1.5 block text-sm font-medium text-slate-600">Start date</label>
            <input
              id="submission-start-date"
              type="date"
              bind:value={submissionStartDate}
              class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-200"
            />
          </div>

          <div>
            <label for="submission-end-date" class="mb-1.5 block text-sm font-medium text-slate-600">End date</label>
            <input
              id="submission-end-date"
              type="date"
              bind:value={submissionEndDate}
              class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-200"
            />
          </div>

          <div>
            <label for="submission-category" class="mb-1.5 block text-sm font-medium text-slate-600">Category</label>
            <select
              id="submission-category"
              bind:value={selectedCategory}
              onchange={onCategoryChange}
              class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-200"
            >
              <option value="">All categories</option>
              {#each availableCategories as category}
                <option value={category}>{getCategoryLabel(category)}</option>
              {/each}
            </select>
          </div>

          <div>
            <label for="submission-type" class="mb-1.5 block text-sm font-medium text-slate-600">Contribution type</label>
            <select
              id="submission-type"
              bind:value={selectedContributionType}
              class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-200"
            >
              <option value="">All contribution types</option>
              {#each filteredContributionTypes as type}
                <option value={type.id}>{type.name}</option>
              {/each}
            </select>
          </div>

          <div>
            <label for="submission-group-by" class="mb-1.5 block text-sm font-medium text-slate-600">Group by</label>
            <select
              id="submission-group-by"
              bind:value={submissionGroupBy}
              class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-200"
            >
              <option value="day">Daily</option>
              <option value="week">Weekly</option>
              <option value="month">Monthly</option>
            </select>
          </div>

          <div class="flex flex-wrap items-end gap-3">
            <button
              onclick={applySubmissionFilters}
              disabled={submissionsLoading}
              class="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Apply filters
            </button>
            <button
              onclick={clearSubmissionFilters}
              disabled={submissionsLoading}
              class="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Reset
            </button>
          </div>
        </div>

        {#if submissionError}
          <div class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <span class="font-semibold">Submission analytics error:</span> {submissionError}
          </div>
        {/if}
      </div>

      <div class="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
        {#if loading}
          {#each [0, 1, 2, 3, 4] as _, i (i)}
            <div class="h-[124px] animate-pulse rounded-[24px] border border-slate-200 bg-slate-50"></div>
          {/each}
        {:else}
          <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {reviewPalette.ingress.surface} p-5">
            <p class="text-sm font-medium text-slate-500">New submissions</p>
            <p class="mt-3 text-3xl font-semibold {reviewPalette.ingress.text}">
              {formatNumber(submissionsSummary.ingress)}
            </p>
            <p class="mt-2 text-xs leading-5 text-slate-500">Submissions created in the selected range.</p>
          </div>

          <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-slate-50/40 p-5">
            <p class="text-sm font-medium text-slate-500">Reviewed</p>
            <p class="mt-3 text-3xl font-semibold text-slate-900">{formatNumber(submissionsSummary.reviewed)}</p>
            <p class="mt-2 text-xs leading-5 text-slate-500">Accepted, rejected, and more-info combined.</p>
          </div>

          <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {reviewPalette.pending.surface} p-5">
            <p class="text-sm font-medium text-slate-500">Pending review</p>
            <p class="mt-3 text-3xl font-semibold {reviewPalette.pending.text}">
              {formatNumber(submissionsSummary.pendingReview)}
            </p>
            <p class="mt-2 text-xs leading-5 text-slate-500">Submissions in this range still awaiting a decision.</p>
          </div>

          <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {reviewPalette.accepted.surface} p-5">
            <p class="text-sm font-medium text-slate-500">Acceptance rate</p>
            <p class="mt-3 text-3xl font-semibold {reviewPalette.accepted.text}">
              {formatPercent(submissionsSummary.acceptanceRate)}
            </p>
            <p class="mt-2 text-xs leading-5 text-slate-500">
              {formatNumber(submissionsSummary.accepted)} accepted of {formatNumber(submissionsSummary.reviewed)} reviewed.
            </p>
          </div>

          <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {reviewPalette.points.surface} p-5">
            <p class="text-sm font-medium text-slate-500">Points awarded</p>
            <p class="mt-3 text-3xl font-semibold {reviewPalette.points.text}">
              {formatNumber(submissionsSummary.pointsAwarded)}
            </p>
            <p class="mt-2 text-xs leading-5 text-slate-500">
              Avg. {formatNumber(submissionsSummary.avgPointsPerAccepted)} per accepted.
            </p>
          </div>
        {/if}
      </div>

      <div class="grid gap-6 xl:grid-cols-2">
        <div class="rounded-[28px] border border-slate-200 bg-slate-50/70 p-5 sm:p-6">
          <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 class="text-lg font-semibold text-slate-900">Submission intake vs reviewed outcomes</h3>
              <p class="mt-1 text-sm text-slate-500">
                Each period compares newly submitted work against the review decisions made in that same period.
              </p>
            </div>
            <button
              type="button"
              title="Export 16:9 PNG"
              aria-label="Export submission intake chart as 16:9 PNG"
              onclick={() => exportPortalChart('submissions')}
              disabled={loading || submissionsLoading || !submissionsData.data?.length || Boolean(chartExporting)}
              class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-transparent text-slate-400 transition hover:border-slate-200 hover:bg-white hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5"/>
                <path d="M4 13.5V16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2.5"/>
              </svg>
              <span class="sr-only">{chartExporting === 'submissions' ? 'Exporting submission intake chart' : 'Export submission intake chart as 16:9 PNG'}</span>
            </button>
          </div>

          {#if loading}
            <div class="h-[320px] animate-pulse rounded-2xl border border-slate-200 bg-white"></div>
          {:else if submissionsData.data?.length > 0}
            <div class="h-[320px]">
              <canvas id="submissionsChart"></canvas>
            </div>
          {:else}
            <div class="flex h-[320px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white text-sm text-slate-500">
              No submissions matched the selected filters.
            </div>
          {/if}
        </div>

        <div class="rounded-[28px] border border-slate-200 bg-slate-50/70 p-5 sm:p-6">
          <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 class="text-lg font-semibold text-slate-900">Submission state trends</h3>
              <p class="mt-1 text-sm text-slate-500">
                Per-state curves over time. Click a legend label to toggle its visibility.
              </p>
            </div>
            <button
              type="button"
              title="Export 16:9 PNG"
              aria-label="Export submission state trends as 16:9 PNG"
              onclick={() => exportPortalChart('submission-trends')}
              disabled={loading || submissionsLoading || !submissionsData.data?.length || Boolean(chartExporting)}
              class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-transparent text-slate-400 transition hover:border-slate-200 hover:bg-white hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5"/>
                <path d="M4 13.5V16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2.5"/>
              </svg>
              <span class="sr-only">{chartExporting === 'submission-trends' ? 'Exporting submission state trends' : 'Export submission state trends as 16:9 PNG'}</span>
            </button>
          </div>

          {#if loading}
            <div class="h-[320px] animate-pulse rounded-2xl border border-slate-200 bg-white"></div>
          {:else if submissionsData.data?.length > 0}
            <div class="h-[320px]">
              <canvas id="submissionsTrendChart"></canvas>
            </div>
          {:else}
            <div class="flex h-[320px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white text-sm text-slate-500">
              No reviewed submissions are available for this selection.
            </div>
          {/if}
        </div>
      </div>
    </section>

      </div>
    </div>
</div>
