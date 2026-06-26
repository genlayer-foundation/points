<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';
  import { authState } from '../lib/auth';
  import { getCurrentUser, journeyAPI } from '../lib/api';
  import { userStore } from '../lib/userStore.js';
  import { showError } from '../lib/toastStore.js';
  import JourneyNotice from '../components/funnel/journeys/JourneyNotice.svelte';
  import JourneyHeroCard from '../components/funnel/journeys/JourneyHeroCard.svelte';
  import JourneyStepRow from '../components/funnel/journeys/JourneyStepRow.svelte';

  const APPLICATION_FORM_URL = 'https://forms.gle/hdH5ssuQPAT9i6hg9';
  const DISCORD_URL = 'https://discord.gg/genlayerlabs';

  let currentUser = $state(null);
  let hasFilledForm = $state(false);
  let isJoiningWaitlist = $state(false);
  let error = $state('');
  let loading = $state(true);

  let isAuthenticated = $derived($authState.isAuthenticated);
  let noticeMessage = $derived(
    error || (
      hasFilledForm
        ? 'Application checked. Enter the waitlist when you are ready.'
        : 'Complete the validator application, then check it off in step one.'
    )
  );

  const graduatedUnlocks = [
    {
      title: 'Decisions',
      body: 'Get assigned real decisions and judge them as they come in.',
      label: 'Earn a fee per decision',
    },
    {
      title: 'Leaderboard',
      body: 'Climb the validator ranks by accuracy and uptime.',
      label: 'Compete for top validator',
    },
    {
      title: 'Appeals',
      body: 'Take part in appeals and Optimistic Democracy governance.',
      label: 'Shape the protocol',
    },
  ];

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    try {
      if (isAuthenticated) {
        currentUser = await getCurrentUser();
        if (currentUser?.validator || currentUser?.has_validator_waitlist) {
          replace('/validators');
          return;
        }
      }
    } catch (err) {
      // Keep the pre-join flow visible; submit will surface any auth/API error.
    } finally {
      loading = false;
    }
  }

  function triggerSignIn() {
    document.querySelector('[data-auth-button]')?.click();
  }

  async function handleJoinWaitlist() {
    if (!hasFilledForm || isJoiningWaitlist) {
      return;
    }

    if (!isAuthenticated) {
      triggerSignIn();
      return;
    }

    isJoiningWaitlist = true;
    error = '';

    try {
      await journeyAPI.startValidatorJourney();
    } catch (err) {
      error = err.response?.data?.error || 'Failed to join waitlist';
      showError(error);
      isJoiningWaitlist = false;
      return;
    }
    // Joined server-side. The user refresh and success-banner write are both
    // best-effort and must not block (or undo) the success redirect.
    userStore.loadUser?.()?.catch(() => {});
    try {
      sessionStorage.setItem('journeySuccess', 'Successfully joined Validator Waitlist!');
    } catch {
      // Storing the success banner is best-effort; the join already succeeded.
    }
    replace('/validators');
  }
</script>

<svelte:head>
  <title>Validator Waitlist | GenLayer Portal</title>
</svelte:head>

