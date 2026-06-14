<script>
  import Router from 'svelte-spa-router';
  import { wrap } from 'svelte-spa-router/wrap';
  import { replace } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import Navbar from './components/Navbar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import ToastContainer from './components/ToastContainer.svelte';
  import ProfileCompletionGuard from './components/ProfileCompletionGuard.svelte';
  import { currentCategory, detectCategoryFromRoute } from './stores/category.js';
  import { location } from 'svelte-spa-router';
  import { setRouteMeta } from './lib/meta.js';
  import { authState, verifyAuth } from './lib/auth.js';
  import { normalizeLocation } from './lib/normalizePath.js';
  
  // Early OAuth result detection — runs before routes mount.
  // Backend redirects here with ?oauth_platform=X&oauth_verified=true/false&oauth_error=...
  // We relay the result to the opener tab via postMessage (primary) and localStorage (fallback).
  {
    const search = window.location.search;
    if (search && search.includes('oauth_platform')) {
      const params = new URLSearchParams(search);
      const platform = params.get('oauth_platform');
      if (platform) {
        const result = {
          type: 'oauth_result',
          platform,
          verified: params.get('oauth_verified') || 'false',
          error: params.get('oauth_error') || '',
        };

        // Primary: postMessage to opener (standard OAuth popup pattern).
        // The opener is always this same portal, so target our own origin
        // instead of '*' to keep the result from being readable by any
        // window that managed to open this page.
        if (window.opener) {
          window.opener.postMessage(result, window.location.origin);
        }

        // Fallback: localStorage for when window.opener is null (Safari)
        const storageKey = `oauth_result_${platform}`;
        localStorage.setItem(storageKey, JSON.stringify({
          verified: result.verified,
          error: result.error,
        }));

        setTimeout(() => {
          window.close();
          // Fallback: if close fails, strip params so the page loads clean
          window.history.replaceState({}, '', window.location.pathname + (window.location.hash || ''));
        }, 100);
      }
    }
  }

  // The portal uses hash routing. Direct/path-based links (sidebar hrefs
  // opened in a new tab, refreshes of a path route, shared or indexed links)
  // arrive without a hash and would otherwise 404. Rewrite any such path into
  // its hash equivalent so the router can resolve it; unknown paths still
  // fall through to the router's own NotFound view.
  normalizeLocation(window);

  // State for sidebar toggle on mobile and collapse on desktop
  let sidebarOpen = $state(false);
  let sidebarCollapsed = $state(false);

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
  import MissionDetail from './routes/MissionDetail.svelte';
  import BadgeDetail from './routes/BadgeDetail.svelte';
  import Validators from './routes/Validators.svelte';
  import SubmitContribution from './routes/SubmitContribution.svelte';
  import MySubmissions from './routes/MySubmissions.svelte';
  import EditSubmission from './routes/EditSubmission.svelte';
  import Metrics from './routes/Metrics.svelte';
  import ProfileEdit from './routes/ProfileEdit.svelte';
  import NotFound from './routes/NotFound.svelte';
  import LoaderShowcase from './routes/LoaderShowcase.svelte';
  import StewardDashboard from './routes/StewardDashboard.svelte';
  import StewardSubmissions from './routes/StewardSubmissions.svelte';
  import StewardDiscordXP from './routes/StewardDiscordXP.svelte';
  import StewardManageUsers from './routes/StewardManageUsers.svelte';
  import ValidatorWaitlist from './routes/ValidatorWaitlist.svelte';
  import Waitlist from './routes/Waitlist.svelte';
  import WaitlistParticipants from './routes/WaitlistParticipants.svelte';
  import WallOfShame from './routes/WallOfShame.svelte';

  import TermsOfUse from './routes/TermsOfUse.svelte';
  import PrivacyPolicy from './routes/PrivacyPolicy.svelte';
  import EcosystemPartners from './routes/EcosystemPartners.svelte';
  import GenNews from './routes/GenNews.svelte';
  import GenTV from './routes/GenTV.svelte';
  import FoundationsCompass from './routes/FoundationsCompass.svelte';
  import FoundationsManifesto from './routes/FoundationsManifesto.svelte';
  import FoundationsWhitepaper from './routes/FoundationsWhitepaper.svelte';
  import Referrals from './routes/Referrals.svelte';
  import LegacyReferralRedirect from './routes/LegacyReferralRedirect.svelte';
  import CommunityPoaps from './routes/CommunityPoaps.svelte';
  import PoapDetail from './routes/PoapDetail.svelte';
  import PoapClaim from './routes/PoapClaim.svelte';
  import PoapRecovery from './routes/PoapRecovery.svelte';
  import Hackathon from './routes/Hackathon.svelte';
  import HackathonWinners from './routes/HackathonWinners.svelte';
  import Resources from './routes/Resources.svelte';
  import ReferralProgram from './routes/ReferralProgram.svelte';
  import HowItWorks from './routes/HowItWorks.svelte';
  import StartupRequestDetail from './routes/StartupRequestDetail.svelte';
  import ContributionPreview from './routes/ContributionPreview.svelte';
  import ProjectDetail from './routes/ProjectDetail.svelte';
  import ProjectPageEditor from './routes/ProjectPageEditor.svelte';
  import GlobalDashboard from './components/GlobalDashboard.svelte';
  import SystemAlerts from './components/portal/SystemAlerts.svelte';
  import SocialTasks from './routes/SocialTasks.svelte';

  async function requireAuthForRoute({ location, querystring }) {
    const state = authState.get();
    const isAuthenticated = state.isAuthenticated || await verifyAuth();

    if (isAuthenticated) {
      return true;
    }

    sessionStorage.setItem(
      'redirectAfterLogin',
      `${location || '/'}${querystring ? `?${querystring}` : ''}`
    );

    // replace, not push: a pushed redirect leaves the protected URL in
    // history, so the back button bounces off it and re-redirects forever.
    replace('/');

    setTimeout(() => {
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) {
        authButton.click();
      }
    }, 0);

    return false;
  }

  const protectedRoute = (component) => wrap({
    component,
    conditions: [requireAuthForRoute],
  });

  // Define routes
  const routes = {

    // Global/Testnet Asimov routes
    // Overview and Testnet Asimov routes
    '/': Overview,
    '/testnets': protectedRoute(GlobalDashboard),
    '/how-it-works': HowItWorks,
    '/contributions': protectedRoute(Contributions),
    '/all-contributions': protectedRoute(AllContributions),
    '/leaderboard': protectedRoute(Leaderboard),
    '/participants': Validators,
    '/referrals': protectedRoute(Referrals),
    '/community': protectedRoute(Dashboard),
    '/community/contributions': protectedRoute(Contributions),
    '/community/all-contributions': protectedRoute(AllContributions),
    '/community/referrals': LegacyReferralRedirect,
    '/community/leaderboard': protectedRoute(Leaderboard),
    '/community/poaps': CommunityPoaps,
    '/community/poaps/recover': PoapRecovery,
    '/community/poaps/:slug': PoapDetail,
    '/community/tasks': protectedRoute(SocialTasks),
    '/community/contribution/:id': protectedRoute(ContributionPreview),
    '/claim/poap/:token': PoapClaim,
    '/hackathon': Hackathon,
    '/hackathon-winners': HackathonWinners,
    '/referral-program': ReferralProgram,

    // Builders routes
    '/builders': protectedRoute(Dashboard),
    '/builders/contributions': protectedRoute(Contributions),
    '/builders/all-contributions': protectedRoute(AllContributions),
    '/builders/leaderboard': protectedRoute(Leaderboard),

    '/builders/resources': Resources,
    '/builders/projects/:slug/edit': protectedRoute(ProjectPageEditor),
    '/builders/projects/:slug': ProjectDetail,
    '/builders/tasks': protectedRoute(SocialTasks),
    '/builders/startup-requests/:id': StartupRequestDetail,
    
    // Validators routes
    '/validators': protectedRoute(Dashboard),
    '/validators/contributions': protectedRoute(Contributions),
    '/validators/all-contributions': protectedRoute(AllContributions),
    '/validators/leaderboard': protectedRoute(Leaderboard),
    '/validators/tasks': protectedRoute(SocialTasks),
    '/validators/participants': Validators,
    '/validators/wall-of-shame': WallOfShame,
    '/validators/waitlist': protectedRoute(Waitlist),
    '/validators/waitlist/participants': protectedRoute(WaitlistParticipants),
    '/validators/waitlist/join': ValidatorWaitlist,
    
    // Shared routes
    '/participant/:address': protectedRoute(Profile),
    '/contribution/:id': protectedRoute(ContributionPreview),
    '/builders/contribution/:id': protectedRoute(ContributionPreview),
    '/validators/contribution/:id': protectedRoute(ContributionPreview),
    '/contribution-type/:id': protectedRoute(ContributionTypeDetail),
    '/mission/:id': protectedRoute(MissionDetail),
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
    '/stewards/discord-xp': StewardDiscordXP,
    '/stewards/manage-users': StewardManageUsers,

    // Legal routes
    '/terms-of-use': TermsOfUse,
    '/privacy-policy': PrivacyPolicy,

    // Ecosystem
    '/ecosystem-partners': EcosystemPartners,
    '/gen-news': GenNews,
    '/gen-tv': GenTV,

    // Genesis (Manifesto / Compass / Whitepaper)
    '/genesis': FoundationsManifesto,
    '/genesis/compass': FoundationsCompass,
    '/genesis/manifesto': FoundationsManifesto,
    '/genesis/whitepaper': FoundationsWhitepaper,

    // Legacy Foundations aliases
    '/foundations': FoundationsManifesto,
    '/foundations/compass': FoundationsCompass,
    '/foundations/manifesto': FoundationsManifesto,
    '/foundations/whitepaper': FoundationsWhitepaper,
    '/manifesto': FoundationsManifesto,

    '*': NotFound
  };
  
  // Automatically update category based on current route
  $effect(() => {
    const category = detectCategoryFromRoute($location);
    currentCategory.set(category);
  });

  // Pages that need full-bleed (no padding): How it works + Foundations documents
  let isFullBleedPage = $derived(
    $location === '/how-it-works' ||
    $location.startsWith('/genesis') ||
    $location.startsWith('/foundations') ||
    $location === '/manifesto'
  );
  
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

        // Clean URL without page reload to remove the ref parameter
        const cleanUrl = window.location.pathname + window.location.hash;
        window.history.replaceState({}, '', cleanUrl);

      }
    } catch (error) {
      // Error capturing referral code silently handled
    }
  }
  
  // Function to handle route loaded events
  function handleRouteLoaded() {
    // Hide tooltips
    hideTooltips();
    setRouteMeta($location);
    const mainEl = document.querySelector('main');
    if (mainEl) {
      mainEl.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    }
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

<div class="h-screen flex flex-col bg-white">
  <Navbar {toggleSidebar} {sidebarOpen} />
  <div class="flex-1 flex overflow-hidden">
    <Sidebar bind:isOpen={sidebarOpen} bind:collapsed={sidebarCollapsed} />
    <main class="flex-1 overflow-y-auto {isFullBleedPage ? '' : 'px-3 py-3'}">
      <SystemAlerts />
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
