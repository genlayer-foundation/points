<script>
  import { setPageMeta, resetPageMeta } from '../lib/meta.js';
  import heroBackground from '../assets/hackathon/hero-background.jpg';
  import ctaBackground from '../assets/hackathon/cta-background.jpg';
  import bulletIcon from '../assets/hackathon/bullet-icon.png';
  import glLogoHero from '../assets/hackathon/gl-logo-hero.svg';
  import badgeBuilder from '../assets/hackathon/badge-builder.svg';
  import badgeValidator from '../assets/hackathon/badge-validator.svg';
  import badgeCommunity from '../assets/hackathon/badge-community.svg';
  import arrowRight from '../assets/hackathon/arrow-right.svg';
  import arrowRightDark from '../assets/hackathon/arrow-right-dark.svg';
  // Sponsor logos (white)
  import sponsorChutesWhite from '../assets/hackathon/sponsors/chutes-white.png';
  import sponsorStakemeWhite from '../assets/hackathon/sponsors/stakeme-white.svg';
  import sponsorCroutonWhite from '../assets/hackathon/sponsors/crouton-white.svg';
  import sponsorPathrockWhite from '../assets/hackathon/sponsors/pathrock-white.svg';
  import ProjectCard from '../components/hackathon/ProjectCard.svelte';
  import {
    hackathonStats,
    trackSubmissions,
    grandWinner,
    trackWinners,
    honorableMentions,
    winnersSponsors,
  } from '../data/hackathonWinners.js';

  // Map white sponsor logos to data (for bottom sponsors section)
  const sponsorWhiteLogos = {
    'Chutes': { src: sponsorChutesWhite, class: 'max-w-[120px] max-h-[36px]' },
    'Pathrock Network': { src: sponsorPathrockWhite, class: 'max-w-[60px] max-h-[60px]' },
    'StakeMe': { src: sponsorStakemeWhite, class: 'max-w-[130px] max-h-[28px]' },
    'Crouton Digital': { src: sponsorCroutonWhite, class: 'max-w-[100px] max-h-[40px]' },
  };

  const sponsors = winnersSponsors.map(s => ({
    ...s,
    logo: sponsorWhiteLogos[s.name]?.src || null,
    logoClass: sponsorWhiteLogos[s.name]?.class || 'max-w-[120px] max-h-[36px]',
  }));

  // Black hexagonal icons for stats (from public/assets/icons/)
  const statIcons = [
    '/assets/icons/hex-black-gl.svg',
    '/assets/icons/hex-black-people.svg',
    '/assets/icons/hex-black-calendar.svg',
  ];

  let tweetContainer = $state(null);
  let tweetLoaded = $state(false);
  let tweetError = $state(false);
  let grandWinnerXOpen = $state(false);
  let expandedMentions = $state({});

  // Close any open X dropdown on outside click
  $effect(() => {
    if (!grandWinnerXOpen) return;
    function handleClick() { grandWinnerXOpen = false; }
    const timer = setTimeout(() => document.addEventListener('click', handleClick), 0);
    return () => { clearTimeout(timer); document.removeEventListener('click', handleClick); };
  });

  const TWEET_ID = '2033965129922990190';

  $effect(() => {
    setPageMeta({
      title: 'Hackathon Winners - Testnet Bradbury',
      description: 'Meet the winners of GenLayer\'s Testnet Bradbury Hackathon. 135 BUIDLs, 280 hackers, built in 2 weeks.',
      image: 'https://portal.genlayer.foundation/assets/hackathon_og_image.png',
      url: 'https://portal.genlayer.foundation/#/hackathon-winners',
    });
    return () => resetPageMeta();
  });

  // Load Twitter widgets.js and render the embedded tweet via oembed blockquote.
  // We use the blockquote + twttr.widgets.load() approach instead of createTweet()
  // because createTweet() can silently fail with certain tweet IDs due to internal
  // numeric precision issues in the Twitter widget library.
  $effect(() => {
    if (!tweetContainer) return;

    // Inject the oembed blockquote HTML so twttr.widgets.load() can enhance it
    tweetContainer.innerHTML = `<blockquote class="twitter-tweet" data-dnt="true"><p lang="en" dir="ltr">Introducing the Bradbury Builders Hackathon, where your project pays you forever.<br><br>Build for humans and AI agents, and earn 10-20% of every transaction fee it generates. Not just during the hackathon, but FOREVER.<br><br>2 weeks, fully online, $5K+ in prizes, and 6 AI-native tracks. <a href="https://t.co/0bZFoE8BiD">pic.twitter.com/0bZFoE8BiD</a></p>&mdash; GenLayer (@GenLayer) <a href="https://twitter.com/GenLayer/status/${TWEET_ID}?ref_src=twsrc%5Etfw">March 17, 2026</a></blockquote>`;

    function loadTweet() {
      if (window.twttr && window.twttr.widgets) {
        window.twttr.widgets.load(tweetContainer).then(() => {
          // Check if the blockquote was replaced with an iframe (success)
          const iframe = tweetContainer.querySelector('iframe');
          if (iframe) {
            tweetLoaded = true;
          } else {
            // widgets.load() resolved but didn't render — treat as error
            tweetError = true;
            tweetLoaded = true;
          }
        }).catch(() => {
          tweetError = true;
          tweetLoaded = true;
        });
      }
    }

    if (window.twttr && window.twttr.widgets) {
      loadTweet();
    } else {
      const script = document.createElement('script');
      script.src = 'https://platform.twitter.com/widgets.js';
      script.async = true;
      script.charset = 'utf-8';
      script.onload = () => {
        if (window.twttr && window.twttr.ready) {
          window.twttr.ready(loadTweet);
        }
      };
      script.onerror = () => { tweetError = true; tweetLoaded = true; };
      document.head.appendChild(script);
    }
  });

  // Helper: parse twitter links — supports string, array of strings, or array of {handle, url}
  function getTwitterLinks(links) {
    if (!links.twitter) return [];
    if (typeof links.twitter === 'string') {
      const handle = links.twitter.replace('https://x.com/', '').replace('https://twitter.com/', '');
      return [{ handle: `@${handle}`, url: links.twitter }];
    }
    if (Array.isArray(links.twitter)) {
      return links.twitter.map(t => {
        if (typeof t === 'string') {
          const handle = t.replace('https://x.com/', '').replace('https://twitter.com/', '');
          return { handle: `@${handle}`, url: t };
        }
        return t;
      });
    }
    return [];
  }
