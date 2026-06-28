<script>
  // @ts-nocheck
  import { onDestroy } from 'svelte';
  import { socialTasksAPI } from '../../lib/api.js';
  import { authState } from '../../lib/auth.js';
  import { userStore } from '../../lib/userStore.js';
  import { showSuccess, showError } from '../../lib/toastStore.js';
  import { getCategoryPillColors } from '../../lib/categoryColors.js';
  import { getAnalyticsContext, setConnectWalletIntent, trackEvent } from '../../lib/analytics.js';
  import SocialLink from '../SocialLink.svelte';

  let { task, onCompleted = () => {}, pointsLabel = 'pts' } = $props();

  // ~5 seconds after a click-through user opens the link, we credit them.
  const CLICK_THROUGH_DELAY_MS = 5000 + Math.floor(Math.random() * 500);

  let busy = $state(false);
  let pendingClickThrough = $state(false);
  // Once the user has opened the link, verifying becomes the primary action.
  let opened = $state(false);
  // Set when the backend says the stored token is dead/missing: switches the
  // action row to the inline SocialLink so the user can reconnect right here
  // instead of looping on a failing Verify button.
  let needsRelink = $state(false);

  // Plain let, not $state — the timer id should not be a reactive dependency.
  let clickThroughTimer = null;

  let isCompleted = $derived(task.status === 'completed');
  let requiresVerification = $derived(task.requires_verification === true);
  let category = $derived(task.category_slug || 'community');
  let colors = $derived(getCategoryPillColors(category));

  let isAuthenticated = $derived($authState.isAuthenticated);
  let user = $derived($userStore?.user || null);

  // Which linked social account the task needs comes straight from the API
  // (derived server-side from the verifier registry), so new verification
  // types need zero frontend changes.
  // Display names for connection platforms; unknown ones fall back to the
  // raw slug so a new backend connection type still renders something sane.
  const PLATFORM_LABELS = { twitter: 'X', discord: 'Discord', github: 'GitHub' };
  const STEP_BY_TASK_SLUG = {
    'star-genlayer-boilerplate': { role: 'builder', step: 'star', index: 3, required: true },
    'follow-genlayer-x': { role: 'community', step: 'follow_x', index: 3, required: true },
    'join-genlayer-discord': { role: 'community', step: 'join_discord', index: 4, required: true },
  };
  let requiredPlatform = $derived(task.required_connection || null);
  let platformLabel = $derived(
    requiredPlatform ? (PLATFORM_LABELS[requiredPlatform] ?? requiredPlatform) : ''
  );
  let hasRequiredConnection = $derived(
    !requiredPlatform || Boolean(user?.[`${requiredPlatform}_connection`])
  );

  onDestroy(() => clearClickThroughTimer());

  function clearClickThroughTimer() {
    if (clickThroughTimer) {
      clearTimeout(clickThroughTimer);
      clickThroughTimer = null;
      pendingClickThrough = false;
    }
  }

  function handleError(err) {
    const code = err?.response?.data?.error;
    if (code === 'social_account_not_linked' || code === 'token_invalid_relink_required') {
      needsRelink = true;
      showError(`Reconnect your ${platformLabel || 'social'} account and try again.`);
    } else if (code === 'verification_failed') {
      showError(err.response.data.message || 'We did not see the action yet. Try again in a moment.');
    } else if (code === 'verification_unavailable') {
      showError('Verification service is busy. Try again shortly.');
    } else if (err?.response?.status === 410) {
      showError('This task is no longer active.');
    } else {
      // Unknown codes (e.g. account_banned) ship a human message field.
      showError(err?.response?.data?.message || 'Could not complete the task. Try again.');
    }
  }

  function taskStepMeta() {
    return STEP_BY_TASK_SLUG[task.slug] || {
      role: category,
      step: task.slug,
      index: 0,
      required: false,
    };
  }

  function taskErrorCode(err) {
    const code = String(err?.response?.data?.error || '').toLowerCase();
    if (['social_account_not_linked', 'token_invalid_relink_required', 'verification_failed', 'verification_unavailable'].includes(code)) {
      return code;
    }
    if (err?.response?.status === 410) return 'task_inactive';
    if (err?.response?.status) return 'backend_error';
    return 'unknown_error';
  }

  function trackTaskStepEvent(name, extra = {}) {
    const meta = taskStepMeta();
    trackEvent(name, getAnalyticsContext({
      role_context: meta.role,
      selected_role: ['builder', 'validator', 'community'].includes(meta.role) ? meta.role : undefined,
      surface: 'journey',
      step_id: meta.step,
      step_index: meta.index,
      step_required: meta.required,
      verification_mode: requiresVerification ? 'social_task' : 'click_through',
      ...extra,
    }));
  }

  async function callComplete({ trackAction = true } = {}) {
    if (busy || isCompleted) return;
    clearClickThroughTimer();
    if (trackAction) trackTaskStepEvent('journey_step_action_click');
    busy = true;
    try {
      const res = await socialTasksAPI.complete(task.slug);
      const data = res.data;
      const points = data?.points_awarded ?? task.points;
      if (data?.status === 'already_completed') {
        showSuccess(`Already completed (${points} ${pointsLabel}).`);
      } else {
        showSuccess(`Nice. ${points} ${pointsLabel} awarded.`);
      }
      trackTaskStepEvent('journey_step_verified');
      onCompleted({ task, completion: data });
    } catch (err) {
      trackTaskStepEvent('journey_step_error', {
        error_code: taskErrorCode(err),
        error_stage: err?.response?.status ? 'backend' : 'network',
      });
      handleError(err);
    } finally {
      busy = false;
    }
  }

  // Runs alongside the CTA anchor's native navigation. The CTA is a real
  // <a target="_blank"> rather than window.open: window.open with noopener
  // always returns null, so a popup blocker suppressing it is undetectable
  // and would credit click-through tasks for a page that never opened.
  // Direct-gesture anchor navigation is not popup-blocked.
  function handleOpened() {
    opened = true;
    trackTaskStepEvent('journey_step_action_click');

    if (!requiresVerification && isAuthenticated) {
      clearClickThroughTimer();
      pendingClickThrough = true;
      clickThroughTimer = setTimeout(() => {
        clickThroughTimer = null;
        pendingClickThrough = false;
        callComplete({ trackAction: false });
      }, CLICK_THROUGH_DELAY_MS);
    }
  }

  function triggerSignIn() {
    const meta = taskStepMeta();
    setConnectWalletIntent({
      surface: 'journey',
      cta_id: `${meta.step}_social_task_auth`,
      selected_role: ['builder', 'validator', 'community'].includes(meta.role) ? meta.role : undefined,
    });
    document.querySelector('[data-auth-button]')?.click();
  }

  function handleLinked(updatedUser) {
    needsRelink = false;
    if (updatedUser) {
      userStore.updateUser(updatedUser);
    } else {
      userStore.loadUser?.();
    }
  }
