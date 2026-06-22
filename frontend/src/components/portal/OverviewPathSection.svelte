<script>
  import { push } from 'svelte-spa-router';
  import CategoryIcon from './CategoryIcon.svelte';

  const roles = [
    {
      key: 'builder',
      title: 'Builder',
      description: 'Ship Intelligent Contracts. Earn up to 20% of the points they generate.',
      cta: 'START BUILDING',
      href: '/builders/contributions',
      accent: '#ff8900',
    },
    {
      key: 'validator',
      title: 'Validator',
      description: 'Run a node that reasons. Get paid per decision.',
      cta: 'JOIN THE WAITLIST',
      href: '/validators/waitlist/join',
      accent: '#4778ff',
    },
    {
      key: 'community',
      title: 'Community',
      description: 'Push the project forward. Earn GenLayer Points.',
      cta: 'BECOME A CREATOR',
      href: '/community',
      accent: '#9880ea',
    },
  ];
</script>

<section class="overview-path-section">
  <div class="path-block">
    <div class="path-title">
      <h2>Choose your path!</h2>
    </div>

    <div class="path-card-band">
      <div class="path-card-grid">
        {#each roles as role}
          <article class="path-card">
            <div class="card-heading">
              <span class="role-icon" aria-hidden="true">
                <CategoryIcon category={role.key} mode="hexagon" size={42} light={true} />
              </span>
              <h3>{role.title}</h3>
            </div>

            <p>{role.description}</p>

            <button type="button" style={`--accent: ${role.accent};`} onclick={() => push(role.href)}>
              <span>{role.cta}</span>
              <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
            </button>
          </article>
        {/each}
      </div>
    </div>
  </div>

  <footer class="auth-layer-footer">
    <div class="footer-message">
      <h2>
        Build the Adjudication<br />
        Layer of the Internet.<br />
        Earn for it.
      </h2>

      <div class="footer-actions">
        <button type="button" class="footer-primary" onclick={() => push('/builders/contributions')}>
          <span>Start Contributing</span>
          <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
        </button>
      </div>
    </div>

    <div class="coin-stage" aria-hidden="true">
      <img
        src="/assets/illustrations/genlayer-coin.webp"
        alt=""
        width="195"
        height="202"
        loading="lazy"
        decoding="async"
        fetchpriority="low"
      />
    </div>

    <p class="footer-copy">
      BUILDERS, VALIDATORS AND COMMUNITY.<br />
      EVERY CONTRIBUTION COUNTS,<br />
      AND EVERY CONTRIBUTION IS REWARDED.
    </p>
  </footer>
</section>

<style>
  .overview-path-section {
    display: flex;
    flex-direction: column;
    isolation: isolate;
    margin: 0;
    position: relative;
  }

  .path-block {
    padding: 72px clamp(20px, 5vw, 72px) 0;
    position: relative;
    z-index: 1;
  }

  .path-title {
    background: transparent;
    padding: 0 0 34px;
    text-align: center;
  }

  .path-title h2 {
    color: #101010;
    font-family: var(--font-heading);
    font-size: clamp(28px, 3.4vw, 40px);
    font-weight: 500;
    letter-spacing: 0.012em;
    line-height: 1.12;
    margin: 0;
  }

  .path-card-band {
    background: transparent;
    padding: 0;
  }

  .path-card-grid {
    display: grid;
    gap: 28px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0 auto;
    width: 100%;
  }

  .path-card {
    background: #fff;
    border: 1px solid #ebebee;
    border-radius: 8px;
    box-shadow: none;
    color: #111;
    display: flex;
    flex-direction: column;
    min-height: 166px;
    padding: 18px 22px 20px;
  }

  .card-heading {
    align-items: center;
    display: flex;
    gap: 14px;
    min-width: 0;
  }

  .role-icon {
    display: inline-flex;
    flex: 0 0 auto;
    height: 36px;
    width: 36px;
  }

  .path-card h3 {
    color: #0b0b0b;
    font-family: var(--font-heading);
    font-size: clamp(22px, 2.2vw, 26px);
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.1;
    margin: 0;
  }

  .path-card p {
    color: #767676;
    font-size: clamp(13px, 1.25vw, 15px);
    font-weight: 400;
    line-height: 1.35;
    margin: 18px 0 22px;
    max-width: 300px;
  }

  .path-card button {
    align-items: center;
    align-self: flex-start;
    background: var(--accent);
    border: 0;
    border-radius: 999px;
    color: #fff;
    cursor: pointer;
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    gap: 10px;
    height: 34px;
    justify-content: center;
    letter-spacing: 0;
    line-height: 1;
    margin-top: auto;
    padding: 0 14px 0 17px;
    text-transform: uppercase;
    transition: filter 160ms ease, transform 160ms ease;
  }

  .path-card button:hover {
    filter: brightness(0.96);
    transform: translateY(-1px);
  }

  .path-card button img {
    height: 15px;
    width: 15px;
  }

  .auth-layer-footer {
    align-items: center;
    background: #fff;
    display: grid;
    grid-template-columns:
      minmax(280px, 0.82fr)
      minmax(180px, 220px)
      minmax(280px, 0.82fr);
    margin: 96px -12px -12px;
    min-height: 430px;
    overflow: visible;
    padding: 48px clamp(24px, 6vw, 112px) 58px;
    position: relative;
    z-index: 0;
  }

  .auth-layer-footer::before {
    background: url('/assets/illustrations/welcome-gradient.png') center / 100% 100% no-repeat;
    content: '';
    inset: -190px 0 -120px;
    opacity: 0.5;
    pointer-events: none;
    position: absolute;
    z-index: 0;
    -webkit-mask-image: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.2) 16%, #000 34%, #000 72%, transparent 100%);
    mask-image: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.2) 16%, #000 34%, #000 72%, transparent 100%);
  }

  .auth-layer-footer::after {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.22), rgba(255, 255, 255, 0.56));
    content: '';
    inset: -190px 0 -120px;
    pointer-events: none;
    position: absolute;
    z-index: 0;
    -webkit-mask-image: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.35) 18%, #000 38%, #000 72%, transparent 100%);
    mask-image: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.35) 18%, #000 38%, #000 72%, transparent 100%);
  }

  .auth-layer-footer > * {
    position: relative;
    z-index: 1;
  }

  .footer-message {
    align-items: flex-start;
    display: flex;
    flex-direction: column;
    justify-self: center;
    max-width: 470px;
  }

  .footer-message h2 {
    color: #050505;
    font-family: var(--font-heading);
    font-size: clamp(29px, 2.6vw, 42px);
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.16;
    margin: 0 0 30px;
  }

  .footer-actions {
    align-items: center;
    display: flex;
    gap: 12px;
    justify-self: start;
  }

  .footer-actions button {
    align-items: center;
    border-radius: 999px;
    cursor: pointer;
    display: inline-flex;
    font-family: var(--font-heading);
    font-size: 15px;
    font-weight: 500;
    gap: 10px;
    height: 40px;
    justify-content: center;
    letter-spacing: 0;
    padding: 0 16px 0 20px;
    transition: border-color 160ms ease, color 160ms ease, transform 160ms ease;
    white-space: nowrap;
  }

  .footer-primary {
    background: #17171b;
    border: 1px solid #17171b;
    color: #f4f4f4;
    min-width: 166px;
  }

  .footer-primary:hover {
    transform: translateY(-1px);
  }

  .footer-actions img {
    height: 17px;
    width: 17px;
  }

  .coin-stage {
    align-items: center;
    display: flex;
    height: 200px;
    justify-content: center;
    position: relative;
    width: 200px;
    z-index: 1;
  }

  .coin-stage::before {
    background: radial-gradient(circle, rgba(255, 255, 255, 0.68), transparent 62%);
    content: '';
    filter: blur(22px);
    inset: 0;
    position: absolute;
  }

  .coin-stage img {
    filter: drop-shadow(0 28px 48px rgba(80, 72, 118, 0.18));
    height: auto;
    position: relative;
    width: 186px;
    z-index: 1;
  }

  .footer-copy {
    color: #969696;
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 500;
    justify-self: center;
    letter-spacing: 0;
    line-height: 1.5;
    margin: 0;
    max-width: 380px;
  }

  @media (max-width: 980px) {
    .auth-layer-footer {
      grid-template-columns: 1fr;
      justify-items: center;
      min-height: 0;
      padding: 64px 28px;
      row-gap: 30px;
      text-align: center;
    }

    .footer-message,
    .footer-actions,
    .footer-copy {
      align-items: center;
      justify-self: center;
    }

    .footer-message h2 {
      margin-bottom: 24px;
    }

    .coin-stage {
      grid-row: 2;
    }

    .footer-copy {
      grid-row: 3;
    }
  }

  @media (max-width: 1180px) {
    .path-card-grid {
      gap: 18px;
    }

    .path-card {
      padding: 18px 20px 20px;
    }

    .card-heading {
      gap: 18px;
    }

    .role-icon {
      height: 36px;
      width: 36px;
    }

    .path-card p {
      margin-top: 18px;
    }
  }

  @media (max-width: 860px) {
    .path-card-band {
      padding: 0;
    }

    .path-card-grid {
      grid-template-columns: 1fr;
    }

    .path-card {
      min-height: 0;
    }
  }

  @media (max-width: 560px) {
    .path-block {
      padding-top: 54px;
    }

    .path-title {
      padding: 0 0 28px;
    }

    .path-title h2 {
      font-size: 28px;
    }

    .path-card {
      min-height: 0;
      padding: 18px;
    }

    .path-card h3 {
      font-size: 24px;
    }

    .path-card p {
      margin: 18px 0 24px;
    }

    .path-card button {
      width: 100%;
    }

    .auth-layer-footer {
      margin-top: 58px;
      padding: 54px 20px;
    }

    .footer-message h2 {
      font-size: 29px;
    }

    .coin-stage {
      height: 200px;
      width: 200px;
    }

    .coin-stage img {
      width: 182px;
    }

    .footer-copy {
      font-size: 13px;
    }

    .footer-actions {
      flex-direction: column;
      width: 100%;
    }

    .footer-actions button {
      width: min(100%, 260px);
    }
  }
</style>
