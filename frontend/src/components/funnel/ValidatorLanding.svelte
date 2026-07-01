<script>
  import { onMount } from 'svelte';
  import { validatorsAPI } from '../../lib/api.js';
  import CategoryIcon from '../portal/CategoryIcon.svelte';
  import RoleLandingVideo from './RoleLandingVideo.svelte';

  let { state: roleState = 'unauthenticated', starting = false, onStart = () => {} } = $props();

  const isWaitlisted = $derived(roleState === 'waitlisted');
  const primaryLabel = $derived(starting ? 'Starting...' : 'Join the Waitlist');
  let professionalValidatorCount = $state(null);

  const comparisonCards = [
    {
      icon: 'attest',
      title: 'Traditional validator',
      value: 'Attest',
      body: 'Passive infrastructure with capped single-digit yields.',
    },
    {
      icon: 'genlayer',
      title: 'GenLayer validator',
      value: 'Reason',
      body: 'Run an LLM-backed validator, evaluate evidence through Optimistic Democracy, and finalize accepted outcomes on-chain.',
    },
  ];

  const economics = [
    'Paid per decision, with each decision recorded through 15+ on-chain transactions.',
    'On mainnet, the same activity profile would already rank GenLayer Top-15 among all chains by daily fees.',
  ];

  const proofStats = $derived([
    { value: '4,097', label: 'Peak-day decisions' },
    { value: formatMetricNumber(professionalValidatorCount), label: 'Professional validators live' },
    { value: 'Q4', suffix: '2026', label: 'Mainnet target' },
  ]);

  const workflow = [
    'Random selection assigns a proposer',
    'Proposer runs an LLM-backed evaluation',
    'Validators independently verify',
    'Appeals settle disputes on-chain',
  ];

  function formatMetricNumber(value) {
    if (value == null || value === '') return '—';
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    return n.toLocaleString();
  }

  onMount(async () => {
    try {
      const response = await validatorsAPI.getAllValidatorWallets();
      const active = response.data?.stats?.active;
      if (active != null && active !== '') {
        professionalValidatorCount = active;
        return;
      }
      professionalValidatorCount = null;
    } catch {
      professionalValidatorCount = null;
    }
  });
</script>

<svelte:head>
  <title>Validators | GenLayer Portal</title>
</svelte:head>

