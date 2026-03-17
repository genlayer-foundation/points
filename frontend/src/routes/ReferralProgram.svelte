<script>
  import { setPageMeta, resetPageMeta } from '../lib/meta.js';
  import checkIcon from '../assets/referral/check-icon.png';
  import cardBg1 from '../assets/referral/card-bg-1.png';
  import cardBg2 from '../assets/referral/card-bg-2.png';
  import iconPortal from '../assets/referral/icon-portal.png';
  import iconReferral from '../assets/referral/icon-referral.png';
  import iconShare1 from '../assets/referral/icon-share-1.png';
  import iconShare2 from '../assets/referral/icon-share-2.png';
  import arrowRightWhite from '../assets/referral/arrow-right-white.png';
  import roleBgValidators from '../assets/referral/role-bg-validators.png';
  import roleBgCommunity from '../assets/referral/role-bg-community.png';

  // --- Hex grid canvas + mouse-following gradient mask ---
  // Matches Figma: small, solid-filled, flat-top hexagons
  const HEX_R = 11;
  const VIRTUAL_R = 13.5;  // HEX_R + gap — controls spacing
  const CORNER = 2;

  let heroWrap = $state(null);
  let heroCanvas = $state(null);
  let ctaWrap = $state(null);
  let ctaCanvas = $state(null);

  // ---- drawing ----
  function hexPath(ctx, cx, cy, r, cr) {
    const pts = [];
    for (let i = 0; i < 6; i++) {
      // flat-top: first vertex at 0° (right)
      const a = (Math.PI / 3) * i;
      pts.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
    }
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const c = pts[i];
      const p = pts[(i + 5) % 6];
      const n = pts[(i + 1) % 6];
      const dl = Math.hypot(c.x - p.x, c.y - p.y);
      const dn = Math.hypot(n.x - c.x, n.y - c.y);
      const from = { x: c.x - ((c.x - p.x) / dl) * cr, y: c.y - ((c.y - p.y) / dl) * cr };
      const to = { x: c.x + ((n.x - c.x) / dn) * cr, y: c.y + ((n.y - c.y) / dn) * cr };
      if (i === 0) ctx.moveTo(from.x, from.y);
      else ctx.lineTo(from.x, from.y);
      ctx.quadraticCurveTo(c.x, c.y, to.x, to.y);
    }
    ctx.closePath();
  }

  function paintGrid(canvas, w, h) {
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    // Force CSS size to match layout, not the buffer size
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // flat-top hex tiling: cols spaced 1.5·vr, rows spaced √3·vr
    const colW = 1.5 * VIRTUAL_R;
    const rowH = Math.sqrt(3) * VIRTUAL_R;

    ctx.fillStyle = 'rgba(188, 160, 241, 0.28)';

    for (let col = -1; col * colW <= w + HEX_R; col++) {
      const yOff = (((col % 2) + 2) % 2) === 1 ? rowH / 2 : 0;
      for (let row = -1; row * rowH + yOff <= h + HEX_R; row++) {
        hexPath(ctx, col * colW, row * rowH + yOff, HEX_R, CORNER);
        ctx.fill();
      }
    }

    // Fade edges to transparent so hexagons dissolve smoothly at borders
    ctx.globalCompositeOperation = 'destination-out';
    const fade = 0.18; // fraction of each edge to fade

    // Left
    let g = ctx.createLinearGradient(0, 0, w * fade, 0);
    g.addColorStop(0, 'rgba(0,0,0,1)');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w * fade, h);

    // Right
    g = ctx.createLinearGradient(w * (1 - fade), 0, w, 0);
    g.addColorStop(0, 'rgba(0,0,0,0)');
    g.addColorStop(1, 'rgba(0,0,0,1)');
    ctx.fillStyle = g;
    ctx.fillRect(w * (1 - fade), 0, w * fade, h);

    // Top
    g = ctx.createLinearGradient(0, 0, 0, h * fade);
    g.addColorStop(0, 'rgba(0,0,0,1)');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h * fade);

    // Bottom
    g = ctx.createLinearGradient(0, h * (1 - fade), 0, h);
    g.addColorStop(0, 'rgba(0,0,0,0)');
    g.addColorStop(1, 'rgba(0,0,0,1)');
    ctx.fillStyle = g;
    ctx.fillRect(0, h * (1 - fade), w, h * fade);

    ctx.globalCompositeOperation = 'source-over';
  }

  // ---- all animation via direct DOM manipulation (no $state in hot path) ----
  function setupCanvas(canvas, container) {
    if (!canvas || !container) return;
    const { width, height } = container.getBoundingClientRect();
    paintGrid(canvas, width, height);
  }

  function applyMask(canvas, x, y) {
    if (!canvas) return;
    const px = (x * 100).toFixed(2);
    const py = (y * 100).toFixed(2);
    const g = `radial-gradient(ellipse 30% 45% at ${px}% ${py}%, black 0%, rgba(0,0,0,0.4) 35%, rgba(0,0,0,0.08) 65%, transparent 100%)`;
    canvas.style.webkitMaskImage = g;
    canvas.style.maskImage = g;
  }

  $effect(() => {
    setPageMeta({
      title: 'Referral Program',
      description: 'Invite Builders, Validators, and Community members to GenLayer. Earn 10% of all points from their successful contributions — forever, with no cap.',
      image: 'https://portal.genlayer.foundation/assets/referral_og_image.png',
      url: 'https://portal.genlayer.foundation/#/referral-program',
    });
    return () => resetPageMeta();
  });

  $effect(() => {
    // Grab refs once — if null the effect re-runs when they bind
    const hCanvas = heroCanvas;
    const cCanvas = ctaCanvas;
    const hWrap = heroWrap;
    const cWrap = ctaWrap;
    if (!hCanvas || !cCanvas || !hWrap || !cWrap) return;

    // Draw grids
    setupCanvas(hCanvas, hWrap);
    setupCanvas(cCanvas, cWrap);

    // Plain JS state — no Svelte reactivity overhead
    let mx = 0.7, my = 0.5;
    let hx = 0.7, hy = 0.5;
    let cx = 0.5, cy = 0.5;
    function onMove(e) {
      mx = e.clientX / window.innerWidth;
      my = e.clientY / window.innerHeight;
    }

    function onResize() {
      setupCanvas(hCanvas, hWrap);
      setupCanvas(cCanvas, cWrap);
    }

    let frameId;
    function tick() {
      const k = 0.03;
      hx += (mx - hx) * k;
      hy += (my - hy) * k;
      cx += (mx - cx) * k;
      cy += (my - cy) * k;
      applyMask(hCanvas, hx, hy);
      applyMask(cCanvas, cx, cy);
      frameId = requestAnimationFrame(tick);
    }

    window.addEventListener('mousemove', onMove);
    window.addEventListener('resize', onResize);
    frameId = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('resize', onResize);
      cancelAnimationFrame(frameId);
    };
  });
