<script>
  import heroBackground from '../assets/hackathon/hero-background.jpg';
  import prizeBackground from '../assets/hackathon/prize-background.jpg';
  import ctaBackground from '../assets/hackathon/cta-background.jpg';
  import bulletIcon from '../assets/hackathon/bullet-icon.png';
  import perkIcon1 from '../assets/hackathon/perk-icon-1.png';
  import perkIcon2 from '../assets/hackathon/perk-icon-2.png';
  import perkIcon3 from '../assets/hackathon/perk-icon-3.png';
  import glLogoHero from '../assets/hackathon/gl-logo-hero.svg';
  import badgeBuilder from '../assets/hackathon/badge-builder.svg';
  import badgeValidator from '../assets/hackathon/badge-validator.svg';
  import badgeCommunity from '../assets/hackathon/badge-community.svg';
  import playIcon from '../assets/hackathon/play-icon.svg';
  import trackPrediction from '../assets/hackathon/track-prediction.svg';
  import trackGovernance from '../assets/hackathon/track-governance.svg';
  import trackWork from '../assets/hackathon/track-work.svg';
  import trackJustice from '../assets/hackathon/track-justice.svg';
  import trackGaming from '../assets/hackathon/track-gaming.svg';
  import trackConsensus from '../assets/hackathon/track-consensus.svg';
  import arrowRightDouble from '../assets/hackathon/arrow-right-double.svg';
  import checkboxCircle from '../assets/hackathon/checkbox-circle.svg';
  import arrowRight from '../assets/hackathon/arrow-right.svg';
  import arrowRightDark from '../assets/hackathon/arrow-right-dark.svg';
  import pointsGradientIcon from '../assets/hackathon/points-gradient-icon.svg';
  import glSymbolSmall from '../assets/hackathon/gl-symbol-small.svg';

  const tracks = [
    { icon: trackPrediction, title: 'Prediction Markets & P2P Betting', description: 'Bet, predict, and trade on future outcomes with on-chain markets.', featured: false },
    { icon: trackGovernance, title: 'AI Governance', description: 'AI-driven decisions and coordination between humans and agents.', featured: false },
    { icon: trackWork, title: 'Future of Work', description: 'AI-verified deliverables, reputation tracking, and outcome-based payments.', featured: false },
    { icon: trackJustice, title: 'Onchain Justice', description: 'Decentralized arbitration with AI-evaluated evidence and fair dispute resolution.', featured: false },
    { icon: trackGaming, title: 'AI Gaming', description: 'Multiplayer games exploring coordination, social dynamics, and consensus.', featured: false },
    { icon: trackConsensus, title: 'Bradbury: Subjective Consensus', description: 'Analyse and improve Bradbury\'s consensus: greyboxing, model routing, branchmarks, and appeals.', featured: true },
  ];

  const perks = [
    { icon: perkIcon1, title: 'Mentorship', subtitle: 'Guidance from GenLayer core team' },
    { icon: perkIcon2, title: 'Funding Opportunities', subtitle: 'Access to funding for top projects' },
    { icon: perkIcon3, title: 'Accelerator Program', subtitle: 'Fast-track your project\'s growth' },
    { icon: perkIcon1, title: 'Builders Working Group', subtitle: 'Invitations to the inner circle' },
    { icon: perkIcon2, title: 'Spotlights', subtitle: 'Virtual Demo Day for winners & mentions' },
    { icon: perkIcon3, title: 'Community Recognition', subtitle: 'Featured across GenLayer channels' },
  ];
</script>

