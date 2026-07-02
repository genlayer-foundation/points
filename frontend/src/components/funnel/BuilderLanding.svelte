<script>
  import { onMount } from 'svelte';
  import { projectsAPI } from '../../lib/api.js';
  import { resolvePortalLink } from '../../lib/links.js';
  import CategoryIcon from '../portal/CategoryIcon.svelte';
  import RoleLandingVideo from './RoleLandingVideo.svelte';

  let { state: roleState = 'unauthenticated', starting = false, onStart = () => {} } = $props();

  const BOILERPLATE_REPO = 'genlayerlabs/genlayer-project-boilerplate';
  const INITIAL_BOILERPLATE_STARS = 13852;
  const docsUrl = 'https://docs.genlayer.com';
  const FALLBACK_PROJECTS = [
    { title: 'Rally', href: '/builders/projects/rally', external: false },
    { title: 'MergeProof', href: '/builders/projects/mergeproof', external: false },
    { title: 'FUD.markets', href: '/builders/projects/fudmarkets', external: false },
    { title: 'AutoBounty', href: '/builders/projects/autobounty', external: false },
    { title: 'Shipyard', href: '/builders/projects/shipyard', external: false },
  ];
  let boilerplateStars = $state(INITIAL_BOILERPLATE_STARS);
  let projects = $state(FALLBACK_PROJECTS);

  const isUnauthenticated = $derived(roleState === 'unauthenticated');
  const primaryDisabled = $derived(starting);
  const primaryLabel = $derived(
    starting ? 'Starting Journey...' : 'Become a Builder'
  );
  const ctaHint = $derived(
    isUnauthenticated
      ? 'Connect to unlock builder tasks, points, and your first contribution.'
      : 'Start your builder journey: GitHub, boilerplate star, first contribution.'
  );

  const githubStarsDisplay = $derived(formatCompactStars(boilerplateStars));

  const features = [
    {
      icon: 'globe',
      title: 'Native Web Access',
      body: 'Read APIs, websites, and live events directly during contract execution.',
    },
    {
      icon: 'translate',
      title: 'Natural Language Logic',
      body: 'Write rules in plain language and let validators evaluate the meaning.',
    },
    {
      icon: 'scales',
      title: 'Subjective Resolution',
      body: 'Resolve outcomes that require judgment, evidence, and context.',
    },
    {
      icon: 'bolt',
      title: 'Machine-Speed Finality',
      body: 'Settle disputes in minutes with on-chain finality for agent workflows.',
    },
  ];

  const stats = $derived([
    { title: 'The Codebase', value: githubStarsDisplay, suffix: 'K+', label: 'GitHub Stars' },
    { title: 'The Core Team', value: '1', center: ':', suffix: '1', label: 'Access to the builders of GenLayer' },
    { title: 'The Distribution', value: '100', suffix: 'K+', label: 'Community Reach' },
  ]);

  /**
   * @param {unknown} value
   */
  function formatCompactStars(value) {
    const n = Number(value);
    const stars = Number.isFinite(n) ? n : INITIAL_BOILERPLATE_STARS;
    return (stars / 1000).toFixed(1).replace('.', ',');
  }

  async function fetchBoilerplateStars() {
    try {
      const response = await fetch(`https://api.github.com/repos/${BOILERPLATE_REPO}`, {
        headers: { Accept: 'application/vnd.github+json' },
      });
      if (!response.ok) return;

      const data = await response.json();
      const stars = Number(data?.stargazers_count);
      if (Number.isFinite(stars)) boilerplateStars = stars;
    } catch {
      // Keep the latest verified fallback if GitHub is unavailable.
    }
  }

  async function fetchOverviewProjects() {
    try {
      const response = await projectsAPI.list({ show_in_overview: true, limit: 5 });
      const rows = Array.isArray(response.data) ? response.data : [];
      const overviewProjects = rows
        .slice(0, 5)
        .map((project) => {
          const link = resolvePortalLink(project.link || project.url || (project.slug ? `/builders/projects/${project.slug}` : '#'));
          return {
            title: project.title,
            href: link.href,
            external: link.external,
          };
        })
        .filter((project) => project.title && project.href);
      projects = overviewProjects.length > 0 ? overviewProjects : FALLBACK_PROJECTS;
    } catch {
      projects = FALLBACK_PROJECTS;
    }
  }

  onMount(() => {
    fetchBoilerplateStars();
    fetchOverviewProjects();
  });
