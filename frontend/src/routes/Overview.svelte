<script>
  import HeroBanner from '../components/portal/HeroBanner.svelte';
  import NetworkActivity from '../components/portal/NetworkActivity.svelte';
  import FeaturedBuilds from '../components/portal/FeaturedBuilds.svelte';
  import PartnerLogoBanner from '../components/portal/PartnerLogoBanner.svelte';
  import OverviewPathSection from '../components/portal/OverviewPathSection.svelte';
</script>

<div class="overview-view">
  <!-- overflow-x-clip (not -hidden): hidden computes overflow-y to auto, creating a nested
       scroll container that traps the first touch scroll on mobile (see CLAUDE.md gotcha) -->
  <div class="space-y-8 max-w-full overflow-x-clip md:overflow-x-visible">
    <HeroBanner showNewsLink={true} compact={true} />
    <NetworkActivity />
    <FeaturedBuilds
      title="Built on GenLayer"
      subtitle=""
      overviewOnly={true}
      limit={5}
      variant="vertical"
    />
    <PartnerLogoBanner />
    <OverviewPathSection />
  </div>
</div>

<style>
  .overview-view {
    background-color: #fff;
    background-image:
      linear-gradient(180deg, rgba(248, 249, 252, 0.72) 0%, #fff 26rem),
      radial-gradient(circle at 12% 0%, rgba(127, 82, 225, 0.08), transparent 26rem),
      radial-gradient(circle at 88% 8%, rgba(238, 133, 33, 0.055), transparent 24rem);
    background-position: center top, left top, right top;
    background-repeat: no-repeat;
    background-size: 100% 34rem, 42rem 30rem, 40rem 28rem;
    margin: -12px;
    min-height: 100%;
    /* clip, not hidden: hidden leaves a programmatically-scrollable box that the
       path-section coin bleed (132px) can scroll, cutting off content */
    overflow: clip;
    padding: 12px 12px 0;
  }
</style>
