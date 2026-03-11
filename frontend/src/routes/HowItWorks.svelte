<script>
  import WelcomeHero from '../components/portal/landing-page/WelcomeHero.svelte';
  import JourneySection from '../components/portal/landing-page/JourneySection.svelte';
  import SubmitSection from '../components/portal/landing-page/SubmitSection.svelte';
  import ClimbRanksSection from '../components/portal/landing-page/ClimbRanksSection.svelte';
  import RoleCards from '../components/portal/landing-page/RoleCards.svelte';
  import CTABanner from '../components/shared/CTABanner.svelte';
</script>

<div class="relative w-full overflow-clip isolate">
  <!-- Top glow -->
  <div class="absolute inset-x-0 top-[-477px] aspect-square min-h-[1218px] flex items-center justify-center -rotate-90 -scale-y-100 pointer-events-none" style="z-index: -1;">
    <div class="relative w-full h-full" style="-webkit-mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); -webkit-mask-size: 1818px 1489.395px; mask-size: 1818px 1489.395px; -webkit-mask-position: center -250px; mask-position: center -250px; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;">
      <img src="/assets/illustrations/welcome-gradient.png" alt="" class="absolute inset-0 w-full h-full object-cover mix-blend-screen" />
    </div>
  </div>

  <!-- Bottom glow -->
  <div class="absolute inset-x-0 bottom-[-319px] aspect-square min-h-[1218px] flex items-center justify-center rotate-90 pointer-events-none" style="z-index: -1;">
    <div class="relative w-full h-full" style="-webkit-mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); -webkit-mask-size: 1818px 1489.395px; mask-size: 1818px 1489.395px; -webkit-mask-position: center -21.395px; mask-position: center -21.395px; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;">
      <img src="/assets/illustrations/welcome-gradient.png" alt="" class="absolute inset-0 w-full h-full object-cover mix-blend-screen" />
    </div>
  </div>

  <div class="space-y-[24px] z-10 relative max-w-[1200px] mx-auto">
    <WelcomeHero />
    <JourneySection />
    <SubmitSection />
    <ClimbRanksSection />
    <RoleCards />
    <CTABanner variant="light" />
  </div>
</div>
