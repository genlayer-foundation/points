<script>
  import {
    pageHeader,
    communityLinks,
    sdks,
    documentation,
    boilerplates,
    tools,
    aiResources,
    tracksAndIdeas,
  } from '../data/resources.js';

  let copiedStates = $state({});

  async function copyToClipboard(text, key) {
    try {
      await navigator.clipboard.writeText(text);
      copiedStates[key] = true;
      setTimeout(() => { copiedStates[key] = false; }, 2000);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      copiedStates[key] = true;
      setTimeout(() => { copiedStates[key] = false; }, 2000);
    }
  }
</script>

<div class="flex flex-col gap-6 max-w-[1100px] mx-auto pb-12 px-1 md:px-3">

  <!-- Header: title + community links -->
  <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4 pt-4 md:pt-8">
    <div class="flex flex-col gap-1">
      <h1 class="text-[28px] md:text-[36px] font-display font-medium leading-tight tracking-[-0.72px] text-black">
        {pageHeader.title}
      </h1>
      <p class="text-[15px] leading-[24px] tracking-[0.3px] text-[#6b6b6b]">
        {pageHeader.subtitle}
      </p>
    </div>
    <div class="flex items-center gap-2 shrink-0">
      {#each communityLinks as link}
        <a href={link.url} target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center justify-center w-[34px] h-[34px] rounded-[8px] border border-[#f0f0f0] transition-all hover:shadow-md hover:scale-105 hover:border-transparent"
           title={link.label}>
          {#if link.label === 'Discord'}
            <svg class="w-[18px] h-[18px]" viewBox="0 0 127.14 96.36" fill={link.color}><path d="M107.7 8.07A105.15 105.15 0 0081.47 0a72.06 72.06 0 00-3.36 6.83 97.68 97.68 0 00-29.11 0A72.37 72.37 0 0045.64 0a105.89 105.89 0 00-26.25 8.09C2.79 32.65-1.71 56.6.54 80.21a105.73 105.73 0 0032.17 16.15 77.7 77.7 0 006.89-11.11 68.42 68.42 0 01-10.85-5.18c.91-.66 1.8-1.34 2.66-2a75.57 75.57 0 0064.32 0c.87.71 1.76 1.39 2.66 2a68.68 68.68 0 01-10.87 5.19 77 77 0 006.89 11.1 105.25 105.25 0 0032.19-16.14c2.64-27.38-4.51-51.11-18.9-72.15zM42.45 65.69C36.18 65.69 31 60 31 53.05s5-12.68 11.43-12.68S54 46.06 53.89 53.05 48.84 65.69 42.45 65.69zm42.24 0C78.41 65.69 73.25 60 73.25 53.05s5-12.68 11.44-12.68S96.23 46.06 96.12 53.05 91.08 65.69 84.69 65.69z"/></svg>
          {:else if link.label === 'Telegram'}
            <svg class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill={link.color}><path d="M11.944 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0a12 12 0 00-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 01.171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
          {:else if link.label === 'X'}
            <svg class="w-[15px] h-[15px]" viewBox="0 0 24 24" fill={link.color}><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
          {:else if link.label === 'YouTube'}
            <svg class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill={link.color}><path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
          {/if}
        </a>
      {/each}
    </div>
  </div>

  <!-- ═══ SDKs row ═══ -->
  <div class="flex items-center gap-3 flex-wrap">
    <span class="text-[13px] font-medium text-[#6b6b6b] tracking-[0.26px]">SDKs</span>
    {#each sdks as sdk}
      <a href={sdk.url} target="_blank" rel="noopener noreferrer"
         class="w-[44px] h-[44px] rounded-[10px] border border-[#f0f0f0] flex items-center justify-center group hover:border-[#ee8521]/40 hover:shadow-sm transition-all {sdk.icon === 'js' ? 'bg-[#F7DF1E]/5' : sdk.icon === 'python' ? 'bg-[#3776AB]/5' : 'bg-[#6b6b6b]/5'}"
         title={sdk.label}>
        {#if sdk.icon === 'js'}
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="#F7DF1E"><path d="M0 0h24v24H0V0zm22.034 18.276c-.175-1.095-.888-2.015-3.003-2.873-.736-.345-1.554-.585-1.797-1.14-.091-.33-.105-.51-.046-.705.15-.646.915-.84 1.515-.66.39.12.75.42.976.9 1.034-.676 1.034-.676 1.755-1.125-.27-.42-.405-.6-.586-.78-.63-.705-1.469-1.065-2.834-1.034l-.705.089c-.676.165-1.32.525-1.71 1.005-1.14 1.291-.811 3.541.569 4.471 1.365 1.02 3.361 1.244 3.616 2.205.24 1.17-.87 1.545-1.966 1.41-.811-.18-1.26-.586-1.755-1.336l-1.83 1.051c.21.48.45.689.81 1.109 1.74 1.756 6.09 1.666 6.871-1.004.029-.09.24-.705.074-1.65l.046.067zm-8.983-7.245h-2.248c0 1.938-.009 3.864-.009 5.805 0 1.232.063 2.363-.138 2.711-.33.689-1.18.601-1.566.48-.396-.196-.597-.466-.83-.855-.063-.105-.11-.196-.127-.196l-1.825 1.125c.305.63.75 1.172 1.324 1.517.855.51 2.004.675 3.207.405.783-.226 1.458-.691 1.811-1.411.51-.93.402-2.07.397-3.346.012-2.054 0-4.109 0-6.179l.004-.056z"/></svg>
        {:else if sdk.icon === 'python'}
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="#3776AB"><path d="M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69.05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3.17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.36-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28.25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05zm-6.3 1.98l-.23.33-.08.41.08.41.23.34.33.22.41.09.41-.09.33-.22.23-.34.08-.41-.08-.41-.23-.33-.33-.22-.41-.09-.41.09zm13.09 3.95l.28.06.32.12.35.18.36.27.36.35.35.47.32.59.28.73.21.88.14 1.04.05 1.23-.06 1.23-.16 1.04-.24.86-.32.71-.36.57-.4.45-.42.33-.42.24-.4.16-.36.09-.32.05-.24.02-.16-.01h-8.22v.82h5.84l.01 2.76.02.36-.05.34-.11.31-.17.29-.25.25-.31.24-.38.2-.44.17-.51.15-.58.13-.64.09-.71.07-.77.04-.84.01-1.27-.04-1.07-.14-.9-.2-.73-.25-.59-.3-.45-.33-.34-.34-.25-.34-.16-.33-.1-.3-.04-.25-.02-.2.01-.13v-5.34l.05-.64.13-.54.21-.46.26-.38.3-.32.33-.24.35-.2.35-.14.33-.1.3-.06.26-.04.21-.02.13-.01h5.84l.69-.05.59-.14.5-.21.41-.28.33-.32.27-.35.2-.36.15-.36.1-.35.07-.32.04-.28.02-.21V6.07h2.09l.14.01zm-6.47 14.25l-.23.33-.08.41.08.41.23.33.33.23.41.08.41-.08.33-.23.23-.33.08-.41-.08-.41-.23-.33-.33-.23-.41-.08-.41.08z"/></svg>
        {:else}
          <svg class="w-5 h-5 text-[#6b6b6b]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" /></svg>
        {/if}
      </a>
    {/each}
  </div>

  <!-- ═══ TWO-COLUMN: Documentation + Tools ═══ -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

    <!-- Documentation -->
    <div class="flex flex-col gap-3">
      <div class="flex items-center gap-[10px]">
        <div class="relative flex-shrink-0" style="width: 28px; height: 28px;">
          <img src="/assets/icons/hexagon-builder-light.svg" alt="" class="w-full h-full" />
          <img src="/assets/icons/terminal-line-orange.svg" alt="" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" style="width: 14px; height: 14px;" />
        </div>
        <h2 class="text-[17px] font-semibold text-black" style="letter-spacing: 0.34px;">Documentation</h2>
      </div>
      <section class="bg-white border border-[#f0f0f0] rounded-[14px] p-[16px] flex flex-col flex-1">
        {#each documentation as doc}
          <a href={doc.url} target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 py-3 border-b border-[#f5f5f5] last:border-b-0 group hover:bg-[#fafafa] rounded-[4px] px-2 -mx-2 transition-colors">
            <div class="w-[28px] h-[28px] rounded-[8px] flex items-center justify-center shrink-0 bg-[#ee8521]/10">
              {#if doc.icon === 'docs'}
                <svg class="w-[14px] h-[14px] text-[#ee8521]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" /></svg>
              {:else if doc.icon === 'eq'}
                <svg class="w-[14px] h-[14px] text-[#ee8521]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>
              {:else}
                <svg class="w-[14px] h-[14px] text-[#ee8521]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" /></svg>
              {/if}
            </div>
            <div class="flex flex-col gap-0.5 flex-1 min-w-0">
              <span class="text-[13px] font-medium text-black group-hover:text-[#ee8521] transition-colors">{doc.label}</span>
              <span class="text-[11px] text-[#ababab]">{doc.description}</span>
            </div>
            <svg class="w-3.5 h-3.5 text-[#ababab] group-hover:text-[#ee8521] transition-colors shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        {/each}
      </section>
    </div>

    <!-- Tools -->
    <div class="flex flex-col gap-3">
      <div class="flex items-center gap-[10px]">
        <div class="relative flex-shrink-0" style="width: 28px; height: 28px;">
          <img src="/assets/icons/hexagon-light.svg" alt="" class="w-full h-full" />
          <div
            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
            style="width: 14px; height: 14px; background-color: #7F52E1; -webkit-mask-image: url(/assets/icons/dashboard-fill-black.svg); mask-image: url(/assets/icons/dashboard-fill-black.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
          ></div>
        </div>
        <h2 class="text-[17px] font-semibold text-black" style="letter-spacing: 0.34px;">Tools</h2>
      </div>
      <section class="bg-white border border-[#f0f0f0] rounded-[14px] p-[16px] flex flex-col flex-1">
        {#each tools as tool}
          <a href={tool.url} target="_blank" rel="noopener noreferrer"
             class="flex items-center gap-3 py-3 border-b border-[#f5f5f5] last:border-b-0 group hover:bg-[#fafafa] rounded-[4px] px-2 -mx-2 transition-colors">
            <div class="w-[28px] h-[28px] rounded-[8px] flex items-center justify-center shrink-0 bg-[#7f52e1]/10">
              {#if tool.label === 'GenLayer Studio'}
                <svg class="w-[14px] h-[14px] text-[#7f52e1]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" /></svg>
              {:else if tool.label === 'Testnet Faucet'}
                <svg class="w-[14px] h-[14px] text-[#7f52e1]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {:else}
                <svg class="w-[14px] h-[14px] text-[#7f52e1]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>
              {/if}
            </div>
            <div class="flex flex-col gap-0.5 flex-1 min-w-0">
              <span class="text-[13px] font-medium text-black group-hover:text-[#7f52e1] transition-colors">{tool.label}</span>
              <span class="text-[11px] text-[#ababab]">{tool.description}</span>
            </div>
            <svg class="w-3.5 h-3.5 text-[#ababab] group-hover:text-[#7f52e1] transition-colors shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        {/each}
      </section>
    </div>
  </div>

  <!-- ═══ Boilerplates ═══ -->
  <div class="flex flex-col gap-3">
    <div class="flex items-center gap-[10px]">
      <div class="relative flex-shrink-0" style="width: 28px; height: 28px;">
        <img src="/assets/icons/hexagon-builder-light.svg" alt="" class="w-full h-full" />
        <svg class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[14px] h-[14px]" viewBox="0 0 24 24" fill="#ee8521"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
      </div>
      <h2 class="text-[17px] font-semibold text-black" style="letter-spacing: 0.34px;">Templates & Boilerplates</h2>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      {#each boilerplates as bp}
        <a href={bp.url} target="_blank" rel="noopener noreferrer"
           class="bg-white border border-[#f0f0f0] rounded-[14px] p-4 flex flex-col gap-2 group hover:border-[#ee8521]/30 hover:shadow-sm transition-all">
          <div class="flex items-center justify-between">
            <span class="text-[13px] font-medium text-black group-hover:text-[#ee8521] transition-colors">{bp.label}</span>
            <svg class="w-3.5 h-3.5 text-[#ababab] group-hover:text-[#ee8521] transition-colors shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </div>
          <span class="text-[11px] text-[#ababab] leading-[17px]">{bp.description}</span>
        </a>
      {/each}
    </div>
  </div>

  <!-- ═══ AI-Assisted Development ═══ -->
  <div class="flex flex-col gap-3">
    <div class="flex items-center gap-[10px]">
      <div class="relative flex-shrink-0" style="width: 28px; height: 28px;">
        <img src="/assets/icons/hexagon-builder-light.svg" alt="" class="w-full h-full" />
        <svg class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[14px] h-[14px]" fill="none" stroke="#ee8521" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" /></svg>
      </div>
      <h2 class="text-[17px] font-semibold text-black" style="letter-spacing: 0.34px;">AI-Assisted Development</h2>
    </div>

    <div class="bg-[#fafafa] border border-[#f0f0f0] rounded-[14px] p-[20px] flex flex-col gap-4">
      <!-- Copy for LLMs -->
      <div class="flex flex-col sm:flex-row sm:items-center gap-3">
        <div class="flex-1 min-w-0">
          <p class="text-[13px] font-medium text-black">GenLayer Context Prompt</p>
          <p class="text-[11px] text-[#ababab] mt-0.5">Copy a comprehensive GenLayer context prompt to use with any LLM — covers Intelligent Contracts, the Equivalence Principle, SDKs, testnets, and all key references.</p>
        </div>
        <button
          onclick={() => copyToClipboard(aiResources.metaprompt, 'metaprompt')}
          class="inline-flex items-center gap-1.5 px-4 py-2 rounded-[10px] text-[13px] font-medium transition-all cursor-pointer shrink-0 {copiedStates['metaprompt'] ? 'bg-[#e8fbe8] text-[#2d9a46]' : 'bg-[#101010] text-white hover:bg-[#2a2a2a]'}"
        >
          {#if copiedStates['metaprompt']}
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
            Copied!
          {:else}
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
            Copy for LLMs
          {/if}
        </button>
      </div>

      <!-- AI resource links -->
      <div class="flex flex-col sm:flex-row gap-3">
        {#each aiResources.links as link}
          <a href={link.url} target="_blank" rel="noopener noreferrer"
             class="flex-1 bg-white border border-[#e8e8e8] rounded-[10px] p-3 flex items-center gap-3 group hover:border-[#101010]/20 hover:shadow-sm transition-all">
            <div class="w-[28px] h-[28px] rounded-[8px] flex items-center justify-center shrink-0 bg-[#101010]/5">
              {#if link.label.includes('API')}
                <svg class="w-[14px] h-[14px] text-[#101010]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
              {:else}
                <svg class="w-[14px] h-[14px] text-[#101010]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>
              {/if}
            </div>
            <div class="flex flex-col gap-0.5 flex-1 min-w-0">
              <span class="text-[12px] font-medium text-black group-hover:text-[#101010] transition-colors">{link.label}</span>
              <span class="text-[10px] text-[#ababab]">{link.description}</span>
            </div>
            <svg class="w-3 h-3 text-[#ababab] group-hover:text-[#101010] transition-colors shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        {/each}
      </div>
    </div>
  </div>

  <!-- ═══ Tracks & Ideas ═══ -->
  <div class="flex flex-col gap-3">
    <div class="flex items-center gap-[10px]">
      <div class="relative flex-shrink-0 w-[28px] h-[28px]">
        <svg viewBox="0 0 32 32" class="w-full h-full"><polygon points="16,0 29.86,8 29.86,24 16,32 2.14,24 2.14,8" fill="#101010"/></svg>
        <img src="/assets/icons/gl-symbol-white.svg" alt="" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" style="width: 14px; height: 14px;" />
      </div>
      <h2 class="text-[17px] font-semibold text-black" style="letter-spacing: 0.34px;">Tracks & Ideas</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each tracksAndIdeas as track}
        <div class="bg-white border border-[#f0f0f0] rounded-[14px] p-4 flex flex-col gap-2">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full shrink-0" style="background-color: {track.color};"></div>
            <span class="text-[13px] font-medium text-black">{track.title}</span>
          </div>
          <span class="text-[11px] text-[#ababab] leading-[17px]">{track.description}</span>
        </div>
      {/each}
    </div>
  </div>

</div>
