<script>
  import { m } from '../../../lib/paraglide/messages.js';
</script>

<div class="flex flex-col md:flex-row gap-[24px] items-center p-[20px] rounded-[8px]">
  <!-- Left: text -->
  <div class="flex-1 flex flex-col gap-[24px] justify-center">
    <h2 class="text-[32px] font-medium font-display leading-[40px] text-black" style="letter-spacing: -0.64px;">
      {m.ljs_title()}
    </h2>
    <p class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">
      {m.ljs_description()}
    </p>
    <div class="flex flex-col gap-[4px]">
      <div class="flex gap-[10px] items-center">
        <img src="/assets/icons/checkbox-circle-fill.svg" alt="" class="w-4 h-4 flex-shrink-0" />
        <span class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">{m.ljs_bullet_builder()}</span>
      </div>
      <div class="flex gap-[10px] items-center">
        <img src="/assets/icons/checkbox-circle-fill.svg" alt="" class="w-4 h-4 flex-shrink-0" />
        <span class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">{m.ljs_bullet_validator()}</span>
      </div>
      <div class="flex gap-[10px] items-center">
        <img src="/assets/icons/checkbox-circle-fill.svg" alt="" class="w-4 h-4 flex-shrink-0" />
        <span class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">{m.ljs_bullet_community()}</span>
      </div>
    </div>
  </div>

  <!-- Right: illustration -->
  <div class="flex-1 bg-white border border-[#f5f5f5] rounded-[8px] h-[400px] overflow-hidden relative flex items-center justify-center p-4">
    <img
      src="/assets/illustrations/journey-illustration.svg"
      alt={m.ljs_illustration_alt()}
      class="w-full h-full max-w-[500px] object-contain"
    />
  </div>
</div>
