<div class="flex flex-col md:flex-row gap-[24px] items-center p-[20px] rounded-[8px]">
  <!-- Left: code editor mockup -->
  <div class="flex-1 border border-[#f5f5f5] rounded-[8px] h-[400px] overflow-hidden relative flex items-center justify-center">
    <div class="relative w-[500px] h-[400px] flex-shrink-0 flex items-center justify-center">
      <!-- Dashed connector lines -->
      <img
        src="/assets/illustrations/vector-connector.svg"
        alt=""
        class="absolute left-[134.5px] top-[108px] w-[238.5px] h-[127.5px]"
      />

      <!-- Code editor card -->
      <div class="absolute left-[46.5px] top-[58px] bg-white border border-[#f5f5f5] rounded-[8px] p-[19.2px] w-[220.8px] h-[223.2px] flex flex-col gap-[19.2px]" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <p class="text-[16.8px] font-medium leading-[25.2px] text-black" style="letter-spacing: 0.336px;">
          studio.genlayer.com
        </p>
        <div class="text-[14.4px] leading-[21.6px] w-[182.4px] whitespace-pre-wrap" style="font-family: Menlo, monospace;">
          <p><span class="text-[#a456f7]">contract</span><span class="text-black">{' GLSwap {'}</span></p>
          <p><span class="text-black">{'   '}</span><span class="text-[#3779f5]">func</span><span class="text-black"> swap(a, b):</span></p>
          <p><span class="text-black">{'      validate(a, b)'}</span></p>
          <p><span class="text-black">{'      execute_trade()'}</span></p>
        </div>
        <div class="flex gap-[4.8px] items-center w-full">
          <div class="flex-1 flex items-center justify-center px-[9.6px] py-[4.8px] rounded-[24px] bg-[#f3f3f3]">
            <span class="text-[16.8px] font-medium leading-[25.2px] text-[#bdbdbd]">Solidity</span>
          </div>
          <div class="flex-1 flex items-center justify-center px-[9.6px] py-[4.8px] rounded-[24px] bg-[#eefdf2]">
            <span class="text-[16.8px] font-medium leading-[25.2px] text-[#169941]">Verified</span>
          </div>
        </div>
      </div>

      <!-- Submissions card -->
      <div class="absolute left-[296.1px] top-[58px] bg-white border border-[#f5f5f5] rounded-[8px] p-[19.2px] w-[140.4px] h-[121.2px] flex flex-col gap-[19.2px] justify-center" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <div class="flex items-center justify-center">
          <span class="text-[16.8px] font-medium leading-[25.2px] text-[#bdbdbd]" style="letter-spacing: 0.336px;">Submissions</span>
        </div>
        <div class="flex gap-[4.8px] items-center justify-center">
          <span class="text-[28.8px] font-medium font-display leading-[38.4px] text-[#4083ea]" style="letter-spacing: -0.864px;">3</span>
          <span class="text-[16.8px] font-medium leading-[25.2px] text-black" style="letter-spacing: 0.336px;">Accepted</span>
        </div>
      </div>

      <!-- Accepted + GP card -->
      <div class="absolute left-[296.5px] top-[220px] bg-white border border-[#f5f5f5] rounded-[8px] p-[19.2px] w-[140px] h-[121px] flex flex-col gap-[19.2px] justify-center" style="box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.05);">
        <div class="flex gap-[4.8px] items-center justify-center">
          <img src="/assets/illustrations/circle-fill-green.svg" alt="" class="w-[9.6px] h-[9.6px]" />
          <span class="text-[16.8px] font-medium leading-[25.2px] text-[#169941]" style="letter-spacing: 0.336px;">Accepted</span>
        </div>
        <p class="text-[28.8px] font-medium font-display leading-[38.4px] text-black" style="letter-spacing: -1.44px;">
          +200 GP
        </p>
      </div>
    </div>
  </div>

  <!-- Right: text -->
  <div class="flex-1 flex flex-col gap-[24px] justify-center">
    <h2 class="text-[32px] font-medium font-display leading-[40px] text-black" style="letter-spacing: -0.64px;">
      Submit contributions
    </h2>
    <p class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">
      Every contribution is reviewed by stewards. Accepted work earns GenLayer Points. Quality matters, the 18.5% acceptance rate means your work stands out.
    </p>
    <div class="flex flex-col gap-[4px]">
      <div class="flex gap-[10px] items-center">
        <img src="/assets/icons/checkbox-circle-fill.svg" alt="" class="w-4 h-4 flex-shrink-0" />
        <span class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">Repos verified through GitHub OAuth</span>
      </div>
      <div class="flex gap-[10px] items-center">
        <img src="/assets/icons/checkbox-circle-fill.svg" alt="" class="w-4 h-4 flex-shrink-0" />
        <span class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">Validate subjective outcomes in Intelligent Contracts</span>
      </div>
      <div class="flex gap-[10px] items-center">
        <img src="/assets/icons/checkbox-circle-fill.svg" alt="" class="w-4 h-4 flex-shrink-0" />
        <span class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">Points awarded on acceptance</span>
      </div>
    </div>
  </div>
</div>
