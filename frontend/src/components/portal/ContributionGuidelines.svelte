<script>
  import { isProjectContributionType } from '../../lib/contributionGuidelines.js';

  let {
    contributionType = null,
    mobile = false,
    detail = false,
    onRoute = null,
    milestoneEligible = null,
  } = $props();

  const WEEK_WINDOW = 'Monday 00:00 to Sunday 23:59 UTC';

  let panel = $derived.by(() => {
    if (isProjectContributionType(contributionType)) return 'projects';
    if (contributionType?.slug === 'create-intelligent-contracts') return 'contract';
    if (contributionType?.slug === 'milestones') return 'milestone';
    return 'general';
  });

  let weeklyLimit = $derived.by(() => {
    const configuredLimit = Number(
      contributionType?.max_submissions_per_user_per_week,
    );
    if (Number.isFinite(configuredLimit) && configuredLimit > 0) {
      return configuredLimit;
    }
    return panel === 'projects' ? 2 : null;
  });
  let slotsRemaining = $derived.by(() => {
    if (weeklyLimit === null) return null;
    const remaining = Number(contributionType?.user_weekly_submissions_remaining);
    return Number.isFinite(remaining)
      ? Math.min(Math.max(remaining, 0), weeklyLimit)
      : null;
  });
  let slotsUsed = $derived(
    slotsRemaining === null || weeklyLimit === null
      ? null
      : weeklyLimit - slotsRemaining,
  );
  let slotNoun = $derived(panel === 'projects' ? 'Project slots' : 'slots');
  let submissionNoun = $derived(
    panel === 'projects' ? 'Project submissions' : 'submissions',
  );

  let title = $derived.by(() => {
    if (panel === 'projects') return 'Before you submit a Project';
    if (panel === 'contract') return 'Before you submit an Intelligent Contract';
    if (panel === 'milestone') return 'Before you submit a Milestone';
    return 'Before you submit';
  });
  let subtitle = $derived.by(() => {
    if (panel === 'projects') return 'Check the quality bar. Reviews are strict.';
    if (panel === 'contract') {
      return 'This category is strict. Most submissions are rejected.';
    }
    if (panel === 'milestone') {
      return 'Milestones reward substantial progress on highlighted projects.';
    }
    return 'Weekly limits, categories, and what reviewers look for.';
  });

  const PROJECT_QUALITY_BAR = [
    ['Solves a real trust problem.', 'Not just a better LLM response.'],
    ['Uses live or authoritative data', 'when outcomes depend on real-world facts.'],
    [
      'Complete source code and accurate docs.',
      'Submission notes must explain what it does, the problem it solves, and how to use it.',
    ],
    ['Frontend genuinely calls the contract', 'and handles the full transaction lifecycle.'],
    ['Meaningfully different from boilerplate,', 'with a credible path to continued use.'],
  ];
  const CONTRACT_QUALITY_BAR = [
    ['Reusable by other builders.', 'Primitives, patterns, and building blocks others can integrate.'],
    ['Not extracted from a submitted project.', 'The same work does not count twice.'],
    ['Not a learning exercise.', 'Contracts written to explore how consensus works are not contributions.'],
    ['Meaningfully different', 'from contracts that already exist in the ecosystem.'],
    ['Documented for reuse.', 'Clear docs on what it does and how to integrate it.'],
  ];
  const MILESTONE_QUALITY_BAR = [
    ['Substantial improvement.', 'New functionality, real integrations, or meaningful scope. Not cosmetic updates.'],
    ['Not repackaging.', 'Renaming, restyling, or reorganizing existing work does not qualify.'],
    ['Builds on the accepted version.', 'The delta from the last accepted state is what gets evaluated.'],
    ['Documented delta.', 'Submission notes must state exactly what changed and why it matters.'],
    ['Moves the project toward real usage.', 'Adoption, users, or external interest strengthen the case.'],
  ];
  let qualityBar = $derived(
    panel === 'projects'
      ? PROJECT_QUALITY_BAR
      : panel === 'contract'
        ? CONTRACT_QUALITY_BAR
        : panel === 'milestone'
          ? MILESTONE_QUALITY_BAR
          : [],
  );
  let routerItems = $derived(
    panel === 'contract'
      ? [
          ['A full project with a frontend or product around it', 'Project', 'projects'],
          ['An improvement to an accepted project', 'Milestone', 'milestones'],
        ]
      : [
          ['A standalone reusable contract', 'Intelligent Contract', 'create-intelligent-contracts'],
          ['An improvement to an accepted project', 'Milestone', 'milestones'],
        ],
  );

  let mobileSummaryLine = $derived.by(() => {
    if (panel === 'milestone' && milestoneEligible === false) {
      return 'A highlighted project is required';
    }
    if (slotsUsed !== null) {
      return `${slotsUsed} of ${weeklyLimit} ${slotNoun} used this week`;
    }
    if (weeklyLimit !== null) {
      return `${weeklyLimit} per week, Monday to Sunday UTC`;
    }
    if (panel === 'contract') {
      return 'Strict category · lightweight contracts are rejected';
    }
    return `Weekly limits run ${WEEK_WINDOW}`;
  });
