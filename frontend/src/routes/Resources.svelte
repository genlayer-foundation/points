<script>
  import { push } from 'svelte-spa-router';
  import prizeBackground from '../assets/hackathon/prize-background.jpg';
  import arrowRight from '../assets/hackathon/arrow-right.svg';
  import {
    pageHeader,
    sections,
    gettingStarted,
    documentation,
    aiDevelopment,
    bradburyLinks,
    ecosystemProjects,
    hackathon,
    portalInfo,
    tracksAndIdeas,
  } from '../data/resources.js';

  // Track which commands have been copied
  let copiedStates = $state({});

  async function copyToClipboard(text, key) {
    try {
      await navigator.clipboard.writeText(text);
      copiedStates[key] = true;
      setTimeout(() => {
        copiedStates[key] = false;
      }, 2000);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      copiedStates[key] = true;
      setTimeout(() => {
        copiedStates[key] = false;
      }, 2000);
    }
  }

  function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
</script>

<div class="flex flex-col gap-6 md:gap-8 max-w-[1200px] mx-auto pb-12 px-1 md:px-3">

  <!-- A. Hero Header -->
  <section class="flex flex-col gap-5 pt-4 md:pt-8">
    <div class="flex flex-col gap-3">
      <h1 class="text-[32px] md:text-[64px] font-display font-medium leading-[36px] md:leading-[68px] tracking-[-0.64px] md:tracking-[-1.28px] text-black">
        {pageHeader.title}
      </h1>
      <p class="text-[15px] md:text-[17px] leading-[24px] md:leading-[28px] tracking-[0.34px] text-[#6b6b6b] max-w-[700px]">
        {pageHeader.subtitle}
      </p>
    </div>

    <!-- Quick-jump pills -->
    <div class="flex flex-wrap gap-2">
      {#each sections as section}
        <button
          onclick={() => scrollToSection(section.id)}
          class="px-3 py-1.5 rounded-full text-[12px] md:text-[13px] font-medium text-[#6b6b6b] border border-[#e3e3e3] hover:border-[#ababab] hover:text-black transition-colors cursor-pointer bg-white"
        >
          {section.label}
        </button>
      {/each}
    </div>

    <!-- Gradient accent line -->
    <div class="h-[2px] rounded-full" style="background: linear-gradient(to right, #f8b93d, #ee8d24, #a77fee, #7f52e1);"></div>
  </section>

  <!-- B. Getting Started -->
  <section id="getting-started" class="scroll-mt-4">
    <div class="relative rounded-lg p-6 md:p-8 overflow-hidden text-white"
         style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);">
      <!-- Decorative glows -->
      <div class="absolute top-0 right-0 w-[300px] h-[300px] rounded-full opacity-[0.07]" style="background: radial-gradient(circle, #f8b93d, transparent 70%); transform: translate(30%, -30%);"></div>
      <div class="absolute bottom-0 left-0 w-[200px] h-[200px] rounded-full opacity-[0.05]" style="background: radial-gradient(circle, #a77fee, transparent 70%); transform: translate(-30%, 30%);"></div>

      <div class="relative flex flex-col gap-4">
        <span class="inline-flex items-center self-start px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.5px]"
              style="background: linear-gradient(135deg, #f8b93d, #ee8d24); color: #1a1a2e;">
          {gettingStarted.tag}
        </span>
        <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[28px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px]">
          {gettingStarted.title}
        </h2>
        <p class="text-[14px] md:text-[16px] leading-[22px] md:leading-[26px] text-white/70 max-w-[600px]">
          {gettingStarted.description}
        </p>
        <a href={gettingStarted.url} target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-2 self-start bg-[#9e4bf6] hover:bg-[#8a3de0] text-white h-10 rounded-[20px] px-5 text-[14px] font-medium tracking-[0.28px] transition-colors">
          {gettingStarted.ctaLabel}
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
        </a>
      </div>
    </div>
  </section>

  <!-- C. Documentation & Core Concepts -->
  <section id="documentation" class="flex flex-col gap-4 scroll-mt-4">
    <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[28px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">
      Documentation
    </h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      {#each documentation as doc}
        <div class="bg-white border border-[#f0f0f0] rounded-lg p-5 flex flex-col gap-3" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
          <span class="inline-flex items-center self-start px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.5px] bg-[#e8f0fe] text-[#387de8]">
            {doc.tag}
          </span>
          <h3 class="text-[18px] md:text-[20px] font-medium leading-[22px] md:leading-[24px] tracking-[-0.4px] text-black">
            {doc.title}
          </h3>
          <p class="text-[13px] md:text-[14px] leading-[20px] md:leading-[22px] text-[#6b6b6b] tracking-[0.28px]">
            {doc.description}
          </p>
          <a href={doc.url} target="_blank" rel="noopener noreferrer"
             class="inline-flex items-center gap-1 text-[#4083ea] text-[13px] font-medium tracking-[0.26px] hover:underline mt-auto">
            {doc.ctaLabel}
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
          </a>
        </div>
      {/each}
    </div>
  </section>

  <!-- D. AI-Assisted Development -->
  <section id="ai-development" class="flex flex-col gap-4 scroll-mt-4">
    <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[28px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">
      AI-Assisted Development
    </h2>
    <div class="rounded-lg p-4 md:p-6" style="background: linear-gradient(135deg, #f8f5ff, #f0ebff);">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        {#each aiDevelopment as tool, toolIdx}
          <div class="bg-white border border-[#e8e0f5] rounded-lg p-5 flex flex-col gap-3" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
            <span class="inline-flex items-center self-start px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.5px] bg-[#f3edff] text-[#7f52e1]">
              {tool.tag}
            </span>
            <h3 class="text-[18px] md:text-[20px] font-medium leading-[22px] md:leading-[24px] tracking-[-0.4px] text-black">
              {tool.title}
            </h3>
            <p class="text-[13px] md:text-[14px] leading-[20px] md:leading-[22px] text-[#6b6b6b] tracking-[0.28px]">
              {tool.description}
            </p>

            <!-- Install command blocks -->
            {#each tool.installSteps as step, stepIdx}
              <div class="flex flex-col gap-1.5">
                <span class="text-[11px] text-[#ababab] uppercase tracking-[0.5px] font-medium">{step.label}</span>
                <div class="flex items-center gap-2 rounded-md px-3 py-2.5 font-mono text-[12px] md:text-[13px] text-[#e3e3e3] overflow-x-auto"
                     style="background: #1a1a2e;">
                  <code class="flex-1 whitespace-nowrap">{step.command}</code>
                  <button
                    onclick={() => copyToClipboard(step.command, `ai-${toolIdx}-${stepIdx}`)}
                    class="shrink-0 p-1 rounded hover:bg-white/10 transition-colors cursor-pointer"
                    title="Copy to clipboard"
                  >
                    {#if copiedStates[`ai-${toolIdx}-${stepIdx}`]}
                      <svg class="w-4 h-4 text-[#3eb359]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                    {:else}
                      <svg class="w-4 h-4 text-[#ababab]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                    {/if}
                  </button>
                </div>
              </div>
            {/each}

            <a href={tool.url} target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center gap-1 text-[#7f52e1] text-[13px] font-medium tracking-[0.26px] hover:underline mt-auto">
              {tool.ctaLabel}
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- E. Bradbury Developer Links -->
  <section id="bradbury-links" class="flex flex-col gap-4 scroll-mt-4">
    <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[28px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">
      Bradbury Developer Links
    </h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">

      <!-- Network -->
      <div class="bg-white border border-[#f0f0f0] rounded-lg p-5 flex flex-col gap-3" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <h3 class="text-[16px] font-semibold leading-[20px] tracking-[0.32px] text-black">{bradburyLinks.network.title}</h3>
        <div class="flex flex-col gap-2.5">
          {#each bradburyLinks.network.items as item, idx}
            <div class="flex flex-col gap-1">
              <span class="text-[11px] text-[#ababab] uppercase tracking-[0.5px] font-medium">{item.label}</span>
              {#if item.copyable}
                <div class="flex items-center gap-2 rounded-md px-3 py-2 font-mono text-[11px] md:text-[12px] text-[#e3e3e3] overflow-x-auto"
                     style="background: #1a1a2e;">
                  <code class="flex-1 whitespace-nowrap">{item.value}</code>
                  <button
                    onclick={() => copyToClipboard(item.value, `net-${idx}`)}
                    class="shrink-0 p-1 rounded hover:bg-white/10 transition-colors cursor-pointer"
                    title="Copy"
                  >
                    {#if copiedStates[`net-${idx}`]}
                      <svg class="w-3.5 h-3.5 text-[#3eb359]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                    {:else}
                      <svg class="w-3.5 h-3.5 text-[#ababab]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                    {/if}
                  </button>
                </div>
              {:else}
                <span class="text-[13px] font-mono text-[#6b6b6b]">{item.value}</span>
              {/if}
            </div>
          {/each}
        </div>
      </div>

      <!-- Explorers & Tools -->
      <div class="bg-white border border-[#f0f0f0] rounded-lg p-5 flex flex-col gap-3" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <h3 class="text-[16px] font-semibold leading-[20px] tracking-[0.32px] text-black">{bradburyLinks.explorers.title}</h3>
        <div class="flex flex-col gap-1">
          {#each bradburyLinks.explorers.items as item}
            <a href={item.url} target="_blank" rel="noopener noreferrer"
               class="flex items-center justify-between py-2.5 px-1 border-b border-[#f5f5f5] last:border-b-0 group hover:bg-[#fafafa] rounded transition-colors">
              <span class="text-[13px] md:text-[14px] text-black group-hover:text-[#4083ea] transition-colors">{item.label}</span>
              <svg class="w-4 h-4 text-[#ababab] group-hover:text-[#4083ea] transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>
          {/each}
        </div>
      </div>

      <!-- SDKs & CLI -->
      <div class="bg-white border border-[#f0f0f0] rounded-lg p-5 flex flex-col gap-3" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <h3 class="text-[16px] font-semibold leading-[20px] tracking-[0.32px] text-black">{bradburyLinks.sdks.title}</h3>
        <div class="flex flex-col gap-3">
          {#each bradburyLinks.sdks.items as sdk, idx}
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center gap-2">
                <a href={sdk.url} target="_blank" rel="noopener noreferrer" class="text-[13px] md:text-[14px] font-medium text-black hover:text-[#4083ea] transition-colors">
                  {sdk.label}
                </a>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#f0f0f0] text-[#6b6b6b]">{sdk.version}</span>
              </div>
              <div class="flex items-center gap-2 rounded-md px-3 py-2 font-mono text-[11px] md:text-[12px] text-[#e3e3e3] overflow-x-auto"
                   style="background: #1a1a2e;">
                <code class="flex-1 whitespace-nowrap">{sdk.installCommand}</code>
                <button
                  onclick={() => copyToClipboard(sdk.installCommand, `sdk-${idx}`)}
                  class="shrink-0 p-1 rounded hover:bg-white/10 transition-colors cursor-pointer"
                  title="Copy"
                >
                  {#if copiedStates[`sdk-${idx}`]}
                    <svg class="w-3.5 h-3.5 text-[#3eb359]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                  {:else}
                    <svg class="w-3.5 h-3.5 text-[#ababab]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                  {/if}
                </button>
              </div>
            </div>
          {/each}
        </div>
      </div>

    </div>
  </section>

  <!-- F. Ecosystem Projects -->
  <section id="ecosystem" class="flex flex-col gap-4 scroll-mt-4">
    <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[28px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">
      Ecosystem Projects
    </h2>
    <div class="relative">
      <!-- Edge fade masks -->
      <div class="absolute left-0 top-0 bottom-0 w-6 z-10 pointer-events-none" style="background: linear-gradient(to right, white, transparent);"></div>
      <div class="absolute right-0 top-0 bottom-0 w-6 z-10 pointer-events-none" style="background: linear-gradient(to left, white, transparent);"></div>

      <div class="flex gap-3 overflow-x-auto pb-2 scroll-smooth" style="-ms-overflow-style: none; scrollbar-width: none;">
        {#each ecosystemProjects as project}
          <div class="w-[280px] shrink-0 bg-white border border-[#f0f0f0] rounded-lg p-5 flex flex-col gap-3" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
            <span class="inline-flex items-center self-start px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-[0.5px] bg-[#f5f0ff] text-[#7f52e1]">
              {project.track}
            </span>
            <h3 class="text-[16px] md:text-[18px] font-medium leading-[20px] md:leading-[22px] tracking-[-0.3px] text-black">
              {project.title}
            </h3>
            <p class="text-[13px] leading-[20px] text-[#6b6b6b] tracking-[0.26px] flex-1">
              {project.description}
            </p>
            <a href={project.url} target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center gap-1 text-[#4083ea] text-[13px] font-medium tracking-[0.26px] hover:underline mt-auto">
              Visit project
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- G. Hackathon Banner -->
  <section id="hackathon" class="scroll-mt-4">
    <div class="relative rounded-lg overflow-hidden">
      <img src={prizeBackground} alt="" class="w-full h-auto min-h-[200px] object-cover" />
      <div class="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 md:p-8">
        <h2 class="text-white font-display font-medium text-[24px] md:text-[40px] leading-[28px] md:leading-[44px] tracking-[-0.48px] md:tracking-[-0.8px] text-center">
          {hackathon.title}
        </h2>
        <p class="text-white/70 text-[14px] md:text-[16px] leading-[22px] md:leading-[26px] text-center max-w-[400px]">
          {hackathon.subtitle}
        </p>
        <div class="flex flex-wrap justify-center gap-2">
          {#each hackathon.highlights as hl}
            <span class="inline-flex items-center px-3 py-1.5 rounded-full text-[11px] md:text-[12px] font-medium text-white/90"
                  style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
              {hl}
            </span>
          {/each}
        </div>
        <button
          onclick={() => push('/hackathon')}
          class="inline-flex items-center gap-2 bg-[#9e4bf6] hover:bg-[#8a3de0] text-white h-10 rounded-[20px] px-5 text-[14px] font-medium tracking-[0.28px] transition-colors cursor-pointer"
        >
          {hackathon.ctaLabel}
          <img src={arrowRight} alt="" class="w-4 h-4 brightness-0 invert" />
        </button>
      </div>
    </div>
  </section>

  <!-- H. How the Portal Works -->
  <section id="how-it-works" class="flex flex-col gap-5 scroll-mt-4">
    <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[28px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">
      How the Portal Works
    </h2>

    <!-- Desktop: horizontal timeline -->
    <div class="hidden md:flex items-start gap-3">
      {#each portalInfo as step, idx}
        <div class="flex-1 flex flex-col items-center gap-3 text-center">
          <div class="w-12 h-12 rounded-full flex items-center justify-center text-white font-display font-bold text-[20px] bg-gradient-to-br {step.color}">
            {step.step}
          </div>
          <h3 class="text-[16px] font-semibold leading-[20px] text-black">{step.title}</h3>
          <p class="text-[13px] leading-[20px] text-[#6b6b6b] tracking-[0.26px]">{step.description}</p>
        </div>
        {#if idx < portalInfo.length - 1}
          <div class="flex items-center pt-5 shrink-0">
            <svg class="w-6 h-6 text-[#e3e3e3]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
          </div>
        {/if}
      {/each}
    </div>

    <!-- Mobile: vertical timeline -->
    <div class="flex md:hidden flex-col gap-4">
      {#each portalInfo as step}
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-display font-bold text-[16px] bg-gradient-to-br {step.color} shrink-0">
            {step.step}
          </div>
          <div class="flex flex-col gap-1 pt-1">
            <h3 class="text-[15px] font-semibold leading-[18px] text-black">{step.title}</h3>
            <p class="text-[13px] leading-[20px] text-[#6b6b6b] tracking-[0.26px]">{step.description}</p>
          </div>
        </div>
      {/each}
    </div>

    <button
      onclick={() => push('/how-it-works')}
      class="inline-flex items-center gap-1 self-start text-[#4083ea] text-[14px] font-medium tracking-[0.28px] hover:underline cursor-pointer bg-transparent border-none p-0"
    >
      Learn more about the portal
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
    </button>
  </section>

  <!-- I. Tracks & Ideas -->
  <section id="tracks" class="flex flex-col gap-4 scroll-mt-4">
    <h2 class="text-[24px] md:text-[32px] font-display font-medium leading-[28px] md:leading-[40px] tracking-[-0.48px] md:tracking-[-0.64px] text-black">
      Tracks & Ideas
    </h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each tracksAndIdeas as track}
        <div class="bg-white border border-[#f0f0f0] rounded-lg p-5 flex flex-col gap-2 relative overflow-hidden" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
          <!-- Left gradient border accent -->
          <div class="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b {track.gradient}"></div>
          <h3 class="text-[16px] md:text-[18px] font-medium leading-[20px] md:leading-[22px] tracking-[-0.3px] text-black pl-2">
            {track.title}
          </h3>
          <p class="text-[13px] leading-[20px] text-[#6b6b6b] tracking-[0.26px] pl-2">
            {track.description}
          </p>
        </div>
      {/each}
    </div>
  </section>

</div>

<style>
  /* Hide scrollbar for ecosystem horizontal scroll */
  div::-webkit-scrollbar {
    display: none;
  }
</style>
