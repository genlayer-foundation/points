<script>
  import { onMount, onDestroy } from 'svelte';
  import { Chart, registerables } from 'chart.js';
  import api from '../lib/api.js';
  
  Chart.register(...registerables);
  
  let activeValidatorsChart;
  let contributionTypesChart;
  let loading = $state(true);
  let error = $state(null);
  
  let activeValidatorsData = $state([]);
  let contributionTypesData = $state([]);
  
  onMount(async () => {
    await fetchMetricsData();
    if (!error) {
      // Use nextTick to ensure DOM is ready
      setTimeout(() => {
        createCharts();
      }, 0);
    }
    
    return () => {
      // Cleanup charts on unmount
      if (activeValidatorsChart) activeValidatorsChart.destroy();
      if (contributionTypesChart) contributionTypesChart.destroy();
    };
  });
  
  async function fetchMetricsData() {
    try {
      loading = true;
      
      // Fetch active validators data
      const validatorsResponse = await api.get('/metrics/active-validators/');
      activeValidatorsData = validatorsResponse.data.data || [];
      
      // Fetch contribution types data
      const typesResponse = await api.get('/metrics/contribution-types/');
      contributionTypesData = typesResponse.data.data || [];
      
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load metrics data';
      loading = false;
    }
  }
  
  function createCharts() {
    // Active Validators Chart
    const validatorsCanvas = document.getElementById('activeValidatorsChart');
    if (validatorsCanvas) {
      const validatorsCtx = validatorsCanvas.getContext('2d');
      activeValidatorsChart = new Chart(validatorsCtx, {
        type: 'line',
        data: {
          labels: activeValidatorsData.map(d => new Date(d.date).toLocaleDateString()),
          datasets: [{
            label: 'Active Validators',
            data: activeValidatorsData.map(d => d.count),
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            title: {
              display: true,
              text: 'Active Validators Over Time'
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                stepSize: 1
              }
            }
          }
        }
      });
    }
    
    // Contribution Types Chart
    const typesCanvas = document.getElementById('contributionTypesChart');
    if (typesCanvas) {
      const typesCtx = typesCanvas.getContext('2d');
      contributionTypesChart = new Chart(typesCtx, {
        type: 'line',
        data: {
          labels: contributionTypesData.map(d => new Date(d.date).toLocaleDateString()),
          datasets: [{
            label: 'Cumulative Contribution Types',
            data: contributionTypesData.map(d => d.count),
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            title: {
              display: true,
              text: 'Contribution Types Assigned Over Time'
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                stepSize: 1
              }
            }
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
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
      <strong class="font-bold">Error!</strong>
      <span class="block sm:inline"> {error}</span>
    </div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Active Validators Chart -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-4">Active Validators</h2>
        <div class="h-64">
          <canvas id="activeValidatorsChart"></canvas>
        </div>
        <p class="text-sm text-gray-600 mt-4">
          Shows the number of active validators based on their first uptime contribution.
        </p>
      </div>
      
      <!-- Contribution Types Chart -->
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-4">Contribution Types Growth</h2>
        <div class="h-64">
          <canvas id="contributionTypesChart"></canvas>
        </div>
        <p class="text-sm text-gray-600 mt-4">
          Shows how many different contribution types have been assigned over time.
        </p>
      </div>
    </div>
    
    <!-- Summary Stats -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold text-gray-700">Total Active Validators</h3>
        <p class="text-3xl font-bold text-blue-600 mt-2">
          {activeValidatorsData.length > 0 ? activeValidatorsData[activeValidatorsData.length - 1].count : 0}
        </p>
      </div>
      
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold text-gray-700">Total Contribution Types</h3>
        <p class="text-3xl font-bold text-green-600 mt-2">
          {contributionTypesData.length > 0 ? contributionTypesData[contributionTypesData.length - 1].count : 0}
        </p>
      </div>
      
      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold text-gray-700">Latest Date</h3>
        <p class="text-xl font-bold text-purple-600 mt-2">
          {contributionTypesData.length > 0 ? new Date(contributionTypesData[contributionTypesData.length - 1].date).toLocaleDateString() : 'N/A'}
        </p>
      </div>
    </div>
  {/if}
</div>