<div class="role-landing validator-landing">
  {#snippet waitlistBadge()}
    <div class="waitlist-status">
      <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path
          fill-rule="evenodd"
          d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.5 7.59a1 1 0 0 1-1.42.006L3.29 9.79a1 1 0 1 1 1.42-1.408l3.79 3.83 6.79-6.872a1 1 0 0 1 1.414-.06Z"
          clip-rule="evenodd"
        />
      </svg>
      You&apos;re on the waitlist
    </div>
  {/snippet}

  <section class="role-hero" aria-labelledby="validator-landing-title">
    <div class="hero-copy">
      <div class="role-badge">
        <CategoryIcon category="validator" mode="hexagon" size={40} />
        <span>Validators</span>
      </div>
      <h1 id="validator-landing-title">Don&apos;t Validate Blocks.<br />Adjudicate the Agentic Economy.</h1>
      <p>
        GenLayer validators run LLM-backed nodes that inspect web data, evaluate
        evidence, and commit accepted judgments on-chain.
      </p>
      <div class="cta-cluster">
        <div class="button-row">
          {#if isWaitlisted}
            {@render waitlistBadge()}
          {:else}
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
          {/if}
        </div>
        <p class="cta-hint">A selected validator proposes an answer, others verify it, and appeals resolve disagreements before finality.</p>
      </div>
    </div>

    <RoleLandingVideo
      variant="validator"
      eyebrow="Validator Preview"
      title="Adjudication in motion"
      description="Watch the flow for reasoning, verification, and finality before joining the validator path."
    />
  </section>

  <section class="comparison-section" aria-labelledby="validator-comparison-title">
    <div class="section-header centered">
      <h2 id="validator-comparison-title">From Passive Infrastructure to Active Judgment</h2>
    </div>
    <div class="comparison-grid">
      {#each comparisonCards as card, index}
        {#if index === 1}
          <div class="versus-badge" aria-hidden="true"><span>vs.</span></div>
        {/if}
        <article class="feature-card">
          <div class="feature-heading">
            <span class="feature-icon" aria-hidden="true">
              {#if card.icon === 'genlayer'}
                <CategoryIcon category="genlayer" mode="hexagon" size={36} />
              {:else}
                <svg viewBox="0 0 24 24">
                  <rect x="4" y="4" width="6" height="6" rx="1.5"></rect>
                  <rect x="14" y="4" width="6" height="6" rx="1.5"></rect>
                  <rect x="9" y="14" width="6" height="6" rx="1.5"></rect>
                  <path d="M10 7h4M12 10v4"></path>
                </svg>
              {/if}
            </span>
            <h3>{card.title}</h3>
          </div>
          <strong>{card.value}</strong>
          <p>{card.body}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="statement-section" aria-label="Validator statement">
    <h2>
      Validators don&apos;t just secure GenLayer.<br />
      <span>They adjudicate it.</span>
    </h2>
  </section>

  <section class="earn-banner" id="validator-economics" aria-labelledby="validator-economics-title">
    <div class="earn-copy">
      <h2 id="validator-economics-title">Higher Fees Per Transaction Than Anywhere Else</h2>
    </div>
    <div class="economics-list">
      {#each economics as item}
        <div>
          <span aria-hidden="true"></span>
          <p>{item}</p>
        </div>
      {/each}
    </div>
  </section>

  <section class="stack-section" aria-labelledby="validator-demand-title">
    <h2 id="validator-demand-title">On-chain activity and operator readiness.</h2>
    <div class="stack-grid">
      {#each proofStats as stat}
        <article class="stack-card">
          <p class="stack-value">
            <span>{stat.value}</span>{#if stat.suffix}<em>{stat.suffix}</em>{/if}
          </p>
          <p class="stack-label">{stat.label}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="workflow-section" aria-labelledby="validator-workflow-title">
    <div class="section-header centered">
      <h2 id="validator-workflow-title">How It Works</h2>
      <p>
        A proposer produces a judgment with an LLM-backed validator. Other
        validators verify independently, and appeals settle disagreements before
        the result is finalized on-chain.
      </p>
    </div>
    <div class="project-chip-row" aria-label="Validator workflow">
      {#each workflow as step}
        <span>{step}</span>
      {/each}
    </div>
  </section>

  <section class="final-cta" aria-labelledby="validator-final-title">
    <h2 id="validator-final-title">Run the node that reasons.</h2>
    <p>Join the validator path and prepare to resolve the agentic economy.</p>
    {#if isWaitlisted}
      {@render waitlistBadge()}
    {:else}
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
    {/if}
  </section>
</div>

<style>
  .role-landing {
    --role-accent: #3a7ce7;
    --role-accent-rgb: 58, 124, 231;
    --role-border: #e8eef8;
    --role-muted: #6f7b90;
    --role-black: #131214;
    --role-gradient: linear-gradient(168deg, #6fa3f8 15%, #4f76f6 50%, #3b5dd6 85%);
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
  .earn-copy {
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
    color: #667085;
    font-size: 14px;
    line-height: 20px;
    margin: 0;
    max-width: 430px;
  }

  .landing-button,
  .waitlist-status {
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

  .landing-button span,
  .waitlist-status {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .landing-button img,
  .waitlist-status svg {
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

  .waitlist-status {
    background: rgba(var(--role-accent-rgb), 0.1);
    border: 1px solid rgba(var(--role-accent-rgb), 0.24);
    color: var(--role-accent);
  }

  .comparison-section,
  .workflow-section,
  .stack-section,
  .final-cta {
    margin-inline: auto;
    max-width: var(--landing-max);
    width: 100%;
  }

  .comparison-section,
  .workflow-section,
  .stack-section {
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

  .section-header h2,
  .stack-section > h2 {
    font-size: 40px;
    letter-spacing: -1.2px;
    line-height: 48px;
    max-width: 560px;
  }

  .section-header p {
    color: var(--role-muted);
    font-size: 16px;
    line-height: 24px;
    margin: 0;
    max-width: 590px;
  }

  .section-header.centered h2,
  .section-header.centered p {
    max-width: 760px;
  }

  .comparison-grid {
    align-items: stretch;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 88px minmax(0, 1fr);
    width: 100%;
  }

  .versus-badge {
    align-items: center;
    align-self: stretch;
    display: flex;
    justify-content: center;
    position: relative;
    z-index: 1;
  }

  .versus-badge::before {
    background: linear-gradient(180deg, transparent, rgba(var(--role-accent-rgb), 0.3), transparent);
    bottom: 22px;
    content: '';
    left: 50%;
    position: absolute;
    top: 22px;
    transform: translateX(-50%);
    width: 1px;
  }

  .versus-badge span {
    align-items: center;
    background: #fff;
    border: 1px solid rgba(var(--role-accent-rgb), 0.28);
    border-radius: 999px;
    box-shadow: 0 10px 24px rgba(var(--role-accent-rgb), 0.12);
    color: var(--role-accent);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    height: 42px;
    justify-content: center;
    min-width: 52px;
    padding: 0 14px;
    position: relative;
    text-transform: uppercase;
  }

  .feature-card {
    align-items: center;
    border: 1px solid var(--role-border);
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 18px;
    text-align: center;
  }

  .feature-heading {
    align-items: center;
    display: flex;
    gap: 12px;
    justify-content: center;
  }

  .feature-icon {
    align-items: center;
    color: var(--role-accent);
    display: inline-flex;
    height: 36px;
    justify-content: center;
    width: 36px;
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

  .feature-card strong {
    color: var(--role-accent);
    font-family: var(--font-display);
    font-size: 44px;
    font-weight: 500;
    line-height: 1;
  }

  .feature-card p {
    color: #667085;
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

  .earn-banner {
    align-items: center;
    align-self: center;
    background:
      radial-gradient(circle at 94% 46%, rgba(var(--role-accent-rgb), 0.82) 0, rgba(var(--role-accent-rgb), 0.42) 24%, rgba(var(--role-accent-rgb), 0.12) 45%, transparent 60%),
      linear-gradient(90deg, #111827 0%, #121820 60%, #193967 100%);
    border-radius: 8px;
    color: #fff;
    display: flex;
    gap: 40px;
    justify-content: space-between;
    max-width: 1028px;
    overflow: hidden;
    padding: 48px;
    position: relative;
    width: min(100%, 1028px);
  }

  .earn-copy {
    max-width: 560px;
  }

  .earn-copy h2 {
    color: #fff;
    font-size: 40px;
    letter-spacing: -1.2px;
    line-height: 48px;
  }

  .earn-copy p {
    color: rgba(255, 255, 255, 0.72);
    font-size: 16px;
    line-height: 24px;
    margin: 0;
  }

  .economics-list {
    display: flex;
    flex: 0 1 360px;
    flex-direction: column;
    gap: 12px;
  }

  .economics-list div {
    align-items: flex-start;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    display: flex;
    gap: 10px;
    padding: 12px;
  }

  .economics-list span {
    background: var(--role-gradient);
    border-radius: 999px;
    flex: 0 0 auto;
    height: 10px;
    margin-top: 6px;
    width: 10px;
  }

  .economics-list p {
    color: #fff;
    font-size: 14px;
    line-height: 20px;
    margin: 0;
  }

  .stack-section {
    align-items: center;
  }

  .stack-section > h2 {
    max-width: 780px;
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
    font-size: 60px;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    letter-spacing: -1.8px;
    line-height: 64px;
    margin: 0;
  }

  .stack-value em {
    color: var(--role-accent);
    font-style: normal;
    margin-left: 2px;
  }

  .stack-label {
    color: #5e6878;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.26px;
    line-height: 18px;
    margin: 0;
    text-transform: uppercase;
  }

  .project-chip-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    width: 100%;
  }

  .project-chip-row span {
    border: 1px solid var(--role-border);
    border-radius: 32px;
    color: #000;
    font-family: var(--font-mono);
    font-size: 15px;
    line-height: 24px;
    padding: 14px 20px;
    white-space: nowrap;
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

  @media (max-width: 1100px) {
    .stack-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 900px) {
    .role-hero,
    .comparison-grid {
      grid-template-columns: 1fr;
    }

    .versus-badge {
      height: 58px;
      width: 100%;
    }

    .versus-badge::before {
      background: linear-gradient(90deg, transparent, rgba(var(--role-accent-rgb), 0.3), transparent);
      bottom: auto;
      height: 1px;
      left: 12%;
      right: 12%;
      top: 50%;
      transform: translateY(-50%);
      width: auto;
    }

    .role-hero {
      padding: 32px 12px 64px;
    }

    .hero-copy,
    .section-header,
    .earn-banner {
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

    .earn-banner {
      padding: 32px 20px;
    }

    .project-chip-row span {
      max-width: 100%;
      overflow-wrap: anywhere;
      text-align: center;
      white-space: normal;
    }

    .stack-grid {
      grid-template-columns: 1fr;
    }

    .stack-value {
      font-size: 52px;
      line-height: 56px;
    }
  }
</style>