</script>

<div class="flex flex-col">
  <!-- Hero Section — full width, hex grid background -->
  <div
    class="relative w-full overflow-hidden"
    bind:this={heroWrap}
  >
    <canvas
      bind:this={heroCanvas}
      class="absolute inset-0 pointer-events-none"
    ></canvas>
    <div class="relative z-10 flex flex-col items-center text-center px-4 md:px-8 py-16 md:py-32 max-w-[1200px] mx-auto">
      <h1 class="text-[32px] md:text-[64px] font-medium font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
        Referral Program
      </h1>
      <p class="text-[20px] md:text-[32px] font-medium font-display leading-tight mb-4" style="letter-spacing: -0.64px;">
        Invite Builders, Validators & Community members
      </p>
      <p class="text-[15px] md:text-[17px] text-[#656567] mb-8 max-w-xl">
        Earn 10% of the points of their successful contributions
      </p>
      <button
        class="inline-flex items-center gap-2 h-12 px-8 text-white font-medium rounded-full text-base transition-opacity hover:opacity-90"
        style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
      >
        Get Your Referral Link
        <img src={arrowRightWhite} alt="" class="w-4 h-4" />
      </button>
    </div>
  </div>

  <!-- Middle sections — contained max-width -->
  <div class="flex flex-col gap-8 md:gap-16 max-w-[1200px] mx-auto w-full pb-12 px-1 md:px-3 pt-8 md:pt-16">

    <!-- How it works Section -->
    <div>
      <h2 class="text-[28px] md:text-[48px] font-medium font-display text-center leading-tight mb-8 md:mb-12" style="letter-spacing: -0.96px;">
        How it works
      </h2>

      <div class="space-y-6 md:space-y-8">
        <!-- Step 1 - Text left, Image right -->
        <div class="flex flex-col md:flex-row gap-6 md:gap-8 items-center">
          <div class="flex-1 space-y-4 md:space-y-5">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-lg flex-shrink-0"
              style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
            >
              1
            </div>
            <h3 class="text-[24px] md:text-[32px] font-medium font-display leading-tight" style="letter-spacing: -0.64px;">
              Join the portal
            </h3>
            <p class="text-[15px] md:text-[17px] text-[#656567]">
              Sign up and create your GenLayer Portal account to start tracking your contributions across the ecosystem.
            </p>
            <ul class="space-y-3">
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Connect your GitHub account</span>
              </li>
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Choose your primary role</span>
              </li>
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Start earning points immediately</span>
              </li>
            </ul>
          </div>
          <div class="flex-1 w-full">
            <div class="relative bg-white border border-[#f5f5f5] rounded-[12px] overflow-hidden flex items-center justify-center" style="min-height: 280px;">
              <img src={cardBg2} alt="" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none" />
              <img src={iconPortal} alt="Portal" class="relative z-10 w-20 h-20" />
            </div>
          </div>
        </div>

        <!-- Step 2 - Image left, Text right -->
        <div class="flex flex-col md:flex-row-reverse gap-6 md:gap-8 items-center">
          <div class="flex-1 space-y-4 md:space-y-5">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-lg flex-shrink-0"
              style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
            >
              2
            </div>
            <h3 class="text-[24px] md:text-[32px] font-medium font-display leading-tight" style="letter-spacing: -0.64px;">
              Get your referral link
            </h3>
            <p class="text-[15px] md:text-[17px] text-[#656567]">
              Head to your profile to grab your unique referral link — it's ready as soon as you join the portal.
            </p>
            <ul class="space-y-3">
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Unique link tied to your account</span>
              </li>
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Track referrals in real time</span>
              </li>
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Earn 10% of their points forever</span>
              </li>
            </ul>
          </div>
          <div class="flex-1 w-full">
            <div class="relative bg-white border border-[#f5f5f5] rounded-[12px] overflow-hidden flex items-center justify-center" style="min-height: 280px;">
              <img src={cardBg1} alt="" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none" />
              <img src={iconReferral} alt="Referral" class="relative z-10 w-20 h-20" />
            </div>
          </div>
        </div>

        <!-- Step 3 - Text left, Image right -->
        <div class="flex flex-col md:flex-row gap-6 md:gap-8 items-center">
          <div class="flex-1 space-y-4 md:space-y-5">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-lg flex-shrink-0"
              style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
            >
              3
            </div>
            <h3 class="text-[24px] md:text-[32px] font-medium font-display leading-tight" style="letter-spacing: -0.64px;">
              Share with your friends
            </h3>
            <p class="text-[15px] md:text-[17px] text-[#656567]">
              Send your link to developers, node operators, and community members. The more they contribute, the more you earn.
            </p>
            <ul class="space-y-3">
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Share across all your channels</span>
              </li>
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">Works for Builders, Validators & Community</span>
              </li>
              <li class="flex items-center gap-3">
                <img src={checkIcon} alt="" class="w-5 h-5 flex-shrink-0" />
                <span class="text-[14px] md:text-[15px] text-gray-800">No cap on referral earnings</span>
              </li>
            </ul>
          </div>
          <div class="flex-1 w-full">
            <div class="relative bg-white border border-[#f5f5f5] rounded-[12px] overflow-hidden flex items-center justify-center" style="min-height: 280px;">
              <img src={cardBg1} alt="" class="absolute inset-0 w-full h-full object-contain opacity-40 pointer-events-none" />
              <div class="relative z-10 flex items-center gap-6">
                <img src={iconReferral} alt="Builders" class="w-14 h-14" />
                <img src={iconShare1} alt="Validators" class="w-14 h-14 -mt-8" />
                <img src={iconShare2} alt="Community" class="w-14 h-14" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Who can you invite? Section -->
    <div>
      <h2 class="text-[28px] md:text-[48px] font-medium font-display text-center leading-tight mb-3" style="letter-spacing: -0.96px;">
        Who can you invite?
      </h2>
      <p class="text-[15px] md:text-[17px] text-[#656567] text-center mb-8 md:mb-12">
        Pick your path — you can always take on more roles later.
      </p>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <!-- Builders card -->
        <div class="bg-white border border-[#e5e5e5] rounded-[12px] overflow-hidden flex flex-col">
          <div class="relative flex items-center justify-center" style="min-height: 240px;">
            <img src={cardBg1} alt="" class="absolute inset-0 w-full h-full object-contain opacity-30 pointer-events-none" />
            <img src={iconReferral} alt="Builders" class="relative z-10 w-20 h-20" />
          </div>
          <div class="p-5 md:p-6 flex flex-col flex-1 gap-3">
            <h3 class="text-[22px] md:text-[24px] font-semibold font-display" style="letter-spacing: -0.48px;">Builders</h3>
            <p class="text-[14px] md:text-[15px] text-[#656567] leading-relaxed">
              Write Intelligent Contracts, build dApps, and contribute developer tools to the GenLayer ecosystem.
            </p>
            <button
              class="flex items-center justify-center gap-2 w-full h-11 mt-auto text-white font-medium rounded-full text-sm transition-opacity hover:opacity-90"
              style="background-color: #131214;"
            >
              Invite a Builder
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Validators card -->
        <div class="bg-white border border-[#e5e5e5] rounded-[12px] overflow-hidden flex flex-col">
          <div class="relative flex items-center justify-center" style="min-height: 240px;">
            <img src={roleBgValidators} alt="" class="absolute inset-0 w-full h-full object-contain opacity-30 pointer-events-none" />
            <img src={iconShare1} alt="Validators" class="relative z-10 w-20 h-20" />
          </div>
          <div class="p-5 md:p-6 flex flex-col flex-1 gap-3">
            <h3 class="text-[22px] md:text-[24px] font-semibold font-display" style="letter-spacing: -0.48px;">Validators</h3>
            <p class="text-[14px] md:text-[15px] text-[#656567] leading-relaxed">
              Run nodes, provide AI models, and help scale and secure the network through Optimistic Democracy.
            </p>
            <button
              class="flex items-center justify-center gap-2 w-full h-11 mt-auto text-white font-medium rounded-full text-sm transition-opacity hover:opacity-90"
              style="background-color: #131214;"
            >
              Invite a Validator
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Community card -->
        <div class="bg-white border border-[#e5e5e5] rounded-[12px] overflow-hidden flex flex-col">
          <div class="relative flex items-center justify-center" style="min-height: 240px;">
            <img src={roleBgCommunity} alt="" class="absolute inset-0 w-full h-full object-contain opacity-30 pointer-events-none" />
            <img src={iconShare2} alt="Community" class="relative z-10 w-20 h-20" />
          </div>
          <div class="p-5 md:p-6 flex flex-col flex-1 gap-3">
            <h3 class="text-[22px] md:text-[24px] font-semibold font-display" style="letter-spacing: -0.48px;">Community</h3>
            <p class="text-[14px] md:text-[15px] text-[#656567] leading-relaxed">
              Create content, spread the word, and bring new contributors through referrals and outreach.
            </p>
            <button
              class="flex items-center justify-center gap-2 w-full h-11 mt-auto text-white font-medium rounded-full text-sm transition-opacity hover:opacity-90"
              style="background-color: #131214;"
            >
              Invite Community
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- CTA Footer Section — full width, hex grid background -->
  <div
    class="relative w-full overflow-hidden mb-12"
    bind:this={ctaWrap}
  >
    <canvas
      bind:this={ctaCanvas}
      class="absolute inset-0 pointer-events-none"
    ></canvas>
    <div class="relative z-10 flex flex-col items-center text-center px-4 md:px-8 py-16 md:py-32 max-w-[1200px] mx-auto">
      <h2 class="text-[28px] md:text-[64px] font-medium font-display leading-tight mb-4" style="letter-spacing: -1.28px;">
        Let's Build Together
      </h2>
      <p class="text-[15px] md:text-[17px] text-[#656567] max-w-xl mb-8">
        Every person you bring into GenLayer earns you 10% of their contribution points — forever.
      </p>
      <button
        class="inline-flex items-center gap-2 h-12 px-8 text-white font-medium rounded-full text-base transition-opacity hover:opacity-90"
        style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
      >
        Get Your Referral Link
        <img src={arrowRightWhite} alt="" class="w-4 h-4" />
      </button>
    </div>
  </div>
</div>
