<script>
  import { setPageMeta, resetPageMeta } from '../lib/meta.js';
  import { authState } from '../lib/auth.js';
  import { push } from 'svelte-spa-router';
  import { userStore } from '../lib/userStore';
  import { journeyAPI } from '../lib/api.js';
  import checkIcon from '../assets/referral/check-icon.png';
  import cardBg1 from '../assets/referral/card-bg-1.png';
  import cardBg2 from '../assets/referral/card-bg-2.png';
  const iconPortal = '/assets/icons/hexagon-genlayer.svg';
  const iconBuilder = '/assets/illustrations/builder-badge.svg';
  const iconValidator = '/assets/illustrations/validator-badge.svg';
  const iconCommunity = '/assets/illustrations/community-badge.svg';
  import arrowRightWhite from '../assets/referral/arrow-right-white.png';

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
      url: 'https://portal.genlayer.foundation/#/community',
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

  function handleGetReferral() {
    if ($authState.isAuthenticated) {
      push('/referrals');
    } else {
      sessionStorage.setItem('redirectAfterLogin', '/referrals');
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton) authButton.click();
    }
  }

  // Community onboarding state
  let linkingX = $state(false);
  let linkingDiscord = $state(false);
  let linkError = $state('');

  let hasLinkedX = $derived($userStore.user?.has_community_link_x || false);
  let hasLinkedDiscord = $derived($userStore.user?.has_community_link_discord || false);
  let hasXConnection = $derived(!!$userStore.user?.twitter_connection);
  let hasDiscordConnection = $derived(!!$userStore.user?.discord_connection);

  async function handleLinkX() {
    linkError = '';
    linkingX = true;
    try {
      await journeyAPI.linkXAccount();
      await userStore.loadUser();
    } catch (err) {
      linkError = err.response?.data?.error || 'Failed to claim X linking reward';
    } finally {
      linkingX = false;
    }
  }

  async function handleLinkDiscord() {
    linkError = '';
    linkingDiscord = true;
    try {
      await journeyAPI.linkDiscordAccount();
      await userStore.loadUser();
    } catch (err) {
      linkError = err.response?.data?.error || 'Failed to claim Discord linking reward';
    } finally {
      linkingDiscord = false;
    }
  }
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
        onclick={handleGetReferral}
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
              <div class="relative z-10 w-20 h-20">
                <img src={iconPortal} alt="Portal" class="w-full h-full" />
                <img src="/assets/illustrations/gl-symbol-white.svg" alt="" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[50%] h-[48%]" />
              </div>
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
              <img src={iconBuilder} alt="Referral" class="relative z-10 w-20 h-20" />
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
                <img src={iconBuilder} alt="Builders" class="w-14 h-14" />
                <img src={iconValidator} alt="Validators" class="w-14 h-14 -mt-8" />
                <img src={iconCommunity} alt="Community" class="w-14 h-14" />
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
        <div class="bg-white border border-[#f5f5f5] rounded-[8px] p-[8px] flex flex-col">
          <div class="border border-[#f5f5f5] rounded-[2px] h-[240px] overflow-hidden relative flex items-center justify-center">
            <div class="relative w-[360px] h-[240px] flex-shrink-0">
              <div class="absolute -translate-x-1/2 w-[170px] h-[170px] left-[calc(50%-180.33px)] top-[181px]">
                <img alt="" class="absolute inset-[-75.29%] w-[250%] h-[250%]" src="/assets/illustrations/ellipse-orange.svg" />
              </div>
              <img alt="" class="absolute left-[27px] top-[32px] w-[334.5px] h-[180px] max-w-none" src="/assets/illustrations/group-builder-lines.svg" />
              <img alt="" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[80px] h-[80px]" src="/assets/illustrations/builder-badge.svg" />
            </div>
          </div>
          <div class="flex flex-col gap-[24px] p-[16px]">
            <div class="flex flex-col gap-[12px]">
              <h3 class="text-[24px] font-medium font-display leading-[40px] text-black" style="letter-spacing: -0.48px;">Builders</h3>
              <p class="text-[14px] text-black leading-[21px]" style="letter-spacing: 0.28px;">
                Write Intelligent Contracts, build dApps, and contribute developer tools to the GenLayer ecosystem.
              </p>
            </div>
            <button
              onclick={handleGetReferral}
              class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] w-full transition-colors hover:opacity-90"
              style="background-color: #131214;"
            >
              <span class="text-[14px] font-medium text-white leading-[21px]" style="letter-spacing: 0.28px;">Invite a Builder</span>
              <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Validators card -->
        <div class="bg-white border border-[#f5f5f5] rounded-[8px] p-[8px] flex flex-col">
          <div class="border border-[#f5f5f5] rounded-[2px] h-[240px] overflow-hidden relative flex items-center justify-center">
            <div class="relative w-[360px] h-[240px] flex-shrink-0">
              <div class="absolute -translate-x-1/2 w-[170px] h-[170px] left-[calc(50%+186px)] top-[-85px]">
                <img alt="" class="absolute inset-[-75.29%] w-[250%] h-[250%]" src="/assets/illustrations/ellipse-blue.svg" />
              </div>
              <img alt="" class="absolute left-[0.33px] top-[32px] w-[360px] h-[180px] max-w-none" src="/assets/illustrations/group-validator-lines.svg" />
              <img alt="" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[80px] h-[80px]" src="/assets/illustrations/validator-badge.svg" />
            </div>
          </div>
          <div class="flex flex-col gap-[24px] p-[16px]">
            <div class="flex flex-col gap-[12px]">
              <h3 class="text-[24px] font-medium font-display leading-[40px] text-black" style="letter-spacing: -0.48px;">Validators</h3>
              <p class="text-[14px] text-black leading-[21px]" style="letter-spacing: 0.28px;">
                Run nodes, provide AI models, and help scale and secure the network through Optimistic Democracy.
              </p>
            </div>
            <button
              onclick={handleGetReferral}
              class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] w-full transition-colors hover:opacity-90"
              style="background-color: #131214;"
            >
              <span class="text-[14px] font-medium text-white leading-[21px]" style="letter-spacing: 0.28px;">Invite a Validator</span>
              <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Community card -->
        <div class="bg-white border border-[#f5f5f5] rounded-[8px] p-[8px] flex flex-col">
          <div class="border border-[#f5f5f5] rounded-[2px] h-[240px] overflow-hidden relative flex items-center justify-center">
            <div class="relative w-[360px] h-[240px] flex-shrink-0">
              <div class="absolute -translate-x-1/2 w-[170px] h-[170px] left-[calc(50%+186.33px)] top-[155px]">
                <img alt="" class="absolute inset-[-75.29%] w-[250%] h-[250%]" src="/assets/illustrations/ellipse-purple.svg" />
              </div>
              <img alt="" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[360px] h-[286px] max-w-none" src="/assets/illustrations/polygon-community.svg" />
              <img alt="" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[80px] h-[80px]" src="/assets/illustrations/community-badge.svg" />
              <div class="absolute w-[150px] h-[107.36px] left-[76.67px] top-[31px] pointer-events-none">
                <img alt="" class="absolute inset-0 w-full h-full max-w-none" src="/assets/illustrations/ellipse-blue.svg" />
              </div>
              <img alt="" class="absolute left-[calc(50%-81.67px)] top-[148px] -translate-x-1/2 w-[40px] h-[40px]" src="/assets/illustrations/builder-badge-small.svg" />
              <img alt="" class="absolute left-[calc(50%+82.33px)] top-[51px] -translate-x-1/2 w-[40px] h-[40px]" src="/assets/illustrations/builder-badge-small.svg" />
              <img alt="" class="absolute left-[calc(50%+82.33px)] top-[calc(50%+48px)] -translate-x-1/2 -translate-y-1/2 w-[40px] h-[40px]" src="/assets/illustrations/validator-badge-small.svg" />
              <img alt="" class="absolute left-[calc(50%+0.33px)] top-[calc(50%-92px)] -translate-x-1/2 -translate-y-1/2 w-[40px] h-[40px]" src="/assets/illustrations/validator-badge-small.svg" />
              <img alt="" class="absolute left-[calc(50%+0.33px)] top-[calc(50%+92px)] -translate-x-1/2 -translate-y-1/2 w-[40px] h-[40px]" src="/assets/illustrations/community-badge-small.svg" />
            </div>
          </div>
          <div class="flex flex-col gap-[24px] p-[16px]">
            <div class="flex flex-col gap-[12px]">
              <h3 class="text-[24px] font-medium font-display leading-[40px] text-black" style="letter-spacing: -0.48px;">Community</h3>
              <p class="text-[14px] text-black leading-[21px]" style="letter-spacing: 0.28px;">
                Create content, spread the word, and bring new contributors through referrals and outreach.
              </p>
            </div>
            <button
              onclick={handleGetReferral}
              class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] w-full transition-colors hover:opacity-90"
              style="background-color: #131214;"
            >
              <span class="text-[14px] font-medium text-white leading-[21px]" style="letter-spacing: 0.28px;">Invite Community</span>
              <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Community Onboarding — Link Your Accounts -->
  {#if $authState.isAuthenticated}
    <div class="max-w-[1200px] mx-auto px-4 md:px-8 mb-12">
      <h2 class="text-[22px] md:text-[28px] font-medium font-heading mb-2">Earn Points by Linking Accounts</h2>
      <p class="text-[14px] md:text-[15px] text-[#656567] mb-6">Connect your social accounts to earn bonus points and unlock contribution types that require them.</p>

      {#if linkError}
        <div class="bg-red-50 border-l-4 border-red-500 p-4 rounded-md mb-4">
          <p class="text-red-700 text-sm">{linkError}</p>
        </div>
      {/if}

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Link X Account -->
        <div class="border border-[#e6e6e6] rounded-[12px] p-5 bg-white flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full flex items-center justify-center {hasLinkedX ? 'bg-green-100' : 'bg-gray-100'}">
              {#if hasLinkedX}
                <svg class="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
              {:else}
                <svg class="w-5 h-5 text-gray-500" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              {/if}
            </div>
            <div>
              <p class="text-[14px] font-medium text-black">Link X (Twitter)</p>
              <p class="text-[12px] text-[#656567]">
                {#if hasLinkedX}
                  20 points earned
                {:else if hasXConnection}
                  Ready to claim 20 points
                {:else}
                  Link your account to earn 20 points
                {/if}
              </p>
            </div>
          </div>
          {#if hasLinkedX}
            <span class="text-[12px] font-medium text-green-600 bg-green-50 px-3 py-1 rounded-full">Claimed</span>
          {:else if hasXConnection}
            <button
              onclick={handleLinkX}
              disabled={linkingX}
              class="text-[13px] font-medium text-white bg-[#9333ea] hover:bg-[#7e22ce] px-4 py-2 rounded-full disabled:opacity-50 transition-colors"
            >
              {linkingX ? 'Claiming...' : 'Claim 20 pts'}
            </button>
          {:else}
            <button
              onclick={() => push('/profile')}
              class="text-[13px] font-medium text-[#9333ea] border border-[#9333ea] px-4 py-2 rounded-full hover:bg-purple-50 transition-colors"
            >
              Link Account
            </button>
          {/if}
        </div>

        <!-- Link Discord Account -->
        <div class="border border-[#e6e6e6] rounded-[12px] p-5 bg-white flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full flex items-center justify-center {hasLinkedDiscord ? 'bg-green-100' : 'bg-gray-100'}">
              {#if hasLinkedDiscord}
                <svg class="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
              {:else}
                <svg class="w-5 h-5 text-gray-500" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/></svg>
              {/if}
            </div>
            <div>
              <p class="text-[14px] font-medium text-black">Link Discord</p>
              <p class="text-[12px] text-[#656567]">
                {#if hasLinkedDiscord}
                  20 points earned
                {:else if hasDiscordConnection}
                  Ready to claim 20 points
                {:else}
                  Link your account to earn 20 points
                {/if}
              </p>
            </div>
          </div>
          {#if hasLinkedDiscord}
            <span class="text-[12px] font-medium text-green-600 bg-green-50 px-3 py-1 rounded-full">Claimed</span>
          {:else if hasDiscordConnection}
            <button
              onclick={handleLinkDiscord}
              disabled={linkingDiscord}
              class="text-[13px] font-medium text-white bg-[#9333ea] hover:bg-[#7e22ce] px-4 py-2 rounded-full disabled:opacity-50 transition-colors"
            >
              {linkingDiscord ? 'Claiming...' : 'Claim 20 pts'}
            </button>
          {:else}
            <button
              onclick={() => push('/profile')}
              class="text-[13px] font-medium text-[#9333ea] border border-[#9333ea] px-4 py-2 rounded-full hover:bg-purple-50 transition-colors"
            >
              Link Account
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}

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
        onclick={handleGetReferral}
        class="inline-flex items-center gap-2 h-12 px-8 text-white font-medium rounded-full text-base transition-opacity hover:opacity-90"
        style="background: linear-gradient(to bottom, #be8ff5, #ac6df3);"
      >
        Get Your Referral Link
        <img src={arrowRightWhite} alt="" class="w-4 h-4" />
      </button>
    </div>
  </div>
</div>
