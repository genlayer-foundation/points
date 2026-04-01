<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { Chart, registerables } from 'chart.js';
  import api from '../lib/api.js';

  Chart.register(...registerables);

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
    waitlist: {
      border: 'rgb(14, 165, 233)',
      fillTop: 'rgba(14, 165, 233, 0.20)',
      fillBottom: 'rgba(14, 165, 233, 0.03)',
      surface: 'from-sky-50 via-white to-sky-50/40',
      text: 'text-sky-600',
      track: 'bg-sky-100',
      bar: 'bg-sky-500'
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
    validators: 0,
    waitlist: 0
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
    const pendingReview = Math.max(0, ingress - reviewed);

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

  let selectedContributionTypeLabel = $derived.by(() => {
    if (!selectedContributionType) {
      return 'All contribution types';
    }

    const matchedType = contributionTypes.find(
      (type) => String(type.id) === String(selectedContributionType)
    );

    return matchedType?.name || 'Custom type';
  });

  onMount(() => {
    fetchMetricsData();

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

    participantsChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: participantsData.map((point) => point.date),
        datasets: [
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
            yAxisID: 'y'
          },
          {
            label: 'Validator waitlist',
            data: participantsData.map((point) => point.waitlist),
            borderColor: participantPalette.waitlist.border,
            backgroundColor: createGradient(
              ctx,
              height,
              participantPalette.waitlist.fillTop,
              participantPalette.waitlist.fillBottom
            ),
            borderWidth: 2.5,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.24,
            yAxisID: 'y'
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
            borderWidth: 2,
            borderDash: [6, 3],
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.24,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              padding: 18,
              usePointStyle: true
            },
            onClick: function(event, legendItem, legend) {
              const index = legendItem.datasetIndex;
              const chart = legend.chart;
              const meta = chart.getDatasetMeta(index);

              meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
              chart.update();
            }
          },
          tooltip: {
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
              maxRotation: 0,
              maxTicksLimit: 8
            }
          },
          y: {
            type: 'linear',
            position: 'left',
            beginAtZero: true,
            title: {
              display: true,
              text: 'Builders / Waitlist',
              color: '#64748b',
              font: { size: 11 }
            },
            grid: {
              color: 'rgba(148, 163, 184, 0.12)'
            },
            ticks: {
              color: '#64748b',
              callback: (value) => formatNumber(value)
            }
          },
          y1: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            max: Math.round((participantsData[participantsData.length - 1]?.validators || 10) * 1.5 / 10) * 10,
            title: {
              display: true,
              text: 'Validators',
              color: 'rgb(37, 99, 235)',
              font: { size: 11 }
            },
            grid: {
              drawOnChartArea: false
            },
            ticks: {
              color: 'rgb(37, 99, 235)',
              callback: (value) => formatNumber(value)
            }
          }
        }
      }
    });
  }

  function createSubmissionsChart() {
    const submissionsCanvas = document.getElementById('submissionsChart');

    if (!submissionsCanvas || !submissionsData.data?.length) {
      return;
    }

    const ctx = submissionsCanvas.getContext('2d');

    submissionsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: submissionsData.data.map((point) => formatPeriodLabel(point.period, submissionGroupBy)),
        datasets: [
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
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              padding: 18,
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            bodyColor: '#0f172a',
            borderColor: 'rgba(148, 163, 184, 0.32)',
            borderWidth: 1,
            callbacks: {
              title: (items) => formatPeriodTooltip(submissionsData.data[items[0]?.dataIndex]?.period, submissionGroupBy),
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
              callback: (value) => formatNumber(value)
            }
          }
        }
      }
    });
  }

  function createSubmissionsTrendChart() {
    const trendCanvas = document.getElementById('submissionsTrendChart');

    if (!trendCanvas || !submissionsData.data?.length) {
      return;
    }

    const ctx = trendCanvas.getContext('2d');
    const height = trendCanvas.parentElement?.clientHeight || 320;
    const isDaily = submissionGroupBy === 'day';
    const dotRadius = isDaily ? 0 : 3;
    const hoverRadius = isDaily ? 3 : 5;

    // Build cumulative sums per state
    let cumIngress = 0;
    let cumAccepted = 0;
    let cumRejected = 0;
    let cumMoreInfo = 0;
    const cumData = submissionsData.data.map((point) => {
      cumIngress += Number(point.ingress || 0);
      cumAccepted += Number(point.accepted || 0);
      cumRejected += Number(point.rejected || 0);
      cumMoreInfo += Number(point.more_info_requested || 0);
      const pending = Math.max(0, cumIngress - cumAccepted - cumRejected - cumMoreInfo);
      return { pending, accepted: cumAccepted, rejected: cumRejected, moreInfo: cumMoreInfo };
    });

    submissionsTrendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: submissionsData.data.map((point) => formatPeriodLabel(point.period, submissionGroupBy)),
        datasets: [
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
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              padding: 18,
              usePointStyle: true
            },
            onClick: function(event, legendItem, legend) {
              const index = legendItem.datasetIndex;
              const chart = legend.chart;
              const meta = chart.getDatasetMeta(index);

              meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
              chart.update();
            }
          },
          tooltip: {
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            bodyColor: '#0f172a',
            borderColor: 'rgba(148, 163, 184, 0.32)',
            borderWidth: 1,
            callbacks: {
              title: (items) => formatPeriodTooltip(submissionsData.data[items[0]?.dataIndex]?.period, submissionGroupBy),
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
              callback: (value) => formatNumber(value)
            }
          }
        }
      }
    });
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

  function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
  }
</script>

