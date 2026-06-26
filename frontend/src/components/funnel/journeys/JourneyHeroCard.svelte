<script>
  // @ts-nocheck
  let {
    role = 'builder',
    iconHex = '/assets/icons/hexagon-builder-light.svg',
    iconGlyph = '/assets/icons/terminal-line-orange.svg',
    iconPlacement = 'kicker',
    kickerIconHex = '',
    kickerIconGlyph = '',
    eyebrow = '',
    accentValue = '',
    titleRest = '',
    description = '',
    completed = 0,
    total = 1,
    primaryLabel = '',
    primaryDisabled = false,
    primaryBusy = false,
    helper = '',
    heroContribution = 'progress',
    contributionIconHex = '',
    contributionIconGlyph = '',
    showProgress = true,
    onPrimary = () => {},
  } = $props();

  let progressPercent = $derived(
    total > 0 ? Math.max(0, Math.min(100, Math.round((completed / total) * 100))) : 0
  );
  let kickerHex = $derived(kickerIconHex || iconHex);
  let kickerGlyph = $derived(kickerIconGlyph || iconGlyph);
  let showKickerIcon = $derived(iconPlacement !== 'title' || Boolean(kickerIconHex || kickerIconGlyph));
  let heroBadgeHex = $derived(contributionIconHex || iconHex);
  let heroBadgeGlyph = $derived(contributionIconGlyph || iconGlyph);
</script>

