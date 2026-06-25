<script>
  import { push } from "svelte-spa-router";
  import { journeyPath, rolePath } from "../../lib/roleState.js";

  let { role = "builder", participant = null } = $props();

  /** @type {Record<string, { title: string; journeyLabel: string; accent: string; rgb: string; glyph: string; description: string }>} */
  const ROLE_META = {
    builder: {
      title: "Builder",
      journeyLabel: "Builder journey",
      accent: "#ee8521",
      rgb: "238, 133, 33",
      glyph: "/assets/icons/terminal-line-orange.svg",
      description:
        "Complete the remaining steps, then claim your Builder role.",
    },
    validator: {
      title: "Validator",
      journeyLabel: "Validator journey",
      accent: "#387de8",
      rgb: "56, 125, 232",
      glyph: "/assets/icons/folder-shield-line-blue.svg",
      description:
        "Complete the application to enter the validator waitlist.",
    },
    community: {
      title: "Community",
      journeyLabel: "Community journey",
      accent: "#8d81e1",
      rgb: "141, 129, 225",
      glyph: "/assets/icons/group-3-line-purple.svg",
      description:
        "Finish the required community steps, then claim your Community role.",
    },
  };

  let meta = $derived(ROLE_META[role] || ROLE_META.builder);
  let isValidatorWaitlist = $derived(
    role === "validator" && participant?.has_validator_waitlist && !participant?.validator,
  );
  let statusLabel = $derived(isValidatorWaitlist ? "Waiting for graduation" : "Action needed");
  let title = $derived.by(() => {
    if (isValidatorWaitlist) return "Validator application submitted";
    if (role === "validator") return "Complete your Validator application";
    return `Finish your ${meta.title} journey`;
  });
  let description = $derived.by(() => {
    if (isValidatorWaitlist) {
      return "You're on the waitlist. Check your validator status while graduation is reviewed.";
    }
    return meta.description;
  });
  let ctaText = $derived.by(() => {
    if (isValidatorWaitlist) return "View validator status";
    if (role === "validator") return "Continue application";
    return "Continue journey";
  });
  let ctaPath = $derived.by(() => {
    if (isValidatorWaitlist) return rolePath(role);
    return journeyPath(role);
  });
  let ariaLabel = $derived(isValidatorWaitlist ? "Validator waitlist status" : `${meta.title} journey in progress`);
</script>

<section
  class="journey-reminder"
  style={`--role-accent: ${meta.accent}; --role-accent-rgb: ${meta.rgb};`}
  aria-label={ariaLabel}
>
  <div class="journey-reminder__glow" aria-hidden="true"></div>

  <div class="journey-reminder__header">
    <div class="journey-reminder__icon" aria-hidden="true">
      <img src={meta.glyph} alt="" />
    </div>
    <div class="journey-reminder__title-block">
      <p>{meta.journeyLabel}</p>
      <h2>{title}</h2>
    </div>
    <span class="journey-reminder__status">{statusLabel}</span>
  </div>

  <p class="journey-reminder__copy">{description}</p>

  <button type="button" class="journey-reminder__button" onclick={() => push(ctaPath)}>
    {ctaText}
    <img src="/assets/icons/arrow-right-line-white.svg" alt="" />
  </button>
</section>

<style>
  .journey-reminder {
    --role-accent: #ee8521;
    --role-accent-rgb: 238, 133, 33;
    background: #fff;
    border: 1px solid #ededed;
    border-radius: 14px;
    box-shadow: 0 10px 28px rgba(19, 18, 20, 0.035);
    box-sizing: border-box;
    color: #131214;
    isolation: isolate;
    overflow: hidden;
    padding: 22px;
    position: relative;
    width: 100%;
  }

  .journey-reminder__glow {
    background: linear-gradient(180deg, rgba(var(--role-accent-rgb), 0.15), rgba(var(--role-accent-rgb), 0));
    height: 3px;
    left: 0;
    pointer-events: none;
    position: absolute;
    top: 0;
    width: 100%;
    z-index: 0;
  }

  .journey-reminder__header {
    align-items: center;
    display: flex;
    gap: 12px;
    min-width: 0;
    position: relative;
    z-index: 1;
  }

  .journey-reminder__icon {
    align-items: center;
    background: #f3f3f3;
    clip-path: polygon(50% 0%, 94% 25%, 94% 75%, 50% 100%, 6% 75%, 6% 25%);
    display: flex;
    flex: 0 0 44px;
    height: 44px;
    justify-content: center;
    width: 44px;
  }

  .journey-reminder__icon img {
    height: 21px;
    width: 21px;
  }

  .journey-reminder__title-block {
    flex: 1;
    min-width: 0;
  }

  .journey-reminder__title-block p {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    line-height: 16px;
    margin: 0 0 3px;
    text-transform: uppercase;
  }

  .journey-reminder__title-block h2 {
    color: #131214;
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 28px;
    margin: 0;
  }

  .journey-reminder__status {
    align-items: center;
    background: rgba(var(--role-accent-rgb), 0.08);
    border: 1px solid rgba(var(--role-accent-rgb), 0.16);
    border-radius: 999px;
    color: var(--role-accent);
    display: inline-flex;
    flex: 0 0 auto;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    height: 26px;
    letter-spacing: 0.6px;
    padding: 0 10px;
    text-transform: uppercase;
  }

  .journey-reminder__copy {
    color: #737373;
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 21px;
    margin: 14px 0 20px;
    max-width: 680px;
    position: relative;
    z-index: 1;
  }

  .journey-reminder__button {
    align-items: center;
    background: #131214;
    border: 0;
    border-radius: 20px;
    color: #fff;
    cursor: pointer;
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 500;
    gap: 6px;
    height: 40px;
    justify-content: center;
    line-height: 20px;
    padding: 0 16px;
    position: relative;
    transition: background 0.16s ease, transform 0.16s ease;
    z-index: 1;
  }

  .journey-reminder__button:hover {
    background: #2a292c;
    transform: translateY(-1px);
  }

  .journey-reminder__button img {
    height: 16px;
    width: 16px;
  }

  @media (max-width: 640px) {
    .journey-reminder {
      border-radius: 12px;
      padding: 18px;
    }

    .journey-reminder__header {
      align-items: flex-start;
      flex-wrap: wrap;
    }

    .journey-reminder__status {
      margin-left: 56px;
      margin-top: -4px;
    }

    .journey-reminder__title-block h2 {
      font-size: 21px;
      line-height: 25px;
    }

    .journey-reminder__button {
      width: 100%;
    }

  }
</style>
