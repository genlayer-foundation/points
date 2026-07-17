<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';
  import { journeyAPI, socialTasksAPI } from '../lib/api.js';
  import { userStore } from '../lib/userStore.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import {
    getAnalyticsContext,
    getFunnelDurationMs,
    getLifecycleDurations,
    markLifecycleTime,
    markFunnelTime,
    trackEvent,
  } from '../lib/analytics.js';
  import SocialLink from '../components/SocialLink.svelte';
  import SocialTaskCard from '../components/social-tasks/SocialTaskCard.svelte';
  import JourneyWelcome from '../components/funnel/journeys/JourneyWelcome.svelte';
  import JourneyHeroCard from '../components/funnel/journeys/JourneyHeroCard.svelte';
  import JourneyStepRow from '../components/funnel/journeys/JourneyStepRow.svelte';
  import JourneyUnlockCard from '../components/funnel/journeys/JourneyUnlockCard.svelte';

  const TOTAL_STEPS = 5;
  const FOLLOW_X_TASK_SLUG = 'follow-genlayer-x';
  const JOIN_DISCORD_TASK_SLUG = 'join-genlayer-discord';

  const STEP_IDS = ['link_x', 'link_discord', 'follow_x', 'join_discord', 'x_post'];
  const VERIFICATION_MODES = {
    link_x: 'oauth_x',
    link_discord: 'oauth_discord',
    follow_x: 'social_task',
    join_discord: 'social_task',
    x_post: 'sorsa_tweet_info',
  };
  const POST_VERIFICATION_RESULTS = new Set([
    'success',
    'invalid_url',
    'account_mismatch',
    'post_not_found',
    'code_missing',
    'tag_missing',
    'verification_unavailable',
    'unknown_error',
  ]);

  let journey = $state(null);
  let tasks = $state([]);
  let loading = $state(true);
  let loadError = $state('');
  let actionError = $state('');
  let completing = $state(false);
  let linkingX = $state(false);
  let linkingDiscord = $state(false);
  let verifyingPost = $state(false);
  let postUrl = $state('');
  let selectedPostIndex = $state(0);
  let lastJourneyViewKey = $state('');
  let lastStepViewKey = $state('');
  let lastJourneyExitKey = $state('');
  let mounted = $state(false);
  let latestJourneyRequestId = 0;

  let user = $derived($userStore.user);
  let twitterConnection = $derived(user?.twitter_connection || null);
  let discordConnection = $derived(user?.discord_connection || null);
  let steps = $derived(journey?.steps || {});
  let xPost = $derived(steps.x_post || {});
  let completedSteps = $derived(STEP_IDS.filter((id) => stepDone(id)).length);
  let remainingSteps = $derived(Math.max(0, TOTAL_STEPS - completedSteps));
  let complete = $derived(Boolean(journey?.complete));
  let activeStep = $derived(STEP_IDS.find((id) => !stepDone(id)) || null);
  let activeStepId = $derived(activeStep || 'done');
  let activeStepNumber = $derived(activeStep ? STEP_IDS.indexOf(activeStep) + 1 : TOTAL_STEPS);
  let followTask = $derived(tasks.find((task) => task.slug === FOLLOW_X_TASK_SLUG) || null);
  let discordTask = $derived(tasks.find((task) => task.slug === JOIN_DISCORD_TASK_SLUG) || null);
  let postOptions = $derived(
    Array.isArray(xPost.post_options) && xPost.post_options.length
      ? xPost.post_options
      : [{ id: 'default', text: xPost.share_text || '', intent_url: xPost.intent_url || '' }]
  );
  let selectedPost = $derived(postOptions[Math.min(selectedPostIndex, Math.max(postOptions.length - 1, 0))] || null);
  let selectedShareText = $derived(selectedPost?.text || xPost.share_text || '');
  let selectedIntentUrl = $derived(selectedPost?.intent_url || xPost.intent_url || 'https://x.com/intent/post');
  let displayName = $derived(user?.name?.trim() || '');
  let welcomeTitle = $derived(displayName ? `Welcome, ${displayName}` : 'Welcome to your Community journey');
  let welcomeMessage = $derived(
    complete
      ? 'Your community steps are complete. Finish the journey to unlock the Creator role and start submitting community work.'
      : 'Connect your social accounts, verify the community actions, and post your referral code to unlock the Creator role.'
  );
  let welcomeAlert = $derived(actionError || loadError || '');
  let welcomeChips = $derived([
    { label: 'Progress', value: `${completedSteps}/${TOTAL_STEPS}` },
    { label: 'Left', value: remainingSteps === 1 ? '1 step' : `${remainingSteps} steps` },
    { label: 'Next', value: complete ? 'Finish journey' : `Step ${activeStepNumber}` },
  ]);
  let heroHelper = $derived(
    complete
      ? 'Click to finish.'
      : `Step ${activeStepNumber} is highlighted below.`
  );

  const unlocks = [
    {
      title: 'Missions',
      body: 'Pick up open missions across the ecosystem and ship with the community.',
      label: 'Earn points for every mission',
      icon: 'folder',
    },
    {
      title: 'Leaderboard',
      body: 'Climb the community ranks and get noticed by the ecosystem.',
      label: 'Compete for top contributor',
      icon: 'leaderboard',
    },
    {
      title: 'Rewards',
      body: 'Redeem your GenLayer Points for ecosystem rewards.',
      label: 'Turn points into rewards',
      icon: 'rewards',
    },
  ];

  onMount(() => {
    markFunnelTime('journey_visible:community');
    const handlePageHide = () => trackJourneyExit('pagehide');
    window.addEventListener('pagehide', handlePageHide);

    mounted = true;
    return () => {
      mounted = false;
      latestJourneyRequestId += 1;
      window.removeEventListener('pagehide', handlePageHide);
      trackJourneyExit('route_leave');
    };
  });

  // The route gate verifies membership before this component mounts. Keep the
  // same check here as a final boundary for direct component mounts and stale
  // profile transitions so Creator accounts never read journey/task state.
  let initialLoadStarted = false;
  $effect(() => {
    if (!mounted || !user) return;
    if (user.creator) {
      replace('/community');
      return;
    }
    if (initialLoadStarted) return;
    initialLoadStarted = true;
    loadJourney({ showLoading: true });
  });

  // Start the journey only once the user profile has actually loaded. The
  // route can mount before /users/me/ resolves, so this must be reactive (an
  // onMount check would permanently skip the start marker for direct visits),
  // and a null user (backend down) must never trigger the mutation.
  let journeyStartChecked = false;
  $effect(() => {
    if (journeyStartChecked || !user || user.creator) return;
    journeyStartChecked = true;
    if (user.has_community_welcome) return;
    journeyAPI
      .startRoleJourney('community')
      .then(() => {
        markFunnelTime('journey_start:community');
        markLifecycleTime('first_journey_start:community');
        trackEvent('journey_started', getAnalyticsContext({
          role_context: 'community',
          selected_role: 'community',
          surface: 'journey',
          journey_state: 'started',
          time_from_role_landing_ms: getFunnelDurationMs('role_landing:community'),
          time_from_wallet_click_ms: getFunnelDurationMs('wallet_click'),
          time_from_wallet_auth_success_ms: getFunnelDurationMs('wallet_auth_success'),
          time_from_profile_completion_ms: getFunnelDurationMs('profile_completion'),
        }));
        userStore.loadUser?.();
      })
      .catch((err) => {
        trackEvent('journey_start_error', getAnalyticsContext({
          role_context: 'community',
          selected_role: 'community',
          surface: 'journey',
          error_stage: err.response?.status ? 'backend' : 'network',
        }));
        showError('Could not start your creator journey. Try refreshing in a moment.');
      });
  });

  $effect(() => {
    if (loading) return;
    const viewKey = `community:${completedSteps}:${complete}`;
    if (viewKey === lastJourneyViewKey) return;
    lastJourneyViewKey = viewKey;
    trackEvent('journey_view', getAnalyticsContext({
      role_context: 'community',
      selected_role: 'community',
      role_funnel_state: user?.creator ? 'earned' : 'started',
      journey_state: user?.creator ? 'earned' : (complete ? 'completed' : 'started'),
      surface: 'journey',
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
    }));
  });

  $effect(() => {
    if (loading || !activeStepId || activeStepId === 'done') return;
    const viewKey = `community:${activeStepId}`;
    if (viewKey === lastStepViewKey) return;
    lastStepViewKey = viewKey;
    markFunnelTime(`journey_step_visible:community:${activeStepId}`);
    trackCommunityStepEvent('journey_step_view', activeStepId);
  });

  $effect(() => {
    if (selectedPostIndex >= postOptions.length) selectedPostIndex = 0;
  });

  function stepDone(id) {
    return Boolean(steps?.[id]?.done);
  }

  function statusFor(id) {
    if (stepDone(id)) return 'done';
    if (activeStepId === id) return 'active';
    return 'locked';
  }

  function isActive(id) {
    return statusFor(id) === 'active';
  }

  function stepIndex(stepId) {
    return STEP_IDS.indexOf(stepId) + 1;
  }

  function trackCommunityStepEvent(name, stepId, extra = {}) {
    trackEvent(name, getAnalyticsContext({
      role_context: 'community',
      selected_role: 'community',
      surface: 'journey',
      step_id: stepId,
      step_index: stepIndex(stepId),
      step_required: true,
      verification_mode: VERIFICATION_MODES[stepId] || 'unknown',
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
      ...extra,
    }));
  }

  function trackJourneyExit(exitReason) {
    if (loading || user?.creator) return;
    const stepId = activeStepId || 'unknown';
    const exitKey = `${stepId}:${completedSteps}:${complete}`;
    if (exitKey === lastJourneyExitKey) return;
    lastJourneyExitKey = exitKey;
    trackEvent('journey_exit', getAnalyticsContext({
      role_context: 'community',
      selected_role: 'community',
      surface: 'journey',
      exit_reason: exitReason,
      step_id: stepId,
      step_index: stepIndex(stepId),
      step_required: stepId !== 'done',
      journey_state: complete ? 'claim_ready' : 'started',
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
      time_on_journey_ms: getFunnelDurationMs('journey_visible:community'),
      time_on_step_ms: getFunnelDurationMs(`journey_step_visible:community:${stepId}`),
    }));
  }

  function postVerificationResult(err) {
    const code = String(err?.response?.data?.error || '').toLowerCase();
    if (POST_VERIFICATION_RESULTS.has(code)) return code;
    if (err?.response?.status === 503) return 'verification_unavailable';
    if (err?.response?.status === 404) return 'post_not_found';
    return 'unknown_error';
  }

  function stepPoints(id) {
    return steps?.[id]?.points ?? null;
  }

  async function loadJourney({ showLoading = false } = {}) {
    if (user?.creator) {
      replace('/community');
      return;
    }

    const requestId = ++latestJourneyRequestId;
    if (showLoading) loading = true;
    loadError = '';
    try {
      const [journeyRes, tasksRes] = await Promise.all([
        journeyAPI.communityJourney(),
        socialTasksAPI.list({ category: 'community' }),
      ]);
      if (requestId !== latestJourneyRequestId || user?.creator) return;
      journey = journeyRes.data;
      tasks = Array.isArray(tasksRes.data) ? tasksRes.data : [];
      const existingPostUrl = journeyRes.data?.steps?.x_post?.post_url || '';
      if (existingPostUrl && !postUrl) postUrl = existingPostUrl;
    } catch (err) {
      if (requestId !== latestJourneyRequestId || user?.creator) return;
      loadError = err.response?.data?.message || err.response?.data?.error || 'Could not load your creator journey.';
      if (showLoading) {
        journey = null;
        tasks = [];
      }
    } finally {
      if (requestId === latestJourneyRequestId && showLoading) loading = false;
    }
  }

  function markStepDone(id) {
    journey = {
      ...(journey || {}),
      steps: {
        ...(journey?.steps || {}),
        [id]: {
          ...(journey?.steps?.[id] || {}),
          done: true,
        },
      },
    };
  }

  async function claimLinkedAccount(kind) {
    const isX = kind === 'x';
    const stepId = isX ? 'link_x' : 'link_discord';
    if ((isX && linkingX) || (!isX && linkingDiscord)) return;
    trackCommunityStepEvent('journey_step_action_click', stepId);
    if (isX) linkingX = true;
    else linkingDiscord = true;
    actionError = '';

    try {
      const res = isX ? await journeyAPI.linkXAccount() : await journeyAPI.linkDiscordAccount();
      if (res.data?.user) userStore.updateUser(res.data.user);
      else await userStore.loadUser?.();
      trackCommunityStepEvent('journey_step_verified', stepId);
      markStepDone(stepId);
      showSuccess(isX ? 'X account linked for community points.' : 'Discord account linked for community points.');
      await loadJourney({ showLoading: false });
      markStepDone(stepId);
    } catch (err) {
      trackCommunityStepEvent('journey_step_error', stepId, {
        error_code: err.response?.status ? 'backend_error' : 'unknown_error',
        error_stage: err.response?.status ? 'backend' : 'network',
      });
      actionError = err.response?.data?.message || err.response?.data?.error || `Could not confirm your ${isX ? 'X' : 'Discord'} account.`;
      showError(actionError);
    } finally {
      if (isX) linkingX = false;
      else linkingDiscord = false;
    }
  }

  async function handleXLinked(updatedUser) {
    if (updatedUser) userStore.updateUser(updatedUser);
    await claimLinkedAccount('x');
  }

  async function handleDiscordLinked(updatedUser) {
    if (updatedUser) userStore.updateUser(updatedUser);
    await claimLinkedAccount('discord');
  }

  function handleTaskCompleted(result) {
    tasks = tasks.map((task) =>
      task.slug === result?.task?.slug
        ? {
            ...task,
            status: 'completed',
            points_awarded: result?.completion?.points_awarded ?? task.points_awarded ?? task.points,
          }
        : task
    );
    loadJourney({ showLoading: false });
    userStore.loadUser?.();
  }

  async function copyShareText() {
    const text = selectedShareText || '';
    if (!text) return;
    trackEvent('community_post_copy_click', getAnalyticsContext({
      role_context: 'community',
      selected_role: 'community',
      surface: 'journey',
      step_id: 'x_post',
      verification_mode: 'sorsa_tweet_info',
      post_option: selectedPost?.id || 'default',
    }));
    try {
      await navigator.clipboard.writeText(text);
      showSuccess('Post text copied.');
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      const copied = document.execCommand('copy');
      document.body.removeChild(textarea);
      if (copied) showSuccess('Post text copied.');
      else showError('Could not copy the post text. Please copy it manually.');
    }
  }

  async function verifyPost() {
    if (verifyingPost) return;
    trackEvent('community_post_verify_attempt', getAnalyticsContext({
      role_context: 'community',
      selected_role: 'community',
      surface: 'journey',
      step_id: 'x_post',
      verification_mode: 'sorsa_tweet_info',
    }));
    trackCommunityStepEvent('journey_step_action_click', 'x_post');
    const trimmedUrl = postUrl.trim();
    if (!trimmedUrl) {
      trackEvent('community_post_verify_error', getAnalyticsContext({
        role_context: 'community',
        selected_role: 'community',
        surface: 'journey',
        verification_result: 'invalid_url',
        error_code: 'invalid_url',
        verification_mode: 'sorsa_tweet_info',
      }));
      trackCommunityStepEvent('journey_step_error', 'x_post', {
        error_code: 'invalid_url',
        error_stage: 'validation',
      });
      actionError = 'Paste the URL of your X post first.';
      showError(actionError);
      return;
    }

    verifyingPost = true;
    actionError = '';
    try {
      const res = await journeyAPI.verifyCommunityPost(trimmedUrl);
      if (res.data?.journey) journey = res.data.journey;
      trackEvent('community_post_verify_success', getAnalyticsContext({
        role_context: 'community',
        selected_role: 'community',
        surface: 'journey',
        verification_result: 'success',
        verification_mode: 'sorsa_tweet_info',
      }));
      trackCommunityStepEvent('journey_step_verified', 'x_post');
      showSuccess('Community post verified.');
      await loadJourney({ showLoading: false });
    } catch (err) {
      const verificationResult = postVerificationResult(err);
      trackEvent('community_post_verify_error', getAnalyticsContext({
        role_context: 'community',
        selected_role: 'community',
        surface: 'journey',
        verification_result: verificationResult,
        error_code: verificationResult,
        verification_mode: 'sorsa_tweet_info',
      }));
      trackCommunityStepEvent('journey_step_error', 'x_post', {
        error_code: verificationResult,
        error_stage: err.response?.status ? 'backend' : 'network',
      });
      actionError = err.response?.data?.message || err.response?.data?.error || 'Could not verify your X post.';
      showError(actionError);
    } finally {
      verifyingPost = false;
    }
  }

  async function completeJourney() {
    if (completing || !complete) return;
    const claimParams = {
      role_context: 'community',
      selected_role: 'community',
      surface: 'journey',
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
      time_from_role_landing_ms: getFunnelDurationMs('role_landing:community'),
      time_from_journey_start_ms: getFunnelDurationMs('journey_start:community'),
      ...getLifecycleDurations('community'),
    };
    trackEvent('community_role_claim_attempt', getAnalyticsContext(claimParams));
    completing = true;
    actionError = '';
    try {
      const res = await journeyAPI.completeCommunityJourney();
      if (res.data?.user) userStore.updateUser(res.data.user);
      await userStore.loadUser?.();
      markLifecycleTime('role_unlocked:community');
      trackEvent('community_role_claim_success', getAnalyticsContext(claimParams));
      trackEvent('journey_completed', getAnalyticsContext({
        ...claimParams,
        journey_state: 'completed',
      }));
      trackEvent('role_unlocked', getAnalyticsContext({
        ...claimParams,
        role_context: 'community',
        selected_role: 'community',
        surface: 'journey',
        unlock_source: 'journey',
      }));
      showSuccess('Welcome to the GenLayer community!');
      replace('/community');
    } catch (err) {
      trackEvent('community_role_claim_error', getAnalyticsContext({
        ...claimParams,
        error_code: err.response?.status ? 'backend_error' : 'unknown_error',
        error_stage: err.response?.status ? 'backend' : 'network',
      }));
      actionError = err.response?.data?.message || err.response?.data?.error || 'Complete all creator journey steps first.';
      showError(actionError);
      await loadJourney({ showLoading: false });
    } finally {
      completing = false;
    }
  }
