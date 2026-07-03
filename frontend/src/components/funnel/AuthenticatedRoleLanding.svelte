<script>
  import CategoryIcon from '../portal/CategoryIcon.svelte';

  let { category = 'community', state = 'none', starting = false, onStart = () => {} } = $props();

  const VALIDATOR_CONTACT_URL = 'https://discord.gg/genlayerlabs';

  const roleConfig = {
    builder: {
      accent: '#ee8521',
      accentRgb: '238, 133, 33',
      gradient: 'linear-gradient(168deg, #f8b93d 15%, #ee8d24 50%, #db6917 85%)',
      label: 'Builders',
      eyebrow: 'Builder journey',
      title: 'Build the first contracts that can think.',
      body: 'Start with the boilerplate, make your first contribution, and claim your early Builder role.',
      button: 'Become a Builder',
    },
    validator: {
      accent: '#3a7ce7',
      accentRgb: '58, 124, 231',
      gradient: 'linear-gradient(168deg, #6fa3f8 15%, #4f76f6 50%, #3b5dd6 85%)',
      label: 'Validators',
      eyebrow: 'Validator journey',
      title: 'Run a node that reasons.',
      body: 'Join the validator path, enter the waitlist, and prepare to adjudicate real Intelligent Contract decisions.',
      button: 'Join the Waitlist',
      waitlistBody: 'Your validator waitlist spot is active. Graduation unlocks the next step.',
    },
    community: {
      accent: '#7f52e1',
      accentRgb: '127, 82, 225',
      gradient: 'linear-gradient(168deg, #be8ff5 15%, #a86ff0 50%, #7f52e1 85%)',
      label: 'Creators',
      eyebrow: 'Creator journey',
      title: 'Grow the network before mainnet.',
      body: 'Start your creator path, link your channels, and turn ecosystem action into a visible GenLayer record.',
      button: 'Become a Creator',
    },
  };

  /**
   * @param {string} role
   */
  function getRoleConfig(role) {
    if (role === 'builder') return roleConfig.builder;
    if (role === 'validator') return roleConfig.validator;
    return roleConfig.community;
  }

  const config = $derived(getRoleConfig(category));
  const visualCategory = $derived(category === 'builder' || category === 'validator' ? category : 'community');
  const isWaitlisted = $derived(state === 'waitlisted');
  const body = $derived(isWaitlisted && category === 'validator' ? roleConfig.validator.waitlistBody : config.body);
  const buttonLabel = $derived(starting ? 'Starting...' : config.button);
</script>

<svelte:head>
  <title>{config.label} | GenLayer Portal</title>
</svelte:head>

<div
  class="authenticated-role-landing"
  style={`--role-accent: ${config.accent}; --role-accent-rgb: ${config.accentRgb}; --role-gradient: ${config.gradient};`}