</script>

{#snippet checkIcon()}
  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
    <path d="m5.5 10.2 2.7 2.7 6.3-6.3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
{/snippet}

{#snippet slotCounter()}
  {#if weeklyLimit !== null}
    <div class="slot-counter" class:is-exhausted={slotsRemaining === 0}>
      {#if slotsUsed !== null}
        <p class="slot-copy">
          {#if slotsRemaining === 0}
            <strong>You have used your {weeklyLimit} {slotNoun} for this week.</strong>
          {:else}
            <strong>You have used {slotsUsed} of {weeklyLimit} {slotNoun} this week</strong>
          {/if}
          <span>Resets Monday 00:00 UTC</span>
        </p>
        <div class="slot-segments" role="img" aria-label="{slotsUsed} of {weeklyLimit} weekly slots used">
          {#each Array(weeklyLimit) as _, i}
            <span class="segment" class:is-used={i < slotsUsed}></span>
          {/each}
        </div>
      {:else}
        <p class="slot-copy">
          <strong>{weeklyLimit} new {submissionNoun} per user, each week</strong>
          <span>{WEEK_WINDOW}</span>
        </p>
      {/if}
    </div>
  {/if}
{/snippet}

{#snippet categoryRouter()}
  <div class="router">
    <div class="router-rows">
      {#each routerItems as item}
        <div>
          <span>{item[0]}</span>
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8h10m-3-3 3 3-3 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></svg>
          {#if onRoute}
            <button type="button" onclick={() => onRoute(item[2])}>{item[1]}</button>
          {:else}
            <strong>{item[1]}</strong>
          {/if}
        </div>
      {/each}
    </div>
    {#if panel === 'projects'}
      <p class="router-note">
        Milestones are open only for highlighted projects. Cosmetic changes do not qualify.
      </p>
    {/if}
  </div>
{/snippet}

{#snippet qualityList()}
  <div class="quality">
    <h3>Quality bar</h3>
    <ul>
      {#each qualityBar as item}
        <li>
          <span class="check">{@render checkIcon()}</span>
          <span><strong>{item[0]}</strong> {item[1]}</span>
        </li>
      {/each}
    </ul>
    {#if panel === 'contract'}
      <p class="litmus-note">If it would not be useful to someone else building on GenLayer, it is not ready to be submitted.</p>
    {/if}
  </div>
{/snippet}

{#snippet contractWarning()}
  <div class="contract-warning" role="note">
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 2.8 18 17H2L10 2.8Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
      <path d="M10 7.2v4.4m0 2.4v.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    </svg>
    <p>Lightweight contracts are rejected. This category is not a shortcut to points. A contract must provide real value to the ecosystem to be rewarded.</p>
  </div>
{/snippet}

{#snippet afterSubmit()}
  <details class="after-submit">
    <summary>
      <span>After you submit: reviews, appeals, and slots</span>
      <svg class="accordion-chevron" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="m6 8 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </summary>
    <div class="after-submit-body">
      <p><strong>More information.</strong> We see a path to acceptance and need details. Update the existing submission. Does not use a slot.</p>
      <p><strong>Rejection.</strong> The use case or implementation falls short. Fixes or new evidence require a new submission, which uses a slot.</p>
      <p><strong>Appeal.</strong> Challenges the original decision only, with the work as it was submitted. Does not use a slot.</p>
    </div>
  </details>
{/snippet}

{#snippet fullGuidelinesLink()}
  {#if contributionType?.id && !detail}
    <a class="full-guidelines-link" href={`/contribution-type/${contributionType.id}`}>
      <span>Read full guidelines</span>
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 8h10m-3-3 3 3-3 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </a>
  {/if}
{/snippet}

{#snippet panelBody()}
  {#key panel}
    <div class="panel-body">
      {#if panel === 'milestone' && milestoneEligible === false}
        <div class="milestone-empty">
          <p>Milestones are open only for highlighted projects. Highlighted projects are selected by the review team based on use case and real usage potential. Keep building your project through new submissions to get there.</p>
        </div>
      {:else if panel === 'projects'}
        {@render slotCounter()}
        {@render categoryRouter()}
        {@render qualityList()}
        <p class="go-further"><strong>Go further:</strong> live demos, videos, and public posts earn extra points and speed up review.</p>
      {:else if panel === 'contract'}
        {@render contractWarning()}
        {@render slotCounter()}
        {@render categoryRouter()}
        {@render qualityList()}
      {:else if panel === 'milestone'}
        {@render slotCounter()}
        {@render qualityList()}
      {:else if weeklyLimit !== null}
        {@render slotCounter()}
      {:else}
        <p class="week-chip">
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <rect x="3" y="4.5" width="14" height="12.5" rx="2.5" stroke="currentColor" stroke-width="1.4" />
            <path d="M6.5 2.8v3.4m7-3.4v3.4M3 8h14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          </svg>
          Weekly limits run {WEEK_WINDOW}
        </p>
      {/if}
      {@render afterSubmit()}
      {@render fullGuidelinesLink()}
    </div>
  {/key}
{/snippet}

{#snippet headerIcon()}
  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 5.5h12v10H4zM7 5.5V3.8h6v1.7" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" /><path d="M4 9h12" stroke="currentColor" stroke-width="1.5" /></svg>
{/snippet}

{#if mobile}
  <details class="guidelines-disclosure">
    <summary>
      <span class="summary-icon" aria-hidden="true">{@render headerIcon()}</span>
      <span class="summary-copy">
        <strong>Before you submit</strong>
        <span>{mobileSummaryLine}</span>
      </span>
      <svg class="summary-chevron" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="m6 8 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </summary>
    <div class="disclosure-body">
      {#if panel !== 'general'}
        <p class="disclosure-subtitle">{subtitle}</p>
      {/if}
      {@render panelBody()}
    </div>
  </details>
{:else}
  <section class="guidelines-card" class:is-detail={detail} aria-label={title}>
    <header class="guidelines-header">
      <span class="header-icon" aria-hidden="true">{@render headerIcon()}</span>
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </header>
    {@render panelBody()}
  </section>
{/if}

<style>
  .guidelines-card,
  .guidelines-disclosure {
    -webkit-font-smoothing: antialiased;
    background: white;
    border: 1px solid #f5f5f5;
    box-shadow: 0px 4px 20px 0px rgba(0, 0, 0, 0.02);
    color: #171719;
  }

  .guidelines-card {
    border-radius: 16px;
    padding: 20px;
  }

  .guidelines-header {
    align-items: flex-start;
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
  }

  .header-icon,
  .summary-icon {
    align-items: center;
    background: #f5f6f8;
    border-radius: 9px;
    color: #475467;
    display: inline-flex;
    flex: 0 0 auto;
    height: 32px;
    justify-content: center;
    width: 32px;
  }

  .header-icon svg,
  .summary-icon svg {
    height: 17px;
    width: 17px;
  }

  .guidelines-header h2 {
    color: #171719;
    font-family: 'Switzer', sans-serif;
    font-size: 15px;
    font-weight: 650;
    line-height: 20px;
    margin: 0;
    text-wrap: balance;
  }

  .guidelines-header p {
    color: #667085;
    font-family: 'Switzer', sans-serif;
    font-size: 12px;
    line-height: 16px;
    margin: 2px 0 0;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-width: 0;
  }

  .slot-counter {
    background: #fff5e8;
    border: 1px solid rgba(238, 133, 33, 0.22);
    border-radius: 10px;
    padding: 11px 12px;
  }

  .slot-counter.is-exhausted {
    background: #fff7ed;
    border-color: rgba(234, 88, 12, 0.35);
  }

  .contract-warning {
    align-items: flex-start;
    background: #fff4e8;
    border: 1px solid rgba(220, 92, 20, 0.28);
    border-radius: 10px;
    color: #8a3d0b;
    display: flex;
    gap: 9px;
    padding: 11px 12px;
  }

  .contract-warning svg {
    flex: 0 0 auto;
    height: 17px;
    margin-top: 1px;
    width: 17px;
  }

  .contract-warning p {
    color: #6f310b;
    font-family: 'Switzer', sans-serif;
    font-size: 11.5px;
    font-weight: 580;
    line-height: 16px;
    margin: 0;
  }

  .slot-copy {
    display: flex;
    flex-direction: column;
    font-family: 'Switzer', sans-serif;
    margin: 0;
  }

  .slot-copy strong {
    color: #5e2d07;
    font-size: 12px;
    font-weight: 650;
    line-height: 16px;
  }

  .is-exhausted .slot-copy strong {
    color: #9a3412;
  }

  .slot-copy span {
    color: #9b5a22;
    font-size: 11px;
    line-height: 15px;
    margin-top: 2px;
  }

  .slot-segments {
    display: flex;
    gap: 4px;
    margin-top: 8px;
  }

  .segment {
    background: rgba(238, 133, 33, 0.22);
    border-radius: 999px;
    flex: 1 1 0;
    height: 4px;
  }

  .segment.is-used {
    background: #ee8521;
  }

  .router-rows {
    border: 1px solid #eceef2;
    border-radius: 10px;
    overflow: hidden;
  }

  .router-rows > div {
    align-items: center;
    display: grid;
    font-family: 'Switzer', sans-serif;
    font-size: 11px;
    gap: 7px;
    grid-template-columns: minmax(0, 1fr) 14px minmax(82px, auto);
    line-height: 15px;
    padding: 9px 10px;
  }

  .router-rows > div + div {
    border-top: 1px solid #eceef2;
  }

  .router-rows span {
    color: #667085;
  }

  .router-rows svg {
    color: #98a2b3;
    height: 14px;
    width: 14px;
  }

  .router-rows strong,
  .router-rows button {
    color: #171719;
    font-weight: 650;
    text-align: right;
  }

  .router-rows button {
    background: none;
    border: 0;
    cursor: pointer;
    font-family: inherit;
    font-size: inherit;
    justify-self: end;
    line-height: inherit;
    padding: 0;
    text-decoration-color: #d0d5dd;
    text-decoration-line: underline;
    text-underline-offset: 3px;
  }

  .router-rows button:hover {
    color: #b45309;
    text-decoration-color: currentColor;
  }

  .router-rows button:focus-visible {
    border-radius: 4px;
    outline: 2px solid #ee8521;
    outline-offset: 2px;
  }

  .router-note {
    color: #98a2b3;
    font-family: 'Switzer', sans-serif;
    font-size: 11px;
    line-height: 15px;
    margin: 6px 2px 0;
  }

  .quality h3 {
    color: #667085;
    font-family: 'Geist', sans-serif;
    font-size: 10.5px;
    font-weight: 650;
    letter-spacing: 0.08em;
    line-height: 14px;
    margin: 0 0 8px;
    text-transform: uppercase;
  }

  .quality ul {
    display: flex;
    flex-direction: column;
    gap: 7px;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .quality li {
    align-items: flex-start;
    color: #667085;
    display: flex;
    font-family: 'Switzer', sans-serif;
    font-size: 12px;
    gap: 8px;
    line-height: 16px;
  }

  .quality li strong {
    color: #344054;
    font-weight: 650;
  }

  .check {
    align-items: center;
    background: #f2f4f7;
    border-radius: 50%;
    color: #475467;
    display: inline-flex;
    flex: 0 0 auto;
    height: 16px;
    justify-content: center;
    width: 16px;
  }

  .check svg {
    height: 12px;
    width: 12px;
  }

  .litmus-note {
    border-left: 2px solid #d0d5dd;
    color: #7b8190;
    font-family: 'Switzer', sans-serif;
    font-size: 11px;
    line-height: 15px;
    margin: 9px 2px 0;
    padding-left: 9px;
  }

  .go-further {
    background: #fafafa;
    border-radius: 8px;
    color: #667085;
    font-family: 'Switzer', sans-serif;
    font-size: 11px;
    line-height: 15px;
    margin: 0;
    padding: 8px 10px;
  }

  .go-further strong {
    color: #344054;
    font-weight: 650;
  }

  .milestone-empty {
    background: #fff7ed;
    border: 1px solid rgba(234, 88, 12, 0.3);
    border-radius: 10px;
    padding: 12px;
  }

  .milestone-empty p {
    color: #7c4a12;
    font-family: 'Switzer', sans-serif;
    font-size: 12px;
    line-height: 17px;
    margin: 0;
  }

  .week-chip {
    align-items: center;
    background: #f5f6f8;
    border-radius: 999px;
    color: #475467;
    display: inline-flex;
    font-family: 'Switzer', sans-serif;
    font-size: 11.5px;
    font-weight: 500;
    gap: 7px;
    line-height: 15px;
    margin: 0;
    padding: 7px 12px;
    width: fit-content;
  }

  .week-chip svg {
    flex: 0 0 auto;
    height: 15px;
    width: 15px;
  }

  .after-submit {
    border-top: 1px solid #eceef2;
    padding-top: 12px;
  }

  .after-submit summary {
    align-items: center;
    color: #475467;
    cursor: pointer;
    display: flex;
    font-family: 'Switzer', sans-serif;
    font-size: 12px;
    font-weight: 650;
    gap: 8px;
    justify-content: space-between;
    line-height: 16px;
    list-style: none;
  }

  .after-submit summary::-webkit-details-marker {
    display: none;
  }

  .after-submit summary:focus-visible {
    border-radius: 6px;
    outline: 2px solid #ee8521;
    outline-offset: 2px;
  }

  .accordion-chevron {
    color: #98a2b3;
    flex: 0 0 auto;
    height: 16px;
    transition: transform 160ms ease;
    width: 16px;
  }

  .after-submit[open] .accordion-chevron {
    transform: rotate(180deg);
  }

  .after-submit-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-top: 10px;
  }

  .after-submit-body p {
    color: #667085;
    font-family: 'Switzer', sans-serif;
    font-size: 11px;
    line-height: 16px;
    margin: 0;
  }

  .after-submit-body strong {
    color: #344054;
    font-weight: 650;
  }

  .full-guidelines-link {
    align-items: center;
    color: #475467;
    display: inline-flex;
    font-family: 'Switzer', sans-serif;
    font-size: 11.5px;
    font-weight: 650;
    gap: 5px;
    line-height: 16px;
    text-decoration-color: #d0d5dd;
    text-decoration-line: underline;
    text-underline-offset: 3px;
    width: fit-content;
  }

  .full-guidelines-link svg {
    height: 14px;
    transition: transform 160ms ease;
    width: 14px;
  }

  .full-guidelines-link:hover {
    color: #b45309;
    text-decoration-color: currentColor;
  }

  .full-guidelines-link:hover svg {
    transform: translateX(2px);
  }

  .full-guidelines-link:focus-visible {
    border-radius: 4px;
    outline: 2px solid #ee8521;
    outline-offset: 3px;
  }

  .guidelines-disclosure {
    border-radius: 12px;
    overflow: hidden;
    width: 100%;
  }

  .guidelines-disclosure summary {
    align-items: center;
    cursor: pointer;
    display: flex;
    gap: 10px;
    list-style: none;
    min-height: 58px;
    padding: 11px 13px;
    touch-action: manipulation;
  }

  .guidelines-disclosure summary::-webkit-details-marker {
    display: none;
  }

  .guidelines-disclosure summary:focus-visible {
    outline: 2px solid #ee8521;
    outline-offset: -2px;
  }

  .summary-copy {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-width: 0;
  }

  .summary-copy strong {
    color: #171719;
    font-family: 'Switzer', sans-serif;
    font-size: 13px;
    font-weight: 650;
    line-height: 17px;
  }

  .summary-copy span {
    color: #7b8190;
    font-family: 'Switzer', sans-serif;
    font-size: 11px;
    line-height: 15px;
    margin-top: 1px;
  }

  .summary-chevron {
    color: #7b8190;
    flex: 0 0 auto;
    height: 20px;
    transition: transform 160ms ease;
    width: 20px;
  }

  .guidelines-disclosure[open] .summary-chevron {
    transform: rotate(180deg);
  }

  .disclosure-body {
    border-top: 1px solid #eff0f3;
    padding: 14px;
  }

  .disclosure-subtitle {
    color: #667085;
    font-family: 'Switzer', sans-serif;
    font-size: 12px;
    line-height: 16px;
    margin: 0 0 12px;
  }

  @media (min-width: 900px) {
    .guidelines-card.is-detail {
      padding: 26px;
    }

    .guidelines-card.is-detail .quality li,
    .guidelines-card.is-detail .router-rows > div {
      font-size: 13px;
      line-height: 18px;
    }

    .guidelines-card.is-detail .after-submit-body p,
    .guidelines-card.is-detail .contract-warning p,
    .guidelines-card.is-detail .litmus-note,
    .guidelines-card.is-detail .milestone-empty p,
    .guidelines-card.is-detail .router-note,
    .guidelines-card.is-detail .go-further {
      font-size: 12px;
      line-height: 17px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .summary-chevron,
    .accordion-chevron,
    .full-guidelines-link svg {
      transition: none;
    }
  }
</style>
