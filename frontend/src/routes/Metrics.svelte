<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { Chart, registerables } from 'chart.js';
  import api from '../lib/api.js';
  import { authState, verifyAuth } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';

  Chart.register(...registerables);

  /**
   * @typedef {Object} ParticipantPoint
   * @property {number} builders
   * @property {number} cohort_total
   * @property {number} contributor_cohort_total
   * @property {number} contributor_overlap_count
   * @property {number} community_members
   * @property {string} date
   * @property {number} overlap_count
   * @property {number} total
   * @property {number} unique_contributors
   * @property {number} validators
   * @property {number} waitlist
   *
   * @typedef {Object} ContributionType
   * @property {string | number} id
   * @property {string} name
   * @property {string} category
   * @property {boolean} is_submittable
   *
   * @typedef {Object} SubmissionTotals
   * @property {number} [accepted]
   * @property {number} [canceled]
   * @property {number} [ingress]
   * @property {number} [more_info_requested]
   * @property {number} [pending_review]
   * @property {number} [points_awarded]
   * @property {number} [rejected]
   *
   * @typedef {Object} SubmissionPoint
   * @property {number} accepted
   * @property {number} canceled
   * @property {number} ingress
   * @property {number} more_info_requested
   * @property {number} pending_review
   * @property {string} period
   * @property {number} points_awarded
   * @property {number} rejected
   *
   * @typedef {Object} SubmissionsResponse
   * @property {SubmissionPoint[]} data
   * @property {string} [end_date]
   * @property {string} [group_by]
   * @property {string} [start_date]
   * @property {SubmissionTotals} totals
   *
   * @typedef {Object} SubmissionSummary
   * @property {number} accepted
   * @property {number} acceptanceRate
   * @property {number} avgPointsPerAccepted
   * @property {number} ingress
   * @property {number} moreInfoRequested
   * @property {number} pendingReview
   * @property {number} pointsAwarded
   * @property {number} rejected
   * @property {number} reviewed
   *
   * @typedef {'day' | 'week' | 'month'} SubmissionGroupBy
   * @typedef {'participants' | 'submissions' | 'submission-trends'} ExportKind
   */

  const EXPORT_WIDTH = 1920;
  const EXPORT_HEIGHT = 1080;
  const EXPORT_FORMAT = 'image/png';
  const COMMUNITY_CATEGORY_SLUGS = ['community', 'creator'];
  const SUBMISSION_CATEGORY_ORDER = ['builder', 'validator', 'community'];
  const SUBMISSION_DEFAULT_CATEGORIES = ['builder', 'validator', 'community'];

  const exportBackgroundPlugin = {
    id: 'exportBackground',
    /**
     * @param {import('chart.js').Chart} chart
     * @param {unknown} _args
     * @param {{ color?: string }} options
     */
    beforeDraw(chart, _args, options) {
      const { ctx, width, height } = chart;
      ctx.save();
      ctx.fillStyle = options?.color || '#ffffff';
      ctx.fillRect(0, 0, width, height);
      ctx.restore();
    }
  };

  /** @type {Record<string, string>} */
  const CATEGORY_LABELS = {
    builder: 'Builder',
    community: 'Community',
    creator: 'Community',
    genlayer: 'Portal',
    steward: 'Steward',
    validator: 'Validator'
  };

  const participantPalette = {
    builders: {
      border: 'rgb(238, 133, 33)',
      fillTop: 'rgba(238, 133, 33, 0.2)',
      fillBottom: 'rgba(238, 133, 33, 0.02)',
      text: 'text-[#d96816]'
    },
    validators: {
      border: 'rgb(56, 125, 232)',
      fillTop: 'rgba(56, 125, 232, 0.16)',
      fillBottom: 'rgba(56, 125, 232, 0.02)',
      text: 'text-[#1f56f2]'
    },
    community: {
      border: 'rgb(127, 82, 225)',
      fillTop: 'rgba(127, 82, 225, 0.18)',
      fillBottom: 'rgba(127, 82, 225, 0.02)',
      text: 'text-[#6f35d7]'
    },
    total: {
      border: 'rgb(16, 16, 16)',
      text: 'text-[#101010]'
    }
  };

  const reviewPalette = {
    ingress: {
      bg: 'rgba(127, 82, 225, 0.24)',
      border: 'rgb(127, 82, 225)',
      text: 'text-[#6f35d7]',
      surface: 'from-[#f4efff] via-white to-[#fbf9ff]'
    },
    accepted: {
      bg: 'rgba(25, 166, 99, 0.74)',
      border: 'rgb(25, 166, 99)',
      text: 'text-[#12814b]',
      surface: 'from-[#effaf4] via-white to-[#f8fefa]'
    },
    moreInfo: {
      bg: 'rgba(238, 133, 33, 0.72)',
      border: 'rgb(217, 104, 22)',
      text: 'text-[#d96816]',
      surface: 'from-[#fff4e8] via-white to-[#fffaf5]'
    },
    pending: {
      border: 'rgb(56, 125, 232)',
      text: 'text-[#1f56f2]',
      surface: 'from-[#edf4ff] via-white to-[#f8fbff]'
    }
  };

  /** @type {ParticipantPoint} */
  const emptyParticipantsSnapshot = {
    builders: 0,
    cohort_total: 0,
    contributor_cohort_total: 0,
    contributor_overlap_count: 0,
    community_members: 0,
    date: '',
    overlap_count: 0,
    total: 0,
    unique_contributors: 0,
    validators: 0,
    waitlist: 0
  };

  /** @type {import('chart.js').Chart | null} */
  let participantsChart = null;
  /** @type {import('chart.js').Chart | null} */
  let submissionsChart = null;
  /** @type {import('chart.js').Chart | null} */
  let submissionsTrendChart = null;

  let loading = $state(true);
  let submissionsLoading = $state(false);
  let pageError = $state(/** @type {string | null} */ (null));
  let submissionError = $state(/** @type {string | null} */ (null));
  let chartExporting = $state('');
  let chartExportError = $state(/** @type {string | null} */ (null));
  let reduceChartMotion = $state(false);

  let participantsData = $state(/** @type {ParticipantPoint[]} */ ([]));
  let submissionsData = $state(/** @type {SubmissionsResponse} */ ({
    data: [],
    end_date: '',
    group_by: 'week',
    start_date: '',
    totals: {}
  }));
  let submissionsByCategory = $state(/** @type {Record<string, SubmissionsResponse>} */ ({}));
  let contributionTypes = $state(/** @type {ContributionType[]} */ ([]));
  let canViewSubmissionAnalytics = $state(false);

  let submissionGroupBy = $state(/** @type {SubmissionGroupBy} */ ('week'));
  let submissionStartDate = $state('');
  let submissionEndDate = $state('');
  let selectedCategory = $state('');
  let selectedContributionType = $state('');
  let appliedSubmissionFilters = $state(/** @type {{ category: string, contributionType: string, endDate: string, groupBy: SubmissionGroupBy, startDate: string }} */ ({
    category: '',
    contributionType: '',
    endDate: '',
    groupBy: 'week',
    startDate: ''
  }));

  let availableCategories = $derived.by(() => getSubmissionCategories());

  let filteredContributionTypes = $derived.by(() => {
    const baseTypes = contributionTypes.filter((type) => type.is_submittable);
    if (!selectedCategory) {
      return baseTypes;
    }

    return baseTypes.filter(
      (type) => getCanonicalCategory(type.category) === getCanonicalCategory(selectedCategory)
    );
  });

  let latestParticipantsSnapshot = $derived(
    participantsData.length > 0
      ? participantsData[participantsData.length - 1]
      : emptyParticipantsSnapshot
  );

  let participantCards = $derived.by(() => [
    {
      key: 'builders',
      category: 'builder',
      label: 'Builders',
      value: latestParticipantsSnapshot.builders,
      textClass: participantPalette.builders.text
    },
    {
      key: 'validators',
      category: 'validator',
      label: 'Validators',
      value: latestParticipantsSnapshot.validators,
      textClass: participantPalette.validators.text
    },
    {
      key: 'community_members',
      category: 'community',
      label: 'Community members',
      value: latestParticipantsSnapshot.community_members,
      textClass: participantPalette.community.text
    },
    {
      key: 'total',
      category: 'genlayer',
      label: 'Unique contributors',
      value: latestParticipantsSnapshot.unique_contributors,
      textClass: participantPalette.total.text
    }
  ]);

  let submissionsSummary = $derived.by(() =>
    buildSubmissionsSummary(submissionsData.totals || {})
  );

  let showSubmissionCategoryBreakdown = $derived(
    !appliedSubmissionFilters.category && !appliedSubmissionFilters.contributionType
  );

  let submissionCategoryBreakdown = $derived.by(() =>
    getSubmissionCategories().map((category) => ({
      category,
      label: getCategoryLabel(category),
      summary: buildSubmissionsSummary(submissionsByCategory[category]?.totals || {})
    }))
  );

  onMount(() => {
    const mainEl = document.querySelector('main');
    mainEl?.classList.add('metrics-scroll-container');
    reduceChartMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches || false;

    fetchMetricsData();

    return () => {
      mainEl?.classList.remove('metrics-scroll-container');
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

      const participantsResponse = await api.get('/metrics/participants-growth/');

      participantsData = participantsResponse.data.data || [];

      let isAuthenticated = $authState.isAuthenticated;
      if (!isAuthenticated) {
        try {
          isAuthenticated = await verifyAuth();
        } catch (err) {
          isAuthenticated = false;
        }
      }

      if (isAuthenticated) {
        let activeUser = /** @type {any} */ ($userStore.user);

        if (!activeUser) {
          try {
            activeUser = await userStore.loadUser();
          } catch (err) {
            // Keep public metrics usable even if the authenticated user payload is unavailable.
          }
        }

        canViewSubmissionAnalytics = Boolean(activeUser?.steward);

        const typesResponse = await api.get('/contribution-types/', { params: { page_size: 1000 } });
        contributionTypes = normalizeContributionTypes(
          typesResponse.data.results || typesResponse.data || []
        );

        if (canViewSubmissionAnalytics) {
          await fetchSubmissionsData({ syncDates: true });
        }
      } else {
        canViewSubmissionAnalytics = false;
      }

      loading = false;
      await tick();
      createCharts();
    } catch (err) {
      pageError = getErrorMessage(err, 'Failed to load metrics data');
      loading = false;
    }
  }

  /**
   * @param {{ category?: string }} [options]
   * @returns {Record<string, string>}
   */
  function buildSubmissionMetricsParams({ category = selectedCategory } = {}) {
    /** @type {Record<string, string>} */
    const params = {
      group_by: submissionGroupBy
    };

    if (submissionStartDate) {
      params.start_date = submissionStartDate;
    }

    if (submissionEndDate) {
      params.end_date = submissionEndDate;
    }

    if (category) {
      params.category = getCanonicalCategory(category);
    }

    if (selectedContributionType) {
      params.contribution_type = selectedContributionType;
    }

    return params;
  }

  async function fetchSubmissionCategorySummaries() {
    if (selectedCategory || selectedContributionType) {
      submissionsByCategory = {};
      return;
    }

    const categories = getSubmissionCategories();
    const responses = await Promise.all(
      categories.map((category) =>
        api.get('/steward-submissions/daily-metrics/', {
          params: buildSubmissionMetricsParams({ category })
        }).then((response) => [category, response.data || { data: [], totals: {} }])
      )
    );

    submissionsByCategory = /** @type {Record<string, SubmissionsResponse>} */ (Object.fromEntries(responses));
  }

  /** @param {{ syncDates?: boolean }} [options] */
  async function fetchSubmissionsData({ syncDates = false } = {}) {
    const params = buildSubmissionMetricsParams();

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

    await fetchSubmissionCategorySummaries();

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
      submissionsLoading = false;
      await tick();
      recreateSubmissionCharts();
    } catch (err) {
      submissionError = getErrorMessage(err, 'Failed to load contribution analytics');
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
      submissionsLoading = false;
      await tick();
      recreateSubmissionCharts();
    } catch (err) {
      submissionError = getErrorMessage(err, 'Failed to reset contribution analytics');
    } finally {
      submissionsLoading = false;
    }
  }

  function onCategoryChange() {
    selectedContributionType = '';
  }

  /**
   * @param {Partial<SubmissionTotals>} [totals]
   * @returns {SubmissionSummary}
   */
  function buildSubmissionsSummary(totals = {}) {
    const ingress = Number(totals.ingress || 0);
    const accepted = Number(totals.accepted || 0);
    const rejected = Number(totals.rejected || 0);
    const moreInfoRequested = Number(totals.more_info_requested || 0);
    const pointsAwarded = Number(totals.points_awarded || 0);
    const reviewed = accepted + rejected + moreInfoRequested;
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
  }

  /**
   * @param {ContributionType[]} types
   * @returns {ContributionType[]}
   */
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

  /**
   * @param {Iterable<string>} categories
   * @returns {string[]}
   */
  function sortCategories(categories) {
    return [...categories].sort((left, right) => {
      const leftIndex = SUBMISSION_CATEGORY_ORDER.indexOf(getCanonicalCategory(left));
      const rightIndex = SUBMISSION_CATEGORY_ORDER.indexOf(getCanonicalCategory(right));

      if (leftIndex !== -1 || rightIndex !== -1) {
        return (leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex) -
          (rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex);
      }

      return getCategoryLabel(left).localeCompare(getCategoryLabel(right));
    });
  }

  function getSubmissionCategories() {
    const typeCategories = new Set(
      contributionTypes
        .map((type) => type.category)
        .filter(Boolean)
    );
    const categories = new Set(SUBMISSION_DEFAULT_CATEGORIES.filter((category) => category !== 'community'));
    const communityCategory = typeCategories.has('community')
      ? 'community'
      : typeCategories.has('creator')
        ? 'creator'
        : 'community';

    categories.add(communityCategory);

    for (const category of typeCategories) {
      if (!COMMUNITY_CATEGORY_SLUGS.includes(category)) {
        categories.add(category);
      }
    }

    return sortCategories(categories);
  }

  /**
   * @param {string | undefined | null} category
   * @returns {string}
   */
  function getCanonicalCategory(category) {
    return category && COMMUNITY_CATEGORY_SLUGS.includes(category) ? 'community' : (category || '');
  }

  /**
   * @param {SubmissionSummary} summary
   * @param {string} metric
   * @returns {number}
   */
  function getMetricValue(summary, metric) {
    if (metric === 'ingress') return summary.ingress;
    if (metric === 'accepted') return summary.accepted;
    if (metric === 'moreInfoRequested') return summary.moreInfoRequested;
    if (metric === 'pendingReview') return summary.pendingReview;
    if (metric === 'reviewed') return summary.reviewed;
    if (metric === 'acceptanceRate') return summary.acceptanceRate;
    if (metric === 'pointsAwarded') return summary.pointsAwarded;
    return 0;
  }

  /**
   * @param {SubmissionSummary} summary
   * @param {string} metric
   */
  function formatMetricValue(summary, metric) {
    const value = getMetricValue(summary, metric);
    return metric === 'acceptanceRate' ? formatPercent(value) : formatNumber(value);
  }

  /**
   * @param {SubmissionSummary} summary
   * @param {string} metric
   */
  function getMetricDetail(summary, metric) {
    if (metric === 'ingress') {
      return 'Contributions submitted in the selected range.';
    }

    if (metric === 'accepted') {
      return 'Accepted contributions in the selected range.';
    }

    if (metric === 'moreInfoRequested') {
      return 'Contributions sent back for more info.';
    }

    if (metric === 'reviewed') {
      return 'All reviewed outcomes combined.';
    }

    if (metric === 'pendingReview') {
      return 'Pending contributions still awaiting a decision.';
    }

    if (metric === 'acceptanceRate') {
      return `${formatNumber(summary.accepted)} accepted of ${formatNumber(summary.reviewed)} reviewed.`;
    }

    if (metric === 'pointsAwarded') {
      return `Avg. ${formatNumber(summary.avgPointsPerAccepted)} per accepted.`;
    }

    return '';
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
    const participantsCanvas = /** @type {HTMLCanvasElement | null} */ (document.getElementById('participantsChart'));

    if (!participantsCanvas || participantsData.length === 0) {
      return;
    }

    const ctx = participantsCanvas.getContext('2d');
    if (!ctx) {
      return;
    }
    const height = participantsCanvas.parentElement?.clientHeight || 360;

    participantsChart = new Chart(ctx, buildParticipantsChartConfig(ctx, height));
  }

  function createSubmissionsChart() {
    const submissionsCanvas = /** @type {HTMLCanvasElement | null} */ (document.getElementById('submissionsChart'));

    if (!submissionsCanvas || !submissionsData.data?.length) {
      return;
    }

    const ctx = submissionsCanvas.getContext('2d');
    if (!ctx) {
      return;
    }

    submissionsChart = new Chart(ctx, buildSubmissionsChartConfig());
  }

  function createSubmissionsTrendChart() {
    const trendCanvas = /** @type {HTMLCanvasElement | null} */ (document.getElementById('submissionsTrendChart'));

    if (!trendCanvas || !submissionsData.data?.length) {
      return;
    }

    const ctx = trendCanvas.getContext('2d');
    if (!ctx) {
      return;
    }

    submissionsTrendChart = new Chart(ctx, buildSubmissionsTrendChartConfig());
  }

  /**
   * @param {unknown} _event
   * @param {{ datasetIndex?: number }} legendItem
   * @param {{ chart: import('chart.js').Chart }} legend
   */
  function handleLegendClick(_event, legendItem, legend) {
    const index = legendItem.datasetIndex;
    const chart = legend.chart;
    if (index === undefined) {
      return;
    }
    const meta = chart.getDatasetMeta(index);

    /** @type {any} */ (meta).hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
    chart.update();
  }

  /**
   * @param {{ interactive?: boolean, fontSize?: number, padding?: number }} [options]
   * @returns {any}
   */
  function getLegendOptions({ interactive = true, fontSize = 12, padding = 18 } = {}) {
    /** @type {any} */
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

  /**
   * @param {import('chart.js').Chart | null} chart
   * @returns {Set<string>}
   */
  function getHiddenDatasetLabels(chart) {
    if (!chart) {
      return new Set();
    }

    return new Set(
      chart.data.datasets
        .filter((_, index) => !chart.isDatasetVisible(index))
        .map((dataset) => String(dataset.label || ''))
    );
  }

  /**
   * @param {any[]} datasets
   * @param {Set<string>} [hiddenLabels]
   * @returns {any[]}
   */
  function applyHiddenDatasets(datasets, hiddenLabels = new Set()) {
    return datasets.map((dataset) => ({
      ...dataset,
      hidden: hiddenLabels.has(dataset.label)
    }));
  }

  /**
   * @param {string} title
   * @param {string} subtitle
   * @param {boolean} forExport
   * @returns {any}
   */
  function getExportTitleOptions(title, subtitle, forExport) {
    return {
      title: {
        display: forExport,
        text: title,
        align: 'start',
        color: '#101010',
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
        color: '#6b6b6b',
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

  /**
   * @param {boolean} forExport
   * @returns {any}
   */
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

  /**
   * @param {boolean} forExport
   * @param {number} pointCount
   * @returns {any}
   */
  function getLineTraceAnimation(forExport, pointCount) {
    if (forExport || reduceChartMotion) {
      return false;
    }

    const totalDuration = Math.min(1500, Math.max(650, pointCount * 30));
    const delayBetweenPoints = pointCount ? totalDuration / pointCount : 0;
    /** @param {any} ctx */
    const previousY = (ctx) => {
      if (ctx.index === 0) {
        const scale = ctx.chart.scales[ctx.dataset.yAxisID || 'y'];
        return scale?.getPixelForValue(0);
      }

      return ctx.chart
        .getDatasetMeta(ctx.datasetIndex)
        .data[ctx.index - 1]
        ?.getProps(['y'], true)
        .y;
    };

    return {
      x: {
        type: 'number',
        easing: 'easeOutCubic',
        duration: delayBetweenPoints,
        from: NaN,
        /** @param {any} ctx */
        delay(ctx) {
          if (ctx.type !== 'data' || ctx.xStarted) return 0;
          ctx.xStarted = true;
          return ctx.index * delayBetweenPoints;
        }
      },
      y: {
        type: 'number',
        easing: 'easeOutCubic',
        duration: delayBetweenPoints,
        from: previousY,
        /** @param {any} ctx */
        delay(ctx) {
          if (ctx.type !== 'data' || ctx.yStarted) return 0;
          ctx.yStarted = true;
          return ctx.index * delayBetweenPoints;
        }
      }
    };
  }

  /**
   * @param {boolean} forExport
   * @returns {any}
   */
  function getBarAnimation(forExport) {
    if (forExport || reduceChartMotion) {
      return false;
    }

    return {
      duration: 850,
      easing: 'easeOutQuart'
    };
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} height
   * @param {{ forExport?: boolean, hiddenLabels?: Set<string> }} [options]
   * @returns {any}
   */
  function buildParticipantsChartConfig(ctx, height, { forExport = false, hiddenLabels = new Set() } = {}) {
    const exportTitle = getExportTitleOptions(
      'Portal participation growth',
      'Builders, validators, and community members by category scale',
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
            borderCapStyle: 'round',
            borderJoinStyle: 'round',
            borderWidth: forExport ? 4 : 2.75,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.32,
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
            borderCapStyle: 'round',
            borderJoinStyle: 'round',
            borderWidth: forExport ? 4 : 2.75,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.32,
            yAxisID: 'yValidators'
          },
          {
            label: 'Community members',
            data: participantsData.map((point) => point.community_members || 0),
            borderColor: participantPalette.community.border,
            backgroundColor: createGradient(
              ctx,
              height,
              participantPalette.community.fillTop,
              participantPalette.community.fillBottom
            ),
            borderCapStyle: 'round',
            borderJoinStyle: 'round',
            borderWidth: forExport ? 4 : 2.75,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.32,
            yAxisID: 'yCommunity'
          }
        ], hiddenLabels)
      },
      options: {
        animation: getLineTraceAnimation(forExport, participantsData.length),
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
            bodyColor: '#101010',
            borderColor: 'rgba(16, 16, 16, 0.12)',
            borderWidth: 1,
            callbacks: {
              /** @param {any[]} items */
              title: (items) => formatDate(items[0]?.label),
              /** @param {any} context */
              label: (context) => `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            },
            titleColor: '#101010'
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#6b6b6b',
              /** @param {string | number} value */
              callback: function(value) {
                return formatParticipantAxisDate(/** @type {any} */ (this).getLabelForValue(value));
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
            grid: {
              color: 'rgba(16, 16, 16, 0.08)'
            },
            title: {
              display: true,
              text: 'Builders',
              color: participantPalette.builders.border,
              font: { size: forExport ? 18 : 11 }
            },
            ticks: {
              color: participantPalette.builders.border,
              font: { size: forExport ? 18 : 12 },
              /** @param {string | number} value */
              callback: (value) => formatNumber(value)
            }
          },
          yValidators: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            grid: {
              drawOnChartArea: false
            },
            title: {
              display: true,
              text: 'Validators',
              color: participantPalette.validators.border,
              font: { size: forExport ? 18 : 11 }
            },
            ticks: {
              color: participantPalette.validators.border,
              font: { size: forExport ? 18 : 12 },
              maxTicksLimit: 6,
              /** @param {string | number} value */
              callback: (value) => formatNumber(value)
            }
          },
          yCommunity: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            grid: {
              drawOnChartArea: false
            },
            title: {
              display: true,
              text: 'Community',
              color: participantPalette.community.border,
              font: { size: forExport ? 18 : 11 }
            },
            ticks: {
              color: participantPalette.community.border,
              font: { size: forExport ? 18 : 12 },
              maxTicksLimit: 6,
              /** @param {string | number} value */
              callback: (value) => formatNumber(value)
            },
            weight: 2
          }
        }
      },
      plugins: forExport ? [exportBackgroundPlugin] : []
    };
  }

  /**
   * @param {{ forExport?: boolean, groupBy?: SubmissionGroupBy, hiddenLabels?: Set<string> }} [options]
   * @returns {any}
   */
  function buildSubmissionsChartConfig({
    forExport = false,
    groupBy = submissionGroupBy,
    hiddenLabels = new Set()
  } = {}) {
    const exportTitle = getExportTitleOptions(
      'Contribution intake vs reviewed outcomes',
      getSubmissionExportSubtitle(),
      forExport
    );

    return {
      type: 'bar',
      data: {
        labels: submissionsData.data.map((point) => formatPeriodLabel(point.period, groupBy)),
        datasets: applyHiddenDatasets([
          {
            label: 'Submission intake',
            data: submissionsData.data.map((point) => point.ingress),
            backgroundColor: reviewPalette.ingress.bg,
            borderColor: reviewPalette.ingress.border,
            borderRadius: 8,
            borderWidth: 1,
            maxBarThickness: 22,
            stack: 'intake'
          },
          {
            label: 'Accepted',
            data: submissionsData.data.map((point) => point.accepted),
            backgroundColor: reviewPalette.accepted.bg,
            borderColor: reviewPalette.accepted.border,
            borderRadius: 8,
            borderWidth: 1,
            maxBarThickness: 22,
            stack: 'review'
          },
          {
            label: 'More info',
            data: submissionsData.data.map((point) => point.more_info_requested),
            backgroundColor: reviewPalette.moreInfo.bg,
            borderColor: reviewPalette.moreInfo.border,
            borderRadius: 8,
            borderWidth: 1,
            maxBarThickness: 22,
            stack: 'review'
          }
        ], hiddenLabels)
      },
      options: {
        animation: getBarAnimation(forExport),
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
            bodyColor: '#101010',
            borderColor: 'rgba(16, 16, 16, 0.12)',
            borderWidth: 1,
            callbacks: {
              /** @param {any[]} items */
              title: (items) => formatPeriodTooltip(submissionsData.data[items[0]?.dataIndex]?.period, groupBy),
              /** @param {any[]} items */
              footer: (items) => {
                const point = submissionsData.data[items[0]?.dataIndex];
                const reviewed =
                  Number(point?.accepted || 0) +
                  Number(point?.rejected || 0) +
                  Number(point?.more_info_requested || 0);

                return `Reviewed contributions: ${formatNumber(reviewed)}`;
              },
              /** @param {any} context */
              label: (context) => `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            },
            titleColor: '#101010'
          }
        },
        scales: {
          x: {
            stacked: true,
            grid: {
              display: false
            },
            ticks: {
              color: '#6b6b6b',
              font: { size: forExport ? 18 : 12 },
              maxRotation: 0
            }
          },
          y: {
            beginAtZero: true,
            stacked: true,
            grid: {
              color: 'rgba(16, 16, 16, 0.08)'
            },
            ticks: {
              color: '#6b6b6b',
              font: { size: forExport ? 18 : 12 },
              /** @param {string | number} value */
              callback: (value) => formatNumber(value)
            }
          }
        }
      },
      plugins: forExport ? [exportBackgroundPlugin] : []
    };
  }

  /** @returns {{ pending: number, accepted: number, moreInfo: number }[]} */
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
      return { pending, accepted: cumAccepted, moreInfo: cumMoreInfo };
    });
  }

  /**
   * @param {{ forExport?: boolean, groupBy?: SubmissionGroupBy, hiddenLabels?: Set<string> }} [options]
   * @returns {any}
   */
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
      'Contribution state trends',
      getSubmissionExportSubtitle(),
      forExport
    );

    return {
      type: 'line',
      data: {
        labels: submissionsData.data.map((point) => formatPeriodLabel(point.period, groupBy)),
        datasets: applyHiddenDatasets([
          {
            label: 'Pending contributions',
            data: cumData.map((point) => point.pending),
            borderColor: reviewPalette.pending.border,
            backgroundColor: 'rgba(56, 125, 232, 0.08)',
            borderCapStyle: 'round',
            borderJoinStyle: 'round',
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
            backgroundColor: 'rgba(25, 166, 99, 0.06)',
            borderCapStyle: 'round',
            borderJoinStyle: 'round',
            borderWidth: isDaily ? 1.5 : 2.5,
            fill: false,
            pointRadius: dotRadius,
            pointHoverRadius: hoverRadius,
            pointBackgroundColor: reviewPalette.accepted.border,
            tension: 0.3
          },
          {
            label: 'More info',
            data: cumData.map((point) => point.moreInfo),
            borderColor: reviewPalette.moreInfo.border,
            backgroundColor: 'rgba(217, 104, 22, 0.06)',
            borderCapStyle: 'round',
            borderJoinStyle: 'round',
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
        animation: getLineTraceAnimation(forExport, submissionsData.data.length),
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
            bodyColor: '#101010',
            borderColor: 'rgba(16, 16, 16, 0.12)',
            borderWidth: 1,
            callbacks: {
              /** @param {any[]} items */
              title: (items) => formatPeriodTooltip(submissionsData.data[items[0]?.dataIndex]?.period, groupBy),
              /** @param {any} context */
              label: (context) => `${context.dataset.label}: ${formatNumber(context.parsed.y)}`
            },
            titleColor: '#101010'
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#6b6b6b',
              font: { size: forExport ? 18 : 12 },
              maxRotation: 0
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(16, 16, 16, 0.08)'
            },
            ticks: {
              color: '#6b6b6b',
              font: { size: forExport ? 18 : 12 },
              /** @param {string | number} value */
              callback: (value) => formatNumber(value)
            }
          }
        }
      },
      plugins: forExport ? [exportBackgroundPlugin] : []
    };
  }

  /**
   * @param {string | number | undefined | null} typeId
   * @returns {string}
   */
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

  /**
   * @param {string | number | undefined | null} value
   * @returns {string}
   */
  function slugify(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'all';
  }

  /**
   * @param {string} kind
   * @returns {string}
   */
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

  /**
   * @param {HTMLCanvasElement} canvas
   * @param {string} filename
   * @returns {Promise<void>}
   */
  function downloadCanvas(canvas, filename) {
    return new Promise((resolve, reject) => {
      /** @param {Blob | null} blob */
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
        resolve(undefined);
      }, EXPORT_FORMAT);
    });
  }

  /**
   * @param {string} kind
   * @returns {Promise<void>}
   */
  async function exportPortalChart(kind) {
    if (chartExporting) {
      return;
    }

    /** @type {import('chart.js').Chart | null} */
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

      /** @type {any} */
      let config;
      let filename = '';

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
      await new Promise((resolve) => requestAnimationFrame(() => resolve(undefined)));
      await downloadCanvas(exportCanvas, filename);
    } catch (err) {
      chartExportError = getErrorMessage(err, 'Failed to export chart');
    } finally {
      if (exportChart) {
        exportChart.destroy();
      }
      chartExporting = '';
    }
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} height
   * @param {string} topColor
   * @param {string} bottomColor
   * @returns {CanvasGradient}
   */
  function createGradient(ctx, height, topColor, bottomColor) {
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, topColor);
    gradient.addColorStop(1, bottomColor);
    return gradient;
  }

  /**
   * @param {string} dateStr
   * @returns {string}
   */
  function formatParticipantAxisDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short'
    });
  }

  /**
   * @param {string} dateStr
   * @param {SubmissionGroupBy | string} groupBy
   * @returns {string}
   */
  function formatPeriodLabel(dateStr, groupBy) {
    const date = new Date(dateStr);

    if (groupBy === 'month') {
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    }

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  /**
   * @param {string | undefined} dateStr
   * @param {SubmissionGroupBy | string} groupBy
   * @returns {string}
   */
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
      return `Week of ${startStr} - ${endStr}`;
    }

    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  /**
   * @param {string | undefined | null} slug
   * @returns {string}
   */
  function getCategoryLabel(slug) {
    if (!slug) {
      return 'Unknown';
    }

    return CATEGORY_LABELS[slug] || slug[0].toUpperCase() + slug.slice(1);
  }

  /**
   * @param {SubmissionGroupBy | string} groupBy
   * @returns {string}
   */
  function getGroupingLabel(groupBy) {
    if (groupBy === 'day') {
      return 'Daily';
    }

    if (groupBy === 'month') {
      return 'Monthly';
    }

    return 'Weekly';
  }

  /**
   * @param {string | undefined | null} dateStr
   * @returns {string}
   */
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

  /**
   * @param {string | number | undefined | null} value
   * @returns {string}
   */
  function formatNumber(value) {
    return Number(value || 0).toLocaleString('en-US');
  }

  /**
   * @param {string | number | undefined | null} value
   * @returns {string}
   */
  function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
  }

  /**
   * @param {unknown} err
   * @param {string} fallback
   * @returns {string}
   */
  function getErrorMessage(err, fallback) {
    return err instanceof Error ? err.message : fallback;
  }
