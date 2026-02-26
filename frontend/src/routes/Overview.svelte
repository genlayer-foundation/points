<script>
  import HeroBanner from '../components/portal/HeroBanner.svelte';
  import LiveStats from '../components/portal/LiveStats.svelte';
  import TrendingContributors from '../components/portal/TrendingContributors.svelte';
  import FeaturedBuilds from '../components/portal/FeaturedBuilds.svelte';
  import PortalHighlights from '../components/portal/PortalHighlights.svelte';
  import NewestMembers from '../components/portal/NewestMembers.svelte';
  import MiniLeaderboard from '../components/portal/MiniLeaderboard.svelte';
  import CTAFooter from '../components/portal/CTAFooter.svelte';
</script>

<div class="space-y-8">
  <HeroBanner />
  <LiveStats />
  <TrendingContributors />
  <FeaturedBuilds />
  <PortalHighlights />
  <NewestMembers />
  <MiniLeaderboard />
  <CTAFooter />
</div>