</script>

<div class="flex flex-col gap-4 md:gap-6 max-w-[1200px] mx-auto pb-12 px-1 md:px-3">

  <!-- Hero Banner -->
  <section class="relative rounded-lg overflow-hidden">
    <img src={heroBackground} alt="" class="w-full h-auto min-h-[350px] md:min-h-0 object-cover" />
    <div class="absolute inset-0 flex items-center justify-center p-4 md:p-8">
      <div class="inline-grid relative scale-[0.35] sm:scale-[0.48] md:scale-[0.65] lg:scale-[0.85]" style="grid-template-columns: max-content; grid-template-rows: max-content;">
        <!-- GenLayer Logo -->
        <img src={glLogoHero} alt="GenLayer" class="col-start-1 row-start-1 h-[58px] w-auto ml-[200px]" />
        <!-- Hackathon -->
        <div class="col-start-1 row-start-1 flex items-center justify-center mt-[10px]" style="height: 275px; width: 788px;">
          <span class="text-white font-display font-bold text-[155px] leading-normal tracking-[-10.89px] whitespace-nowrap" style="transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">Hackathon</span>
        </div>
        <!-- Winners -->
        <div class="col-start-1 row-start-1 flex items-center justify-center ml-[306px] mt-[99px]" style="height: 256px; width: 580px;">
          <span class="text-white font-display font-bold text-[155px] leading-normal tracking-[-10.89px] whitespace-nowrap" style="transform: rotate(-3.75deg) skewX(-14.17deg) scaleY(0.97);">Winners</span>
        </div>
      </div>
    </div>
    <!-- Role icons -->
    <div class="absolute bottom-4 right-4 md:bottom-8 md:right-8 flex gap-1">
      <img src={badgeBuilder} alt="" class="w-8 h-8 md:w-12 md:h-12" />
      <img src={badgeValidator} alt="" class="w-8 h-8 md:w-12 md:h-12" />
      <img src={badgeCommunity} alt="" class="w-8 h-8 md:w-12 md:h-12" />
    </div>
    <!-- Sponsor logos in banner (white versions, uniform sizing) -->
    <div class="absolute bottom-[18%] left-1/2 -translate-x-1/2 flex items-center gap-5 md:gap-7">
      <a href="https://chutes.ai" target="_blank" rel="noopener noreferrer" class="hover:opacity-80 transition-opacity flex items-center justify-center w-[100px] md:w-[150px] h-[30px] md:h-[46px]">
        <img src={sponsorChutesWhite} alt="Chutes" class="max-w-full max-h-full object-contain" />
      </a>
      <a href="https://stakeme.pro" target="_blank" rel="noopener noreferrer" class="hover:opacity-80 transition-opacity flex items-center justify-center w-[130px] md:w-[180px] h-[24px] md:h-[34px]">
        <img src={sponsorStakemeWhite} alt="StakeMe" class="max-w-full max-h-full object-contain" />
      </a>
      <a href="https://crouton.digital" target="_blank" rel="noopener noreferrer" class="hover:opacity-80 transition-opacity flex items-center justify-center w-[90px] md:w-[130px] h-[34px] md:h-[50px]">
        <img src={sponsorCroutonWhite} alt="Crouton Digital" class="max-w-full max-h-full object-contain" />
      </a>
      <a href="https://pathrocknetwork.org" target="_blank" rel="noopener noreferrer" class="hover:opacity-80 transition-opacity flex items-center justify-center w-[46px] md:w-[60px] h-[46px] md:h-[60px]">
        <img src={sponsorPathrockWhite} alt="Pathrock Network" class="max-w-full max-h-full object-contain" />
      </a>
    </div>
  </section>

  <!-- Stats Bar -->
  <section class="grid grid-cols-1 md:grid-cols-3 gap-[13px]">
    {#each hackathonStats as stat, i}
      <div class="border border-[#f0f0f0] rounded-[8px] h-[80px] flex items-center overflow-hidden">
        <div class="flex items-center h-full">
          <div class="flex items-center p-4">
            <img src={statIcons[i]} alt="" class="w-12 h-12 shrink-0" />
          </div>
          <div class="flex flex-col justify-between h-full py-4">
            <span class="font-display font-medium text-[32px] leading-[32px] text-black tracking-[-0.96px]">{stat.value}</span>
            <span class="text-[12px] leading-[15px] text-[#6b6b6b] tracking-[0.24px]">{stat.label}</span>
          </div>
        </div>
      </div>
    {/each}
  </section>

  <!-- About Section -->
  <section class="flex flex-col lg:flex-row gap-6 pt-3 md:pt-5 px-0 md:px-5">
    <!-- Left column -->
    <div class="flex-1 flex flex-col gap-4">
      <h2 class="text-[24px] md:text-[40px] font-display font-medium leading-[32px] md:leading-[48px] tracking-[-0.48px] md:tracking-[-0.8px] text-black">What happens when builders get access to AI consensus</h2>
      <p class="text-[#6b6b6b] text-[15px] md:text-[17px] leading-[24px] md:leading-[28px] tracking-[0.34px]">
        135 teams took GenLayer's Intelligent Contracts and built products that make subjective decisions on-chain, from courtrooms to prediction markets to autonomous agent economies.
      </p>
      <div class="space-y-2">
        <div class="flex items-center gap-3">
          <img src={bulletIcon} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">AI agents that hire, pay, and arbitrate with each other</span>
        </div>
        <div class="flex items-center gap-3">
          <img src={bulletIcon} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Treasuries governed by community-written constitutions</span>
        </div>
        <div class="flex items-center gap-3">
          <img src={bulletIcon} alt="" class="w-4 h-4 shrink-0" />
          <span class="text-[15px] md:text-[17px] text-black leading-[24px] md:leading-[28px] tracking-[0.34px]">Bounties verified by reading actual code on GitHub</span>
        </div>
      </div>
      <p class="text-[#6b6b6b] text-[15px] md:text-[17px] leading-[24px] md:leading-[28px] tracking-[0.34px]">
        Every submission pushed the boundaries of what's possible on-chain. Here are the winners.
      </p>
      <a href="https://dorahacks.io/hackathon/genlayer-bradbury/buidl" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-[#4083ea] text-[14px] font-medium tracking-[0.28px] hover:underline">
        Explore all 135 projects →
      </a>

      <!-- BUIDLs by Tracks -->
      <div class="flex flex-col gap-4 mt-4">
        <h3 class="text-[24px] md:text-[32px] font-display font-medium leading-[32px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">BUIDLs by Tracks</h3>
        <div class="flex flex-col gap-3">
          {#each trackSubmissions as track}
            {@const maxCount = Math.max(...trackSubmissions.map(t => t.count))}
            {@const pct = (track.count / maxCount) * 100}
            <div class="flex items-center gap-3 w-full">
              <div class="flex-1 relative">
                <div class="bg-[#fbead5] rounded-[12px] h-[40px] md:h-[44px]" style="width: {pct}%; min-width: fit-content;">
                  <span class="font-display font-medium text-[16px] md:text-[20px] leading-[40px] md:leading-[44px] text-black tracking-[-0.6px] whitespace-nowrap px-3">{track.name}</span>
                </div>
              </div>
              <span class="font-display font-medium text-[20px] md:text-[24px] leading-[24px] text-[#e99322] tracking-[-0.72px] whitespace-nowrap">{track.count}</span>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Right column - Embedded X post -->
    <div class="flex-1 flex items-start">
      <div class="w-full sticky top-6">
        <!-- Skeleton loader -->
        {#if !tweetLoaded}
          <div class="w-full border border-[#e1e8ed] rounded-xl overflow-hidden bg-white animate-pulse">
            <div class="p-4 flex flex-col gap-3">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-full bg-[#f0f0f0] shrink-0"></div>
                <div class="flex flex-col gap-1.5 flex-1">
                  <div class="h-4 bg-[#f0f0f0] rounded w-32"></div>
                  <div class="h-3 bg-[#f0f0f0] rounded w-24"></div>
                </div>
                <svg class="w-5 h-5 text-[#e0e0e0]" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </div>
              <div class="flex flex-col gap-2">
                <div class="h-4 bg-[#f0f0f0] rounded w-full"></div>
                <div class="h-4 bg-[#f0f0f0] rounded w-full"></div>
                <div class="h-4 bg-[#f0f0f0] rounded w-3/4"></div>
              </div>
              <div class="h-48 bg-[#f0f0f0] rounded-lg w-full"></div>
              <div class="flex items-center gap-6 pt-1">
                <div class="h-4 bg-[#f0f0f0] rounded w-12"></div>
                <div class="h-4 bg-[#f0f0f0] rounded w-12"></div>
                <div class="h-4 bg-[#f0f0f0] rounded w-12"></div>
              </div>
            </div>
          </div>
        {/if}
        <!-- Tweet renders here -->
        <div bind:this={tweetContainer} style={tweetLoaded ? '' : 'position:absolute;opacity:0;pointer-events:none;'}></div>
        {#if tweetError}
          <a
            href="https://x.com/GenLayer/status/{TWEET_ID}"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center justify-center gap-2 mt-3 px-4 py-3 border border-[#e1e8ed] rounded-xl text-[14px] text-[#536471] hover:bg-[#f7f9f9] transition-colors"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
            View post on X
          </a>
        {/if}
      </div>
    </div>
  </section>

  <!-- Grand Winner -->
  <section class="flex flex-col gap-6 items-center py-5">
    <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-center text-black">Grand Winner</h2>
    <div class="flex flex-col lg:flex-row gap-[10px] w-full">
      <!-- Left: Large project card (image only) -->
      <div class="flex-1">
        <ProjectCard
          name={grandWinner.name}
          builder={grandWinner.builder}
          avatar={grandWinner.avatar}
          screenshot={grandWinner.screenshot}
          category={grandWinner.category}
          links={grandWinner.links}
          variant="large"
        />
      </div>
      <!-- Right: Description + Action buttons -->
      <div class="flex-1 flex flex-col justify-between gap-4">
        <div class="text-[#6b6b6b] text-[15px] md:text-[17px] leading-[24px] md:leading-[28px] tracking-[0.34px]">
          <p>{grandWinner.descriptionIntro}</p>
          {#if grandWinner.descriptionBullets}
            <ul class="mt-3 space-y-2">
              {#each grandWinner.descriptionBullets as bullet}
                <li class="flex gap-2">
                  <span class="text-[#9e4bf6] mt-[2px] shrink-0">•</span>
                  <span>{bullet}</span>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
        <div class="flex gap-2 items-start w-full">
          {#if grandWinner.links.project}
            <a
              href={grandWinner.links.project}
              target="_blank"
              rel="noopener noreferrer"
              class="bg-[#9e4bf6] flex flex-1 gap-2 h-[40px] items-center justify-center px-4 rounded-[20px] text-[14px] font-medium text-white tracking-[0.28px] whitespace-nowrap hover:bg-[#8a3de0] transition-colors"
            >
              View Project
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke-width="1.5" />
                <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke-width="1.5" />
              </svg>
            </a>
          {/if}
          {#if grandWinner.links.youtube}
            <a href={grandWinner.links.youtube} target="_blank" rel="noopener noreferrer" class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors">
              <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
                <path d="M21.543 6.498C22 8.28 22 12 22 12s0 3.72-.457 5.502c-.254.985-.997 1.76-1.938 2.022C17.896 20 12 20 12 20s-5.893 0-7.605-.476c-.945-.266-1.687-1.04-1.938-2.022C2 15.72 2 12 2 12s0-3.72.457-5.502c.254-.985.997-1.76 1.938-2.022C6.107 4 12 4 12 4s5.896 0 7.605.476c.945.266 1.687 1.04 1.938 2.022zM10 15.5l6-3.5-6-3.5v7z" />
              </svg>
            </a>
          {/if}
          {#if grandWinner.links.github}
            <a href={grandWinner.links.github} target="_blank" rel="noopener noreferrer" class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors">
              <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z" />
              </svg>
            </a>
          {/if}
          <!-- Twitter: single or dropdown -->
          {#if getTwitterLinks(grandWinner.links).length === 1}
            <a href={getTwitterLinks(grandWinner.links)[0].url} target="_blank" rel="noopener noreferrer" class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors">
              <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>
          {:else if getTwitterLinks(grandWinner.links).length > 1}
            <div class="relative">
              <button
                onclick={(e) => { e.preventDefault(); e.stopPropagation(); grandWinnerXOpen = !grandWinnerXOpen; }}
                class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors cursor-pointer"
              >
                <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </button>
              {#if grandWinnerXOpen}
                <div class="absolute bottom-full mb-2 right-0 bg-white border border-[#e8e8e8] rounded-xl shadow-lg overflow-hidden z-50 min-w-[180px] x-dropdown">
                  {#each getTwitterLinks(grandWinner.links) as tl}
                    <a href={tl.url} target="_blank" rel="noopener noreferrer" class="flex items-center gap-2.5 px-4 py-2.5 text-[14px] text-[#333] hover:bg-[#f5f5f5] transition-colors">
                      <svg class="w-4 h-4 text-[#666] shrink-0" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                      </svg>
                      {tl.handle}
                    </a>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </section>

  <!-- Hackathon Track Winners -->
  <section class="flex flex-col gap-6 items-center py-5">
    <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-center text-black">Hackathon Track Winners</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
      {#each trackWinners as winner}
        <ProjectCard
          name={winner.name}
          builder={winner.builder}
          avatar={winner.avatar}
          screenshot={winner.screenshot}
          category={winner.category}
          description={winner.description}
          links={winner.links}
          variant="medium"
        />
      {/each}
    </div>
  </section>

  <!-- Honorable Mentions -->
  <section class="flex flex-col gap-6 items-center py-5">
    <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-center text-black">Honorable Mentions</h2>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 w-full">
      {#each honorableMentions as mention}
        <div class="flex flex-col gap-3">
          <!-- Square card -->
          <a
            href={mention.links.website || mention.links.project || '#'}
            target={(mention.links.website || mention.links.project) ? '_blank' : undefined}
            rel={(mention.links.website || mention.links.project) ? 'noopener noreferrer' : undefined}
            class="relative rounded-[8px] overflow-hidden flex items-end justify-between p-3 aspect-square {mention.screenshot && mention.avatar !== mention.screenshot ? 'bg-black' : 'bg-gradient-to-br from-[#1a1a2e] to-[#16213e]'}"
          >
            {#if mention.screenshot && mention.avatar !== mention.screenshot}
              <img src={mention.screenshot} alt={mention.name} class="absolute inset-0 w-full h-full object-cover pointer-events-none" />
            {:else if mention.avatar}
              <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                <img src={mention.avatar} alt={mention.name} class="max-w-[45%] max-h-[45%] object-contain opacity-90" />
              </div>
            {/if}
            <!-- Category label -->
            <div class="flex flex-col h-full items-start justify-between relative z-10 w-full">
              <div class="backdrop-blur-[10px] bg-white/10 flex items-center p-1.5 rounded-[4px] self-start">
                <span class="text-[11px] md:text-[12px] font-medium leading-[14px] text-white whitespace-nowrap">{mention.category}</span>
              </div>
              <div class="flex gap-1 items-center mt-auto">
                {#if mention.avatar && mention.screenshot && mention.avatar !== mention.screenshot}
                  <img src={mention.avatar} alt={mention.builder} class="w-7 h-7 rounded-full object-cover shrink-0" />
                {:else if mention.avatar}
                  <img src={mention.avatar} alt={mention.builder} class="w-7 h-7 rounded-full object-contain bg-white/10 backdrop-blur-sm p-0.5 shrink-0" />
                {:else}
                  <div class="w-7 h-7 rounded-full bg-white/20 shrink-0"></div>
                {/if}
                <div class="flex flex-col justify-center whitespace-nowrap min-w-0">
                  <span class="text-[12px] font-medium leading-[16px] text-white truncate">{mention.name}</span>
                  <span class="text-[10px] leading-[13px] text-[#bbb] tracking-[0.2px]">by {mention.builder}</span>
                </div>
              </div>
            </div>
            <!-- Arrow icon -->
            <div class="absolute top-3 right-3 z-10">
              <div class="backdrop-blur-[10px] bg-white/10 flex items-center p-1.5 rounded-[4px]">
                <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17L17 7M17 7H7M17 7v10" />
                </svg>
              </div>
            </div>
          </a>
          <!-- Award label with gift icon -->
          {#if mention.awardLabel}
            <div class="flex gap-1.5 items-center">
              <svg class="w-5 h-5 text-[#6b6b6b] shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M15 2a4 4 0 0 1 3.464 6.001L23 8v2h-1v10a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V10H1V8l4.536.001A4 4 0 0 1 12 3.355 3.983 3.983 0 0 1 15 2zm-2 10h-2v8h2v-8zm-5 0H5v8h3v-8zm8 0h-3v8h3v-8zM9 4a2 2 0 0 0-.15 3.995L9 8h2V6a2 2 0 0 0-1.697-1.977l-.154-.018L9 4zm6 0a2 2 0 0 0-1.995 1.85L13 6v2h2a2 2 0 0 0 1.995-1.85L17 6a2 2 0 0 0-2-2z" />
              </svg>
              <span class="text-[13px] md:text-[14px] leading-[20px] text-[#6b6b6b] tracking-[0.28px]">{mention.awardLabel}</span>
            </div>
          {/if}
          <!-- Description with Show more -->
          {#if mention.description}
            <div class="flex flex-col gap-1">
              <p class="text-[12px] md:text-[13px] leading-[18px] md:leading-[20px] text-[#6b6b6b] tracking-[0.2px] {expandedMentions[mention.name] ? '' : 'line-clamp-2'}">
                {mention.description}
              </p>
              <button
                onclick={() => expandedMentions[mention.name] = !expandedMentions[mention.name]}
                class="inline-flex items-center gap-0.5 text-[12px] font-semibold text-black hover:text-[#333] transition-colors self-start"
              >
                {expandedMentions[mention.name] ? 'Show less' : 'Show more'}
                <svg class="w-3.5 h-3.5 transition-transform {expandedMentions[mention.name] ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          {/if}
          <!-- Action buttons (compact) -->
          <div class="flex gap-1.5 items-start w-full">
            {#if mention.links.project}
              <a href={mention.links.project} target="_blank" rel="noopener noreferrer"
                class="bg-[#9e4bf6] flex flex-1 h-[36px] items-center justify-center rounded-[20px] hover:bg-[#8a3de0] transition-colors">
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke-width="1.5" />
                  <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke-width="1.5" />
                </svg>
              </a>
            {/if}
            {#if mention.links.youtube}
              <a href={mention.links.youtube} target="_blank" rel="noopener noreferrer"
                class="bg-[#f5f5f5] flex flex-1 h-[36px] items-center justify-center rounded-[20px] hover:bg-[#ebebeb] transition-colors">
                <svg class="w-4 h-4 text-black" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M21.543 6.498C22 8.28 22 12 22 12s0 3.72-.457 5.502c-.254.985-.997 1.76-1.938 2.022C17.896 20 12 20 12 20s-5.893 0-7.605-.476c-.945-.266-1.687-1.04-1.938-2.022C2 15.72 2 12 2 12s0-3.72.457-5.502c.254-.985.997-1.76 1.938-2.022C6.107 4 12 4 12 4s5.896 0 7.605.476c.945.266 1.687 1.04 1.938 2.022zM10 15.5l6-3.5-6-3.5v7z" />
                </svg>
              </a>
            {/if}
            {#if mention.links.github}
              <a href={mention.links.github} target="_blank" rel="noopener noreferrer"
                class="bg-[#f5f5f5] flex flex-1 h-[36px] items-center justify-center rounded-[20px] hover:bg-[#ebebeb] transition-colors">
                <svg class="w-4 h-4 text-black" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z" />
                </svg>
              </a>
            {/if}
            {#if getTwitterLinks(mention.links).length === 1}
              <a href={getTwitterLinks(mention.links)[0].url} target="_blank" rel="noopener noreferrer"
                class="bg-[#f5f5f5] flex flex-1 h-[36px] items-center justify-center rounded-[20px] hover:bg-[#ebebeb] transition-colors">
                <svg class="w-4 h-4 text-black" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  </section>

  <!-- Sponsors -->
  <section class="flex flex-col gap-4 md:gap-6 items-center py-3 md:py-5">
    <h2 class="text-[32px] md:text-[48px] font-display font-medium leading-[40px] md:leading-[56px] tracking-[-0.64px] md:tracking-[-0.96px] text-center text-black">Thanks To Our Sponsors</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 w-full">
      {#each sponsors as sponsor}
        <a href={sponsor.url} target="_blank" rel="noopener noreferrer" class="bg-[#1a1a1a] rounded-lg h-20 overflow-hidden flex items-center justify-center px-8 hover:bg-[#252525] transition-colors">
          {#if sponsor.logo}
            <img src={sponsor.logo} alt={sponsor.name} class="{sponsor.logoClass} w-auto h-auto object-contain" />
          {:else}
            <span class="text-[14px] font-medium text-white">{sponsor.name}</span>
          {/if}
        </a>
      {/each}
    </div>
  </section>

  <!-- CTA Footer -->
  <section class="relative rounded-lg overflow-hidden">
    <img src={ctaBackground} alt="" class="w-full h-auto min-h-[400px] md:min-h-0 object-cover" />
    <div class="absolute inset-0 flex flex-col items-center justify-center gap-4 md:gap-6 p-4 md:p-8">
      <span class="inline-flex items-center justify-center h-8 md:h-10 px-3 md:px-4 rounded-[20px] bg-white/10 text-[#f5f5f5] text-[11px] md:text-[12px] font-medium tracking-[0.24px]">
        Keep Building on GenLayer
      </span>
      <h2 class="text-white font-display font-medium text-[24px] sm:text-[32px] md:text-[48px] leading-[28px] sm:leading-[36px] md:leading-[52px] tracking-[-0.48px] sm:tracking-[-0.64px] md:tracking-[-0.96px] text-center">
        The Hackathon Ended.<br />Your Project Doesn't Have To.
      </h2>
      <p class="text-white text-[14px] md:text-[17px] leading-[22px] md:leading-[28px] tracking-[0.34px] text-center max-w-[560px]">
        Whether you shipped a BUIDL or you're just getting started, there's a place for you. Submit your work as a contribution, climb the leaderboard, and earn Builder Points for everything you build on GenLayer.
      </p>
      <div class="flex flex-col sm:flex-row items-center gap-2">
        <a href="/#/submit-contribution"
           class="inline-flex items-center gap-2 bg-[#9e4bf6] text-white h-10 rounded-[20px] px-4 text-[14px] font-medium tracking-[0.28px]">
          Submit a Contribution
          <img src={arrowRight} alt="" class="w-4 h-4 brightness-0 invert" />
        </a>
        <a href="https://dorahacks.io/hackathon/genlayer-bradbury/buidl" target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-2 bg-[#f5f5f5] text-black h-10 rounded-[20px] px-4 text-[14px] font-medium tracking-[0.28px]">
          View on DoraHacks
          <img src={arrowRightDark} alt="" class="w-4 h-4" />
        </a>
      </div>
    </div>
  </section>

</div>

<style>
  :global(.x-dropdown) {
    animation: xDropdownIn 0.15s ease-out;
    transform-origin: bottom right;
  }

  @keyframes xDropdownIn {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(4px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
</style>
