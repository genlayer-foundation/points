<script>
  import CategoryIcon from '../portal/CategoryIcon.svelte';
  import RoleLandingVideo from './RoleLandingVideo.svelte';
  import { m } from '../../lib/paraglide/messages.js';

  let { state: roleState = 'unauthenticated', starting = false, onStart = () => {} } = $props();

  const primaryLabel = $derived(starting ? m.cl_cta_starting() : m.cl_cta_become_creator());
  const isUnauthenticated = $derived(roleState === 'unauthenticated');
  const ctaHint = $derived(
    isUnauthenticated
      ? m.cl_cta_hint_unauthenticated()
      : m.cl_cta_hint_authenticated()
  );

  const contributionCards = [
    {
      icon: 'protocol',
      title: m.cl_card_protocol_title(),
      body: m.cl_card_protocol_body(),
    },
    {
      icon: 'bug',
      title: m.cl_card_bugs_title(),
      body: m.cl_card_bugs_body(),
    },
    {
      icon: 'content',
      title: m.cl_card_content_title(),
      body: m.cl_card_content_body(),
    },
    {
      icon: 'ecosystem',
      title: m.cl_card_ecosystem_title(),
      body: m.cl_card_ecosystem_body(),
    },
  ];

  const pointsCards = [
    {
      title: m.cl_points_onchain_title(),
      body: m.cl_points_onchain_body(),
    },
    {
      title: m.cl_points_social_title(),
      body: m.cl_points_social_body(),
    },
    {
      title: m.cl_points_passport_title(),
      body: m.cl_points_passport_body(),
    },
  ];

  const stats = [
    { value: '100', suffix: 'K+', label: m.cl_stat_reach_label() },
    { value: '∞', label: m.cl_stat_ways_label() },
    { value: 'Q4', suffix: '2026', label: m.cl_stat_mainnet_label() },
  ];
</script>

<svelte:head>
  <title>{m.cl_page_title()}</title>
</svelte:head>

