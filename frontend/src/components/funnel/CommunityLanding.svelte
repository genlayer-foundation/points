<script>
  let { state: roleState = 'unauthenticated', starting = false, onStart = () => {} } = $props();

  const primaryLabel = $derived(starting ? 'Starting...' : 'Grow the Community');
  const finalLabel = $derived(starting ? 'Starting...' : 'Grow the Community');
  const isUnauthenticated = $derived(roleState === 'unauthenticated');
  const ctaHint = $derived(
    isUnauthenticated
      ? 'Connect to start tracking your community contributions and points.'
      : 'Start contributing across tasks, content, testing, and ecosystem growth.'
  );

  const contributionCards = [
    {
      title: 'Test the protocol',
      body: 'Try projects, explore flows, and help make the network stronger before mainnet.',
    },
    {
      title: 'Surface bugs',
      body: 'Catch edge cases, report issues, and turn product feedback into contribution credit.',
    },
    {
      title: 'Create content',
      body: "Explain the adjudication layer, teach new users, and expand GenLayer's reach.",
    },
    {
      title: 'Grow the ecosystem',
      body: 'Bring builders, validators, and contributors into the network from day one.',
    },
  ];

  const pointsCards = [
    {
      title: 'Onchain tasks',
      body: 'Test projects and act across the ecosystem as the network comes online.',
    },
    {
      title: 'Social tasks',
      body: 'Take the project beyond its borders with content, distribution, and community action.',
    },
    {
      title: 'Portal record',
      body: 'Every contribution builds your public record of helping GenLayer from the earliest days.',
    },
  ];

  const stats = [
    { value: '100', suffix: 'K+', label: 'Community reach' },
    { value: '∞', label: 'Ways to contribute' },
    { value: 'Q4', suffix: '2026', label: 'Mainnet target' },
  ];
</script>

<svelte:head>
  <title>Community | GenLayer Portal</title>
</svelte:head>

<div class="role-landing community-landing">
  <section class="role-hero" aria-labelledby="community-landing-title">
    <div class="hero-copy">
      <p class="role-eyebrow">Community</p>
      <h1 id="community-landing-title">+100,000 Strong.<br />Building the Court of the Internet.</h1>
      <p>
        Join the community pushing the adjudication layer of the agentic economy
        and get rewarded for every contribution.
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

    <div class="hero-visual" aria-hidden="true">
      <div class="community-orbit">
        <span>Test</span>
        <span>Create</span>
        <strong>Portal</strong>
        <span>Grow</span>
        <span>Earn</span>
      </div>
      <div class="visual-card">
        <span>Contribution tracked</span>
        <strong>Points, tasks, referrals, and ecosystem action</strong>
      </div>
    </div>
  </section>

  <section class="feature-section" aria-labelledby="community-contribution-title">
    <div class="section-header">
      <h2 id="community-contribution-title">This Isn&apos;t a Spectator Community</h2>
      <p>
        Test the protocol. Surface bugs. Create content. Grow the ecosystem.
        On GenLayer, community work is tracked on the Portal and rewarded.
      </p>
    </div>
    <div class="feature-grid">
      {#each contributionCards as card}
        <article class="feature-card">
          <div class="feature-heading">
            <span class="feature-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 3v18M4 8h16M6 21h12M7 8c0 4.5 2 7 5 7s5-2.5 5-7M8 3h8"></path></svg>
            </span>
            <h3>{card.title}</h3>
          </div>
          <p>{card.body}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="statement-section" aria-label="Community statement">
    <h2>
      You&apos;re a contributor,<br />
      <span>not an audience.</span>
    </h2>
  </section>

  <section class="points-banner" id="community-points" aria-labelledby="community-points-title">
    <div class="points-copy">
      <h2 id="community-points-title">Earn GenLayer Points for Everything You Do</h2>
      <p>
        Every contribution earns GenLayer Points, your record of helping build
        the network from the earliest days.
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
      <h2 id="community-why-title">The Missing Layer of the Internet Is Being Built in the Open</h2>
      <p>
        Mainnet is coming. The contributors of today are the foundation of the
        network tomorrow. Position yourself in the next revolution of the internet,
        the agentic economy.
      </p>
    </div>
    <div class="stack-grid">
      {#each stats as stat}
        <article class="stack-card">
          <p class="stack-value">
            <span>{stat.value}</span>{#if stat.suffix}<em>{stat.suffix}</em>{/if}
          </p>
          <p class="stack-label">{stat.label}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="final-cta" aria-labelledby="community-final-title">
    <h2 id="community-final-title">Join and start earning.</h2>
    <p>Start contributing, collect community points, and help grow the network from day one.</p>
    <button
      type="button"
      class="landing-button landing-button-primary"
      onclick={() => onStart()}
      disabled={starting}
      aria-busy={starting}
    >
      <span>{finalLabel}</span>
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

  .role-eyebrow {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-size: 13px;
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

  .hero-copy > p,
  .final-cta > p {
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

  .hero-visual {
    align-content: center;
    aspect-ratio: 16 / 9;
    background:
      radial-gradient(circle at 80% 20%, rgba(var(--role-accent-rgb), 0.24), transparent 32%),
      linear-gradient(135deg, #fbf8ff 0%, #f3edff 100%);
    border: 1px solid rgba(var(--role-accent-rgb), 0.18);
    border-radius: 8px;
    display: grid;
    gap: 18px;
    padding: 28px;
    width: 100%;
  }

  .community-orbit {
    align-items: center;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .community-orbit span,
  .community-orbit strong,
  .visual-card {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(var(--role-accent-rgb), 0.16);
    border-radius: 8px;
    box-shadow: 0 14px 30px rgba(74, 46, 128, 0.12);
  }

  .community-orbit span,
  .community-orbit strong {
    align-items: center;
    display: flex;
    font-size: 12px;
    font-weight: 700;
    justify-content: center;
    min-height: 54px;
    padding: 10px;
    text-align: center;
    text-transform: uppercase;
  }

  .community-orbit strong {
    background: var(--role-gradient);
    color: #fff;
    min-height: 76px;
  }

  .visual-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 18px;
  }

  .visual-card span {
    color: #6b7280;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .visual-card strong {
    color: #111827;
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 500;
    line-height: 30px;
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

  .section-header h2 {
    font-size: 40px;
    letter-spacing: -1.2px;
    line-height: 48px;
    max-width: 570px;
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
    border: 1px solid var(--role-border);
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 18px;
  }

  .feature-heading {
    align-items: center;
    display: flex;
    gap: 12px;
  }

  .feature-icon {
    color: var(--role-accent);
    display: inline-flex;
    height: 24px;
    width: 24px;
  }

  .feature-icon svg {
    fill: none;
    height: 24px;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
    width: 24px;
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

    .community-orbit {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .community-orbit strong {
      grid-column: 1 / -1;
      order: -1;
    }
  }
</style>
