<script>
  import { push } from 'svelte-spa-router';
</script>

<section class="overflow-hidden rounded-[8px] border border-[#f1dfca] bg-white shadow-[0_12px_30px_rgba(115,75,32,0.08)]">
  <div class="grid grid-cols-1 gap-4 p-4 sm:p-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
    <div class="flex min-w-0 items-start gap-3">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-[8px] bg-[#ee8521]/12 text-[#ee8521]">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.7">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.75 6.75A2 2 0 016.75 4.75h10.5a2 2 0 012 2v10.5a2 2 0 01-2 2H6.75a2 2 0 01-2-2V6.75z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 9h8M8 12h5M8 15h7" />
        </svg>
      </div>

      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-[18px] font-semibold leading-[23px] text-black" style="letter-spacing: 0.2px;">Builder Resources</h2>
          <span class="rounded-full bg-[#fff2e4] px-2 py-0.5 text-[11px] font-semibold uppercase text-[#a85e16]" style="letter-spacing: 0.7px;">Agent-first</span>
        </div>
        <p class="mt-1 max-w-[760px] text-[13px] leading-[19px] text-[#666]">
          Skills, starters, GenTV sessions, network links, tools, and raw docs for building GenLayer projects with coding agents.
        </p>
        <div class="mt-3 flex flex-wrap gap-1.5">
          {#each ['Skills', 'Open-source starters', 'GenTV', 'Tools'] as item}
            <span class="rounded-full border border-[#f0dfcb] bg-[#fffaf4] px-2.5 py-1 text-[12px] font-medium leading-[15px] text-[#625548]">{item}</span>
          {/each}
        </div>
      </div>
    </div>

    <button
      type="button"
      onclick={() => push('/builders/resources')}
      class="inline-flex h-10 w-fit items-center justify-center gap-2 rounded-[20px] bg-[#101010] px-4 text-[14px] font-medium text-white transition hover:bg-black lg:justify-self-end"
    >
      Open resources
      <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4 brightness-0 invert" />
    </button>
  </div>
</section>
