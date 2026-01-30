<script>
  import { onMount, onDestroy } from 'svelte';
  import { Chart, registerables } from 'chart.js';
  import api from '../lib/api.js';

  Chart.register(...registerables);

  let participantsChart;
  let submissionsChart;
  let cumulativeChart;
  let loading = $state(true);
  let error = $state(null);

  let participantsData = $state([]);
  let submissionsData = $state({ data: [], totals: {}, group_by: 'week' });

  // Filters
  let groupBy = $state('week');
  let startDate = $state('');
  let endDate = $state('');

  onMount(async () => {
    await fetchMetricsData();
    if (!error) {
      setTimeout(() => {
        createCharts();
      }, 0);
    }

    return () => {
      if (participantsChart) participantsChart.destroy();
      if (submissionsChart) submissionsChart.destroy();
      if (cumulativeChart) cumulativeChart.destroy();
    };
  });

  async function fetchMetricsData() {
    try {
      loading = true;

      const participantsResponse = await api.get('/metrics/participants-growth/');
      participantsData = participantsResponse.data.data || [];

      await fetchSubmissionsData();

      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load metrics data';
      loading = false;
    }
  }

  async function fetchSubmissionsData() {
    let url = `/steward-submissions/daily-metrics/?group_by=${groupBy}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    const submissionsResponse = await api.get(url);
    submissionsData = submissionsResponse.data || { data: [], totals: {} };

    // Set date inputs from response if not already set
    if (!startDate && submissionsData.start_date) {
      startDate = submissionsData.start_date;
    }
    if (!endDate && submissionsData.end_date) {
      endDate = submissionsData.end_date;
    }
  }

  async function applyFilters() {
    await fetchSubmissionsData();
    recreateAllCharts();
  }

  function recreateAllCharts() {
    if (participantsChart) participantsChart.destroy();
    if (submissionsChart) submissionsChart.destroy();
    if (cumulativeChart) cumulativeChart.destroy();
    createCharts();
  }

  function createCharts() {
    createParticipantsChart();
    createSubmissionsChart();
    createCumulativeChart();
  }

  function createParticipantsChart() {
    const participantsCanvas = document.getElementById('participantsChart');
    if (participantsCanvas && participantsData.length > 0) {
      const participantsCtx = participantsCanvas.getContext('2d');
      participantsChart = new Chart(participantsCtx, {
        type: 'line',
        data: {
          labels: participantsData.map(d => new Date(d.date).toLocaleDateString()),
          datasets: [
            {
              label: 'Validators',
              data: participantsData.map(d => d.validators),
              borderColor: 'rgb(2, 132, 199)',      // sky-600
              backgroundColor: 'rgba(2, 132, 199, 0.1)',
              tension: 0.2,
              fill: true
            },
            {
              label: 'Waitlist',
              data: participantsData.map(d => d.waitlist),
              borderColor: 'rgb(125, 211, 252)',    // sky-300
              backgroundColor: 'rgba(125, 211, 252, 0.1)',
              tension: 0.2,
              fill: true
            },
            {
              label: 'Builders',
              data: participantsData.map(d => d.builders),
              borderColor: 'rgb(234, 88, 12)',      // orange-600
              backgroundColor: 'rgba(234, 88, 12, 0.1)',
              tension: 0.2,
              fill: true
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
            title: { display: true, text: 'Participants Growth Over Time' }
          },
          scales: {
            y: { beginAtZero: true }
          }
        }
      });
    }
  }

  function formatPeriodLabel(dateStr, groupBy) {
    const date = new Date(dateStr);
    if (groupBy === 'month') {
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    } else if (groupBy === 'week') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
    return date.toLocaleDateString();
  }

  function createSubmissionsChart() {
    const submissionsCanvas = document.getElementById('submissionsChart');
    if (submissionsCanvas && submissionsData.data && submissionsData.data.length > 0) {
      const submissionsCtx = submissionsCanvas.getContext('2d');
      const groupLabel = groupBy === 'day' ? 'Daily' : groupBy === 'week' ? 'Weekly' : 'Monthly';

      submissionsChart = new Chart(submissionsCtx, {
        type: 'bar',
        data: {
          labels: submissionsData.data.map(d => formatPeriodLabel(d.period, groupBy)),
          datasets: [
            {
              label: 'New Submissions',
              data: submissionsData.data.map(d => d.ingress),
              backgroundColor: 'rgba(99, 102, 241, 0.7)',
              borderColor: 'rgb(99, 102, 241)',
              borderWidth: 1
            },
            {
              label: 'Accepted',
              data: submissionsData.data.map(d => d.accepted),
              backgroundColor: 'rgba(16, 185, 129, 0.7)',
              borderColor: 'rgb(16, 185, 129)',
              borderWidth: 1
            },
            {
              label: 'Rejected',
              data: submissionsData.data.map(d => d.rejected),
              backgroundColor: 'rgba(239, 68, 68, 0.7)',
              borderColor: 'rgb(239, 68, 68)',
              borderWidth: 1
            },
            {
              label: 'More Info Requested',
              data: submissionsData.data.map(d => d.more_info_requested),
              backgroundColor: 'rgba(245, 158, 11, 0.7)',
              borderColor: 'rgb(245, 158, 11)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
            title: { display: true, text: `${groupLabel} Submissions Flow` }
          },
          scales: {
            x: { stacked: false },
            y: { beginAtZero: true, stacked: false }
          }
        }
      });
    }
  }

  function createCumulativeChart() {
    const cumulativeCanvas = document.getElementById('cumulativeChart');
    if (cumulativeCanvas && submissionsData.data && submissionsData.data.length > 0) {
      const cumulativeCtx = cumulativeCanvas.getContext('2d');

      // Calculate cumulative values
      let cumAccepted = 0;
      let cumRejected = 0;
      let cumPending = 0;
      let cumMoreInfo = 0;

      const cumulativeAccepted = [];
      const cumulativeRejected = [];
      const queueDepth = [];
      const moreInfoQueue = [];

      for (const d of submissionsData.data) {
        cumAccepted += d.accepted;
        cumRejected += d.rejected;
        cumMoreInfo += d.more_info_requested;
        cumPending += d.ingress - d.accepted - d.rejected;

        cumulativeAccepted.push(cumAccepted);
        cumulativeRejected.push(cumRejected);
        queueDepth.push(Math.max(0, cumPending));
        moreInfoQueue.push(cumMoreInfo);
      }

      cumulativeChart = new Chart(cumulativeCtx, {
        type: 'line',
        data: {
          labels: submissionsData.data.map(d => formatPeriodLabel(d.period, groupBy)),
          datasets: [
            {
              label: 'Cumulative Accepted',
              data: cumulativeAccepted,
              borderColor: 'rgb(16, 185, 129)',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: true,
              tension: 0.2
            },
            {
              label: 'Cumulative Rejected',
              data: cumulativeRejected,
              borderColor: 'rgb(239, 68, 68)',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              fill: true,
              tension: 0.2
            },
            {
              label: 'Pending Queue',
              data: queueDepth,
              borderColor: 'rgb(99, 102, 241)',
              backgroundColor: 'rgba(99, 102, 241, 0.1)',
              fill: true,
              tension: 0.2
            },
            {
              label: 'Awaiting More Info',
              data: moreInfoQueue,
              borderColor: 'rgb(245, 158, 11)',
              backgroundColor: 'rgba(245, 158, 11, 0.1)',
              fill: true,
              tension: 0.2
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
            title: { display: true, text: 'Cumulative Totals & Queue Depth' }
          },
          scales: {
            y: { beginAtZero: true }
          }
        }
      });
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold mb-6">Metrics Dashboard</h1>

  {#if loading}
    <div class="flex justify-center items-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-500"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
      <strong class="font-bold">Error!</strong>
      <span class="block sm:inline"> {error}</span>
    </div>
  {:else}
    <!-- Filters - Page Wide at Top -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="flex flex-wrap items-end gap-4">
        <div class="flex-1 min-w-[150px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
          <input
            type="date"
            bind:value={startDate}
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>
        <div class="flex-1 min-w-[150px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">End Date</label>
          <input
            type="date"
            bind:value={endDate}
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>
        <div class="flex-1 min-w-[120px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">Group By</label>
          <select
            bind:value={groupBy}
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </select>
        </div>
        <div>
          <button
            onclick={applyFilters}
            class="px-4 py-2 bg-sky-600 text-white rounded-md text-sm hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>

    <!-- Participants Growth Section -->
    <div class="bg-white rounded-lg shadow p-6 mb-6">
      <h2 class="text-xl font-semibold mb-4">Participants Growth</h2>
      <div class="h-72">
        <canvas id="participantsChart"></canvas>
      </div>
    </div>

    <!-- Participants Summary Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">Validators</h3>
        <p class="text-2xl font-bold text-sky-600 mt-1">
          {participantsData.length > 0 ? participantsData[participantsData.length - 1].validators : 0}
        </p>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">Waitlist</h3>
        <p class="text-2xl font-bold text-sky-300 mt-1">
          {participantsData.length > 0 ? participantsData[participantsData.length - 1].waitlist : 0}
        </p>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">Builders</h3>
        <p class="text-2xl font-bold text-orange-600 mt-1">
          {participantsData.length > 0 ? participantsData[participantsData.length - 1].builders : 0}
        </p>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">Total Participants</h3>
        <p class="text-2xl font-bold text-gray-900 mt-1">
          {participantsData.length > 0 ? participantsData[participantsData.length - 1].total : 0}
        </p>
      </div>
    </div>

    <!-- Submissions Section -->
    <h2 class="text-xl font-semibold mb-4">Submissions Analytics</h2>

    <!-- Submissions Summary Stats -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">New Submissions</h3>
        <p class="text-2xl font-bold text-indigo-600 mt-1">
          {submissionsData.totals?.ingress || 0}
        </p>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">Accepted</h3>
        <p class="text-2xl font-bold text-green-600 mt-1">
          {submissionsData.totals?.accepted || 0}
        </p>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">Rejected</h3>
        <p class="text-2xl font-bold text-red-600 mt-1">
          {submissionsData.totals?.rejected || 0}
        </p>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">More Info Requested</h3>
        <p class="text-2xl font-bold text-amber-600 mt-1">
          {submissionsData.totals?.more_info_requested || 0}
        </p>
      </div>
      <div class="bg-white rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-500">Points Awarded</h3>
        <p class="text-2xl font-bold text-purple-600 mt-1">
          {(submissionsData.totals?.points_awarded || 0).toLocaleString()}
        </p>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Submissions Flow Chart -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold mb-4">Submissions Flow</h3>
        <div class="h-80">
          <canvas id="submissionsChart"></canvas>
        </div>
      </div>

      <!-- Cumulative Chart -->
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold mb-4">Cumulative Totals & Queue</h3>
        <div class="h-80">
          <canvas id="cumulativeChart"></canvas>
        </div>
      </div>
    </div>
  {/if}
</div>