>
  <section class="start-panel" aria-labelledby="authenticated-role-title">
    <div class="mb-[-6px] flex h-[118px] w-[118px] items-center justify-center drop-shadow-[0_22px_34px_rgba(var(--role-accent-rgb),0.22)]" aria-hidden="true">
      <CategoryIcon category={visualCategory} mode="hexagon" size={118} />
    </div>
    <p class="role-eyebrow">{config.eyebrow}</p>
    <h1 id="authenticated-role-title">{config.title}</h1>
    <p class="role-body">{body}</p>

    {#if isWaitlisted}
      <div class="waitlist-status">
        <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.5 7.59a1 1 0 0 1-1.42.006L3.29 9.79a1 1 0 1 1 1.42-1.408l3.79 3.83 6.79-6.872a1 1 0 0 1 1.414-.06Z"
            clip-rule="evenodd"
          />
        </svg>
        Validator waitlist active
      </div>

      <article class="validator-contact-card" aria-labelledby="validator-contact-title">
        <div>
          <p class="contact-kicker">Operator onboarding</p>
          <h2 id="validator-contact-title">Need to speak with the validator team?</h2>
          <p>
            If you operate validator infrastructure or need to share operator details,
            contact the team with your wallet, organization, and relevant node experience.
          </p>
        </div>
        <a href={VALIDATOR_CONTACT_URL} target="_blank" rel="noopener noreferrer">
          Contact the team
        </a>
      </article>
    {:else}
      <button
        type="button"
        class="start-button"
        onclick={() => onStart()}
        disabled={starting}
        aria-busy={starting}
      >
        <span>{buttonLabel}</span>
        <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
      </button>
    {/if}

  </section>
</div>

<style>
  .authenticated-role-landing {
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
    color: #131214;
    display: flex;
    isolation: isolate;
    justify-content: center;
    margin: -12px;
    min-height: calc(100vh - 57px);
    min-height: calc(100dvh - 57px);
    min-width: 0;
    overflow: hidden;
    padding: 92px 24px 108px;
    position: relative;
    width: calc(100% + 24px);
  }

  .authenticated-role-landing::before {
    background:
      linear-gradient(rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.24)),
      radial-gradient(circle at 16% 8%, rgba(var(--role-accent-rgb), 0.34) 0%, transparent 34%),
      radial-gradient(circle at 82% 10%, rgba(var(--role-accent-rgb), 0.22) 0%, transparent 32%),
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

  .start-panel {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 22px;
    max-width: 820px;
    min-width: 0;
    position: relative;
    text-align: center;
    width: 100%;
    z-index: 1;
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

  h1 {
    color: #09090b;
    font-family: var(--font-display);
    font-size: clamp(40px, 7vw, 64px);
    font-weight: 500;
    letter-spacing: -1.92px;
    line-height: 1;
    margin: 0;
    max-width: 760px;
    text-wrap: balance;
  }

  .role-body {
    color: #626262;
    font-family: var(--font-body);
    font-size: 18px;
    line-height: 28px;
    margin: 0;
    max-width: 600px;
    text-wrap: pretty;
  }

  .start-button,
  .waitlist-status {
    align-items: center;
    border-radius: 24px;
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 15px;
    font-weight: 600;
    gap: 8px;
    height: 48px;
    justify-content: center;
    max-width: 100%;
    min-width: 184px;
    padding: 0 20px;
    transition-duration: 160ms;
    transition-property: box-shadow, opacity, transform;
    transition-timing-function: ease;
    white-space: nowrap;
  }

  .start-button {
    background: var(--role-gradient);
    box-shadow: 0 12px 28px rgba(var(--role-accent-rgb), 0.3);
    color: #fff;
  }

  .start-button:hover:not(:disabled) {
    box-shadow: 0 16px 34px rgba(var(--role-accent-rgb), 0.36);
    transform: translateY(-1px);
  }

  .start-button:active:not(:disabled) {
    transform: scale(0.96);
  }

  .start-button:disabled {
    cursor: default;
    opacity: 0.62;
  }

  .start-button img,
  .waitlist-status svg {
    height: 16px;
    width: 16px;
  }

  .waitlist-status {
    background: rgba(var(--role-accent-rgb), 0.1);
    color: var(--role-accent);
    min-width: auto;
  }

  .validator-contact-card {
    align-items: center;
    background: rgba(255, 255, 255, 0.78);
    border-radius: 10px;
    box-shadow:
      0 0 0 1px rgba(var(--role-accent-rgb), 0.14),
      0 18px 40px rgba(15, 23, 42, 0.07);
    display: grid;
    gap: 20px;
    grid-template-columns: minmax(0, 1fr) auto;
    margin-top: 8px;
    max-width: 680px;
    padding: 18px 20px;
    text-align: left;
    width: 100%;
  }

  .validator-contact-card div {
    min-width: 0;
  }

  .contact-kicker {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 1.1px;
    line-height: 17px;
    margin: 0 0 6px;
    text-transform: uppercase;
  }

  .validator-contact-card h2 {
    color: #131214;
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 500;
    letter-spacing: -0.22px;
    line-height: 28px;
    margin: 0;
  }

  .validator-contact-card p:not(.contact-kicker) {
    color: #5f6673;
    font-family: var(--font-body);
    font-size: 14.5px;
    line-height: 22px;
    margin: 8px 0 0;
  }

  .validator-contact-card a {
    align-items: center;
    background: #131214;
    border-radius: 20px;
    color: #fff;
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 600;
    height: 40px;
    justify-content: center;
    padding: 0 16px;
    text-decoration: none;
    transition: background-color 160ms ease, transform 160ms ease;
    white-space: nowrap;
  }

  .validator-contact-card a:hover {
    background: #2a292c;
    transform: translateY(-1px);
  }

  .validator-contact-card a:active {
    transform: scale(0.96);
  }

  @media (max-width: 720px) {
    .authenticated-role-landing {
      padding: 68px 16px 76px;
    }

    h1 {
      font-size: 42px;
      letter-spacing: -1.26px;
      line-height: 46px;
    }

    .role-body {
      font-size: 16px;
      line-height: 24px;
    }

    .start-button,
    .waitlist-status {
      width: min(100%, 320px);
    }

    .validator-contact-card {
      grid-template-columns: 1fr;
      text-align: center;
    }

    .validator-contact-card a {
      width: 100%;
    }
  }

  @media (max-width: 420px) {
    .authenticated-role-landing {
      padding: 52px 12px 64px;
    }

    h1 {
      font-size: 34px;
      line-height: 38px;
    }

    .start-panel {
      gap: 18px;
    }

    .start-button,
    .waitlist-status {
      min-width: 0;
      width: 100%;
    }

    .start-button span,
    .waitlist-status {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
</style>