<div class="journey-page validator-journey">
  <JourneyNotice
    message={noticeMessage}
    tone={error ? 'error' : 'default'}
  />

  <JourneyHeroCard
    role="validator"
    iconHex="/assets/icons/hexagon-validator-light.svg"
    iconGlyph="/assets/icons/folder-shield-line-blue.svg"
    contributionIconHex="/assets/icons/hexagon-validator.svg"
    contributionIconGlyph="/assets/icons/shield-white.svg"
    heroContribution="icon"
    showProgress={false}
    eyebrow="Your validator waitlist"
    titleRest="Enter the Validator waitlist"
    description="Submit the application, confirm it in step one, and enter the waitlist for future GenLayer validator graduation."
    primaryLabel={isJoiningWaitlist ? 'Entering...' : 'Enter the waitlist'}
    primaryDisabled={loading || isJoiningWaitlist || !hasFilledForm}
    primaryBusy={isJoiningWaitlist}
    helper={hasFilledForm ? 'Step one is complete. Click to enter the waitlist.' : 'The waitlist unlocks after you check off the application.'}
    onPrimary={handleJoinWaitlist}
  />

  <section class="steps-card" aria-label="Validator waitlist steps">
    {#if loading}
      <JourneyStepRow number={1} loading={true} />
      <JourneyStepRow number={2} loading={true} />
    {:else}
      <div class="step-block">
        <JourneyStepRow
          number={1}
          title="Complete validator application"
          contributionLabel={hasFilledForm ? '' : 'Up next'}
          detail={hasFilledForm ? 'application complete' : 'open the form, submit it, then check it off'}
          status={hasFilledForm ? 'done' : 'active'}
          actionLabel="Open Form"
          actionHref={APPLICATION_FORM_URL}
          actionExternal={true}
          actionTone={hasFilledForm ? 'secondary' : 'accent'}
        />

        <div class="step-check-panel">
          <label class="form-confirmation" for="formCompleted">
            <input
              type="checkbox"
              id="formCompleted"
              bind:checked={hasFilledForm}
            />
            <span>
              <strong>I completed the GenLayer Validator Application</strong>
              <small>Check this once the external form has been submitted.</small>
            </span>
          </label>
        </div>
      </div>

      <JourneyStepRow
        number={2}
        title="Wait for graduation"
        contributionLabel="Informational"
        detail="the team reviews applications and graduates validators in cohorts"
        status="locked"
      />
    {/if}
  </section>

  <section class="graduation-section" aria-labelledby="validator-graduation-title">
    <div class="section-label">
      <p id="validator-graduation-title">What unlocks once you're graduated</p>
      <span></span>
    </div>

    <div class="graduation-grid">
      {#each graduatedUnlocks as item}
        <article class="graduation-card">
          <span class="lock-badge">Locked</span>
          <div class="outline-hex" aria-hidden="true">
            <img src="/assets/icons/hexagon-light.svg" alt="" />
          </div>
          <h2>{item.title}</h2>
          <p>{item.body}</p>
          <a href={DISCORD_URL} target="_blank" rel="noopener noreferrer">{item.label}</a>
        </article>
      {/each}
    </div>

    <article class="contact-card">
      <div class="contact-icon" aria-hidden="true">
        <img src="/assets/icons/hexagon-validator-light.svg" alt="" />
        <img src="/assets/icons/folder-shield-line-blue.svg" alt="" />
      </div>

      <div class="contact-copy">
        <p class="role-eyebrow">While you wait</p>
        <h2>Want to know more about being a validator?</h2>
        <p>
          Reach out to <strong>@validator-lead</strong> on Discord to learn what we look for,
          ask about timing, or make your case for an earlier spot.
        </p>
      </div>

      <a class="landing-button landing-button-accent" href={DISCORD_URL} target="_blank" rel="noopener noreferrer">
        Contact the team
      </a>
    </article>
  </section>
</div>

<style>
  .journey-page {
    --role-accent: #387de8;
    --role-accent-hover: #2f6fd4;
    --journey-active-bg: #f0f6ff;
    --journey-black: #131214;
    --journey-border: #ededed;
    --journey-muted: #909090;
    --journey-hero-bg: linear-gradient(163deg, #fff 40%, #f1f7ff 96%);
    --journey-hero-border: #dceafe;
    --journey-hero-glow: rgba(56, 125, 232, 0.17);
    --journey-points-bg: #edf5ff;
    --journey-complete-gradient: linear-gradient(135deg, #5c9af1 0%, #387de8 100%);
    --journey-complete-shadow: rgba(56, 125, 232, 0.19);
    color: #000;
    display: flex;
    flex-direction: column;
    gap: 24px;
    margin: 0 auto;
    max-width: 940px;
    padding: 20px 12px 80px;
    width: 100%;
  }

  .journey-page :global(*) {
    letter-spacing: 0;
  }

  .steps-card {
    background: #fff;
    border: 1px solid var(--journey-border);
    border-radius: 14px;
    overflow: hidden;
    width: 100%;
  }

  .step-block {
    width: 100%;
  }

  .step-check-panel {
    background: linear-gradient(90deg, var(--journey-active-bg) 0%, #fff 82%);
    border-top: 1px solid #f0f0f0;
    padding: 14px 18px 18px 58px;
  }

  .form-confirmation {
    align-items: flex-start;
    background: #fff;
    border: 1px solid #dceafe;
    border-radius: 12px;
    color: var(--journey-black);
    cursor: pointer;
    display: flex;
    font-family: var(--font-body);
    gap: 11px;
    max-width: 520px;
    padding: 12px;
  }

  .form-confirmation input {
    accent-color: var(--role-accent);
    flex: 0 0 auto;
    height: 16px;
    margin: 2px 0 0;
    width: 16px;
  }

  .form-confirmation span {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .form-confirmation strong {
    color: var(--journey-black);
    font-size: 13.5px;
    font-weight: 600;
    line-height: 20px;
  }

  .form-confirmation small {
    color: #737373;
    font-size: 12.5px;
    line-height: 19px;
  }

  .graduation-section {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding-top: 4px;
  }

  .section-label {
    align-items: center;
    display: flex;
    gap: 12px;
    width: 100%;
  }

  .section-label p {
    color: #ababab;
    font-family: var(--font-mono);
    font-size: 11px;
    line-height: 17px;
    margin: 0;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .section-label span {
    background: #e6e6e6;
    flex: 1 1 auto;
    height: 1px;
  }

  .graduation-grid {
    display: grid;
    gap: 18px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .graduation-card {
    background: #fff;
    border: 1px solid var(--journey-border);
    border-radius: 16px;
    min-height: 236px;
    padding: 24px 26px 26px;
    position: relative;
  }

  .lock-badge {
    align-items: center;
    background: #fff;
    border: 1px solid #f0f0f0;
    border-radius: 6px;
    color: #b7b7b7;
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 10px;
    height: 20px;
    justify-content: center;
    line-height: 16px;
    min-width: 68px;
    position: absolute;
    right: 12px;
    text-transform: uppercase;
    top: 14px;
  }

  .outline-hex {
    height: 48px;
    margin-bottom: 18px;
    width: 48px;
  }

  .outline-hex img {
    height: 100%;
    opacity: 0.9;
    width: 100%;
  }

  .graduation-card h2,
  .contact-card h2 {
    color: var(--journey-black);
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 500;
    line-height: 28px;
    margin: 0;
  }

  .graduation-card p {
    color: #737373;
    font-family: var(--font-body);
    font-size: 15px;
    line-height: 24px;
    margin: 10px 0 0;
  }

  .graduation-card a {
    color: #5e7cf6;
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
    margin-top: 14px;
    text-decoration: none;
  }

  .graduation-card a:hover {
    color: var(--role-accent-hover);
  }

  .contact-card {
    align-items: center;
    background: #fff;
    border: 1px solid var(--journey-border);
    border-radius: 18px;
    display: grid;
    gap: 18px;
    grid-template-columns: 40px minmax(0, 1fr) auto;
    padding: 28px 30px;
  }

  .contact-icon {
    height: 40px;
    position: relative;
    width: 40px;
  }

  .contact-icon img:first-child {
    height: 100%;
    width: 100%;
  }

  .contact-icon img:last-child {
    height: 18px;
    left: 50%;
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 18px;
  }

  .contact-copy {
    min-width: 0;
  }

  .role-eyebrow {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-size: 11px;
    line-height: 17px;
    margin: 0 0 8px;
    text-transform: uppercase;
  }

  .contact-copy p:not(.role-eyebrow) {
    color: #3f3f3f;
    font-family: var(--font-body);
    font-size: 14.5px;
    line-height: 23px;
    margin: 8px 0 0;
    max-width: 620px;
  }

  .contact-copy strong {
    font-weight: 700;
  }

  .landing-button {
    align-items: center;
    border-radius: 20px;
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 600;
    height: 40px;
    justify-content: center;
    line-height: 20px;
    padding: 0 20px;
    text-decoration: none;
    transition: background-color 160ms ease, opacity 160ms ease;
    white-space: nowrap;
  }

  .landing-button-accent {
    background: var(--role-accent);
    color: #fff;
  }

  .landing-button-accent:hover {
    background: var(--role-accent-hover);
  }

  @media (max-width: 900px) {
    .graduation-grid {
      grid-template-columns: 1fr;
    }

    .contact-card {
      align-items: flex-start;
      grid-template-columns: 40px minmax(0, 1fr);
    }

    .contact-card .landing-button {
      grid-column: 2;
      justify-self: flex-start;
    }
  }

  @media (max-width: 640px) {
    .journey-page {
      gap: 20px;
      padding: 12px 0 56px;
    }

    .step-check-panel {
      padding: 14px;
    }

    .section-label {
      padding: 0 2px;
    }

    .section-label p {
      white-space: normal;
    }

    .graduation-card {
      min-height: 0;
      padding: 22px;
    }

    .contact-card {
      grid-template-columns: 1fr;
      padding: 22px;
    }

    .contact-card .landing-button {
      grid-column: 1;
      width: 100%;
    }
  }
</style>