</script>

<div class="metrics-view">
  <div class="metrics-gradient-band" aria-hidden="true">
    <div class="metrics-gradient-rainbow"></div>
    <div class="metrics-gradient-wash"></div>
  </div>

  <div class="metrics-shell">
    <header class="metrics-header">
      <div class="metrics-header-copy">
        <div class="metrics-title-row">
          <div class="metrics-header-icon">
            <CategoryIcon category="genlayer" mode="hexagon" size={48} />
          </div>
          <h1>Portal metrics</h1>
        </div>
        <p class="metrics-subtitle">
          Participation growth and contribution flow across builders, validators, and community.
        </p>
      </div>
    </header>

    {#if pageError}
      <div class="mb-5 rounded-[8px] border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700 shadow-sm">
        <span class="font-semibold">Error:</span> {pageError}
      </div>
    {/if}

    {#if chartExportError}
      <div class="mb-5 rounded-[8px] border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700 shadow-sm">
        <span class="font-semibold">Export error:</span> {chartExportError}
      </div>
    {/if}

    {#snippet exportButton(kind = 'participants', label = '', disabled = false)}
      <button
        type="button"
        title={label}
        aria-label={label}
        onclick={() => exportPortalChart(kind)}
        disabled={disabled || Boolean(chartExporting)}
        class="export-button"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5"/>
          <path d="M4 13.5V16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2.5"/>
        </svg>
        <span class="sr-only">{chartExporting === kind ? `Exporting ${label}` : label}</span>
      </button>
    {/snippet}

    {#snippet submissionMetricCard(title = '', metric = '', surface = '', textClass = '')}
      <div class="summary-card bg-gradient-to-br {surface}">
        <p class="summary-label">{title}</p>

        {#if showSubmissionCategoryBreakdown}
          <div class="mt-4 space-y-2">
            {#each submissionCategoryBreakdown as item (item.category)}
              <div class="summary-breakdown-row">
                <div class="flex min-w-0 items-center gap-2.5">
                  <CategoryIcon category={getCanonicalCategory(item.category)} mode="hexagon" size={24} light={true} />
                  <span class="truncate text-sm font-medium text-[#565656]">{item.label}</span>
                </div>
                <span class="shrink-0 text-lg font-semibold tabular-nums {textClass}">
                  {formatMetricValue(item.summary, metric)}
                </span>
              </div>
            {/each}
          </div>
        {:else}
          <p class="mt-3 text-3xl font-semibold tabular-nums {textClass}">
            {formatMetricValue(submissionsSummary, metric)}
          </p>
          <p class="mt-2 text-xs leading-5 text-[#6b6b6b]">
            {getMetricDetail(submissionsSummary, metric)}
          </p>
        {/if}
      </div>
    {/snippet}

    <section class="portal-section">
      <div class="section-heading">
        <div>
          <h2>Portal contributors</h2>
        </div>
        {#if latestParticipantsSnapshot.date}
          <p class="section-meta">Updated {formatDate(latestParticipantsSnapshot.date)}</p>
        {/if}
      </div>

      <div class="stat-grid">
        {#if loading}
          {#each [0, 1, 2, 3] as _, i (i)}
            <div class="stat-card skeleton-shimmer" aria-hidden="true"></div>
          {/each}
        {:else}
          {#each participantCards as card (card.key)}
            <div class="stat-card" data-category={card.category}>
              <div class="stat-card-main">
                <CategoryIcon category={card.category} mode="hexagon" size={48} />
                <div class="min-w-0">
                  <p class="stat-value tabular-nums {card.textClass}">{formatNumber(card.value)}</p>
                  <p class="stat-label">{card.label}</p>
                </div>
              </div>
            </div>
          {/each}
        {/if}
      </div>

      <div class="chart-card mt-5">
        <div class="chart-heading">
          <div>
            <h3>Growth trajectory</h3>
            <p>Daily cumulative contributors by Portal category.</p>
          </div>
          {@render exportButton('participants', 'Export growth trajectory as 16:9 PNG', loading || participantsData.length === 0)}
        </div>

        {#if loading}
          <div class="chart-placeholder chart-placeholder--large skeleton-shimmer"></div>
        {:else if participantsData.length > 0}
          <div class="chart-canvas chart-canvas--large">
            <canvas id="participantsChart"></canvas>
          </div>
        {:else}
          <div class="chart-empty">No participant growth data available.</div>
        {/if}
      </div>
    </section>

    {#if canViewSubmissionAnalytics}
      <section class="portal-section">
        <div class="section-heading">
          <div>
            <h2>Portal contributions</h2>
          </div>

          {#if submissionsLoading}
            <div class="refresh-pill">Refreshing analytics...</div>
          {/if}
        </div>

        <div class="filter-panel">
          <div class="filter-grid">
            <div>
              <label for="submission-start-date" class="filter-label">Start date</label>
              <input
                id="submission-start-date"
                type="date"
                bind:value={submissionStartDate}
                class="filter-control"
              />
            </div>

            <div>
              <label for="submission-end-date" class="filter-label">End date</label>
              <input
                id="submission-end-date"
                type="date"
                bind:value={submissionEndDate}
                class="filter-control"
              />
            </div>

            <div>
              <label for="submission-category" class="filter-label">Category</label>
              <select
                id="submission-category"
                bind:value={selectedCategory}
                onchange={onCategoryChange}
                class="filter-control"
              >
                <option value="">All categories</option>
                {#each availableCategories as category}
                  <option value={category}>{getCategoryLabel(category)}</option>
                {/each}
              </select>
            </div>

            <div>
              <label for="submission-type" class="filter-label">Contribution type</label>
              <select
                id="submission-type"
                bind:value={selectedContributionType}
                class="filter-control"
              >
                <option value="">All contribution types</option>
                {#each filteredContributionTypes as type}
                  <option value={type.id}>{type.name}</option>
                {/each}
              </select>
            </div>

            <div>
              <label for="submission-group-by" class="filter-label">Group by</label>
              <select
                id="submission-group-by"
                bind:value={submissionGroupBy}
                class="filter-control"
              >
                <option value="day">Daily</option>
                <option value="week">Weekly</option>
                <option value="month">Monthly</option>
              </select>
            </div>

            <div class="filter-actions">
              <button
                type="button"
                onclick={applySubmissionFilters}
                disabled={submissionsLoading}
                class="primary-action"
              >
                Apply filters
              </button>
              <button
                type="button"
                onclick={clearSubmissionFilters}
                disabled={submissionsLoading}
                class="secondary-action"
              >
                Reset
              </button>
            </div>
          </div>

          {#if submissionError}
            <div class="mt-4 rounded-[8px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <span class="font-semibold">Contribution analytics error:</span> {submissionError}
            </div>
          {/if}
        </div>

        <div class="summary-grid">
          {#if loading || submissionsLoading}
            {#each [0, 1, 2, 3] as _, i (i)}
              <div class="summary-card skeleton-shimmer" aria-hidden="true"></div>
            {/each}
          {:else}
            {@render submissionMetricCard('Pending contributions', 'pendingReview', reviewPalette.pending.surface, reviewPalette.pending.text)}
            {@render submissionMetricCard('Accepted', 'accepted', reviewPalette.accepted.surface, reviewPalette.accepted.text)}
            {@render submissionMetricCard('More info', 'moreInfoRequested', reviewPalette.moreInfo.surface, reviewPalette.moreInfo.text)}
            {@render submissionMetricCard('Submission intake', 'ingress', reviewPalette.ingress.surface, reviewPalette.ingress.text)}
          {/if}
        </div>

        <div class="chart-grid">
          <div class="chart-card">
            <div class="chart-heading">
              <div>
                <h3>Contribution intake vs reviewed outcomes</h3>
                <p>Each period compares newly submitted contributions against decisions made in that same period.</p>
              </div>
              {@render exportButton('submissions', 'Export contribution intake chart as 16:9 PNG', loading || submissionsLoading || !submissionsData.data?.length)}
            </div>

            {#if loading || submissionsLoading}
              <div class="chart-placeholder skeleton-shimmer"></div>
            {:else if submissionsData.data?.length > 0}
              <div class="chart-canvas">
                <canvas id="submissionsChart"></canvas>
              </div>
            {:else}
              <div class="chart-empty">No contributions matched the selected filters.</div>
            {/if}
          </div>

          <div class="chart-card">
            <div class="chart-heading">
              <div>
                <h3>Contribution state trends</h3>
                <p>Pending, accepted, and more-info curves over time.</p>
              </div>
              {@render exportButton('submission-trends', 'Export contribution state trends as 16:9 PNG', loading || submissionsLoading || !submissionsData.data?.length)}
            </div>

            {#if loading || submissionsLoading}
              <div class="chart-placeholder skeleton-shimmer"></div>
            {:else if submissionsData.data?.length > 0}
              <div class="chart-canvas">
                <canvas id="submissionsTrendChart"></canvas>
              </div>
            {:else}
              <div class="chart-empty">No reviewed contributions are available for this selection.</div>
            {/if}
          </div>
        </div>
      </section>
    {/if}
  </div>
</div>

<style>
  :global(main.metrics-scroll-container) {
    overflow-x: hidden;
    overscroll-behavior: contain;
  }

  .metrics-view {
    background-color: #fff;
    background-image:
      linear-gradient(180deg, rgba(248, 249, 252, 0.64) 0%, #fff 28rem),
      radial-gradient(circle at 12% 0%, rgba(127, 82, 225, 0.055), transparent 26rem),
      radial-gradient(circle at 88% 8%, rgba(238, 133, 33, 0.045), transparent 24rem);
    background-position: center top, left top, right top;
    background-repeat: no-repeat;
    background-size: 100% 36rem, 42rem 30rem, 40rem 28rem;
    margin: -12px;
    min-height: 100%;
    overflow: hidden;
    padding: 28px 12px 52px;
    position: relative;
    -webkit-font-smoothing: antialiased;
  }

  .metrics-gradient-band {
    height: 430px;
    inset: -150px 0 auto;
    overflow: hidden;
    pointer-events: none;
    position: absolute;
    -webkit-mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.6) 0%, #000 28%, transparent 100%);
    mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.6) 0%, #000 28%, transparent 100%);
  }

  .metrics-gradient-rainbow {
    background: url('/assets/illustrations/welcome-gradient.png') center top / 1420px auto no-repeat;
    inset: 0;
    opacity: 0.38;
    position: absolute;
  }

  .metrics-gradient-wash {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.42), rgba(255, 255, 255, 0.82));
    inset: 0;
    position: absolute;
  }

  .metrics-shell {
    margin: 0 auto;
    max-width: 1480px;
    padding: 0 clamp(4px, 1.4vw, 18px);
    position: relative;
    z-index: 1;
  }

  .metrics-header {
    display: grid;
    justify-items: start;
    margin-bottom: 28px;
    padding-top: 2px;
    text-align: left;
  }

  .metrics-header-copy {
    max-width: 760px;
  }

  .metrics-title-row {
    align-items: center;
    display: flex;
    gap: 13px;
    justify-content: flex-start;
  }

  .metrics-header-icon {
    display: flex;
    flex: 0 0 auto;
  }

  h1,
  h2,
  h3,
  p {
    margin: 0;
  }

  h1 {
    color: #101010;
    font-family: var(--font-display, inherit);
    font-size: clamp(34px, 4.6vw, 58px);
    font-weight: 600;
    letter-spacing: 0;
    line-height: 0.95;
    text-wrap: balance;
  }

  .metrics-subtitle {
    color: #3f4b5f;
    font-size: 15px;
    line-height: 1.55;
    letter-spacing: 0.2px;
    margin: 10px 0 0;
    max-width: 700px;
    text-wrap: pretty;
  }

  .portal-section {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #ececf0;
    border-radius: 8px;
    box-shadow: 0 18px 48px rgba(31, 42, 68, 0.06);
    padding: clamp(18px, 2.2vw, 28px);
  }

  .portal-section + .portal-section {
    margin-top: 20px;
  }

  .section-heading {
    align-items: flex-start;
    display: flex;
    gap: 16px;
    justify-content: space-between;
    margin-bottom: 18px;
  }

  .section-heading h2 {
    color: #101010;
    font-family: var(--font-display, inherit);
    font-size: clamp(24px, 2.4vw, 34px);
    font-weight: 600;
    letter-spacing: 0;
    line-height: 1.08;
    text-wrap: balance;
  }

  .section-meta {
    color: #6b6b6b;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.4;
    max-width: 360px;
    text-align: right;
  }

  .stat-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  .stat-card {
    align-items: center;
    background: #fbfbfc;
    border: 1px solid #eeeeef;
    border-radius: 8px;
    display: grid;
    justify-items: start;
    min-height: 104px;
    overflow: hidden;
    padding: 16px;
    position: relative;
  }

  .stat-card::before {
    content: '';
    inset: 0;
    opacity: 0.9;
    pointer-events: none;
    position: absolute;
  }

  .stat-card > * {
    position: relative;
    z-index: 1;
  }

  .stat-card[data-category='builder'] {
    border-color: rgba(238, 133, 33, 0.2);
  }

  .stat-card[data-category='builder']::before {
    background: linear-gradient(135deg, rgba(238, 133, 33, 0.11), rgba(255, 209, 163, 0.04) 58%, transparent);
  }

  .stat-card[data-category='validator'] {
    border-color: rgba(56, 125, 232, 0.2);
  }

  .stat-card[data-category='validator']::before {
    background: linear-gradient(135deg, rgba(56, 125, 232, 0.11), rgba(184, 199, 255, 0.05) 58%, transparent);
  }

  .stat-card[data-category='community'] {
    border-color: rgba(127, 82, 225, 0.2);
  }

  .stat-card[data-category='community']::before {
    background: linear-gradient(135deg, rgba(127, 82, 225, 0.11), rgba(214, 195, 255, 0.05) 58%, transparent);
  }

  .stat-card[data-category='genlayer'] {
    background:
      linear-gradient(110deg, rgba(255, 255, 255, 0.93), rgba(255, 255, 255, 0.78)),
      url('/assets/illustrations/welcome-gradient.png') center / cover;
    border-color: rgba(127, 82, 225, 0.2);
  }

  .stat-card[data-category='genlayer']::before {
    background: linear-gradient(135deg, rgba(127, 82, 225, 0.08), rgba(238, 133, 33, 0.06) 46%, rgba(56, 125, 232, 0.06));
  }

  .stat-card-main {
    align-items: center;
    display: flex;
    gap: 14px;
    justify-content: flex-start;
    min-width: 0;
    width: 100%;
  }

  .stat-value {
    font-family: var(--font-display, inherit);
    font-size: 34px;
    font-weight: 600;
    letter-spacing: 0;
    line-height: 1;
  }

  .stat-label {
    color: #4d4d4d;
    font-size: 13px;
    font-weight: 600;
    line-height: 1.2;
    margin-top: 4px;
  }

  .chart-card,
  .filter-panel,
  .summary-card {
    background: #fbfbfc;
    border: 1px solid #eeeeef;
    border-radius: 8px;
  }

  .chart-card {
    padding: clamp(16px, 1.8vw, 22px);
  }

  .chart-heading {
    align-items: flex-start;
    display: flex;
    gap: 14px;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .chart-heading h3 {
    color: #101010;
    font-size: 18px;
    font-weight: 650;
    line-height: 1.2;
    text-wrap: balance;
  }

  .chart-heading p {
    color: #6b6b6b;
    font-size: 13px;
    line-height: 1.45;
    margin-top: 5px;
    max-width: 560px;
    text-wrap: pretty;
  }

  .chart-canvas {
    height: 320px;
  }

  .chart-canvas--large {
    height: 380px;
  }

  .chart-placeholder--large {
    height: 380px;
  }

  .chart-placeholder,
  .chart-empty {
    border: 1px solid #eeeeef;
    border-radius: 8px;
    height: 320px;
  }

  .chart-empty {
    align-items: center;
    background: #fff;
    border-style: dashed;
    color: #6b6b6b;
    display: flex;
    font-size: 14px;
    justify-content: center;
  }

  .chart-canvas--large + .chart-empty {
    height: 380px;
  }

  .export-button {
    align-items: center;
    background: #fff;
    border: 1px solid #eeeeef;
    border-radius: 8px;
    color: #6b6b6b;
    display: inline-flex;
    flex: 0 0 auto;
    height: 40px;
    justify-content: center;
    transition-duration: 160ms;
    transition-property: background-color, border-color, color, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    width: 40px;
  }

  .export-button:hover {
    border-color: #d7d7dc;
    color: #101010;
  }

  .export-button:active {
    transform: scale(0.96);
  }

  .export-button:disabled {
    cursor: not-allowed;
    opacity: 0.45;
    transform: none;
  }

  .filter-panel {
    margin-bottom: 18px;
    padding: 16px;
  }

  .filter-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  .filter-label {
    color: #565656;
    display: block;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .filter-control {
    background: #fff;
    border: 1px solid #dfdfe4;
    border-radius: 8px;
    color: #101010;
    font-size: 14px;
    height: 42px;
    outline: none;
    padding: 0 12px;
    transition-duration: 160ms;
    transition-property: border-color, box-shadow;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
    width: 100%;
  }

  .filter-control:focus {
    border-color: #8d81e1;
    box-shadow: 0 0 0 3px rgba(141, 129, 225, 0.18);
  }

  .filter-actions {
    align-items: end;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .primary-action,
  .secondary-action {
    border-radius: 8px;
    font-size: 14px;
    font-weight: 650;
    height: 42px;
    padding: 0 16px;
    transition-duration: 160ms;
    transition-property: background-color, border-color, color, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .primary-action {
    background: #101010;
    color: #fff;
  }

  .primary-action:hover {
    background: #2a2a2a;
  }

  .secondary-action {
    background: #fff;
    border: 1px solid #dfdfe4;
    color: #565656;
  }

  .secondary-action:hover {
    border-color: #cfcfd5;
    color: #101010;
  }

  .primary-action:active,
  .secondary-action:active {
    transform: scale(0.96);
  }

  .primary-action:disabled,
  .secondary-action:disabled {
    cursor: not-allowed;
    opacity: 0.55;
    transform: none;
  }

  .refresh-pill {
    background: #fff;
    border: 1px solid #eeeeef;
    border-radius: 999px;
    color: #565656;
    font-size: 13px;
    font-weight: 600;
    padding: 9px 13px;
  }

  .summary-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(1, minmax(0, 1fr));
    margin-bottom: 22px;
  }

  .summary-card {
    min-height: 132px;
    padding: 16px;
  }

  .summary-label {
    color: #565656;
    font-size: 13px;
    font-weight: 650;
  }

  .summary-breakdown-row {
    align-items: center;
    background: rgba(255, 255, 255, 0.76);
    border: 1px solid rgba(255, 255, 255, 0.88);
    border-radius: 8px;
    display: flex;
    gap: 12px;
    justify-content: space-between;
    min-height: 44px;
    padding: 8px 10px;
    box-shadow: 0 1px 0 rgba(16, 16, 16, 0.04);
  }

  .chart-grid {
    display: grid;
    gap: 16px;
    grid-template-columns: minmax(0, 1fr);
  }

  .skeleton-shimmer {
    animation: metrics-shimmer 1.4s ease-in-out infinite;
    background: linear-gradient(90deg, #f0f1f4 0%, #fafafb 48%, #f0f1f4 100%);
    background-size: 220% 100%;
  }

  .tabular-nums {
    font-variant-numeric: tabular-nums;
  }

  @keyframes metrics-shimmer {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }

  @media (min-width: 640px) {
    .stat-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .summary-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (min-width: 1024px) {
    .stat-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .filter-grid {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 190px minmax(220px, 1fr) 150px auto;
    }

    .summary-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }

  @media (min-width: 1280px) {
    .chart-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .section-heading,
    .chart-heading {
      align-items: stretch;
      flex-direction: column;
    }

    .section-meta {
      max-width: none;
      text-align: left;
    }

    .chart-canvas,
    .chart-canvas--large,
    .chart-placeholder,
    .chart-empty {
      height: 300px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton-shimmer {
      animation: none;
    }

    .export-button,
    .filter-control,
    .primary-action,
    .secondary-action {
      transition-duration: 0ms;
    }
  }
</style>