<div class="mx-auto max-w-[1480px] px-4 py-8 lg:px-6">
  <div class="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="mb-2 text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Portal Metrics</p>
      <h1 class="text-3xl font-semibold tracking-tight text-slate-900">Metrics Dashboard</h1>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
        Participant counts are shown as all-time footprint. Submission filters are isolated below so the scope of
        each graph is explicit.
      </p>
    </div>
  </div>

  {#if loading}
    <div class="flex h-72 items-center justify-center rounded-[28px] border border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.06)]">
      <div class="h-12 w-12 animate-spin rounded-full border-b-2 border-sky-500"></div>
    </div>
  {:else if pageError}
    <div class="rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700 shadow-sm">
      <span class="font-semibold">Error:</span> {pageError}
    </div>
  {:else}
    <section class="mb-10 rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_20px_70px_rgba(15,23,42,0.06)] lg:p-8">
      <div class="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="max-w-3xl">
          <p class="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Participants Overview</p>
          <h2 class="text-2xl font-semibold tracking-tight text-slate-900">Participant growth</h2>
          <p class="mt-2 text-sm leading-6 text-slate-500">
            Builders and waitlist share the left axis; validators use the right axis due to their smaller cohort size.
            Click a legend label to toggle its visibility.
          </p>
        </div>
        <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          Snapshot date: <span class="font-semibold text-slate-900">{formatDate(latestParticipantsSnapshot.date)}</span>
        </div>
      </div>

      <div class="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {participantPalette.validators.surface} p-5">
          <p class="text-sm font-medium text-slate-500">Active validators</p>
          <div class="mt-3 flex items-end justify-between gap-4">
            <p class="text-3xl font-semibold {participantPalette.validators.text}">
              {formatNumber(latestParticipantsSnapshot.validators)}
            </p>
            <p class="text-xs font-medium text-slate-500">
              {formatPercent((latestParticipantsSnapshot.validators / (latestParticipantsSnapshot.total || 1)) * 100)}
              of unique participants
            </p>
          </div>
        </div>

        <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {participantPalette.waitlist.surface} p-5">
          <p class="text-sm font-medium text-slate-500">Validator waitlist</p>
          <div class="mt-3 flex items-end justify-between gap-4">
            <p class="text-3xl font-semibold {participantPalette.waitlist.text}">
              {formatNumber(latestParticipantsSnapshot.waitlist)}
            </p>
            <p class="text-xs font-medium text-slate-500">
              {formatPercent((latestParticipantsSnapshot.waitlist / (latestParticipantsSnapshot.total || 1)) * 100)}
              of unique participants
            </p>
          </div>
        </div>

        <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br {participantPalette.builders.surface} p-5">
          <p class="text-sm font-medium text-slate-500">Builders</p>
          <div class="mt-3 flex items-end justify-between gap-4">
            <p class="text-3xl font-semibold {participantPalette.builders.text}">
              {formatNumber(latestParticipantsSnapshot.builders)}
            </p>
            <p class="text-xs font-medium text-slate-500">
              {formatPercent((latestParticipantsSnapshot.builders / (latestParticipantsSnapshot.total || 1)) * 100)}
              of unique participants
            </p>
          </div>
        </div>

        <div class="rounded-[24px] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-slate-50/40 p-5">
          <p class="text-sm font-medium text-slate-500">Unique participants</p>
          <div class="mt-3 flex items-end justify-between gap-4">
            <p class="text-3xl font-semibold text-slate-900">{formatNumber(latestParticipantsSnapshot.total)}</p>
            <p class="text-xs font-medium text-slate-500">Deduplicated across roles</p>
          </div>
        </div>
      </div>

      <div class="rounded-[28px] border border-slate-200 bg-slate-50/70 p-5 sm:p-6">
        <div class="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 class="text-lg font-semibold text-slate-900">Growth trajectory</h3>
            <p class="mt-1 text-sm text-slate-500">All-time cumulative growth. Left axis: builders & waitlist. Right axis: validators.</p>
          </div>
          <p class="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Daily points</p>
        </div>

        {#if participantsData.length > 0}
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

    <section class="rounded-[32px] border border-slate-200 bg-white p-6 shadow-[0_20px_70px_rgba(15,23,42,0.06)] lg:p-8">
      <div class="mb-6 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div class="max-w-3xl">
          <p class="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Submission Analytics</p>
          <h2 class="text-2xl font-semibold tracking-tight text-slate-900">Filtered review flow and trends</h2>
          <p class="mt-2 text-sm leading-6 text-slate-500">
            Category and contribution type filters apply only to this section. The charts below use reviewed outcomes
            and accepted-contribution points from the submissions endpoint.
          </p>
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
          <p class="mt-2 text-xs leading-5 text-slate-500">Remaining submissions awaiting a decision.</p>
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
      </div>

      <div class="grid gap-6 xl:grid-cols-2">
        <div class="rounded-[28px] border border-slate-200 bg-slate-50/70 p-5 sm:p-6">
          <div class="mb-5">
            <h3 class="text-lg font-semibold text-slate-900">Submission intake vs reviewed outcomes</h3>
            <p class="mt-1 text-sm text-slate-500">
              Each period compares newly submitted work against the review decisions made in that same period.
            </p>
          </div>

          {#if submissionsData.data?.length > 0}
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
          <div class="mb-5">
            <h3 class="text-lg font-semibold text-slate-900">Submission state trends</h3>
            <p class="mt-1 text-sm text-slate-500">
              Per-state curves over time. Click a legend label to toggle its visibility.
            </p>
          </div>

          {#if submissionsData.data?.length > 0}
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
  {/if}
</div>