</script>

<svelte:head>
  <title>Builders | GenLayer Portal</title>
</svelte:head>

<div class="builder-landing">
  <section class="builder-hero" aria-labelledby="builder-hero-title">
    <div class="hero-copy">
      <div class="role-badge">
        <CategoryIcon category="builder" mode="hexagon" size={40} />
        <span>Builders</span>
      </div>
      <h1 id="builder-hero-title">Build Contracts<br />That Can Think</h1>
      <p>
        Smart contracts execute. Intelligent Contracts reason: they read the web,
        understand natural language, and resolve disputes no if/else ever could.
      </p>
      <div class="cta-cluster">
        <div class="button-row">
          <button
            type="button"
            class="landing-button landing-button-primary"
            onclick={() => onStart()}
            disabled={primaryDisabled}
            aria-busy={starting}
          >
            <span>{primaryLabel}</span>
            <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
          </button>
          <a class="landing-button landing-button-secondary" href={docsUrl} target="_blank" rel="noopener noreferrer">
            Read the Docs
          </a>
        </div>
        <p class="cta-hint">{ctaHint}</p>
      </div>
    </div>
    <RoleLandingVideo
      variant="builder"
      eyebrow="Builder Preview"
      title="Contracts that reason"
      description="A short look at the portal path from first action to intelligent contract launch."
    />
  </section>

  <section class="capability-section" aria-labelledby="builder-capabilities-title">
    <h2 id="builder-capabilities-title">
      What you can build here that<br />you can't build anywhere else.
    </h2>
    <div class="feature-grid">
      {#each features as feature}
        <article class="feature-card">
          <div class="feature-heading">
            <span class="feature-icon" aria-hidden="true">
              {#if feature.icon === 'globe'}
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><path d="M3 12h18M12 3c2.4 2.5 3.6 5.5 3.6 9S14.4 18.5 12 21M12 3c-2.4 2.5-3.6 5.5-3.6 9s1.2 6.5 3.6 9"></path></svg>
              {:else if feature.icon === 'translate'}
                <svg viewBox="0 0 24 24"><path d="M4 5h9M9 3v2M7 19l5-11M5 9c1.1 2.4 3.1 4.4 6 6M13 15c-2.1-.7-4.3-2.4-6-5M14 21l4-9 4 9M15.5 18h5"></path></svg>
              {:else if feature.icon === 'scales'}
                <svg viewBox="0 0 24 24"><path d="M12 3v18M5 6h14M7 6l-4 7h8L7 6ZM17 6l-4 7h8l-4-7ZM8 21h8"></path></svg>
              {:else}
                <svg viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 10-13h-7l1-7Z"></path></svg>
              {/if}
            </span>
            <h3>{feature.title}</h3>
          </div>
          <p>{feature.body}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="statement-section" aria-label="GenLayer statement">
    <h2>
      Oracles verify facts.<br />
      <span>GenLayer</span> adjudicates meaning.
    </h2>
  </section>

  <section class="category-section" aria-labelledby="builder-category-title">
    <div class="category-header">
      <h2 id="builder-category-title">An entire category, wide open.</h2>
      <p>
        Performance-based contracts, agent marketplaces, prediction markets,
        parametric insurance, autonomous finance: every vertical on GenLayer is
        unclaimed territory. The builders shipping today are defining the category,
        not competing in it.
      </p>
    </div>
    <div class="project-chip-row" aria-label="Featured builder projects">
      {#each projects as project}
        <a
          href={project.href}
          target={project.external ? '_blank' : undefined}
          rel={project.external ? 'noopener noreferrer' : undefined}
        >
          {project.title}
        </a>
      {/each}
    </div>
  </section>

  <section class="earn-banner" aria-labelledby="builder-earn-title">
    <div class="earn-copy">
      <h2 id="builder-earn-title">Don't just deploy. Earn.</h2>
      <p>
        Earn up to 20% of the fees from every transaction your project generates,
        and win GenLayer Points for all your daily actions. On GenLayer, your app
        is a revenue stream from day one.
      </p>
    </div>
    <div class="earn-stat">
      <div class="earn-stat-value">
        <span class="earn-stat-prefix">Up to</span>
        <strong>20%</strong>
      </div>
      <span class="earn-stat-label">Of transaction fees, back to you</span>
    </div>
  </section>

  <section class="stack-section" aria-labelledby="builder-stack-title">
    <h2 id="builder-stack-title">A full stack behind you.</h2>
    <div class="stack-grid">
      {#each stats as stat}
        <article class="stack-card">
          <h3>{stat.title}</h3>
          <p class="stack-value">
            <span>{stat.value}</span>{#if stat.center}<em>{stat.center}</em>{/if}{#if stat.suffix}<span class:accent={!stat.center}>{stat.suffix}</span>{/if}
          </p>
          <p class="stack-label">{stat.label}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="final-cta" aria-labelledby="builder-final-title">
    <h2 id="builder-final-title">Ship your first<br />Intelligent Contract.</h2>
    <div class="cta-cluster cta-cluster-centered">
      <div class="button-row">
        <button
          type="button"
          class="landing-button landing-button-primary"
          onclick={() => onStart()}
          disabled={primaryDisabled}
          aria-busy={starting}
        >
          <span>{primaryLabel}</span>
          <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
        </button>
        <a class="landing-button landing-button-secondary" href={docsUrl} target="_blank" rel="noopener noreferrer">
          Read the Docs
        </a>
      </div>
    </div>
  </section>
</div>

<style>
  .builder-landing {
    --builder-black: #131214;
    --builder-orange: #ee8521;
    --builder-border: #ededed;
    --builder-muted: #909090;
    --landing-accent-rgb: 238, 133, 33;
    --landing-max: 1316px;
    align-items: center;
    background-color: #fff;
    background-image:
      linear-gradient(0deg, rgba(var(--landing-accent-rgb), 0.13) 0%, rgba(255, 255, 255, 0) 34rem),
      radial-gradient(circle at 12% 100%, rgba(var(--landing-accent-rgb), 0.22), transparent 28rem),
      radial-gradient(circle at 88% 96%, rgba(var(--landing-accent-rgb), 0.16), transparent 26rem);
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

  .builder-landing :global(*) {
    letter-spacing: 0;
  }

  .builder-landing::before {
    content: '';
    left: 0;
    pointer-events: none;
    position: absolute;
    right: 0;
    z-index: 0;
  }

  .builder-landing::before {
    background:
      linear-gradient(rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0.25)),
      radial-gradient(circle at 14% 8%, rgba(var(--landing-accent-rgb), 0.38) 0%, transparent 34%),
      radial-gradient(circle at 82% 12%, rgba(var(--landing-accent-rgb), 0.24) 0%, transparent 32%),
      linear-gradient(180deg, rgba(var(--landing-accent-rgb), 0.16) 0%, rgba(255, 255, 255, 0) 100%);
    height: 320px;
    top: 0;
    -webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%);
    mask-image: linear-gradient(to bottom, black 0%, transparent 100%);
  }

  .builder-landing > section {
    box-sizing: border-box;
    min-width: 0;
    position: relative;
    z-index: 1;
  }

  .builder-hero {
    align-items: center;
    display: grid;
    gap: 48px;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 1fr);
    margin-inline: auto;
    max-width: var(--landing-max);
    padding: 32px 20px 88px;
    width: 100%;
  }

  .hero-copy {
    align-items: flex-start;
    display: flex;
    flex-direction: column;
    gap: 24px;
    justify-content: center;
  }

  .role-badge {
    align-items: center;
    color: var(--builder-orange);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 13px;
    gap: 10px;
    letter-spacing: 0.8px !important;
    line-height: 20px;
    margin: 0;
    text-transform: uppercase;
  }

  .hero-copy h1,
  .capability-section h2,
  .statement-section h2,
  .category-header h2,
  .earn-banner h2,
  .stack-section > h2,
  .final-cta h2 {
    font-family: var(--font-display);
    font-weight: 500;
  }

  .hero-copy h1 {
    font-size: 48px;
    letter-spacing: -1.44px !important;
    line-height: 52px;
    margin: 0;
  }

  .hero-copy > p {
    color: var(--builder-muted);
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 400;
    letter-spacing: 0.32px !important;
    line-height: 24px;
    margin: 0;
    max-width: 590px;
    text-transform: uppercase;
  }

  .button-row {
    align-items: flex-start;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .cta-cluster {
    align-items: flex-start;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .cta-cluster-centered {
    align-items: center;
  }

  .cta-hint {
    color: #6f6f6f;
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 20px;
    margin: 0;
    max-width: 420px;
    text-wrap: pretty;
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
    letter-spacing: 0.28px !important;
    line-height: 21px;
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
    background: linear-gradient(168deg, #f8b93d 15%, #ee8d24 50%, #db6917 85%);
    box-shadow: 0 10px 24px rgba(238, 133, 33, 0.28);
    color: #fff;
  }

  .landing-button-primary:hover:not(:disabled) {
    background: linear-gradient(168deg, #ffc64e 15%, #f39a32 50%, #e17420 85%);
    box-shadow: 0 14px 28px rgba(238, 133, 33, 0.34);
    transform: translateY(-1px);
  }

  .landing-button-primary:disabled {
    cursor: default;
    opacity: 0.62;
  }

  .landing-button:active:not(:disabled) {
    transform: scale(0.96);
  }

  .landing-button-secondary {
    border: 1px solid var(--builder-black);
    color: var(--builder-black);
  }

  .landing-button-secondary:hover {
    background: #f5f5f5;
  }

  .capability-section,
  .statement-section,
  .category-section,
  .stack-section,
  .final-cta {
    margin-inline: auto;
    max-width: var(--landing-max);
  }

  .capability-section,
  .category-section,
  .stack-section {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 40px;
    justify-content: center;
    padding: 20px;
    width: 100%;
  }

  .capability-section h2 {
    font-size: 40px;
    letter-spacing: -1.2px !important;
    line-height: 48px;
    margin: 0;
    text-align: center;
  }

  .feature-grid {
    align-items: stretch;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    width: 100%;
  }

  .feature-card {
    align-items: center;
    border: 1px solid var(--builder-border);
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    text-align: center;
  }

  .feature-heading {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .feature-icon {
    color: var(--builder-orange);
    display: inline-flex;
    flex: 0 0 auto;
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
    font-family: var(--font-display);
    font-size: clamp(18px, 1.55vw, 24px);
    font-weight: 500;
    letter-spacing: -0.48px !important;
    line-height: 1.2;
    margin: 0;
    text-transform: none;
    white-space: nowrap;
  }

  .feature-card p {
    color: #737373;
    font-family: var(--font-body);
    font-size: 18px;
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
    letter-spacing: -1.92px !important;
    line-height: 1;
    margin: 0;
    max-width: 1129px;
  }

  .statement-section span {
    color: var(--builder-orange);
  }

  .category-header {
    align-items: flex-start;
    display: flex;
    justify-content: space-between;
    width: 100%;
  }

  .category-header h2 {
    font-size: 40px;
    letter-spacing: -1.2px !important;
    line-height: 48px;
    margin: 0;
    white-space: nowrap;
  }

  .category-header p {
    color: var(--builder-muted);
    font-family: var(--font-body);
    font-size: 16px;
    letter-spacing: 0.32px !important;
    line-height: 24px;
    margin: 0;
    max-width: 590px;
  }

  .project-chip-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    width: 100%;
  }

  .project-chip-row a {
    border: 1px solid var(--builder-border);
    border-radius: 32px;
    color: #000;
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 400;
    letter-spacing: -0.32px !important;
    line-height: 32px;
    padding: 16px 24px;
    text-decoration: none;
    text-transform: none;
    transition: border-color 160ms ease, color 160ms ease, transform 160ms ease;
    white-space: nowrap;
  }

  .project-chip-row a:hover {
    border-color: rgba(238, 133, 33, 0.5);
    color: var(--builder-orange);
    transform: translateY(-1px);
  }

  .earn-banner {
    align-items: center;
    align-self: center;
    background:
      radial-gradient(circle at 94% 46%, rgba(238, 133, 33, 0.95) 0, rgba(238, 133, 33, 0.56) 22%, rgba(238, 133, 33, 0.12) 43%, transparent 58%),
      linear-gradient(90deg, #131214 0%, #171518 59%, #6c340f 100%);
    border-radius: 8px;
    color: #fff;
    display: flex;
    gap: 40px;
    justify-content: center;
    max-width: 1028px;
    overflow: hidden;
    padding: 48px;
    position: relative;
    width: min(100%, 1028px);
  }

  .earn-copy {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    gap: 24px;
    max-width: 590px;
    position: relative;
    z-index: 1;
  }

  .earn-copy h2 {
    color: #fff;
    font-size: 40px;
    letter-spacing: -1.2px !important;
    line-height: 48px;
    margin: 0;
  }

  .earn-copy p {
    color: #b3b3b3;
    font-family: var(--font-body);
    font-size: 16px;
    letter-spacing: 0.32px !important;
    line-height: 24px;
    margin: 0;
  }

  .earn-stat {
    align-items: center;
    display: flex;
    flex: 0 0 auto;
    flex-direction: column;
    gap: 12px;
    justify-content: center;
    position: relative;
    z-index: 1;
  }

  .earn-stat-value {
    align-items: baseline;
    display: flex;
    gap: 12px;
    justify-content: center;
    white-space: nowrap;
  }

  .earn-stat-prefix {
    color: rgba(255, 255, 255, 0.86);
    font-family: var(--font-mono);
    font-size: 18px;
    font-weight: 500;
    letter-spacing: 0.36px !important;
    line-height: 24px;
    text-transform: uppercase;
  }

  .earn-stat strong {
    color: #fff;
    font-family: var(--font-display);
    font-size: 128px;
    font-weight: 500;
    letter-spacing: -3.84px !important;
    line-height: 128px;
  }

  .earn-stat-label {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    color: #fff;
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0.28px !important;
    line-height: 20px;
    padding: 6px 12px;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .stack-section > h2 {
    font-size: 40px;
    letter-spacing: -1.2px !important;
    line-height: 48px;
    margin: 0;
    text-align: center;
  }

  .stack-grid {
    display: grid;
    gap: 25px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .stack-card {
    align-items: center;
    border: 1px solid var(--builder-border);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    text-align: center;
  }

  .stack-card h3 {
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 500;
    letter-spacing: -0.48px !important;
    line-height: 32px;
    margin: 0;
    text-transform: capitalize;
  }

  .stack-value {
    color: #000;
    font-family: var(--font-display);
    font-size: 80px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    letter-spacing: -2.4px !important;
    line-height: 80px;
    margin: 0;
  }

  .stack-value em,
  .stack-value .accent {
    color: var(--builder-orange);
    font-style: normal;
  }

  .stack-label {
    color: #5e5e5e;
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0.28px !important;
    line-height: 20px;
    margin: 0;
    text-transform: uppercase;
  }

  .final-cta {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 24px;
    justify-content: center;
    padding: 0 20px 88px;
    text-align: center;
    width: 100%;
  }

  .final-cta h2 {
    font-size: 48px;
    letter-spacing: -1.44px !important;
    line-height: 52px;
    margin: 0;
  }

  @media (max-width: 1180px) {
    .feature-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .category-header {
      gap: 24px;
    }

    .earn-stat strong {
      font-size: 96px;
      line-height: 100px;
    }

    .earn-stat-prefix {
      font-size: 16px;
      line-height: 22px;
    }
  }

  @media (max-width: 900px) {
    .builder-hero {
      grid-template-columns: 1fr;
      padding: 32px 12px 64px;
    }

    .hero-copy {
      align-items: center;
      text-align: center;
    }

    .cta-cluster {
      align-items: center;
      text-align: center;
    }

    .category-header,
    .earn-banner {
      align-items: center;
      flex-direction: column;
      text-align: center;
    }

    .category-header h2 {
      white-space: normal;
    }

    .stack-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 767px) {
    .builder-landing {
      margin: 0;
      padding: 0 12px 0;
      width: 100%;
    }

    .builder-hero {
      padding: 20px 0 56px;
    }
  }

  @media (max-width: 640px) {
    .builder-landing {
      gap: 36px;
    }

    .hero-copy h1,
    .final-cta h2 {
      font-size: 38px;
      line-height: 42px;
    }

    .capability-section h2,
    .category-header h2,
    .earn-copy h2,
    .stack-section > h2 {
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

    .feature-grid {
      grid-template-columns: 1fr;
    }

    .project-chip-row a {
      font-size: 13px;
      line-height: 22px;
      max-width: 100%;
      overflow-wrap: anywhere;
      padding: 10px 14px;
      text-align: center;
      white-space: normal;
    }

    .earn-banner {
      padding: 32px 20px;
    }

    .earn-stat strong {
      font-size: 80px;
      line-height: 84px;
    }

    .earn-stat-value {
      gap: 8px;
    }

    .earn-stat-prefix {
      font-size: 14px;
      line-height: 20px;
    }

    .earn-stat-label {
      white-space: normal;
    }

    .button-row {
      flex-wrap: wrap;
      justify-content: center;
    }
  }
</style>
