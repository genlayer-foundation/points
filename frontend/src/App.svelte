<script>
  import Router from 'svelte-spa-router';
  import { wrap } from 'svelte-spa-router/wrap';
  import { onMount } from 'svelte';
  import Navbar from './components/Navbar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import { categoryTheme, currentCategory, detectCategoryFromRoute } from './stores/category.js';
  import { location } from 'svelte-spa-router';
  
  // State for sidebar toggle on mobile
  let sidebarOpen = $state(false);
  
  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }
  
  import Dashboard from './routes/Dashboard.svelte';
  import Contributions from './routes/Contributions.svelte';
  import Leaderboard from './routes/Leaderboard.svelte';
  import Profile from './routes/Profile.svelte';
  import ContributionTypeDetail from './routes/ContributionTypeDetail.svelte';
  import BadgeDetail from './routes/BadgeDetail.svelte';
  import Validators from './routes/Validators.svelte';
  import SubmitContribution from './routes/SubmitContribution.svelte';
  import MySubmissions from './routes/MySubmissions.svelte';
  import EditSubmission from './routes/EditSubmission.svelte';
  import Metrics from './routes/Metrics.svelte';
  import ProfileEdit from './routes/ProfileEdit.svelte';
  import Highlights from './routes/Highlights.svelte';
  import NotFound from './routes/NotFound.svelte';
  import LoaderShowcase from './routes/LoaderShowcase.svelte';
  import StewardDashboard from './routes/StewardDashboard.svelte';
  import StewardSubmissions from './routes/StewardSubmissions.svelte';
  import ValidatorWaitlist from './routes/ValidatorWaitlist.svelte';
  import Waitlist from './routes/Waitlist.svelte';
  
  // Define routes
  const routes = {
    // Global/Testnet Asimov routes
    '/': Dashboard,
    '/contributions': Contributions,
    '/contributions/highlights': Highlights,
    '/highlights': Highlights,
    '/leaderboard': Leaderboard,
    '/participants': Validators,
    
    // Builders routes
    '/builders': Dashboard,
    '/builders/contributions': Contributions,
    '/builders/contributions/highlights': Highlights,
    '/builders/highlights': Highlights,
    '/builders/leaderboard': Leaderboard,
    '/builders/participants': Validators,
    
    // Validators routes
    '/validators': Dashboard,
    '/validators/contributions': Contributions,
    '/validators/contributions/highlights': Highlights,
    '/validators/highlights': Highlights,
    '/validators/leaderboard': Leaderboard,
    '/validators/participants': Validators,
    '/validators/waitlist': Waitlist,
    '/validators/waitlist/join': ValidatorWaitlist,
    
    // Shared routes
    '/participant/:address': Profile,
    '/contribution-type/:id': ContributionTypeDetail,
    '/badge/:id': BadgeDetail,
    '/submit-contribution': SubmitContribution,
    '/my-submissions': MySubmissions,
    '/contributions/:id': EditSubmission,
    '/metrics': Metrics,
    '/profile': ProfileEdit,
    '/loader-showcase': LoaderShowcase,
    
    // Steward routes
    '/stewards': StewardDashboard,
    '/stewards/submissions': StewardSubmissions,
    
    '*': NotFound
  };
  
  // Automatically update category based on current route
  $effect(() => {
    const category = detectCategoryFromRoute($location);
    currentCategory.set(category);
  });
  
  // Function to hide tooltips - used for route changes
  function hideTooltips() {
    const tooltipEl = document.getElementById('custom-tooltip');
    const arrowEl = document.getElementById('custom-tooltip-arrow');
    
    if (tooltipEl) {
      tooltipEl.style.opacity = '0';
      tooltipEl.style.display = 'none'; // Completely hide it
    }
    if (arrowEl) {
      arrowEl.style.opacity = '0';
      arrowEl.style.display = 'none'; // Completely hide it
    }
  }

  // Tooltip handling
  onMount(() => {
    // Use event delegation for better performance
    document.body.addEventListener('mouseover', handleTooltipPosition);
    
    // Cleanup
    return () => {
      document.body.removeEventListener('mouseover', handleTooltipPosition);
    };
  });

  function handleTooltipPosition(event) {
    // Check if the hovered element has the tooltip class
    const tooltipElement = event.target.closest('.tooltip');
    if (!tooltipElement || !tooltipElement.title) return;
    
    const title = tooltipElement.getAttribute('title');
    if (!title || title === '') return;
    
    // Get or create tooltip elements
    let tooltipEl = document.getElementById('custom-tooltip');
    let arrowEl = document.getElementById('custom-tooltip-arrow');
    
    // Make sure tooltips are visible if they were hidden
    if (tooltipEl) tooltipEl.style.display = 'block';
    if (arrowEl) arrowEl.style.display = 'block';
    
    // Store the title to restore it later
    tooltipElement.dataset.tooltipText = title;
    
    // Temporarily remove the title to prevent the browser's default tooltip
    tooltipElement.setAttribute('title', '');
    
    // Create elements if they don't exist
    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.id = 'custom-tooltip';
      tooltipEl.style.position = 'fixed';
      tooltipEl.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
      tooltipEl.style.color = 'white';
      tooltipEl.style.padding = '0.5rem';
      tooltipEl.style.borderRadius = '0.25rem';
      tooltipEl.style.zIndex = '9999';
      tooltipEl.style.fontWeight = 'normal';
      tooltipEl.style.fontSize = '0.75rem';
      tooltipEl.style.pointerEvents = 'none';
      tooltipEl.style.maxWidth = '300px';
      tooltipEl.style.textAlign = 'center';
      tooltipEl.style.whiteSpace = 'normal';
      tooltipEl.style.opacity = '0';
      tooltipEl.style.transition = 'opacity 0.2s ease-in-out';
      document.body.appendChild(tooltipEl);
      
      arrowEl = document.createElement('div');
      arrowEl.id = 'custom-tooltip-arrow';
      arrowEl.style.position = 'fixed';
      arrowEl.style.borderWidth = '5px';
      arrowEl.style.borderStyle = 'solid';
      arrowEl.style.borderColor = 'rgba(0, 0, 0, 0.8) transparent transparent transparent';
      arrowEl.style.zIndex = '9999';
      arrowEl.style.pointerEvents = 'none';
      arrowEl.style.opacity = '0';
      arrowEl.style.transition = 'opacity 0.2s ease-in-out';
      document.body.appendChild(arrowEl);
    }
    
    // Set tooltip content
    tooltipEl.textContent = title;
    
    // Position tooltip and arrow based on the element's position
    const rect = tooltipElement.getBoundingClientRect();
    const tooltipWidth = tooltipEl.offsetWidth;
    const tooltipHeight = tooltipEl.offsetHeight;
    
    // Position tooltip above the element
    tooltipEl.style.left = rect.left + rect.width / 2 - tooltipWidth / 2 + 'px';
    tooltipEl.style.top = rect.top - tooltipHeight - 5 + 'px'; // Reduced gap from 10px to 5px
    
    // Position arrow
    arrowEl.style.left = rect.left + rect.width / 2 - 5 + 'px';
    arrowEl.style.top = rect.top - 5 + 'px';
    
    // Check if tooltip goes beyond viewport boundaries and adjust if needed
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Adjust horizontal position if needed
    if (parseFloat(tooltipEl.style.left) < 10) {
      tooltipEl.style.left = '10px';
    } else if (parseFloat(tooltipEl.style.left) + tooltipWidth > viewportWidth - 10) {
      tooltipEl.style.left = viewportWidth - tooltipWidth - 10 + 'px';
    }
    
    // If tooltip goes above viewport, show it below the element instead
    if (parseFloat(tooltipEl.style.top) < 10) {
      tooltipEl.style.top = rect.bottom + 5 + 'px'; // Reduced gap from 10px to 5px
      arrowEl.style.top = rect.bottom + 'px';
      arrowEl.style.borderColor = 'transparent transparent rgba(0, 0, 0, 0.8) transparent';
      arrowEl.style.marginTop = '-5px'; // Reduced gap from 10px to 5px
    } else {
      arrowEl.style.borderColor = 'rgba(0, 0, 0, 0.8) transparent transparent transparent';
      arrowEl.style.marginTop = '0';
    }
    
    // Show tooltip and arrow
    tooltipEl.style.opacity = '1';
    arrowEl.style.opacity = '1';
    
    // Add event listener for mouseout
    tooltipElement.addEventListener('mouseout', function hideTooltip() {
      tooltipEl.style.opacity = '0';
      arrowEl.style.opacity = '0';
      
      // Restore the title attribute
      tooltipElement.setAttribute('title', tooltipElement.dataset.tooltipText);
      tooltipElement.removeEventListener('mouseout', hideTooltip);
    }, { once: true });
  }
</script>

<div class="min-h-screen {$categoryTheme.bg} transition-colors duration-300">
  <Navbar {toggleSidebar} {sidebarOpen} />
  <div class="flex">
    <Sidebar bind:isOpen={sidebarOpen} />
    <main class="flex-1 container mx-auto px-4 py-4 md:py-6 lg:py-8">
      <Router 
        {routes} 
        on:conditionsFailed={hideTooltips}
        on:routeLoaded={hideTooltips}
      />
    </main>
  </div>
</div>