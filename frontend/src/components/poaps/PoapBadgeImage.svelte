<script>
  let { src = '', title = 'POAP', size = 'lg', claimed = false } = $props();

  let sizeClass = $derived(size === 'sm' ? 'w-20 h-20' : size === 'md' ? 'w-28 h-28' : 'w-40 h-40');
  let fallbackText = $derived((title || 'POAP').slice(0, 2).toUpperCase());
</script>

<div class="poap-badge-image relative inline-flex {sizeClass} shrink-0 items-center justify-center rounded-full p-[7px]">
  {#if src}
    <img src={src} alt={title} class="h-full w-full rounded-full object-cover bg-white" />
  {:else}
    <div class="flex h-full w-full items-center justify-center rounded-full bg-white text-[18px] font-semibold text-[#7f52e1]">
      {fallbackText}
    </div>
  {/if}
  {#if claimed}
    <span class="absolute bottom-2 right-2 flex h-7 w-7 items-center justify-center rounded-full border border-white bg-[#19a663] text-white shadow-sm" aria-label="Claimed">
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M9.55 17.6 3.9 11.95l1.4-1.4 4.25 4.25 9.15-9.15 1.4 1.4-10.55 10.55Z" />
      </svg>
    </span>
  {/if}
</div>

<style>
  .poap-badge-image {
    background:
      linear-gradient(#fff, #fff) padding-box,
      conic-gradient(from 135deg, rgba(127, 82, 225, 0.88), rgba(202, 190, 255, 0.42), rgba(25, 166, 99, 0.34), rgba(127, 82, 225, 0.88)) border-box;
    border: 1px solid transparent;
    box-shadow:
      0 18px 38px rgba(80, 64, 150, 0.14),
      inset 0 0 0 1px rgba(127, 82, 225, 0.14);
  }
</style>