</script>

<svelte:head>
  <title>Community Journey | GenLayer Portal</title>
</svelte:head>

<div class="journey-page community-journey">
  <JourneyWelcome
    role="community"
    title={welcomeTitle}
    message={welcomeMessage}
    chips={!loading && loadError && !journey ? [] : welcomeChips}
    alert={!loading && loadError && !journey ? '' : welcomeAlert}
  />

  {#if !loading && loadError && !journey}
    <section class="journey-load-error" aria-labelledby="journey-load-error-title" role="alert">
      <h1 id="journey-load-error-title">Your journey couldn't be loaded</h1>
      <p>{loadError} Your progress is unchanged.</p>
      <button
        type="button"
        class="landing-button landing-button-primary"
        onclick={() => loadJourney({ showLoading: true })}
      >
        Retry
      </button>
    </section>
  {:else}
    <JourneyHeroCard
      role="community"
      iconHex="/assets/icons/hexagon-community-light.svg"
      iconGlyph="/assets/icons/group-3-line-purple.svg"
      eyebrow="Your creator journey"
      accentValue={TOTAL_STEPS}
      titleRest=" steps to become a creator"
      description="Link your social accounts, verify the GenLayer creator actions, and share your unique X post before claiming the Creator role."
      completed={loading ? 0 : completedSteps}
      total={TOTAL_STEPS}
      primaryLabel={completing ? 'Completing...' : 'Become a Creator'}
      primaryDisabled={loading || completing || !complete}
      primaryBusy={completing}
      helper={heroHelper}
      onPrimary={completeJourney}
    />

    <section class="steps-card" aria-label="Creator journey steps">
      {#if loading}
        {#each Array(TOTAL_STEPS) as _, i}
          <JourneyStepRow number={i + 1} loading={true} />
        {/each}
      {:else}
      <div class="step-block" data-step-active={isActive('link_x')}>
        <JourneyStepRow
          number={1}
          title="Link X"
          contributionLabel={isActive('link_x') ? 'Up next' : ''}
          detail={stepDone('link_x') ? twitterConnection?.platform_username ? `@${twitterConnection.platform_username}` : 'X account confirmed' : 'Connect X to verify community actions'}
          points={stepPoints('link_x')}
          pointsLabel="CP"
          status={statusFor('link_x')}
          actionLabel={isActive('link_x') && twitterConnection && !stepDone('link_x') ? 'Confirm' : ''}
          actionTone="accent"
          disabled={linkingX}
          busy={linkingX}
          onAction={() => claimLinkedAccount('x')}
        />

        {#if isActive('link_x') && !stepDone('link_x')}
          <div class="task-panel social-panel">
            <div class="task-panel-copy">
              <p>Link the X account you will use to follow GenLayer and publish your community verification post.</p>
            </div>
            <div class="social-link-frame">
              {#if twitterConnection}
                <button
                  type="button"
                  class="landing-button landing-button-primary"
                  onclick={() => claimLinkedAccount('x')}
                  disabled={linkingX}
                >
                  {linkingX ? 'Confirming...' : 'Confirm X'}
                </button>
              {:else}
                <SocialLink
                  platform="twitter"
                  platformLabel="X"
                  connection={twitterConnection}
                  initiateUrl="/api/auth/twitter/"
                  onLinked={handleXLinked}
                />
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('link_discord')}>
        <JourneyStepRow
          number={2}
          title="Link Discord"
          contributionLabel={isActive('link_discord') ? 'Up next' : ''}
          detail={stepDone('link_discord') ? discordConnection?.platform_username || 'Discord account confirmed' : 'Connect Discord to verify server membership'}
          points={stepPoints('link_discord')}
          pointsLabel="CP"
          status={statusFor('link_discord')}
          actionLabel={isActive('link_discord') && discordConnection && !stepDone('link_discord') ? 'Confirm' : ''}
          actionTone="accent"
          disabled={linkingDiscord}
          busy={linkingDiscord}
          onAction={() => claimLinkedAccount('discord')}
        />

        {#if isActive('link_discord') && !stepDone('link_discord')}
          <div class="task-panel social-panel">
            <div class="task-panel-copy">
              <p>Link the Discord account you will use in the GenLayer community server.</p>
            </div>
            <div class="social-link-frame">
              {#if discordConnection}
                <button
                  type="button"
                  class="landing-button landing-button-primary"
                  onclick={() => claimLinkedAccount('discord')}
                  disabled={linkingDiscord}
                >
                  {linkingDiscord ? 'Confirming...' : 'Confirm Discord'}
                </button>
              {:else}
                <SocialLink
                  platform="discord"
                  platformLabel="Discord"
                  connection={discordConnection}
                  initiateUrl="/api/auth/discord/"
                  onLinked={handleDiscordLinked}
                />
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('follow_x')}>
        <JourneyStepRow
          number={3}
          title="Follow @genlayer"
          contributionLabel={isActive('follow_x') ? 'Up next' : ''}
          detail={stepDone('follow_x') ? '@genlayer follow verified' : 'Follow GenLayer on X'}
          points={stepPoints('follow_x') ?? followTask?.points}
          pointsLabel="CP"
          status={statusFor('follow_x')}
        />

        {#if isActive('follow_x') && !stepDone('follow_x')}
          <div class="task-panel task-card-panel">
            <div class="task-panel-copy">
              <p>Follow @genlayer with your linked X account, then verify the task.</p>
            </div>
            <div class="task-card-frame">
              {#if followTask}
                <SocialTaskCard task={followTask} pointsLabel="CP" onCompleted={handleTaskCompleted} />
              {:else}
                <button type="button" class="landing-button landing-button-secondary" onclick={() => loadJourney({ showLoading: false })}>
                  Reload task
                </button>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('join_discord')}>
        <JourneyStepRow
          number={4}
          title="Join Discord"
          contributionLabel={isActive('join_discord') ? 'Up next' : ''}
          detail={stepDone('join_discord') ? 'GenLayer Discord membership verified' : 'Join the GenLayer Discord'}
          points={stepPoints('join_discord') ?? discordTask?.points}
          pointsLabel="CP"
          status={statusFor('join_discord')}
        />

        {#if isActive('join_discord') && !stepDone('join_discord')}
          <div class="task-panel task-card-panel">
            <div class="task-panel-copy">
              <p>Join the GenLayer Discord with your linked Discord account, then verify the task.</p>
            </div>
            <div class="task-card-frame">
              {#if discordTask}
                <SocialTaskCard task={discordTask} pointsLabel="CP" onCompleted={handleTaskCompleted} />
              {:else}
                <button type="button" class="landing-button landing-button-secondary" onclick={() => loadJourney({ showLoading: false })}>
                  Reload task
                </button>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('x_post')}>
        <JourneyStepRow
          number={5}
          title="Choose a community post"
          contributionLabel={isActive('x_post') ? 'Up next' : ''}
          detail={stepDone('x_post') ? 'X post verified' : xPost.verification_code ? `Referral code ${xPost.verification_code}` : 'Share your referral code'}
          status={statusFor('x_post')}
        />

        {#if isActive('x_post') && !stepDone('x_post')}
          <div class="x-post-panel">
            <div class="x-post-copy">
              <p>Choose one post, publish it from your linked X account, then paste the public post URL to verify it.</p>
              <div class="post-option-list" role="list" aria-label="Community post options">
                {#each postOptions as option, index (option.id || option.text || index)}
                  <button
                    type="button"
                    class="post-option"
                    class:post-option-selected={index === selectedPostIndex}
                    onclick={() => selectedPostIndex = index}
                    aria-pressed={index === selectedPostIndex}
                    disabled={!option.text}
                  >
                    <span class="post-option-index">{index + 1}</span>
                    <span class="post-option-text">{option.text || 'Loading your post option...'}</span>
                  </button>
                {/each}
              </div>
              <div class="x-post-actions">
                <button
                  type="button"
                  class="landing-button landing-button-secondary"
                  onclick={copyShareText}
                  disabled={!selectedShareText}
                >
                  Copy
                </button>
                <a
                  class="landing-button landing-button-secondary"
                  href={selectedIntentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onclick={() => trackEvent('community_post_intent_click', getAnalyticsContext({
                    role_context: 'community',
                    selected_role: 'community',
                    surface: 'journey',
                    step_id: 'x_post',
                    verification_mode: 'sorsa_tweet_info',
                    post_option: selectedPost?.id || 'default',
                  }))}
                >
                  Post on X
                </a>
              </div>
            </div>

            <div class="verify-card">
              <label for="communityPostUrl">X post URL</label>
              <input
                id="communityPostUrl"
                type="url"
                bind:value={postUrl}
                placeholder="https://x.com/yourhandle/status/..."
              />
              <button
                type="button"
                class="landing-button landing-button-primary"
                onclick={verifyPost}
                disabled={verifyingPost}
              >
                {verifyingPost ? 'Verifying...' : 'Verify post'}
              </button>
            </div>
          </div>
        {/if}
      </div>

        {#if complete}
          <div class="completion-panel">
            <div>
              <p>Creator journey complete</p>
              <span>Click to finish.</span>
            </div>
          </div>
        {/if}
      {/if}
    </section>
  {/if}

  <section class="unlock-section" aria-labelledby="community-unlocks-title">
    <div class="section-label">
      <p id="community-unlocks-title">What you will unlock</p>
      <span></span>
    </div>
    <div class="unlock-grid">
      {#each unlocks as item}
        <JourneyUnlockCard {...item} />
      {/each}
    </div>
  </section>
</div>

<style>
  .journey-page {
    --role-accent: #8d81e1;
    --role-accent-hover: #7669d4;
    --journey-active-bg: #f6f3ff;
    --journey-black: #131214;
    --journey-border: #ededed;
    --journey-muted: #909090;
    --journey-hero-bg: linear-gradient(163deg, #fff 40%, #f7f5ff 96%);
    --journey-hero-border: #e6e0ff;
    --journey-hero-glow: rgba(141, 129, 225, 0.18);
    --journey-points-bg: #f1efff;
    --journey-complete-gradient: linear-gradient(135deg, #fff 0%, #f7f5ff 52%, #e8e3ff 100%);
    --journey-complete-border: #ddd6ff;
    --journey-complete-color: #7669d4;
    --journey-complete-shadow: rgba(141, 129, 225, 0.14);
    box-sizing: border-box;
    color: #000;
    display: flex;
    flex-direction: column;
    gap: 24px;
    margin: 0 auto;
    max-width: 1120px;
    min-height: calc(100vh - 81px);
    min-height: calc(100dvh - 81px);
    min-width: 0;
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

  .journey-load-error {
    align-items: flex-start;
    background: #fff;
    border: 1px solid var(--journey-border);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 220px;
    justify-content: center;
    padding: 28px;
  }

  .journey-load-error h1 {
    color: var(--journey-black);
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 30px;
    margin: 0;
  }

  .journey-load-error p {
    color: #666;
    font-size: 14px;
    line-height: 22px;
    margin: 0 0 4px;
    max-width: 620px;
  }

  .step-block {
    width: 100%;
  }

  .task-panel {
    background: linear-gradient(90deg, var(--journey-active-bg) 0%, #fff 82%);
    border-top: 1px solid #f0f0f0;
    display: grid;
    gap: 16px;
    grid-template-columns: minmax(0, 1fr) minmax(240px, 380px);
    padding: 16px 18px 18px 58px;
  }

  .task-panel-copy p,
  .x-post-copy p {
    color: #737373;
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 22px;
    margin: 0;
    max-width: 430px;
  }

  .social-link-frame :global(.social-connect-btn),
  .social-link-frame :global(.social-connected-row) {
    border-radius: 20px;
    font-family: var(--font-body);
    min-height: 40px;
  }

  .social-link-frame :global(.social-connect-btn) {
    background: var(--journey-black) !important;
  }

  .social-link-frame :global(.social-connect-btn:hover:not(:disabled)) {
    background: #2a292c !important;
  }

  .task-card-frame,
  .social-link-frame {
    min-width: 0;
  }

  .x-post-panel {
    background: linear-gradient(90deg, var(--journey-active-bg) 0%, #fff 82%);
    border-top: 1px solid #f0f0f0;
    display: grid;
    gap: 18px;
    grid-template-columns: minmax(0, 1fr) minmax(240px, 360px);
    padding: 16px 18px 18px 58px;
  }

  .x-post-copy {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-width: 0;
  }

  .post-option-list {
    display: grid;
    gap: 8px;
  }

  .post-option {
    align-items: flex-start;
    background: #fff;
    border: 1px solid #e8e4fb;
    border-radius: 10px;
    color: var(--journey-black);
    display: grid;
    gap: 10px;
    grid-template-columns: 24px minmax(0, 1fr);
    min-height: 74px;
    padding: 12px;
    text-align: left;
    transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    width: 100%;
  }

  .post-option:hover:not(:disabled),
  .post-option-selected {
    border-color: var(--role-accent);
    box-shadow: 0 8px 18px rgba(141, 129, 225, 0.12);
  }

  .post-option:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  .post-option:disabled {
    cursor: default;
    opacity: 0.58;
  }

  .post-option-index {
    align-items: center;
    background: var(--journey-active-bg);
    border-radius: 8px;
    color: var(--role-accent);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    height: 24px;
    justify-content: center;
    line-height: 17px;
    width: 24px;
  }

  .post-option-selected .post-option-index {
    background: var(--role-accent);
    color: #fff;
  }

  .post-option-text {
    color: var(--journey-black);
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 22px;
    overflow-wrap: anywhere;
  }

  .x-post-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .verify-card {
    background: #fff;
    border: 1px solid #e8e4fb;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }

  .verify-card label {
    color: #737373;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 1px;
    line-height: 17px;
    text-transform: uppercase;
  }

  .verify-card input {
    border: 1px solid #e6e6e6;
    border-radius: 8px;
    color: var(--journey-black);
    font-family: var(--font-body);
    font-size: 14px;
    height: 40px;
    outline: none;
    padding: 0 12px;
    transition: border-color 160ms ease, box-shadow 160ms ease;
    width: 100%;
  }

  .verify-card input:focus {
    border-color: var(--role-accent);
    box-shadow: 0 0 0 3px rgba(141, 129, 225, 0.14);
  }

  .completion-panel {
    background: var(--journey-complete-gradient);
    border-top: 1px solid var(--journey-complete-border);
    padding: 18px;
  }

  .completion-panel p {
    color: var(--journey-black);
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 500;
    line-height: 24px;
    margin: 0;
  }

  .completion-panel span {
    color: #737373;
    display: block;
    font-family: var(--font-body);
    font-size: 13px;
    line-height: 20px;
    margin-top: 2px;
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
    max-width: 100%;
    padding: 0 16px;
    transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, opacity 160ms ease;
    white-space: nowrap;
  }

  .landing-button:disabled {
    cursor: default;
    opacity: 0.62;
  }

  .landing-button-primary {
    background: var(--journey-black);
    color: #fff;
  }

  .landing-button-primary:hover:not(:disabled) {
    background: #2a292c;
  }

  .landing-button-secondary {
    border: 1px solid var(--journey-black);
    color: var(--journey-black);
  }

  .landing-button-secondary:hover:not(:disabled) {
    background: #f5f5f5;
  }

  .unlock-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-top: 16px;
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
    letter-spacing: 1.54px !important;
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

  .unlock-grid {
    display: grid;
    gap: 20px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  @media (max-width: 1180px) {
    .journey-page {
      max-width: 100%;
    }
  }

  @media (max-width: 900px) {
    .task-panel,
    .x-post-panel {
      grid-template-columns: 1fr;
      padding-left: 18px;
    }

    .unlock-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .journey-page {
      gap: 20px;
      padding: 12px 4px 56px;
    }

    .task-panel,
    .x-post-panel {
      padding: 14px;
    }

    .task-panel-copy p,
    .x-post-copy p {
      max-width: none;
    }

    .task-card-frame,
    .social-link-frame {
      width: 100%;
    }

    .x-post-actions,
    .verify-card .landing-button {
      width: 100%;
    }

    .x-post-actions .landing-button {
      flex: 1 1 140px;
    }

    .section-label {
      padding: 0 2px;
    }
  }
</style>