<div class="flex flex-col gap-4 md:gap-6 max-w-[1200px] mx-auto pb-12 px-1 md:px-3">

  <!-- Hero Banner -->
  <section class="relative rounded-lg overflow-hidden">
    <img src={heroBackground} alt="" class="w-full h-auto min-h-[350px] md:min-h-0 object-cover" />
    <div class="absolute inset-0 flex items-center justify-center p-4 md:p-8">
      <div class="inline-grid relative scale-[0.42] sm:scale-[0.55] md:scale-75 lg:scale-100" style="grid-template-columns: max-content; grid-template-rows: max-content;">
        <!-- GenLayer Logo -->
        <img src={glLogoHero} alt="GenLayer" class="col-start-1 row-start-1 h-[58px] w-auto ml-[145px]" />
        <!-- TESTNET BRADBURY (centered above Hackathon) -->
        <div class="col-start-1 row-start-1 flex items-center justify-center ml-[100px] mt-[21px]" style="height: 128px; width: 587px;">
          <span class="text-white font-display font-bold text-[64px] leading-normal tracking-[-4.48px] whitespace-nowrap" style="transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">TESTNET BRADBURY</span>
        </div>
        <!-- Hackathon (largest, determines grid size) -->
        <div class="col-start-1 row-start-1 flex items-center justify-center mt-[30px]" style="height: 275px; width: 788px;">
          <span class="text-white font-display font-bold text-[160px] leading-normal tracking-[-11.2px] whitespace-nowrap" style="transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">Hackathon</span>
        </div>
        <!-- Date -->
        <span class="col-start-1 row-start-1 text-white text-[20px] uppercase italic leading-none whitespace-nowrap ml-[516px] mt-[217px]">March 20th - April 3rd</span>
      </div>
    </div>
    <div class="absolute bottom-4 right-4 md:bottom-8 md:right-8 flex gap-1">
      <img src={badgeBuilder} alt="" class="w-8 h-8 md:w-12 md:h-12" />
      <img src={badgeValidator} alt="" class="w-8 h-8 md:w-12 md:h-12" />
      <img src={badgeCommunity} alt="" class="w-8 h-8 md:w-12 md:h-12" />
    </div>
  </section>

  <!-- About Section -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-3 md:pt-5 px-0 md:px-5">
    <!-- Left column -->
    <div class="flex flex-col gap-4">
      <h2 class="text-[24px] md:text-[40px] font-display font-medium leading-[32px] md:leading-[48px] tracking-[-0.48px] md:tracking-[-0.8px] text-black">The first testnet where AI directly participates in blockchain consensus</h2>
      <p class="text-[#6b6b6b] text-[15px] md:text-[17px] leading-[24px] md:leading-[28px] tracking-[0.34px]">
        Bradbury marks the transition from infrastructure setup (Asimov) to active AI-driven validation and experimentation.
      </p>
      <div class="space-y-2">
        <div class="flex items-center gap-3">
          <img src={bulletIcon} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Validators choose and optimize LLMs</span>
        </div>
        <div class="flex items-center gap-3">
          <img src={bulletIcon} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Intelligent Contracts run in a decentralized AI consensus</span>
        </div>
        <div class="flex items-center gap-3">
          <img src={bulletIcon} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Performance, security, and economics are tested live</span>
        </div>
      </div>
      <a href="https://genlayer.com/blog/bradbury" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-[#4083ea] text-[14px] font-medium tracking-[0.28px] hover:underline">
        Read more about Bradbury →
      </a>
    </div>

    <!-- Right column - Video placeholder -->
    <div class="bg-[#f5f5f5] rounded-lg flex flex-col items-center justify-center min-h-[250px] md:min-h-[400px] border border-[#f0f0f0]">
      <div class="w-14 h-14 rounded-full bg-[#f0f0f0] flex items-center justify-center mb-3">
        <img src={playIcon} alt="" class="w-6 h-6 opacity-40" />
      </div>
      <span class="text-[#ababab] text-[12px] tracking-[0.24px]">Video coming soon</span>
    </div>
  </section>

  <!-- Prize Section -->
  <section class="relative rounded-lg overflow-hidden">
    <img src={prizeBackground} alt="" class="w-full h-auto min-h-[200px] md:min-h-0 object-cover" />
    <div class="absolute inset-0 flex items-center justify-center p-4 md:p-8">
      <div class="inline-grid relative scale-[0.42] sm:scale-[0.55] md:scale-75 lg:scale-100" style="grid-template-columns: max-content; grid-template-rows: max-content;">
        <!-- $5,000 (largest, left-aligned, determines grid size) -->
        <div class="col-start-1 row-start-1 flex items-center justify-center" style="width: 501px; height: 234px;">
          <span class="text-white font-display font-bold text-[144px] leading-normal tracking-[-10.08px] whitespace-nowrap" style="transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">$5,000</span>
        </div>
        <!-- Prizes & Perks pill (centered above) -->
        <div class="col-start-1 row-start-1 ml-[199px] mt-[16px]">
          <span class="inline-flex items-center justify-center px-4 py-2 rounded-[20px] bg-black text-[#e3e3e3] text-[16px] leading-[24px] border border-[#3f3f3f] whitespace-nowrap">
            Prizes & Perks
          </span>
        </div>
        <!-- + Builder [icon] Points (bottom-right) -->
        <div class="col-start-1 row-start-1 flex items-center gap-1 ml-[211px] mt-[171px]">
          <span class="text-[40px] font-display font-medium leading-[56px] tracking-[-0.8px] text-center whitespace-nowrap" style="background: linear-gradient(110deg, #f8b93d 15%, #ee8d24 50%, #db6917 85%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">+</span>
          <span class="text-white text-[40px] font-display font-medium leading-[56px] tracking-[-0.8px] text-center whitespace-nowrap">Builder</span>
          <!-- Rotated hexagon icon with GL symbol -->
          <div class="relative shrink-0 flex items-center justify-center" style="width: 71px; height: 71px;">
            <div class="rotate-[6.37deg]" style="width: 64px; height: 64px;">
              <img src={pointsGradientIcon} alt="" class="absolute inset-0 w-full h-full" />
              <div class="absolute inset-0 flex items-center justify-center">
                <img src={glSymbolSmall} alt="" class="w-[34px] h-[34px]" />
              </div>
            </div>
          </div>
          <span class="text-white text-[40px] font-display font-medium leading-[56px] tracking-[-0.8px] text-center whitespace-nowrap">Points</span>
        </div>
      </div>
    </div>
  </section>

  <!-- Choose Your Track -->
  <section class="flex flex-col gap-4 md:gap-6">
    <div class="flex flex-col gap-4 md:gap-6">
      <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[32px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">Choose your track</h2>
      <p class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Build an Intelligent Contract with Optimistic Democracy consensus and Equivalence Principle</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each tracks as track}
        <div class="rounded-lg p-[21px] flex flex-col gap-3 {track.featured ? 'text-white' : 'bg-white border border-[#f0f0f0]'}"
             style={track.featured ? 'background: linear-gradient(to bottom, #be8ff5, #ac6df3)' : ''}>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 {track.featured ? 'bg-white/20' : ''}"
                 style={track.featured ? '' : 'background: linear-gradient(to bottom, #be8ff5, #ac6df3)'}>
              <img src={track.icon} alt="" class="w-5 h-5 brightness-0 invert" />
            </div>
            <h3 class="font-display font-medium text-[18px] md:text-[20px] leading-[22px] md:leading-[24px] tracking-[-0.6px] {track.featured ? 'text-white' : 'text-black'}">{track.title}</h3>
          </div>
          <p class="text-[14px] leading-[21px] {track.featured ? 'text-white/80' : 'text-[#6b6b6b]'}">{track.description}</p>
        </div>
      {/each}
    </div>
  </section>

  <!-- Timeline Section -->
  <section class="flex flex-col gap-6 md:gap-10 items-center py-3 md:p-5 max-w-full">
    <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-center text-black">Timeline</h2>
    <div class="flex flex-col md:flex-row md:flex-nowrap items-start gap-3 w-full">
      <!-- Hacking Period -->
      <div class="flex flex-col gap-3 md:gap-4 w-full md:w-auto md:shrink-0">
        <div class="flex items-center justify-center px-3 py-2 md:px-6 md:py-4 rounded-[32px] text-white text-[16px] md:text-[32px] leading-[16px] md:leading-[32px] tracking-[-0.32px] md:tracking-[-0.64px] font-display font-medium relative whitespace-nowrap"
             style="background: linear-gradient(170deg, #f8b93d, #ee8d24, #db6917);">
          March 20th - April 3rd
          <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
        </div>
        <div class="flex flex-col gap-[11px] px-3 md:px-6 text-center md:text-left">
          <h3 class="text-[16px] md:text-[20px] font-semibold leading-[18px] md:leading-[21px] tracking-[0.28px] text-[#6b6b6b]">Hacking Period</h3>
          <p class="text-[11px] md:text-[12px] leading-[14px] md:leading-[15px] text-[#ababab] tracking-[0.24px]">2 Weeks to build your project</p>
        </div>
      </div>

      <!-- Arrow (desktop only) -->
      <div class="hidden md:flex items-center p-5 rounded-[32px] shrink-0 relative"
           style="background: linear-gradient(135deg, #1f1f1f, #0f0f0f, #000);">
        <img src={arrowRightDouble} alt="" class="w-6 h-6" />
        <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
      </div>

      <!-- Judging Process -->
      <div class="flex flex-col gap-3 md:gap-4 w-full md:w-auto md:shrink-0">
        <div class="flex items-center justify-center px-3 py-2 md:px-6 md:py-4 rounded-[32px] text-white text-[16px] md:text-[32px] leading-[16px] md:leading-[32px] tracking-[-0.32px] md:tracking-[-0.64px] font-display font-medium relative whitespace-nowrap"
             style="background: linear-gradient(169deg, #6da7f3, #387de8, #2159d2);">
          April 3rd - April 10th
          <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
        </div>
        <div class="flex flex-col gap-[11px] px-3 md:px-6 text-center md:text-left">
          <h3 class="text-[16px] md:text-[20px] font-semibold leading-[18px] md:leading-[21px] tracking-[0.28px] text-[#6b6b6b]">Judging Process</h3>
          <p class="text-[11px] md:text-[12px] leading-[14px] md:leading-[15px] text-[#ababab] tracking-[0.24px]">Projects reviewed by expert panel</p>
        </div>
      </div>

      <!-- Arrow (desktop only) -->
      <div class="hidden md:flex items-center p-5 rounded-[32px] shrink-0 relative"
           style="background: linear-gradient(135deg, #1f1f1f, #0f0f0f, #000);">
        <img src={arrowRightDouble} alt="" class="w-6 h-6" />
        <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
      </div>

      <!-- Closing Remarks -->
      <div class="flex flex-col gap-3 md:gap-4 w-full md:w-auto md:shrink-0">
        <div class="flex items-center justify-center px-3 py-2 md:px-6 md:py-4 rounded-[32px] text-white text-[16px] md:text-[32px] leading-[16px] md:leading-[32px] tracking-[-0.32px] md:tracking-[-0.64px] font-display font-medium relative whitespace-nowrap"
             style="background: linear-gradient(161deg, #a77fee, #7f52e1, #5f33ca);">
          April 10th
          <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
        </div>
        <div class="flex flex-col gap-[11px] px-3 md:px-6 text-center md:text-left">
          <h3 class="text-[16px] md:text-[20px] font-semibold leading-[18px] md:leading-[21px] tracking-[0.28px] text-[#6b6b6b]">Closing Remarks</h3>
          <p class="text-[11px] md:text-[12px] leading-[14px] md:leading-[15px] text-[#ababab] tracking-[0.24px]">Virtual Demo Day for winners & mentions</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Requirements Section -->
  <section class="flex flex-col items-center py-3 md:p-5">
    <div class="flex flex-col gap-4 md:gap-6 items-center w-full">
      <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-black text-center">Requirements</h2>
      <p class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px] text-center">Your project must include an Intelligent Contract with:</p>
      <div class="inline-flex flex-wrap justify-center items-start gap-3 px-3 py-2 rounded-[22px] border border-[#a77fee]">
        <div class="flex items-center gap-2.5">
          <img src={checkboxCircle} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px] whitespace-nowrap">Optimistic Democracy consensus</span>
        </div>
        <div class="flex items-center gap-2.5">
          <img src={checkboxCircle} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px] whitespace-nowrap">Equivalence Principle</span>
        </div>
      </div>
    </div>
  </section>

  <!-- Perks Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
    {#each perks as perk}
      <div class="bg-white border border-[#f0f0f0] rounded-lg p-[21px] flex items-start gap-4" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <img src={perk.icon} alt="" class="w-12 h-12 shrink-0" />
        <div class="flex flex-col gap-1">
          <h4 class="text-[18px] md:text-[20px] font-medium leading-[23px] md:leading-[25px] tracking-[0.4px] text-black">{perk.title}</h4>
          <p class="text-[14px] leading-[21px] text-[#6b6b6b] tracking-[0.28px]">{perk.subtitle}</p>
        </div>
      </div>
    {/each}
  </div>

  <!-- Sponsors Section -->
  <section class="flex flex-col gap-4 md:gap-6 items-center py-3 md:py-5">
    <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-center text-black">Sponsors</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 w-full">
      {#each Array(4) as _, i}
        <div class="bg-white border border-[#f0f0f0] rounded-lg h-24 flex items-center justify-center">
          <span class="text-[#e3e3e3] text-[14px] font-medium tracking-[0.28px]">Logo</span>
        </div>
      {/each}
    </div>
  </section>

  <!-- CTA Footer -->
  <section class="relative rounded-lg overflow-hidden">
    <img src={ctaBackground} alt="" class="w-full h-auto min-h-[400px] md:min-h-0 object-cover" />
    <div class="absolute inset-0 flex flex-col items-center justify-center gap-4 md:gap-6 p-4 md:p-8">
      <span class="inline-flex items-center justify-center h-8 md:h-10 px-3 md:px-4 rounded-[20px] bg-white/10 text-[#f5f5f5] text-[11px] md:text-[12px] font-medium tracking-[0.24px]">
        March 20th - April 3rd
      </span>
      <h2 class="text-white font-display font-medium text-[28px] sm:text-[40px] md:text-[64px] leading-[32px] sm:leading-[44px] md:leading-[64px] tracking-[-0.56px] sm:tracking-[-0.8px] md:tracking-[-1.28px] text-center">
        Let's build Together
      </h2>
      <p class="text-white text-[14px] md:text-[17px] leading-[22px] md:leading-[28px] tracking-[0.34px] text-center max-w-[500px]">
        Join the first hackathon where AI participates in blockchain consensus. Register now on DoraHacks.
      </p>
      <div class="flex flex-col sm:flex-row items-center gap-2">
        <a href="https://dorahacks.io/hackathon/genlayer" target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-2 bg-[#9e4bf6] text-white h-10 rounded-[20px] px-4 text-[14px] font-medium tracking-[0.28px]">
          Register on DoraHacks
          <img src={arrowRight} alt="" class="w-4 h-4 brightness-0 invert" />
        </a>
        <a href="https://discord.gg/genlayer" target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-2 bg-[#f5f5f5] text-black h-10 rounded-[20px] px-4 text-[14px] font-medium tracking-[0.28px]">
          Join Discord
          <img src={arrowRightDark} alt="" class="w-4 h-4" />
        </a>
      </div>
      <p class="text-[#ababab] text-[11px] md:text-[12px] tracking-[0.24px] text-center">
        Open a ticket or contact <span class="text-[#9e4bf6]">@ras</span> on GenLayer's Discord
      </p>
    </div>
  </section>

</div>
