<script>
  import Router from 'svelte-spa-router';
  import { wrap } from 'svelte-spa-router/wrap';
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import Navbar from './components/Navbar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import ToastContainer from './components/ToastContainer.svelte';
  import ProfileCompletionGuard from './components/ProfileCompletionGuard.svelte';
  import { categoryTheme, currentCategory, detectCategoryFromRoute } from './stores/category.js';
  import { location } from 'svelte-spa-router';
  
  // State for sidebar toggle on mobile
  let sidebarOpen = $state(false);
  
  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }
  
  import Overview from './routes/Overview.svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import Contributions from './routes/Contributions.svelte';
  import AllContributions from './routes/AllContributions.svelte';
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
  import StewardManageUsers from './routes/StewardManageUsers.svelte';
  import ValidatorWaitlist from './routes/ValidatorWaitlist.svelte';
  import Waitlist from './routes/Waitlist.svelte';
  import WaitlistParticipants from './routes/WaitlistParticipants.svelte';
  import BuilderWelcome from './routes/BuilderWelcome.svelte';
  import GitHubCallback from './routes/GitHubCallback.svelte';
  import TermsOfUse from './routes/TermsOfUse.svelte';
  import PrivacyPolicy from './routes/PrivacyPolicy.svelte';
  import Referrals from './routes/Referrals.svelte';
  import Supporters from './routes/Supporters.svelte';
  import GlobalDashboard from './components/GlobalDashboard.svelte';

  // Define routes
  const routes = {

    // Auth callback routes
    '/auth/github/callback': GitHubCallback,

    // Global/Testnet Asimov routes
    // Overview and Testnet Asimov routes
    '/': Overview,
    '/asimov': GlobalDashboard,
    '/contributions': Contributions,
    '/all-contributions': AllContributions,
    '/contributions/highlights': Highlights,
    '/highlights': Highlights,
    '/leaderboard': Leaderboard,
    '/participants': Validators,
    '/referrals': Referrals,
    '/supporters': Supporters,

    // Builders routes
    '/builders': Dashboard,
    '/builders/contributions': Contributions,
    '/builders/all-contributions': AllContributions,
    '/builders/contributions/highlights': Highlights,
    '/builders/highlights': Highlights,
    '/builders/leaderboard': Leaderboard,
    '/builders/welcome': BuilderWelcome,
    
    // Validators routes
    '/validators': Dashboard,
    '/validators/contributions': Contributions,
    '/validators/all-contributions': AllContributions,
    '/validators/contributions/highlights': Highlights,
    '/validators/highlights': Highlights,
    '/validators/leaderboard': Leaderboard,
    '/validators/participants': Validators,
    '/validators/waitlist': Waitlist,
    '/validators/waitlist/participants': WaitlistParticipants,
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
    '/stewards/manage-users': StewardManageUsers,

    // Legal routes
    '/terms-of-use': TermsOfUse,
    '/privacy-policy': PrivacyPolicy,

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

  // Function to capture referral code from URL parameter
  function captureReferralCode() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const referralCode = urlParams.get('ref');
      
      if (referralCode && referralCode.length === 8) {
        // Store referral code in localStorage for later use during login
        localStorage.setItem('referral_code', referralCode.toUpperCase());
        console.log('Referral code captured:', referralCode.toUpperCase());
        
        // Clean URL without page reload to remove the ref parameter
        const cleanUrl = window.location.pathname + window.location.hash;
        window.history.replaceState({}, '', cleanUrl);
      }
    } catch (error) {
      console.error('Error capturing referral code:', error);
    }
  }
  
  // Function to handle route loaded events
  function handleRouteLoaded() {
    // Hide tooltips
    hideTooltips();
  }

  // Tooltip handling
  onMount(() => {
    // Capture referral code from URL on app load
    captureReferralCode();
    
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

<div class="h-screen flex flex-col {$categoryTheme.bg} transition-colors duration-300">
  <Navbar {toggleSidebar} {sidebarOpen} />
  <div class="flex-1 flex overflow-hidden">
    <Sidebar bind:isOpen={sidebarOpen} />
    <main class="flex-1 overflow-y-auto container mx-auto px-4 py-4 md:py-6 lg:py-8">
      <Router
        {routes}
        on:conditionsFailed={hideTooltips}
        on:routeLoaded={handleRouteLoaded}
      />
    </main>
  </div>
  <!-- Global toast container -->
  <ToastContainer />
</div>

<!-- Profile Completion Guard - Shows on all pages until profile is complete -->
<ProfileCompletionGuard />
