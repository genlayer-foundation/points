<script>
  let { state: roleState = 'unauthenticated', starting = false, onStart = () => {} } = $props();

  const isWaitlisted = $derived(roleState === 'waitlisted');
  const primaryLabel = $derived(starting ? 'Starting...' : 'Run a Node');
  const finalLabel = $derived(starting ? 'Starting...' : 'Run a Node');

  const comparisonCards = [
    {
      title: 'Traditional validator',
      value: 'Attest',
      body: 'Passive infrastructure with capped single-digit yields.',
    },
    {
      title: 'GenLayer validator',
      value: 'Reason',
      body: 'Run an AI model, participate in Optimistic Democracy, and earn per decision.',
    },
  ];

  const economics = [
    'Paid per decision, with each decision composed of 15+ transactions.',
    'With gas enabled, GenLayer activity would already rank Top-15 among all chains by daily fees.',
    'Fee potential scales with reasoning demand, not passive uptime alone.',
  ];

  const proofStats = [
    { value: '3.8', suffix: 'K', label: 'Decisions per day' },
    { value: '4,097', label: 'Peak-day decisions' },
    { value: '150', label: 'Professional validators live' },
    { value: 'Q4', suffix: '2026', label: 'Mainnet target' },
  ];

  const workflow = [
    'Verifiable random selection',
    'One validator proposes',
    'Others verify',
    'Appeals resolve disagreement',
  ];
</script>

<svelte:head>
  <title>Validators | GenLayer Portal</title>
</svelte:head>

<div class="role-landing validator-landing">
  <section class="role-hero" aria-labelledby="validator-landing-title">
    <div class="hero-copy">
      <p class="role-eyebrow">Validators</p>
      <h1 id="validator-landing-title">Don&apos;t Validate Blocks.<br />Adjudicate the Agentic Economy.</h1>
      <p>
        GenLayer validators don&apos;t rubber-stamp transactions - they reason,
        judge, and resolve real disputes. And they earn more for it.
      </p>
      <div class="cta-cluster">
        <div class="button-row">
          {#if isWaitlisted}
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
        <p class="cta-hint">Reason through real outcomes, participate in consensus, and earn for judgment.</p>
      </div>
    </div>

    <div class="hero-visual" aria-hidden="true">
      <div class="visual-track">
        <div class="visual-pill muted">Block attestation</div>
        <div class="visual-arrow">-></div>
        <div class="visual-pill active">AI judgment</div>
      </div>
      <div class="decision-card">
        <span>Decision flow</span>
        <strong>Propose -> Verify -> Appeal -> Finality</strong>
      </div>
      <div class="visual-stat">
        <strong>15+</strong>
        <span>transactions per decision</span>
      </div>
    </div>
  </section>

  <section class="comparison-section" aria-labelledby="validator-comparison-title">
    <div class="section-header">
      <h2 id="validator-comparison-title">From Passive Infrastructure to Active Judgment</h2>
      <p>
        On GenLayer, each validator runs an AI model and participates in Optimistic Democracy -
        proposing, verifying, and appealing real decisions.
      </p>
    </div>
    <div class="comparison-grid">
      {#each comparisonCards as card}
        <article class="feature-card">
          <div class="feature-heading">
            <span class="feature-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 3v18M5 6h14M7 6l-4 7h8L7 6ZM17 6l-4 7h8l-4-7ZM8 21h8"></path></svg>
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
      <p>
        With gas enabled, GenLayer&apos;s current activity would already rank it Top-15
        among all chains by daily fees - ahead of Avalanche, Cardano, and Near.
      </p>
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
    <h2 id="validator-demand-title">Thousands of decisions. Every day. Growing.</h2>
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
    <div class="section-header">
      <h2 id="validator-workflow-title">How It Works</h2>
      <p>
        Verifiable random selection chooses who proposes. Other validators verify.
        Disagreement escalates through appeals until finality - in minutes.
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
    {:else}
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
  .earn-copy {
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

  .hero-visual {
    align-content: center;
    aspect-ratio: 16 / 9;
    background:
      radial-gradient(circle at 80% 20%, rgba(var(--role-accent-rgb), 0.24), transparent 32%),
      linear-gradient(135deg, #f8fbff 0%, #edf4ff 100%);
    border: 1px solid rgba(var(--role-accent-rgb), 0.18);
    border-radius: 8px;
    display: grid;
    gap: 18px;
    padding: 28px;
    width: 100%;
  }

  .visual-track,
  .decision-card,
  .visual-stat {
    background: rgba(255, 255, 255, 0.84);
    border: 1px solid rgba(var(--role-accent-rgb), 0.16);
    border-radius: 8px;
    box-shadow: 0 14px 30px rgba(50, 87, 142, 0.12);
  }

  .visual-track {
    align-items: center;
    display: flex;
    gap: 10px;
    justify-content: center;
    padding: 12px;
  }

  .visual-pill {
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 12px;
    text-transform: uppercase;
  }

  .visual-pill.muted {
    background: #f1f4f9;
    color: #667085;
  }

  .visual-pill.active {
    background: var(--role-gradient);
    color: #fff;
  }

  .visual-arrow {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-weight: 700;
  }

  .decision-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 18px;
  }

  .decision-card span,
  .visual-stat span {
    color: #6b7280;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .decision-card strong {
    color: #111827;
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 500;
    line-height: 30px;
  }

  .visual-stat {
    align-items: center;
    display: flex;
    gap: 14px;
    justify-content: center;
    padding: 14px;
  }

  .visual-stat strong {
    color: var(--role-accent);
    font-family: var(--font-display);
    font-size: 48px;
    font-weight: 500;
    line-height: 1;
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

  .comparison-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
    grid-template-columns: repeat(4, minmax(0, 1fr));
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

    .stack-grid {
      grid-template-columns: 1fr;
    }

    .stack-value {
      font-size: 52px;
      line-height: 56px;
    }
  }
</style>
