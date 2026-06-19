<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { metricsAPI } from '../lib/api.js';
  import HeroBanner from '../components/portal/HeroBanner.svelte';
  import NetworkActivity from '../components/portal/NetworkActivity.svelte';
  import FeaturedBuilds from '../components/portal/FeaturedBuilds.svelte';
  import PartnerLogoBanner from '../components/portal/PartnerLogoBanner.svelte';

  let socialStats = $state(null);

  onMount(async () => {
    try {
      const { data } = await metricsAPI.getOverview();
      socialStats = {
        x: data?.metrics?.x_followers?.value ?? null,
        telegram: data?.metrics?.telegram_members?.value ?? null,
        discord: data?.metrics?.discord_members?.value ?? null,
      };
    } catch (err) {
      // hero renders without the social cluster
    }
  });
</script>

<div class="overview-view">
  <div class="space-y-8 max-w-full overflow-x-hidden md:overflow-x-visible">
    <HeroBanner showNewsLink={true} compact={true} {socialStats} />
    <NetworkActivity />
    <FeaturedBuilds
      title="Built on GenLayer"
      subtitle=""
      overviewOnly={true}
      limit={5}
      variant="vertical"
    />
    <PartnerLogoBanner />
  </div>

  <!-- CTA Footer — full-width, flush to bottom, background bleeds over content above -->
  <!-- pointer-events-none so the -mt-16 glow overlap doesn't steal clicks/hover from the section above (e.g. the marquee); the button re-enables them -->
  <div class="relative -mx-3 -mb-3 -mt-16 pt-16 overflow-hidden md:overflow-visible pointer-events-none">
    <!-- Rainbow glow background — fades to transparent at top so it softly overlaps content above -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden" style="-webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 40%); mask-image: linear-gradient(to bottom, transparent 0%, black 40%);">
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="relative w-full h-full" style="-webkit-mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); -webkit-mask-size: 1818px 1489.395px; mask-size: 1818px 1489.395px; -webkit-mask-position: center; mask-position: center; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;">
          <img src="/assets/illustrations/welcome-gradient.png" alt="" class="absolute inset-0 w-full h-full object-cover mix-blend-screen" />
        </div>
      </div>
    </div>

    <div class="relative z-10 px-4 md:px-20 py-24 md:py-32 text-center">
      <h2 class="text-3xl md:text-[64px] font-medium text-gray-900 font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
        Start contributing today
      </h2>
      <p class="text-[#6b6b6b] text-base max-w-2xl mx-auto mb-8 whitespace-normal md:whitespace-nowrap">
        Join professional validators and builders in creating the trust infrastructure for the AI age.
      </p>
      <div class="pointer-events-auto">
        <button
          onclick={() => push('/builders/contributions')}
          class="bg-[#101010] text-white py-2 px-8 rounded-[24px] text-[14px] font-medium hover:bg-black transition-colors"
        >
          Start building <img
            src="/assets/icons/arrow-right-line.svg"
            class="inline w-4 h-4 ml-1 brightness-0 invert"
            alt=""
          />
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  .overview-view {
    background-color: #fff;
    background-image:
      linear-gradient(180deg, rgba(255, 255, 255, 0.7) 0%, rgba(255, 255, 255, 0.9) 34%, #fff 78%),
      radial-gradient(circle at 14% 2%, rgba(127, 82, 225, 0.12), transparent 28rem),
      url('/assets/illustrations/welcome-gradient.png');
    background-position: center top, left top, center -360px;
    background-repeat: no-repeat;
    background-size: auto, auto, clamp(920px, 140vw, 1700px) auto;
    margin: -12px;
    min-height: 100%;
    overflow: hidden;
    padding: 12px 12px 0;
  }
</style>
