<script>
  // PointsAwarded - Points supply visualization
  // Will be wired to a real API later

  const TOTAL_SUPPLY = 1_000_000;
  const DISTRIBUTED = 220_000;
  const REMAINING_PCT = 17;
  const AVG_GP = 32;

  let distributedPct = $derived(Math.round((DISTRIBUTED / TOTAL_SUPPLY) * 100));

  function formatNumber(n) {
    if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
    return n.toLocaleString();
  }
</script>

<div class="relative overflow-hidden rounded-[24px]" style="background-color: #131214;">
  <!-- Decorative gradient blobs -->
  <div class="absolute inset-0 overflow-hidden">
    <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-[120px]"></div>
    <div class="absolute bottom-1/4 right-1/4 w-80 h-80 bg-orange-500/15 rounded-full blur-[100px]"></div>
  </div>

  <div class="relative z-10 px-8 md:px-20 py-32 md:py-40 text-center">
    <!-- Points Program label -->
    <p class="text-[#9e9e9e] text-sm font-medium uppercase tracking-widest mb-6">Portal Program</p>

    <!-- Main title -->
    <h2 class="text-4xl md:text-[64px] font-medium text-white font-display leading-none mb-3" style="letter-spacing: -1.28px;">
      1 Million
    </h2>
    <p class="text-2xl md:text-[32px] font-medium font-display mb-4" style="letter-spacing: -0.96px;">
      <span class="bg-gradient-to-r from-[#a78af8] to-[#fa8736] bg-clip-text text-transparent">Limited Supply</span>
    </p>
    <p class="text-[#9e9e9e] text-base max-w-md mx-auto mb-10">
      Total GenLayer Portal points available for contributors
    </p>

    <!-- Progress bar -->
    <div class="max-w-2xl mx-auto mb-8">
      <div class="flex justify-between text-xs text-[#9e9e9e] mb-2">
        <span>Distributed</span>
        <span>{distributedPct}% of supply</span>
      </div>
      <div class="h-5 bg-[#2a2a2c] rounded-full overflow-hidden">
        <div
          class="h-full bg-gradient-to-r from-[#a78af8] to-[#fa8736] rounded-full transition-all duration-700"
          style="width: {distributedPct}%"
        ></div>
      </div>
    </div>

    <!-- Stat pills -->
    <div class="flex flex-wrap justify-center gap-4">
      <div class="border border-[#3f3f3f] rounded-full px-5 py-2.5 flex items-center gap-2">
        <span class="text-white font-medium font-display text-lg">{formatNumber(DISTRIBUTED)}</span>
        <span class="text-[#9e9e9e] text-sm">Distributed</span>
      </div>
      <div class="border border-[#3f3f3f] rounded-full px-5 py-2.5 flex items-center gap-2">
        <span class="text-white font-medium font-display text-lg">{REMAINING_PCT}%</span>
        <span class="text-[#9e9e9e] text-sm">Remaining</span>
      </div>
      <div class="border border-[#3f3f3f] rounded-full px-5 py-2.5 flex items-center gap-2">
        <span class="text-white font-medium font-display text-lg">${AVG_GP}</span>
        <span class="text-[#9e9e9e] text-sm">Avg GP per contribution</span>
      </div>
    </div>
  </div>
</div>