</script>

<div
  class="relative flex h-[160px] w-full flex-col gap-2 rounded-[8px] border border-[#f0f0f0] bg-white p-4 transition-shadow {isCompleted ? 'opacity-70' : 'hover:shadow-sm'}"
>
  <!-- Title + points pill -->
  <div class="flex items-start justify-between gap-2">
    <h3 class="min-w-0 flex-1 text-sm font-semibold text-black line-clamp-2 leading-snug">
      {task.name}
    </h3>
    <span
      class="flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
      style="background: {colors.pillBg}; color: {colors.pillText};"
    >
      <!-- Completed tasks show the frozen snapshot, not the task's current value -->
      +{isCompleted ? (task.points_awarded ?? task.points) : task.points} {pointsLabel}
    </span>
  </div>

  <!-- Description -->
  {#if task.description}
    <p class="flex-1 min-h-0 overflow-hidden text-xs leading-snug text-[#6b6b6b] line-clamp-2">
      {task.description}
    </p>
  {:else}
    <div class="flex-1"></div>
  {/if}

  <!-- Action area -->
  <div class="flex h-[32px] items-center gap-2">
    {#if isCompleted}
      <span class="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.5 7.59a1 1 0 0 1-1.42.006L3.29 9.79a1 1 0 1 1 1.42-1.408l3.79 3.83 6.79-6.872a1 1 0 0 1 1.414-.06Z"
            clip-rule="evenodd"
          />
        </svg>
        Completed
      </span>
    {:else if !isAuthenticated}
      <button
        type="button"
        onclick={triggerSignIn}
        class="text-xs font-semibold text-gray-700 transition-colors hover:text-black"
      >
        Sign in to earn →
      </button>
    {:else if requiredPlatform && (!hasRequiredConnection || needsRelink)}
      <div class="w-full">
        <SocialLink
          platform={requiredPlatform}
          platformLabel={platformLabel}
          connection={null}
          initiateUrl={`/api/auth/${requiredPlatform}/`}
          onLinked={handleLinked}
          compact={true}
        />
      </div>
    {:else if opened && requiresVerification}
      <!-- The user opened the link: verifying is now the primary action. -->
      <button
        type="button"
        onclick={() => callComplete({ trackAction: false })}
        disabled={busy}
        class="text-xs font-semibold text-black transition-colors hover:opacity-70 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {busy ? 'Verifying…' : 'Verify'}
      </button>

      <div class="ml-auto flex items-center gap-2">
        <a
          href={task.action_url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Open link again"
          title="Open link again"
          class="inline-flex h-7 w-7 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        >
          <svg
            class="h-3.5 w-3.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M15 3h6v6" />
            <path d="M10 14 21 3" />
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          </svg>
        </a>
      </div>
    {:else}
      <a
        href={task.action_url}
        target="_blank"
        rel="noopener noreferrer"
        onclick={handleOpened}
        class="text-xs font-semibold text-black transition-colors hover:opacity-70"
      >
        {task.cta_text || 'Open'} →
      </a>

      <div class="ml-auto flex items-center gap-2">
        {#if pendingClickThrough}
          <span class="text-[11px] text-gray-500" aria-live="polite">Crediting…</span>
        {/if}
        <!-- Verifiable tasks may be verified without opening (the user might
             already follow / be a member — the server checks for real).
             Click-through tasks have no server check, so the claim shortcut
             only appears after the link has been opened. -->
        {#if requiresVerification || opened}
          <button
            type="button"
            onclick={() => callComplete({ trackAction: !opened })}
            disabled={busy}
            aria-label={requiresVerification ? 'Verify completion' : 'Claim now'}
            title={requiresVerification ? 'Verify completion' : 'Claim now'}
            class="inline-flex h-7 w-7 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg
              class="h-3.5 w-3.5 {busy ? 'animate-spin' : ''}"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M21 12a9 9 0 1 1-3-6.7" />
              <polyline points="21 3 21 9 15 9" />
            </svg>
          </button>
        {/if}
      </div>
    {/if}
  </div>
</div>
