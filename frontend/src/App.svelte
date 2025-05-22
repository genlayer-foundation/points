<script>
  import Router from 'svelte-spa-router';
  import { wrap } from 'svelte-spa-router/wrap';
  import Navbar from './components/Navbar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import Contributions from './routes/Contributions.svelte';
  import ParticipantProfile from './routes/ParticipantProfile.svelte';
  import NotFound from './routes/NotFound.svelte';
  
  // Define routes
  const routes = {
    '/': Dashboard,
    '/contributions': Contributions,
    '/leaderboard': Dashboard, // For now, just redirect to Dashboard which contains the leaderboard
    '/participant/:id': ParticipantProfile,
    '*': NotFound
  };
</script>

<div class="min-h-screen bg-gray-50">
  <Navbar />
  <div class="container mx-auto px-4 py-8 flex">
    <Sidebar />
    <main class="flex-1 ml-0 md:ml-64">
      <Router {routes} />
    </main>
  </div>
</div>