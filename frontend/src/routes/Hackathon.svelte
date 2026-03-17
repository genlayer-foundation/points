<script>
  import { setPageMeta, resetPageMeta } from '../lib/meta.js';
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
  import sponsorChutes from '../assets/hackathon/sponsors/chutes.webp';
  import sponsorPathrock from '../assets/hackathon/sponsors/pathrock.png';
  import sponsorStakeme from '../assets/hackathon/sponsors/stakeme.png';
  import sponsorCrouton from '../assets/hackathon/sponsors/crouton.webp';
  import FeaturedBuilds from '../components/portal/FeaturedBuilds.svelte';

  const sponsors = [
    { name: 'CHUTES', logo: sponsorChutes, url: 'https://chutes.ai', bg: '#131313' },
    { name: 'Pathrock Network', logo: sponsorPathrock, url: 'https://pathrocknetwork.org', bg: '#ffffff' },
    { name: 'Stakeme', logo: sponsorStakeme, url: 'https://stakeme.pro', bg: '#ffffff' },
    { name: 'Crouton Digital', logo: sponsorCrouton, url: 'https://crouton.digital', bg: '#ffffff' },
  ].sort(() => Math.random() - 0.5);

  const heroTrack = {
    icon: trackPrediction,
    title: 'Agentic Economy Infrastructure',
    description: 'Agents will soon start interacting with each other. Build the needed infra for their economy to flourish.',
    examples: [
      { label: 'internetcourt.org', url: 'https://internetcourt.org' },
      { label: 'mergeproof.com', url: 'https://mergeproof.com' },
      { label: 'molly.fun', url: 'https://molly.fun' },
    ],
  };

  const tracks = [
    { icon: trackGovernance, title: 'AI Governance', description: 'AI-driven decisions and coordination between humans and agents.', featured: false, examples: [
      { label: 'argue.fun', url: 'https://argue.fun' },
      { label: 'Progressive Autonomy in DAOs', url: 'https://drive.google.com/file/d/1mTwAxJIaP7G_gNvxxaH3lL0zkq8Td-cA/view' },
    ]},
    { icon: trackPrediction, title: 'Prediction Markets & P2P Betting', description: 'Bet, predict, and trade on future outcomes with on-chain markets. Be the first P2P betting platform onchain.', featured: false, examples: [
      { label: 'COFI bets', url: 'https://bet.courtofinternet.com/' },
      { label: 'P2P bets', url: 'https://p2p-betting-mu.vercel.app/create' },
      { label: 'Prediction Market Kit', url: 'https://pmkit.courtofinternet.com/' },
    ]},
    { icon: trackGaming, title: 'AI Gaming', description: 'Multiplayer games exploring coordination, social dynamics, and consensus.', featured: false, examples: [
      { label: 'Mochi: Saving the Consensus', url: 'https://guess-picture.onrender.com/mochi-quest' },
      { label: 'Unstoppable', url: 'https://unstoppable.fun/' },
    ]},
    { icon: trackWork, title: 'Future of Work', description: 'AI-verified deliverables, reputation tracking, and outcome-based payments.', featured: false, examples: [
      { label: 'rally.fun', url: 'https://rally.fun' },
      { label: 'mergeproof.com', url: 'https://mergeproof.com' },
    ]},
    { icon: trackJustice, title: 'Onchain Justice', description: 'Decentralized arbitration with AI-evaluated evidence and fair dispute resolution.', featured: false, examples: [
      { label: 'internetcourt.org', url: 'https://internetcourt.org' },
      { label: 'Cross border settlement', url: 'https://acastellana.github.io/conditional-payment-cross-border-trade/' },
    ]},
    { icon: trackConsensus, title: 'Bradbury Special Track', subtitle: 'Subjective Consensus', description: 'Analyse and improve Bradbury\'s consensus: greyboxing, model routing, branchmarks, and appeals.', featured: true, examples: [
      { label: 'Intelligent Oracle Polymarket Benchmark', url: 'https://genlayer-benchmark.vercel.app/' },
    ]},
  ];

  const perks = [
    { icon: perkIcon1, title: 'Mentorship', subtitle: 'Guidance from GenLayer core team' },
    { icon: perkIcon2, title: 'Funding Opportunities', subtitle: 'Access to funding for top projects' },
    { icon: perkIcon3, title: 'Accelerator Program', subtitle: 'Fast-track your project\'s growth' },
    { icon: perkIcon1, title: 'Builders Working Group', subtitle: 'Invitations to the inner circle' },
    { icon: perkIcon2, title: 'Spotlights', subtitle: 'Virtual Demo Day for winners & mentions' },
    { icon: perkIcon3, title: 'Community Recognition', subtitle: 'Featured across GenLayer channels' },
  ];

  $effect(() => {
    setPageMeta({
      title: 'Testnet Bradbury Hackathon',
      description: 'Build on GenLayer\'s AI-driven testnet. Compete for $5,000 in prizes and Builder Points. Deploy Intelligent Contracts with Optimistic Democracy consensus.',
      image: 'https://portal.genlayer.foundation/assets/hackathon_og_image.png',
      url: 'https://portal.genlayer.foundation/#/hackathon',
    });
    return () => resetPageMeta();
  });
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
      <a href="https://x.com/raskovsky/status/2008978733378724180" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-[#4083ea] text-[14px] font-medium tracking-[0.28px] hover:underline">
        Read more about Bradbury →
      </a>
    </div>

    <!-- Right column - Video -->
    <div class="flex items-center">
      <video
        class="w-full h-auto rounded-lg"
        controls
        playsinline
        preload="metadata"
        poster="https://res.cloudinary.com/dfqmoeawa/video/upload/so_0,f_jpg,q_auto/hackathon/genlayer-ad-hackathon.jpg"
      >
        <source src="https://res.cloudinary.com/dfqmoeawa/video/upload/q_auto/hackathon/genlayer-ad-hackathon.mp4" type="video/mp4" />
      </video>
    </div>
  </section>

  <!-- Dev Fee Section -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 my-[40px] px-0 md:px-5">
    <!-- Text column (first on mobile, right on desktop) -->
    <div class="flex flex-col gap-4 lg:order-last">
      <h2 class="text-[24px] md:text-[40px] font-display font-medium leading-[32px] md:leading-[48px] tracking-[-0.48px] md:tracking-[-0.8px] text-black">Build Once, Earn Forever</h2>
      <p class="text-[#6b6b6b] text-[15px] md:text-[17px] leading-[24px] md:leading-[28px] tracking-[0.34px]">
        Most hackathons give you a one-time prize. GenLayer gives you a revenue stream. Every Intelligent Contract deployed on GenLayer earns its creator up to 20% of all transaction fees it generates — permanently.
      </p>
      <p class="text-[#ababab] text-[13px] md:text-[14px] leading-[20px] md:leading-[22px] tracking-[0.28px]">
        Testnet contracts don't migrate, but the best builders do. Top hackathon projects get priority mainnet deployment and first access to GenLayer's dev fee model.
      </p>
      <a href="https://talks.genlayer.foundation/t/dev-fee-tokenomics-build-once-earn-forever/19" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-[#4083ea] text-[14px] font-medium tracking-[0.28px] hover:underline">
        Learn about the Dev Fee model →
      </a>
    </div>

    <!-- Benefit cards (second on mobile, left on desktop) -->
    <div class="flex flex-col gap-3 lg:order-first">
      <div class="bg-white border border-[#f0f0f0] rounded-lg p-[21px] flex flex-col gap-1.5" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <h4 class="text-[18px] md:text-[20px] font-medium leading-[23px] md:leading-[25px] tracking-[0.4px] text-black">Recurring Revenue</h4>
        <p class="text-[14px] leading-[21px] text-[#6b6b6b] tracking-[0.28px]">Earn from every transaction your contract processes, forever</p>
      </div>
      <div class="bg-white border border-[#f0f0f0] rounded-lg p-[21px] flex flex-col gap-1.5" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <h4 class="text-[18px] md:text-[20px] font-medium leading-[23px] md:leading-[25px] tracking-[0.4px] text-black">Scales With Adoption</h4>
        <p class="text-[14px] leading-[21px] text-[#6b6b6b] tracking-[0.28px]">More users means more fees, no cap on earnings</p>
      </div>
      <div class="bg-white border border-[#f0f0f0] rounded-lg p-[21px] flex flex-col gap-1.5" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <h4 class="text-[18px] md:text-[20px] font-medium leading-[23px] md:leading-[25px] tracking-[0.4px] text-black">Composability Bonus</h4>
        <p class="text-[14px] leading-[21px] text-[#6b6b6b] tracking-[0.28px]">Other devs building on your contract amplify your revenue</p>
      </div>
    </div>
  </section>

  <!-- Prize Section -->
  <section class="relative rounded-lg overflow-hidden">
    <img src={prizeBackground} alt="" class="w-full h-auto min-h-[200px] md:min-h-0 object-cover" />
    <div class="absolute inset-0 flex items-center justify-center p-4 md:p-8">
      <div class="inline-grid relative scale-[0.42] sm:scale-[0.55] md:scale-75 lg:scale-100" style="grid-template-columns: max-content; grid-template-rows: max-content;">
        <!-- Builder Points (largest, center, determines grid size) -->
        <div class="col-start-1 row-start-1 flex items-center justify-center gap-2" style="width: 501px; height: 234px;">
          <span class="text-white font-display font-bold text-[120px] leading-normal tracking-[-8px] whitespace-nowrap" style="transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">Builder</span>
          <!-- Rotated hexagon icon with GL symbol -->
          <div class="relative shrink-0 flex items-center justify-center" style="width: 100px; height: 100px; transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">
            <div style="width: 90px; height: 90px;">
              <img src={pointsGradientIcon} alt="" class="absolute inset-0 w-full h-full" />
              <div class="absolute inset-0 flex items-center justify-center">
                <img src={glSymbolSmall} alt="" class="w-[48px] h-[48px]" />
              </div>
            </div>
          </div>
          <span class="text-white font-display font-bold text-[120px] leading-normal tracking-[-8px] whitespace-nowrap" style="transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">Points</span>
        </div>
        <!-- Prizes & Perks pill (centered above) -->
        <div class="col-start-1 row-start-1 ml-[199px] mt-[16px]">
          <span class="inline-flex items-center justify-center px-4 py-2 rounded-[20px] bg-black text-[#e3e3e3] text-[16px] leading-[24px] border border-[#3f3f3f] whitespace-nowrap">
            Prizes & Perks
          </span>
        </div>
        <!-- +$5,000 (bottom-right, smaller) -->
        <div class="col-start-1 row-start-1 flex items-center justify-end gap-1 mt-[171px]">
          <span class="text-[40px] font-display font-medium leading-[56px] tracking-[-0.8px] whitespace-nowrap" style="background: linear-gradient(110deg, #f8b93d 15%, #ee8d24 50%, #db6917 85%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">+</span>
          <span class="text-white text-[40px] font-display font-medium leading-[56px] tracking-[-0.8px] whitespace-nowrap">$5,000</span>
        </div>
      </div>
    </div>
  </section>

  <!-- Choose Your Track -->
  <section class="flex flex-col gap-4 md:gap-6">
    <div class="flex flex-col gap-4 md:gap-6">
      <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[32px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">Choose your track</h2>
      <p class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Build an Intelligent Contract with Optimistic Democracy consensus and Equivalence Principle</p>
      <p class="text-[14px] md:text-[15px] text-[#6b6b6b] leading-[22px] md:leading-[24px] tracking-[0.28px]">Each track includes example projects to inspire what you could build.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      <!-- Hero Track - spans full width -->
      <div class="md:col-span-2 lg:col-span-3 rounded-lg p-[21px] md:p-[28px] flex flex-col gap-4 text-white relative overflow-hidden"
           style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);">
        <div class="absolute top-0 right-0 w-[300px] h-[300px] rounded-full opacity-[0.07]" style="background: radial-gradient(circle, #f8b93d, transparent 70%); transform: translate(30%, -30%);"></div>
        <div class="absolute bottom-0 left-0 w-[200px] h-[200px] rounded-full opacity-[0.05]" style="background: radial-gradient(circle, #a77fee, transparent 70%); transform: translate(-30%, 30%);"></div>
        <div class="relative flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div class="flex flex-col gap-3 md:max-w-[65%]">
            <div class="flex items-center gap-3">
              <div class="w-11 h-11 rounded-full flex items-center justify-center shrink-0" style="background: linear-gradient(135deg, #f8b93d, #ee8d24);">
                <img src={heroTrack.icon} alt="" class="w-5 h-5 brightness-0 invert" />
              </div>
              <h3 class="font-display font-medium text-[20px] md:text-[24px] leading-[24px] md:leading-[28px] tracking-[-0.6px] text-white">{heroTrack.title}</h3>
            </div>
            <p class="text-[14px] md:text-[15px] leading-[22px] text-white/70">{heroTrack.description}</p>
          </div>
          <div class="flex flex-col gap-2 md:items-end shrink-0">
            <span class="text-[11px] uppercase tracking-[1px] text-white/40 font-medium">Examples</span>
            <div class="flex flex-wrap md:justify-end gap-2">
              {#each heroTrack.examples as example}
                <a href={example.url} target="_blank" rel="noopener noreferrer"
                   class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium text-white/90 hover:text-white transition-colors"
                   style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);">
                  {example.label}
                  <svg class="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              {/each}
            </div>
          </div>
        </div>
      </div>

      <!-- Regular Tracks -->
      {#each tracks as track}
        <div class="rounded-lg p-[21px] flex flex-col gap-3 {track.featured ? 'text-white' : 'bg-white border border-[#f0f0f0]'}"
             style={track.featured ? 'background: linear-gradient(to bottom, #be8ff5, #ac6df3)' : ''}>
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 {track.featured ? 'bg-white/20' : ''}"
                 style={track.featured ? '' : 'background: linear-gradient(to bottom, #be8ff5, #ac6df3)'}>
              <img src={track.icon} alt="" class="w-5 h-5 brightness-0 invert" />
            </div>
            <div class="flex flex-col">
              <h3 class="font-display font-medium text-[18px] md:text-[20px] leading-[22px] md:leading-[24px] tracking-[-0.6px] {track.featured ? 'text-white' : 'text-black'}">{track.title}</h3>
              {#if track.subtitle}
                <span class="text-[12px] {track.featured ? 'text-white/60' : 'text-[#ababab]'}">{track.subtitle}</span>
              {/if}
            </div>
          </div>
          <p class="text-[14px] leading-[21px] {track.featured ? 'text-white/80' : 'text-[#6b6b6b]'}">{track.description}</p>
          {#if track.examples?.length}
            <div class="flex flex-wrap gap-1.5 mt-auto pt-1">
              {#each track.examples as example}
                <a href={example.url} target="_blank" rel="noopener noreferrer"
                   class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors {track.featured ? 'text-white/80 hover:text-white' : 'text-[#6b6b6b] hover:text-black'}"
                   style={track.featured ? 'background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2);' : 'background: #f5f5f5; border: 1px solid #ebebeb;'}>
                  {example.label}
                  <svg class="w-2.5 h-2.5 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <!-- Requirements & Timeline Section -->
  <section class="flex flex-col gap-6 md:gap-10 py-3 md:p-5 max-w-full">
    <div class="flex flex-col lg:flex-row gap-[24px] w-full">
      <!-- Requirements (Left) -->
      <div class="flex-1 flex items-center justify-center p-5">
        <div class="flex flex-col gap-[24px] items-start justify-center">
          <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-black">Requirements</h2>
          <p class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Your project must include an Intelligent Contract with:</p>
          <div class="flex flex-col gap-3">
            <div class="inline-flex items-center gap-2.5 px-3 py-2 rounded-[22px] border border-[#a77fee]">
              <img src={checkboxCircle} alt="" class="w-4 h-4 shrink-0" />
              <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px] whitespace-nowrap">Optimistic Democracy consensus</span>
            </div>
            <div class="inline-flex items-center gap-2.5 px-3 py-2 rounded-[22px] border border-[#a77fee]">
              <img src={checkboxCircle} alt="" class="w-4 h-4 shrink-0" />
              <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px] whitespace-nowrap">Equivalence Principle</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Timeline (Right) -->
      <div class="flex-1 flex flex-col gap-[40px] items-center justify-center p-5">
        <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-black text-center">Timeline</h2>
        <div class="flex flex-col gap-3 items-center justify-center w-full">
          <!-- Hacking Period -->
          <div class="flex items-start justify-between w-full">
            <div class="flex flex-col gap-[11px] px-3">
              <h3 class="text-[20px] md:text-[24px] font-display font-medium leading-[24px] tracking-[-0.72px] text-black">Hacking Period</h3>
              <p class="text-[12px] leading-[15px] text-[#ababab] tracking-[0.24px]">2 Weeks to build your project</p>
            </div>
            <div class="flex items-center justify-center px-3 py-2 rounded-[32px] shrink-0 relative whitespace-nowrap"
                 style="background: linear-gradient(170deg, #f8b93d, #ee8d24, #db6917);">
              <span class="text-white text-[16px] md:text-[20px] font-display font-medium leading-[24px] md:leading-[32px] tracking-[-0.4px]">March 20th - April 3rd</span>
              <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
            </div>
          </div>

          <!-- Arrow Down -->
          <div class="flex items-center justify-center w-[48px] h-[48px]">
            <div class="flex items-center p-3 rounded-[32px] relative rotate-90"
                 style="background: linear-gradient(135deg, #1f1f1f, #0f0f0f, #000);">
              <img src={arrowRightDouble} alt="" class="w-6 h-6" />
              <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
            </div>
          </div>

          <!-- Judging Process -->
          <div class="flex items-start justify-between w-full">
            <div class="flex flex-col gap-[11px] px-3">
              <h3 class="text-[20px] md:text-[24px] font-display font-medium leading-[24px] tracking-[-0.72px] text-black">Judging Process</h3>
              <p class="text-[12px] leading-[15px] text-[#ababab] tracking-[0.24px]">Projects reviewed by expert panel</p>
            </div>
            <div class="flex items-center justify-center px-3 py-2 rounded-[32px] shrink-0 relative whitespace-nowrap"
                 style="background: linear-gradient(169deg, #6da7f3, #387de8, #2159d2);">
              <span class="text-white text-[16px] md:text-[20px] font-display font-medium leading-[24px] md:leading-[32px] tracking-[-0.4px]">April 3rd - April 10th</span>
              <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
            </div>
          </div>

          <!-- Arrow Down -->
          <div class="flex items-center justify-center w-[48px] h-[48px]">
            <div class="flex items-center p-3 rounded-[32px] relative rotate-90"
                 style="background: linear-gradient(135deg, #1f1f1f, #0f0f0f, #000);">
              <img src={arrowRightDouble} alt="" class="w-6 h-6" />
              <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
            </div>
          </div>

          <!-- Closing Remarks -->
          <div class="flex items-start justify-between w-full">
            <div class="flex flex-col gap-[11px] px-3">
              <h3 class="text-[20px] md:text-[24px] font-display font-medium leading-[24px] tracking-[-0.72px] text-black">Closing Remarks</h3>
              <p class="text-[12px] leading-[15px] text-[#ababab] tracking-[0.24px]">Virtual Demo Day for winners & mentions</p>
            </div>
            <div class="flex items-center justify-center px-3 py-2 rounded-[32px] shrink-0 relative whitespace-nowrap"
                 style="background: linear-gradient(161deg, #a77fee, #7f52e1, #5f33ca);">
              <span class="text-white text-[16px] md:text-[20px] font-display font-medium leading-[24px] md:leading-[32px] tracking-[-0.4px]">April 10th</span>
              <div class="absolute inset-0 pointer-events-none rounded-[inherit]" style="box-shadow: inset 0.5px 0.5px 4px rgba(0,0,0,0.05), inset 1px 1px 2px rgba(255,255,255,0.5), inset -0.5px -0.5px 2px rgba(0,0,0,0.25), inset -1px -1px 2px rgba(255,255,255,0.15);"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Perks -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 w-full">
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
  </section>

  <!-- Featured Projects -->
  <FeaturedBuilds title="What We Expect" subtitle="Projects built on GenLayer that show what's possible" />

  <!-- Sponsors Section -->
  <section class="flex flex-col gap-4 md:gap-6 items-center py-3 md:py-5">
    <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-center text-black">Sponsors</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 w-full">
      {#each sponsors as sponsor}
        <a href={sponsor.url} target="_blank" rel="noopener noreferrer" class="border border-[#f0f0f0] rounded-lg h-24 overflow-hidden flex items-center justify-center hover:border-[#e3e3e3] transition-colors" style="background: {sponsor.bg};">
          <img src={sponsor.logo} alt={sponsor.name} class="h-full object-contain" />
        </a>
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
        <a href="https://dorahacks.io/hackathon/genlayer-bradbury" target="_blank" rel="noopener noreferrer"
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
