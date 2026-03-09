<script>
  import { push } from 'svelte-spa-router';
  import { userStore } from '../../lib/userStore.js';
  import { authState } from '../../lib/auth.js';

  let storeValue = $state({ user: null });
  userStore.subscribe(value => { storeValue = value; });

  let authValue = $state({ isAuthenticated: false });
  authState.subscribe(value => { authValue = value; });

  let isLoggedIn = $derived(authValue.isAuthenticated && !!storeValue.user);

  const baseRoles = [
    {
      key: 'builder',
      title: 'Start as a Builder',
      titleLoggedIn: 'Continue building',
      description: 'Deploy intelligent contracts and contribute repos to earn builder points.',
      descriptionLoggedIn: 'Submit your work and earn points for accepted contributions.',
      cta: 'Start building',
      ctaLoggedIn: 'Submit contribution',
      href: '/builders/welcome',
      hrefLoggedIn: '/submit-contribution',
      badge: '/assets/illustrations/builder-badge.svg',
      ellipse: '/assets/illustrations/ellipse-orange.svg',
      ellipseClass: 'left-[calc(50%-180.33px)] top-[181px]',
      lines: '/assets/illustrations/group-builder-lines.svg',
      linesClass: 'left-[27px] top-[32px] w-[334.5px] h-[180px]',
    },
    {
      key: 'validator',
      title: 'Become a validator',
      titleLoggedIn: 'Validator status',
      description: 'Deploy intelligent contracts and contribute repos to earn builder points.',
      descriptionLoggedIn: 'Check your validator waitlist status and node requirements.',
      cta: 'Join the waitlist',
      ctaLoggedIn: 'View status',
      href: '/validators/waitlist/join',
      hrefLoggedIn: '/validators',
      badge: '/assets/illustrations/validator-badge.svg',
      ellipse: '/assets/illustrations/ellipse-blue.svg',
      ellipseClass: 'left-[calc(50%+186px)] top-[-85px]',
      lines: '/assets/illustrations/group-validator-lines.svg',
      linesClass: 'left-[0.33px] top-[32px] w-[360px] h-[180px]',
    },
    {
      key: 'community',
      title: 'Join the community',
      titleLoggedIn: 'Community',
      description: 'Deploy intelligent contracts and contribute repos to earn builder points.',
      descriptionLoggedIn: 'Engage with the GenLayer community and earn community points.',
      cta: 'Join the GenFam',
      ctaLoggedIn: 'View community',
      href: '/community',
      hrefLoggedIn: '/community',
      badge: '/assets/illustrations/community-badge.svg',
      ellipse: '/assets/illustrations/ellipse-purple.svg',
      ellipseClass: 'left-[calc(50%+186.33px)] top-[155px]',
      lines: '/assets/illustrations/polygon-community.svg',
      linesClass: 'left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[360px] h-[286px]',
      extraBadges: true,
    },
  ];

  let roles = $derived(baseRoles.map(role => ({
    ...role,
    title: isLoggedIn ? role.titleLoggedIn : role.title,
    description: isLoggedIn ? role.descriptionLoggedIn : role.description,
    cta: isLoggedIn ? role.ctaLoggedIn : role.cta,
    href: isLoggedIn ? role.hrefLoggedIn : role.href,
  })));
</script>

<div class="flex flex-col gap-[40px] p-[20px] rounded-[8px]">
  <!-- Header -->
  <div class="flex flex-col gap-[24px] items-center text-center">
    <h2 class="text-[36px] md:text-[48px] font-medium font-display leading-[56px] text-black" style="letter-spacing: -0.96px;">
      {isLoggedIn ? 'Your contributions' : 'Choose how you contribute'}
    </h2>
    <p class="text-[17px] text-black leading-[28px]" style="letter-spacing: 0.34px;">
      {isLoggedIn ? 'Keep earning points across all your roles.' : 'Pick your path — you can always take on more roles later.'}
    </p>
  </div>

  <!-- Cards row -->
  <div class="flex flex-col md:flex-row gap-[12px] w-full">
    {#each roles as role}
      <div class="bg-white border border-[#f5f5f5] rounded-[8px] p-[8px] flex-1 flex flex-col">
        <!-- Illustration area -->
        <div class="border border-[#f5f5f5] rounded-[2px] h-[240px] overflow-hidden relative flex items-center justify-center">
          <div class="relative w-[360px] h-[240px] flex-shrink-0">
            <!-- Ellipse blur -->
            <div class="absolute -translate-x-1/2 w-[170px] h-[170px] {role.ellipseClass}">
              <img alt="" class="absolute inset-[-75.29%] w-[250%] h-[250%]" src={role.ellipse} />
            </div>
            <!-- Line art -->
            <img alt="" class="absolute {role.linesClass} max-w-none" src={role.lines} />
            <!-- Badge centered -->
            <img
              alt=""
              class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[80px] h-[80px]"
              src={role.badge}
            />
            {#if role.extraBadges}
              <!-- Community card extra elements strictly from Figma -->
              
              <!-- Light blue skewed background ellipse -->
              <div class="absolute w-[150px] h-[107.36px] left-[76.67px] top-[31px] pointer-events-none">
                <img alt="" class="absolute inset-0 w-full h-full max-w-none" src="/assets/illustrations/ellipse-blue.svg" />
              </div>


              <!-- Two small builder badges -->
              <img alt="" class="absolute left-[calc(50%-81.67px)] top-[148px] -translate-x-1/2 w-[40px] h-[40px]" src="/assets/illustrations/builder-badge-small.svg" />
              <img alt="" class="absolute left-[calc(50%+82.33px)] top-[51px] -translate-x-1/2 w-[40px] h-[40px]" src="/assets/illustrations/builder-badge-small.svg" />

              <!-- Two small validator badges -->
              <img alt="" class="absolute left-[calc(50%+82.33px)] top-[calc(50%+48px)] -translate-x-1/2 -translate-y-1/2 w-[40px] h-[40px]" src="/assets/illustrations/validator-badge-small.svg" />
              <img alt="" class="absolute left-[calc(50%+0.33px)] top-[calc(50%-92px)] -translate-x-1/2 -translate-y-1/2 w-[40px] h-[40px]" src="/assets/illustrations/validator-badge-small.svg" />

              <!-- One extra small community badge (the center logo uses the standard badge) -->
              <img alt="" class="absolute left-[calc(50%+0.33px)] top-[calc(50%+92px)] -translate-x-1/2 -translate-y-1/2 w-[40px] h-[40px]" src="/assets/illustrations/community-badge-small.svg" />
            {/if}
          </div>
        </div>

        <!-- Content -->
        <div class="flex flex-col gap-[24px] p-[16px]">
          <div class="flex flex-col gap-[12px]">
            <h3 class="text-[24px] font-medium font-display leading-[40px] text-black" style="letter-spacing: -0.48px;">
              {role.title}
            </h3>
            <p class="text-[14px] text-black leading-[21px]" style="letter-spacing: 0.28px;">
              {role.description}
            </p>
          </div>
          <button
            onclick={() => push(role.href)}
            class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] w-full transition-colors hover:opacity-90"
            style="background-color: #131214;"
          >
            <span class="text-[14px] font-medium text-white leading-[21px]" style="letter-spacing: 0.28px;">
              {role.cta}
            </span>
            <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4" />
          </button>
        </div>
      </div>
    {/each}
  </div>
</div>
