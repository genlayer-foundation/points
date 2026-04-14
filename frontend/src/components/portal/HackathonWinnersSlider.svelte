<script>
  import { grandWinner, trackWinners, honorableMentions } from '../../data/hackathonWinners.js';

  // Combine all winners with their award label
  let winners = [
    { ...grandWinner, badgeLabel: 'Grand Winner' },
    ...trackWinners.map(w => ({ ...w, badgeLabel: 'Track Winner' })),
    ...honorableMentions.map(w => ({ ...w, badgeLabel: 'Honorable Mention' })),
  ];
</script>

<div>
  <div class="flex items-end justify-between mb-3">
    <div class="flex flex-col gap-1">
      <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Hackathon Winners</h2>
      <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">Bradbury Builders Hackathon top projects</p>
    </div>
    <a
      href="#/hackathon-winners"
      class="flex items-center gap-[4px] text-[14px] text-[#6b6b6b] hover:text-black transition-colors whitespace-nowrap"
      style="letter-spacing: 0.28px;"
    >
      View all
      <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
    </a>
  </div>

  <div class="flex gap-[10px] overflow-x-auto pb-2" style="-ms-overflow-style: none; scrollbar-width: none;">
    {#each winners as winner}
      {@const isLogoOnly = winner.avatar && winner.screenshot && winner.avatar === winner.screenshot}
      {@const hasBg = winner.screenshot && !isLogoOnly}
      <a
        href={winner.links.website || winner.links.project || '#'}
        target="_blank"
        rel="noopener noreferrer"
        class="flex-shrink-0 w-[300px] h-[150px] rounded-[8px] overflow-hidden relative group cursor-pointer {hasBg ? 'bg-black' : 'bg-gradient-to-br from-[#1a1a2e] to-[#16213e]'}"
      >
        {#if hasBg}
          <img src={winner.screenshot} alt="" class="absolute inset-0 w-full h-full object-cover">
        {:else if isLogoOnly || (!winner.screenshot && winner.avatar)}
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <img src={winner.avatar} alt="" class="max-w-[50%] max-h-[50%] object-contain opacity-90">
          </div>
        {/if}

        <!-- Dark gradient overlay -->
        <div class="absolute inset-0 bg-gradient-to-b from-[rgba(0,0,0,0.2)] to-[rgba(0,0,0,0.5)]"></div>

        <!-- Top row: category badge + arrow icon -->
        <div class="absolute top-0 left-0 right-0 p-4 flex items-start justify-between">
          <div class="backdrop-blur-[10px] bg-white/10 flex items-center gap-1.5 px-2 py-1.5 rounded-[4px]">
            {#if winner.badgeLabel === 'Grand Winner'}
              <span class="text-[13px] shrink-0">⭐</span>
            {:else if winner.badgeLabel === 'Track Winner'}
              <span class="text-[13px] shrink-0">🏆</span>
            {:else if winner.badgeLabel === 'Honorable Mention'}
              <span class="text-[13px] shrink-0">🏅</span>
            {/if}
            <span class="text-[12px] font-medium leading-[14px] text-white whitespace-nowrap">
              {winner.badgeLabel}
            </span>
          </div>
          <div class="flex items-center p-2 rounded-[4px] backdrop-blur-[10px] bg-white/10">
            <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17L17 7M17 7H7M17 7v10" />
            </svg>
          </div>
        </div>

        <!-- Bottom content -->
        <div class="absolute bottom-0 left-0 right-0 p-4 flex items-end">
          <div class="flex items-center gap-1">
            {#if winner.avatar && !isLogoOnly}
              <img src={winner.avatar} alt="" class="w-10 h-10 rounded-full object-cover flex-shrink-0">
            {:else if isLogoOnly}
              <img src={winner.avatar} alt="" class="w-10 h-10 rounded-full object-contain bg-white/10 backdrop-blur-sm p-1 flex-shrink-0">
            {:else}
              <div class="w-10 h-10 rounded-full flex-shrink-0 bg-white/20"></div>
            {/if}
            <div class="flex flex-col justify-center ml-0.5">
              <span class="text-white text-[14px] font-medium leading-[21px]">{winner.name}</span>
              <span class="text-[#bbb] text-[12px] leading-[15px]" style="letter-spacing: 0.24px;">by {winner.builder}</span>
            </div>
          </div>
        </div>
      </a>
    {/each}
  </div>
</div>
