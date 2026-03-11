<script>
  import { push } from 'svelte-spa-router';
  import HeroBanner from '../components/portal/HeroBanner.svelte';
  import LiveStats from '../components/portal/LiveStats.svelte';
  import TrendingContributors from '../components/portal/TrendingContributors.svelte';
  import FeaturedBuilds from '../components/portal/FeaturedBuilds.svelte';
  import PortalHighlights from '../components/portal/PortalHighlights.svelte';
  import NewestMembers from '../components/portal/NewestMembers.svelte';
  import MiniLeaderboard from '../components/portal/MiniLeaderboard.svelte';
</script>

<div class="space-y-8">
  <HeroBanner />
  <LiveStats />
  <TrendingContributors />
  <FeaturedBuilds />
  <PortalHighlights />
  <NewestMembers />
  <MiniLeaderboard />
</div>

<!-- CTA Footer — full-width, flush to bottom, background bleeds over content above -->
<div class="relative -mx-3 -mb-3 -mt-16 pt-16">
  <!-- Rainbow glow background — fades to transparent at top so it softly overlaps content above -->
  <div class="absolute inset-0 pointer-events-none overflow-hidden" style="-webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 40%); mask-image: linear-gradient(to bottom, transparent 0%, black 40%);">
    <div class="absolute inset-0 flex items-center justify-center">
      <div class="relative w-full h-full" style="-webkit-mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); -webkit-mask-size: 1818px 1489.395px; mask-size: 1818px 1489.395px; -webkit-mask-position: center; mask-position: center; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;">
        <img src="/assets/illustrations/welcome-gradient.png" alt="" class="absolute inset-0 w-full h-full object-cover mix-blend-screen" />
      </div>
    </div>
  </div>

  <div class="relative z-10 px-8 md:px-20 py-24 md:py-32 text-center">
    <h2 class="text-3xl md:text-[64px] font-medium text-gray-900 font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
      Start contributing today
    </h2>
    <p class="text-[#6b6b6b] text-base max-w-2xl mx-auto mb-8 whitespace-nowrap">
      Join professional validators and builders in creating the trust infrastructure for the AI age.
    </p>
    <div>
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