<section class="journey-hero" aria-labelledby={`${role}-journey-title`}>
  <div class="hero-content">
    <div class="hero-kicker">
      {#if showKickerIcon}
        <span class="role-icon" aria-hidden="true">
          <img src={kickerHex} alt="" />
          <img src={kickerGlyph} alt="" />
        </span>
      {/if}
      <span class="eyebrow-dot"></span>
      <p>{eyebrow}</p>
    </div>

    <h1 id={`${role}-journey-title`}>
      {#if accentValue}
        <span class="accent-value">{accentValue}</span>{titleRest}
      {:else}
        {titleRest}
      {/if}
      {#if iconPlacement === 'title'}
        <span class="role-icon title-role-icon" aria-hidden="true">
          <img src={iconHex} alt="" />
          <img src={iconGlyph} alt="" />
        </span>
      {/if}
    </h1>

    <p class="hero-description">{description}</p>

    {#if showProgress}
      <div class="progress-track" aria-hidden="true">
        <span class:has-progress={progressPercent > 0} style={`width: ${progressPercent}%`}></span>
      </div>
    {/if}

    <div class="hero-action">
      {#if primaryLabel}
        <button
          type="button"
          class="landing-button button-accent"
          onclick={() => onPrimary()}
          disabled={primaryDisabled}
          aria-busy={primaryBusy}
        >
          <span>{primaryLabel}</span>
          <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
        </button>
      {/if}
      {#if helper}
        <p>{helper}</p>
      {/if}
    </div>
  </div>

  {#if heroContribution === 'icon'}
    <div class="hero-role-badge" aria-hidden="true">
      <img src={heroBadgeHex} alt="" />
      <img src={heroBadgeGlyph} alt="" />
    </div>
  {:else}
    <div class="progress-ring" style={`--progress: ${progressPercent}%`} aria-label={`${completed} of ${total} steps complete`}>
      <span>{completed}</span><em>/{total}</em>
    </div>
  {/if}
</section>

<style>
  .journey-hero {
    background: var(--journey-hero-bg, linear-gradient(163deg, #fff 40%, #fff7ec 96%));
    border: 1px solid var(--journey-hero-border, #f3e4cb);
    border-radius: 16px;
    min-height: 320px;
    overflow: hidden;
    padding: 28px;
    position: relative;
    width: 100%;
  }

  .journey-hero::before {
    background: radial-gradient(circle at 100% 0%, var(--journey-hero-glow, rgba(238, 133, 33, 0.16)) 0, transparent 34%);
    content: '';
    inset: 0;
    pointer-events: none;
    position: absolute;
  }

  .hero-content {
    max-width: 725px;
    position: relative;
    z-index: 1;
  }

  .hero-kicker {
    align-items: center;
    display: flex;
    gap: 8px;
    min-height: 25px;
  }

  .role-icon {
    display: inline-flex;
    height: 24px;
    position: relative;
    width: 24px;
  }

  .role-icon img:first-child {
    height: 24px;
    width: 24px;
  }

  .role-icon img:last-child {
    height: 12px;
    left: 50%;
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
  }

  .eyebrow-dot {
    background: var(--role-accent, #ee8521);
    border-radius: 3px;
    display: inline-flex;
    height: 6px;
    opacity: 0.9;
    width: 6px;
  }

  .hero-kicker p {
    color: var(--role-accent, #ee8521);
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 1.44px;
    line-height: 19px;
    margin: 0;
    text-transform: uppercase;
  }

  h1 {
    color: var(--journey-black, #131214);
    font-family: var(--font-display);
    font-size: 36px;
    font-weight: 500;
    letter-spacing: -0.72px;
    line-height: 40px;
    margin: 8px 0 0;
  }

  h1 .accent-value {
    color: var(--role-accent, #ee8521);
  }

  .title-role-icon {
    height: 34px;
    margin-left: 10px;
    vertical-align: -7px;
    width: 30px;
  }

  .title-role-icon img:first-child {
    height: 34px;
    width: 30px;
  }

  .title-role-icon img:last-child {
    height: 16px;
    width: 16px;
  }

  .hero-description {
    color: #3f3f3f;
    font-family: var(--font-body);
    font-size: 16px;
    line-height: 25.6px;
    margin: 14px 0 0;
    max-width: 725px;
  }

  .progress-track {
    background: #f3f3f3;
    border-radius: 999px;
    height: 6px;
    margin-top: 20px;
    max-width: 725px;
    overflow: hidden;
    width: 100%;
  }

  .progress-track span {
    background: var(--role-accent, #ee8521);
    border-radius: inherit;
    display: block;
    height: 100%;
    transition: width 180ms ease;
  }

  .progress-track span.has-progress {
    min-width: 8px;
  }

  .hero-action {
    align-items: center;
    display: flex;
    gap: 13px;
    margin-top: 18px;
  }

  .hero-action p {
    color: #6b6b6b;
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 19px;
    margin: 0;
  }

  .landing-button {
    align-items: center;
    border-radius: 20px;
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    gap: 8px;
    height: 40px;
    justify-content: center;
    letter-spacing: 0.28px;
    line-height: 21px;
    padding: 0 16px;
    transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, opacity 160ms ease;
    white-space: nowrap;
  }

  .landing-button img {
    height: 16px;
    width: 16px;
  }

  .button-accent {
    background: var(--role-accent, #ee8521);
    color: #fff;
  }

  .button-accent:hover:not(:disabled) {
    background: var(--role-accent-hover, #d97518);
  }

  .landing-button:disabled {
    cursor: default;
    opacity: 0.62;
  }

  .progress-ring {
    align-items: center;
    background: conic-gradient(var(--role-accent, #ee8521) var(--progress), #f3f3f3 0);
    border-radius: 999px;
    display: flex;
    height: 78px;
    justify-content: center;
    position: absolute;
    right: 28px;
    top: 120px;
    width: 78px;
    z-index: 1;
  }

  .hero-role-badge {
    align-items: center;
    display: flex;
    height: 86px;
    justify-content: center;
    position: absolute;
    right: 28px;
    top: 112px;
    width: 78px;
    z-index: 1;
  }

  .hero-role-badge img:first-child {
    height: 78px;
    width: 70px;
  }

  .hero-role-badge img:last-child {
    height: 30px;
    position: absolute;
    width: 30px;
  }

  .progress-ring::before {
    background: #fffdf9;
    border-radius: inherit;
    content: '';
    inset: 2px;
    position: absolute;
  }

  .progress-ring span,
  .progress-ring em {
    color: var(--journey-black, #131214);
    font-family: var(--font-display);
    font-size: 17px;
    font-style: normal;
    font-weight: 500;
    letter-spacing: -0.34px;
    line-height: 26px;
    position: relative;
  }

  @media (max-width: 900px) {
    .journey-hero {
      min-height: 0;
      padding: 24px;
    }

    .hero-content {
      max-width: calc(100% - 96px);
    }

    h1 {
      font-size: 32px;
      line-height: 37px;
    }
  }

  @media (max-width: 640px) {
    .journey-hero {
      padding: 20px;
    }

    .hero-content {
      max-width: 100%;
    }

    h1 {
      font-size: 28px;
      line-height: 33px;
    }

    .hero-description {
      font-size: 15px;
      line-height: 23px;
    }

    .hero-action {
      align-items: flex-start;
      flex-direction: column;
    }

    .progress-ring,
    .hero-role-badge {
      height: 58px;
      position: relative;
      right: auto;
      top: auto;
      width: 58px;
      margin-top: 20px;
    }

    .hero-role-badge img:first-child {
      height: 58px;
      width: 52px;
    }

    .hero-role-badge img:last-child {
      height: 22px;
      width: 22px;
    }

    .progress-ring span,
    .progress-ring em {
      font-size: 14px;
      line-height: 20px;
    }
  }
</style>