<div class="role-landing community-landing">
  <section class="role-hero" aria-labelledby="community-landing-title">
    <div class="hero-copy">
      <div class="role-badge">
        <CategoryIcon category="community" mode="hexagon" size={40} />
        <span>{m.cl_role_badge()}</span>
      </div>
      <h1 id="community-landing-title">{m.cl_hero_line1()}<br />{m.cl_hero_line2()}</h1>
      <p>
        {m.cl_hero_description()}
      </p>
      <div class="cta-cluster">
        <div class="button-row">
          <button
            type="button"
            class="landing-button landing-button-primary"
            onclick={() => onStart()}
            disabled={starting}
            aria-busy={starting}
          >
            <span>{primaryLabel}</span>
            <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
          </button>
        </div>
        <p class="cta-hint">{ctaHint}</p>
      </div>
    </div>

    <RoleLandingVideo
      variant="community"
      eyebrow={m.cl_video_eyebrow()}
      title={m.cl_video_title()}
      description={m.cl_video_description()}
    />
  </section>

  <section class="feature-section" aria-labelledby="community-contribution-title">
    <div class="section-header centered">
      <h2 id="community-contribution-title">{m.cl_feature_title()}</h2>
    </div>
    <div class="feature-grid">
      {#each contributionCards as card}
        <article class="feature-card">
          <div class="feature-heading">
            <span class="feature-icon" aria-hidden="true">
              {#if card.icon === 'protocol'}
                <svg viewBox="0 0 24 24"><path d="M12 3 4.5 7v5.5c0 4.1 2.6 7.1 7.5 8.5 4.9-1.4 7.5-4.4 7.5-8.5V7L12 3Z"></path><path d="m9 12 2 2 4-5"></path></svg>
              {:else if card.icon === 'bug'}
                <svg viewBox="0 0 24 24"><path d="M8 8.5A4 4 0 0 1 16 8.5V16a4 4 0 0 1-8 0V8.5Z"></path><path d="M3 13h5M16 13h5M5 19l3-3M16 16l3 3M5 6l3 3M16 9l3-3M9 4l1.5 2M15 4l-1.5 2"></path></svg>
              {:else if card.icon === 'content'}
                <svg viewBox="0 0 24 24"><path d="M4 19.5 5.5 15 16 4.5a2.1 2.1 0 0 1 3 3L8.5 18 4 19.5Z"></path><path d="m14.5 6 3.5 3.5M12 20h8"></path></svg>
              {:else}
                <svg viewBox="0 0 24 24"><path d="M16 11a4 4 0 1 0-8 0"></path><path d="M3 20a7 7 0 0 1 18 0M18 8a3 3 0 0 1 2.5 4.7M6 8a3 3 0 0 0-2.5 4.7"></path></svg>
              {/if}
            </span>
            <h3>{card.title}</h3>
          </div>
          <p>{card.body}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="statement-section" aria-label={m.cl_statement_aria()}>
    <h2>
      {m.cl_statement_line1()}<br />
      <span>{m.cl_statement_line2()}</span>
    </h2>
  </section>

  <section class="points-banner" id="community-points" aria-labelledby="community-points-title">
    <div class="points-copy">
      <h2 id="community-points-title">{m.cl_points_title()}</h2>
      <p>
        {m.cl_points_description()}
      </p>
    </div>
    <div class="points-grid">
      {#each pointsCards as card}
        <article>
          <h3>{card.title}</h3>
          <p>{card.body}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="why-section" aria-labelledby="community-why-title">
    <div class="section-header">
      <h2 id="community-why-title">{m.cl_why_title()}</h2>
      <p>
        {m.cl_why_description()}
      </p>
    </div>
    <div class="stack-grid">
      {#each stats as stat}
        <article class="stack-card">
          <p class="stack-value">
            <span class:stack-symbol={stat.value === '∞'}>{stat.value}</span>{#if stat.suffix}<em>{stat.suffix}</em>{/if}
          </p>
          <p class="stack-label">{stat.label}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="final-cta" aria-labelledby="community-final-title">
    <h2 id="community-final-title">{m.cl_final_title()}</h2>
    <button
      type="button"
      class="landing-button landing-button-primary"
      onclick={() => onStart()}
      disabled={starting}
      aria-busy={starting}
    >
      <span>{primaryLabel}</span>
      <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
    </button>
  </section>
</div>

<style>
  .role-landing {
    --role-accent: #7f52e1;
    --role-accent-rgb: 127, 82, 225;
    --role-border: #eee8fb;
    --role-muted: #7b728d;
    --role-black: #131214;
    --role-gradient: linear-gradient(168deg, #be8ff5 15%, #a86ff0 50%, #7f52e1 85%);
    --landing-max: 1316px;
    align-items: center;
    background-color: #fff;
    background-image:
      linear-gradient(0deg, rgba(var(--role-accent-rgb), 0.13) 0%, rgba(255, 255, 255, 0) 34rem),
      radial-gradient(circle at 12% 100%, rgba(var(--role-accent-rgb), 0.22), transparent 28rem),
      radial-gradient(circle at 88% 96%, rgba(var(--role-accent-rgb), 0.16), transparent 26rem);
    background-position: center bottom, left bottom, right bottom;
    background-repeat: no-repeat;
    background-size: 100% 38rem, 46rem 32rem, 42rem 30rem;
    box-sizing: border-box;
    color: #000;
    display: flex;
    flex-direction: column;
    gap: 32px;
    isolation: isolate;
    margin: -12px;
    min-height: calc(100vh - 57px);
    min-height: calc(100dvh - 57px);
    min-width: 0;
    overflow: hidden;
    padding: 12px 12px 0;
    position: relative;
    width: calc(100% + 24px);
  }

  .role-landing::before {
    background:
      linear-gradient(rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0.25)),
      radial-gradient(circle at 14% 8%, rgba(var(--role-accent-rgb), 0.38) 0%, transparent 34%),
      radial-gradient(circle at 82% 12%, rgba(var(--role-accent-rgb), 0.24) 0%, transparent 32%),
      linear-gradient(180deg, rgba(var(--role-accent-rgb), 0.16) 0%, rgba(255, 255, 255, 0) 100%);
    content: '';
    height: 320px;
    left: 0;
    pointer-events: none;
    position: absolute;
    right: 0;
    top: 0;
    z-index: 0;
    -webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%);
    mask-image: linear-gradient(to bottom, black 0%, transparent 100%);
  }

  .role-landing > section {
    box-sizing: border-box;
    min-width: 0;
    position: relative;
    z-index: 1;
  }

  .role-hero {
    align-items: center;
    display: grid;
    gap: 48px;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 1fr);
    margin-inline: auto;
    max-width: var(--landing-max);
    padding: 32px 20px 88px;
    width: 100%;
  }

  .hero-copy,
  .section-header,
  .points-copy {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .role-badge {
    align-items: center;
    color: var(--role-accent);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 13px;
    gap: 10px;
    letter-spacing: 0.8px;
    line-height: 20px;
    margin: 0;
    text-transform: uppercase;
  }

  h1,
  h2,
  h3 {
    font-family: var(--font-display);
    font-weight: 500;
    margin: 0;
  }

  h1 {
    font-size: 48px;
    letter-spacing: -1.44px;
    line-height: 52px;
  }

  .hero-copy > p {
    color: var(--role-muted);
    font-family: var(--font-mono);
    font-size: 16px;
    letter-spacing: 0.32px;
    line-height: 24px;
    margin: 0;
    max-width: 610px;
    text-transform: uppercase;
  }

  .button-row {
    align-items: flex-start;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .cta-cluster {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .cta-hint {
    color: #736983;
    font-size: 14px;
    line-height: 20px;
    margin: 0;
    max-width: 430px;
  }

  .landing-button {
    align-items: center;
    border-radius: 20px;
    display: inline-flex;
    font-size: 14px;
    font-weight: 500;
    gap: 8px;
    height: 40px;
    justify-content: center;
    padding: 0 16px;
    transition-property: background-color, border-color, color, opacity, transform, box-shadow;
    transition-duration: 160ms;
    transition-timing-function: ease;
    white-space: nowrap;
  }

  .landing-button span {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .landing-button img {
    height: 16px;
    width: 16px;
  }

  .landing-button-primary {
    background: var(--role-gradient);
    box-shadow: 0 10px 24px rgba(var(--role-accent-rgb), 0.28);
    color: #fff;
  }

  .landing-button-primary:hover:not(:disabled) {
    box-shadow: 0 14px 28px rgba(var(--role-accent-rgb), 0.34);
    transform: translateY(-1px);
  }

  .landing-button-primary:disabled {
    cursor: default;
    opacity: 0.62;
  }

  .landing-button:active:not(:disabled) {
    transform: scale(0.96);
  }

  .feature-section,
  .why-section,
  .final-cta {
    margin-inline: auto;
    max-width: var(--landing-max);
    width: 100%;
  }

  .feature-section,
  .why-section {
    display: flex;
    flex-direction: column;
    gap: 40px;
    padding: 20px;
  }

  .section-header {
    align-items: flex-start;
    flex-direction: row;
    justify-content: space-between;
  }

  .section-header.centered {
    align-items: center;
    flex-direction: column;
    text-align: center;
  }

  .section-header h2 {
    font-size: 40px;
    letter-spacing: -1.2px;
    line-height: 48px;
    max-width: 570px;
  }

  .section-header.centered h2 {
    max-width: 780px;
  }

  .section-header p {
    color: var(--role-muted);
    font-size: 16px;
    line-height: 24px;
    margin: 0;
    max-width: 590px;
  }

  .feature-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    width: 100%;
  }

  .feature-card {
    align-items: center;
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid var(--role-border);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 18px;
    text-align: center;
  }

  .feature-heading {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .feature-icon {
    align-items: center;
    background: rgba(var(--role-accent-rgb), 0.08);
    border: 1px solid rgba(var(--role-accent-rgb), 0.14);
    border-radius: 999px;
    color: var(--role-accent);
    display: flex;
    height: 42px;
    justify-content: center;
    width: 42px;
  }

  .feature-icon svg {
    fill: none;
    height: 22px;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
    width: 22px;
  }

  .feature-card h3 {
    font-size: 24px;
    letter-spacing: -0.48px;
    line-height: 32px;
  }

  .feature-card p {
    color: #6d6679;
    font-size: 17px;
    line-height: 24px;
    margin: 0;
  }

  .statement-section {
    align-items: center;
    display: flex;
    justify-content: center;
    padding: 128px 20px;
    text-align: center;
  }

  .statement-section h2 {
    font-size: 64px;
    letter-spacing: -1.92px;
    line-height: 1;
    margin: 0;
    max-width: 1129px;
  }

  .statement-section span {
    color: var(--role-accent);
  }

  .points-banner {
    align-items: center;
    align-self: center;
    background:
      radial-gradient(circle at 94% 46%, rgba(var(--role-accent-rgb), 0.82) 0, rgba(var(--role-accent-rgb), 0.42) 24%, rgba(var(--role-accent-rgb), 0.12) 45%, transparent 60%),
      linear-gradient(90deg, #131214 0%, #181423 60%, #442d7a 100%);
    border-radius: 8px;
    color: #fff;
    display: flex;
    gap: 40px;
    justify-content: space-between;
    max-width: 1028px;
    overflow: hidden;
    padding: 48px;
    width: min(100%, 1028px);
  }

  .points-copy {
    max-width: 520px;
  }

  .points-copy h2 {
    color: #fff;
    font-size: 40px;
    letter-spacing: -1.2px;
    line-height: 48px;
  }

  .points-copy p {
    color: rgba(255, 255, 255, 0.72);
    font-size: 16px;
    line-height: 24px;
    margin: 0;
  }

  .points-grid {
    display: grid;
    flex: 1 1 auto;
    gap: 12px;
    grid-template-columns: 1fr;
    max-width: 390px;
  }

  .points-grid article {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 14px;
  }

  .points-grid h3 {
    color: #fff;
    font-size: 18px;
    line-height: 24px;
  }

  .points-grid p {
    color: rgba(255, 255, 255, 0.72);
    font-size: 14px;
    line-height: 20px;
    margin: 8px 0 0;
  }

  .stack-grid {
    display: grid;
    gap: 25px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .stack-card {
    align-items: center;
    border: 1px solid var(--role-border);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    text-align: center;
  }

  .stack-value {
    color: #000;
    font-family: var(--font-display);
    font-size: 64px;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    letter-spacing: -1.92px;
    line-height: 68px;
    margin: 0;
  }

  .stack-value em {
    color: var(--role-accent);
    font-style: normal;
    margin-left: 2px;
  }

  .stack-symbol {
    display: inline-block;
    font-size: 1.35em;
    line-height: 0.75;
  }

  .stack-label {
    color: #6d6679;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.26px;
    line-height: 18px;
    margin: 0;
    text-transform: uppercase;
  }

  .final-cta {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 24px;
    justify-content: center;
    padding: 0 20px 96px;
    text-align: center;
  }

  .final-cta h2 {
    font-size: 48px;
    letter-spacing: -1.44px;
    line-height: 52px;
  }

  @media (max-width: 1180px) {
    .feature-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 900px) {
    .role-hero,
    .feature-grid,
    .stack-grid {
      grid-template-columns: 1fr;
    }

    .role-hero {
      padding: 32px 12px 64px;
    }

    .hero-copy,
    .section-header,
    .points-banner {
      align-items: center;
      flex-direction: column;
      text-align: center;
    }

    .cta-cluster,
    .button-row {
      align-items: center;
      justify-content: center;
    }
  }

  @media (max-width: 767px) {
    .role-landing {
      margin: 0;
      padding: 0 12px 0;
      width: 100%;
    }

    .role-hero {
      padding: 20px 0 56px;
    }
  }

  @media (max-width: 640px) {
    .role-landing {
      gap: 36px;
    }

    h1,
    .final-cta h2 {
      font-size: 38px;
      line-height: 42px;
    }

    .section-header h2,
    .points-copy h2 {
      font-size: 32px;
      line-height: 38px;
    }

    .statement-section {
      padding: 72px 12px;
    }

    .statement-section h2 {
      font-size: 42px;
      line-height: 1.05;
    }

    .points-banner {
      padding: 32px 20px;
    }

  }
</style>
