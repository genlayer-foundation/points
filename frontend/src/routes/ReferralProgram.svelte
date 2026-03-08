<script>
  import checkIcon from '../assets/referral/check-icon.png';
  import cardBg1 from '../assets/referral/card-bg-1.png';
  import cardBg2 from '../assets/referral/card-bg-2.png';
  import iconPortal from '../assets/referral/icon-portal.png';
  import iconReferral from '../assets/referral/icon-referral.png';
  import iconShare1 from '../assets/referral/icon-share-1.png';
  import iconShare2 from '../assets/referral/icon-share-2.png';
  import arrowRightWhite from '../assets/referral/arrow-right-white.png';
  import roleBgValidators from '../assets/referral/role-bg-validators.png';
  import roleBgCommunity from '../assets/referral/role-bg-community.png';
  import hexagonRevealHero from '../assets/referral/hexagon-reveal-hero.png';
  import hexagonRevealCta from '../assets/referral/hexagon-reveal-cta.png';
</script>

<div class="flex flex-col gap-8 md:gap-16 max-w-[1200px] mx-auto pb-12 px-1 md:px-3">
  <!-- Hero Section -->
  <div class="relative overflow-hidden rounded-[24px]">
    <img
      src={hexagonRevealHero}
      alt=""
      class="absolute inset-0 w-full h-full object-contain pointer-events-none"
    />
    <div class="relative z-10 flex flex-col items-center text-center px-4 md:px-8 py-16 md:py-32">
      <h1 class="text-[32px] md:text-[64px] font-medium font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
        Referral Program
      </h1>
      <p class="text-[20px] md:text-[32px] font-medium font-display leading-tight mb-4" style="letter-spacing: -0.64px;">
        Invite Builders, Validators & Community members
      </p>
      <p class="text-[15px] md:text-[17px] text-[#656567] mb-8 max-w-xl">
        Earn 10% of the points of their successful contributions
      </p>
      <button
        class="inline-flex items-center gap-2 h-12 px-8 text-white font-medium rounded-full text-base transition-opacity hover:opacity-90"
        style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
      >
        Get Your Referral Link
        <img src={arrowRightWhite} alt="" class="w-4 h-4" />
      </button>
    </div>
  </div>

  <!-- How it works Section -->
  <div>
    <h2 class="text-[28px] md:text-[48px] font-medium font-display text-center leading-tight mb-8 md:mb-12" style="letter-spacing: -0.96px;">
      How it works
    </h2>

    <div class="space-y-6 md:space-y-8">
      <!-- Step 1 - Text left, Image right -->
      <div class="flex flex-col md:flex-row gap-6 md:gap-8 items-center">
        <div class="flex-1 space-y-4 md:space-y-5">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-lg flex-shrink-0"
            style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
          >
            1
          </div>
          <h3 class="text-[24px] md:text-[32px] font-medium font-display leading-tight" style="letter-spacing: -0.64px;">
            Join the portal
          </h3>
          <p class="text-[15px] md:text-[17px] text-[#656567]">
            Sign up and create your GenLayer Points account to start tracking your contributions across the ecosystem.
          </p>
          <ul class="space-y-3">
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Connect your GitHub account</span>
            </li>
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Choose your primary role</span>
            </li>
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Start earning points immediately</span>
            </li>
          </ul>
        </div>
        <div class="flex-1 w-full">
          <div class="relative bg-white border border-[#f5f5f5] rounded-[12px] overflow-hidden flex items-center justify-center" style="min-height: 280px;">
            <img src={cardBg2} alt="" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none" />
            <img src={iconPortal} alt="Portal" class="relative z-10 w-20 h-20" />
          </div>
        </div>
      </div>

      <!-- Step 2 - Image left, Text right -->
      <div class="flex flex-col md:flex-row-reverse gap-6 md:gap-8 items-center">
        <div class="flex-1 space-y-4 md:space-y-5">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-lg flex-shrink-0"
            style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
          >
            2
          </div>
          <h3 class="text-[24px] md:text-[32px] font-medium font-display leading-tight" style="letter-spacing: -0.64px;">
            Get your referral link
          </h3>
          <p class="text-[15px] md:text-[17px] text-[#656567]">
            Head to your profile to grab your unique referral link — it's ready as soon as you join the portal.
          </p>
          <ul class="space-y-3">
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Unique link tied to your account</span>
            </li>
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Track referrals in real time</span>
            </li>
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Earn 10% of their points forever</span>
            </li>
          </ul>
        </div>
        <div class="flex-1 w-full">
          <div class="relative bg-white border border-[#f5f5f5] rounded-[12px] overflow-hidden flex items-center justify-center" style="min-height: 280px;">
            <img src={cardBg1} alt="" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none" />
            <img src={iconReferral} alt="Referral" class="relative z-10 w-20 h-20" />
          </div>
        </div>
      </div>

      <!-- Step 3 - Text left, Image right -->
      <div class="flex flex-col md:flex-row gap-6 md:gap-8 items-center">
        <div class="flex-1 space-y-4 md:space-y-5">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-lg flex-shrink-0"
            style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
          >
            3
          </div>
          <h3 class="text-[24px] md:text-[32px] font-medium font-display leading-tight" style="letter-spacing: -0.64px;">
            Share with your friends
          </h3>
          <p class="text-[15px] md:text-[17px] text-[#656567]">
            Send your link to developers, node operators, and community members. The more they contribute, the more you earn.
          </p>
          <ul class="space-y-3">
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Share across all your channels</span>
            </li>
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">Works for Builders, Validators & Community</span>
            </li>
            <li class="flex items-center gap-3">
              <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
              <span class="text-[14px] md:text-[15px] text-gray-800">No cap on referral earnings</span>
            </li>
          </ul>
        </div>
        <div class="flex-1 w-full">
          <div class="relative bg-white border border-[#f5f5f5] rounded-[12px] overflow-hidden flex items-center justify-center" style="min-height: 280px;">
            <img src={cardBg1} alt="" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none" />
            <div class="relative z-10 flex items-center gap-6">
              <img src={iconReferral} alt="Builders" class="w-14 h-14" />
              <img src={iconShare1} alt="Validators" class="w-14 h-14 -mt-8" />
              <img src={iconShare2} alt="Community" class="w-14 h-14" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Who can you invite? Section -->
  <div>
    <h2 class="text-[28px] md:text-[48px] font-medium font-display text-center leading-tight mb-3" style="letter-spacing: -0.96px;">
      Who can you invite?
    </h2>
    <p class="text-[15px] md:text-[17px] text-[#656567] text-center mb-8 md:mb-12">
      Pick your path — you can always take on more roles later.
    </p>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      <!-- Builders card -->
      <div class="bg-white border border-[#e5e5e5] rounded-[12px] overflow-hidden flex flex-col">
        <div class="relative flex items-center justify-center" style="min-height: 240px;">
          <img src={cardBg1} alt="" class="absolute inset-0 w-full h-full object-contain opacity-30 pointer-events-none" />
          <img src={iconReferral} alt="Builders" class="relative z-10 w-20 h-20" />
        </div>
        <div class="p-5 md:p-6 flex flex-col flex-1 gap-3">
          <h3 class="text-[22px] md:text-[24px] font-semibold font-display" style="letter-spacing: -0.48px;">Builders</h3>
          <p class="text-[14px] md:text-[15px] text-[#656567] leading-relaxed">
            Write Intelligent Contracts, build dApps, and contribute developer tools to the GenLayer ecosystem.
          </p>
          <button
            class="flex items-center justify-center gap-2 w-full h-11 mt-auto text-white font-medium rounded-full text-sm transition-opacity hover:opacity-90"
            style="background-color: #131214;"
          >
            Invite a Builder
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Validators card -->
      <div class="bg-white border border-[#e5e5e5] rounded-[12px] overflow-hidden flex flex-col">
        <div class="relative flex items-center justify-center" style="min-height: 240px;">
          <img src={roleBgValidators} alt="" class="absolute inset-0 w-full h-full object-contain opacity-30 pointer-events-none" />
          <img src={iconShare1} alt="Validators" class="relative z-10 w-20 h-20" />
        </div>
        <div class="p-5 md:p-6 flex flex-col flex-1 gap-3">
          <h3 class="text-[22px] md:text-[24px] font-semibold font-display" style="letter-spacing: -0.48px;">Validators</h3>
          <p class="text-[14px] md:text-[15px] text-[#656567] leading-relaxed">
            Run nodes, provide AI models, and help scale and secure the network through Optimistic Democracy.
          </p>
          <button
            class="flex items-center justify-center gap-2 w-full h-11 mt-auto text-white font-medium rounded-full text-sm transition-opacity hover:opacity-90"
            style="background-color: #131214;"
          >
            Invite a Validator
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Community card -->
      <div class="bg-white border border-[#e5e5e5] rounded-[12px] overflow-hidden flex flex-col">
        <div class="relative flex items-center justify-center" style="min-height: 240px;">
          <img src={roleBgCommunity} alt="" class="absolute inset-0 w-full h-full object-contain opacity-30 pointer-events-none" />
          <img src={iconShare2} alt="Community" class="relative z-10 w-20 h-20" />
        </div>
        <div class="p-5 md:p-6 flex flex-col flex-1 gap-3">
          <h3 class="text-[22px] md:text-[24px] font-semibold font-display" style="letter-spacing: -0.48px;">Community</h3>
          <p class="text-[14px] md:text-[15px] text-[#656567] leading-relaxed">
            Create content, spread the word, and bring new contributors through referrals and outreach.
          </p>
          <button
            class="flex items-center justify-center gap-2 w-full h-11 mt-auto text-white font-medium rounded-full text-sm transition-opacity hover:opacity-90"
            style="background-color: #131214;"
          >
            Invite Community
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- CTA Footer Section -->
  <div class="relative overflow-hidden rounded-[24px]">
    <img
      src={hexagonRevealCta}
      alt=""
      class="absolute inset-0 w-full h-full object-contain pointer-events-none"
    />
    <div class="relative z-10 flex flex-col items-center text-center px-4 md:px-8 py-16 md:py-32">
      <h2 class="text-[28px] md:text-[64px] font-medium font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
        Let's Build Together
      </h2>
      <p class="text-[15px] md:text-[17px] text-[#656567] max-w-xl mb-8">
        Every person you bring into GenLayer earns you 10% of their contribution points — forever.
      </p>
      <button
        class="inline-flex items-center gap-2 h-12 px-8 text-white font-medium rounded-full text-base transition-opacity hover:opacity-90"
        style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
      >
        Get Your Referral Link
        <img src={arrowRightWhite} alt="" class="w-4 h-4" />
      </button>
    </div>
  </div>
</div>
