<script>
  let { title = 'Chart', subtitle = 'Coming soon' } = $props();
</script>

<div class="bg-white border border-[#f0f0f0] rounded-[8px] p-6 flex flex-col items-center justify-center min-h-[280px]">
  <div class="text-center">
    <svg class="w-12 h-12 text-[#e0e0e0] mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
    <p class="text-[14px] font-medium text-[#999]">{title}</p>
    <p class="text-[12px] text-[#bbb] mt-1">{subtitle}</p>
  </div>
</div>
