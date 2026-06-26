<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';
  import { journeyAPI, socialTasksAPI } from '../lib/api.js';
  import { userStore } from '../lib/userStore.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import SocialLink from '../components/SocialLink.svelte';
  import SocialTaskCard from '../components/social-tasks/SocialTaskCard.svelte';
  import JourneyNotice from '../components/funnel/journeys/JourneyNotice.svelte';
  import JourneyHeroCard from '../components/funnel/journeys/JourneyHeroCard.svelte';
  import JourneyStepRow from '../components/funnel/journeys/JourneyStepRow.svelte';
  import JourneyUnlockCard from '../components/funnel/journeys/JourneyUnlockCard.svelte';

  const TOTAL_STEPS = 5;
  const FOLLOW_X_TASK_SLUG = 'follow-genlayer-x';
  const JOIN_DISCORD_TASK_SLUG = 'join-genlayer-discord';

  const STEP_IDS = ['link_x', 'link_discord', 'follow_x', 'join_discord', 'x_post'];

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
  let noticeMessage = $derived(
    actionError || loadError || (
      complete
        ? 'Community journey complete. Click to finish.'
        : `There ${remainingSteps === 1 ? 'is' : 'are'} ${remainingSteps} ${remainingSteps === 1 ? 'step' : 'steps'} left to join the community.`
    )
  );
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
    if (!user?.has_community_welcome) {
      journeyAPI
        .startRoleJourney('community')
        .then(() => userStore.loadUser?.())
        .catch(() => {
          showError('Could not start your community journey. Try refreshing in a moment.');
        });
    }
    loadJourney({ showLoading: true });
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

  async function loadJourney({ showLoading = false } = {}) {
    if (showLoading) loading = true;
    loadError = '';
    try {
      const [journeyRes, tasksRes] = await Promise.all([
        journeyAPI.communityJourney(),
        socialTasksAPI.list({ category: 'community' }),
      ]);
      journey = journeyRes.data;
      tasks = Array.isArray(tasksRes.data) ? tasksRes.data : [];
      const existingPostUrl = journeyRes.data?.steps?.x_post?.post_url || '';
      if (existingPostUrl && !postUrl) postUrl = existingPostUrl;
    } catch (err) {
      loadError = err.response?.data?.message || err.response?.data?.error || 'Could not load your community journey.';
      if (showLoading) {
        journey = null;
        tasks = [];
      }
    } finally {
      if (showLoading) loading = false;
    }
  }

  async function claimLinkedAccount(kind) {
    const isX = kind === 'x';
    if ((isX && linkingX) || (!isX && linkingDiscord)) return;
    if (isX) linkingX = true;
    else linkingDiscord = true;
    actionError = '';

    try {
      const res = isX ? await journeyAPI.linkXAccount() : await journeyAPI.linkDiscordAccount();
      if (res.data?.user) userStore.updateUser(res.data.user);
      else await userStore.loadUser?.();
      showSuccess(isX ? 'X account linked for community points.' : 'Discord account linked for community points.');
      await loadJourney({ showLoading: false });
    } catch (err) {
      actionError = err.response?.data?.message || err.response?.data?.error || `Could not confirm your ${isX ? 'X' : 'Discord'} account.`;
      showError(actionError);
    } finally {
      if (isX) linkingX = false;
      else linkingDiscord = false;
    }
  }

  async function handleXLinked() {
    await claimLinkedAccount('x');
  }

  async function handleDiscordLinked() {
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
    const text = xPost.share_text || '';
    if (!text) return;
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
    const trimmedUrl = postUrl.trim();
    if (!trimmedUrl) {
      actionError = 'Paste the URL of your X post first.';
      showError(actionError);
      return;
    }

    verifyingPost = true;
    actionError = '';
    try {
      const res = await journeyAPI.verifyCommunityPost(trimmedUrl);
      if (res.data?.journey) journey = res.data.journey;
      showSuccess('Community post verified.');
      await loadJourney({ showLoading: false });
    } catch (err) {
      actionError = err.response?.data?.message || err.response?.data?.error || 'Could not verify your X post.';
      showError(actionError);
    } finally {
      verifyingPost = false;
    }
  }

  async function completeJourney() {
    if (completing || !complete) return;
    completing = true;
    actionError = '';
    try {
      const res = await journeyAPI.completeCommunityJourney();
      if (res.data?.user) userStore.updateUser(res.data.user);
      await userStore.loadUser?.();
      showSuccess('Welcome to the GenLayer community!');
      replace('/community');
    } catch (err) {
      actionError = err.response?.data?.message || err.response?.data?.error || 'Complete all community journey steps first.';
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
  <JourneyNotice
    message={noticeMessage}
    tone={actionError || loadError ? 'error' : 'default'}
  />

  <JourneyHeroCard
    role="community"
    iconHex="/assets/icons/hexagon-community-light.svg"
    iconGlyph="/assets/icons/group-3-line-purple.svg"
    eyebrow="Your community journey"
    accentValue={TOTAL_STEPS}
    titleRest=" steps to join the community"
    description="Link your social accounts, verify the GenLayer community actions, and share your unique X post before claiming the community role."
    completed={loading ? 0 : completedSteps}
    total={TOTAL_STEPS}
    primaryLabel={completing ? 'Joining...' : 'Join the community'}
    primaryDisabled={loading || completing || !complete}
    primaryBusy={completing}
    helper={heroHelper}
    onPrimary={completeJourney}
  />

  <section class="steps-card" aria-label="Community journey steps">
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
          status={statusFor('follow_x')}
        />

        {#if isActive('follow_x') && !stepDone('follow_x')}
          <div class="task-panel task-card-panel">
            <div class="task-panel-copy">
              <p>Follow @genlayer with your linked X account, then verify the task.</p>
            </div>
            <div class="task-card-frame">
              {#if followTask}
                <SocialTaskCard task={followTask} onCompleted={handleTaskCompleted} />
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
          status={statusFor('join_discord')}
        />

        {#if isActive('join_discord') && !stepDone('join_discord')}
          <div class="task-panel task-card-panel">
            <div class="task-panel-copy">
              <p>Join the GenLayer Discord with your linked Discord account, then verify the task.</p>
            </div>
            <div class="task-card-frame">
              {#if discordTask}
                <SocialTaskCard task={discordTask} onCompleted={handleTaskCompleted} />
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
          title="Post your community code"
          contributionLabel={isActive('x_post') ? 'Up next' : ''}
          detail={stepDone('x_post') ? 'X post verified' : xPost.verification_code || 'Share your unique verification code'}
          status={statusFor('x_post')}
        />

        {#if isActive('x_post') && !stepDone('x_post')}
          <div class="x-post-panel">
            <div class="x-post-copy">
              <p>Copy the generated post, publish it from your linked X account, then paste the public post URL to verify it.</p>
              <div class="share-box">
                <span>{xPost.share_text || 'Loading your verification post...'}</span>
                <button type="button" onclick={copyShareText} disabled={!xPost.share_text}>Copy</button>
              </div>
              <div class="x-post-actions">
                <a
                  class="landing-button landing-button-secondary"
                  href={xPost.intent_url || 'https://x.com/intent/post'}
                  target="_blank"
                  rel="noopener noreferrer"
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
            <p>Community journey complete</p>
            <span>Click to finish.</span>
          </div>
        </div>
      {/if}
    {/if}
  </section>

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

  .task-panel {
    background: linear-gradient(90deg, var(--journey-active-bg) 0%, #fff 82%);
    border-top: 1px solid #f0f0f0;
    display: grid;
    gap: 16px;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
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
    grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
    padding: 16px 18px 18px 58px;
  }

  .x-post-copy {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-width: 0;
  }

  .share-box {
    background: #fff;
    border: 1px solid #e8e4fb;
    border-radius: 10px;
    display: grid;
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 12px;
  }

  .share-box span {
    color: var(--journey-black);
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 22px;
    overflow-wrap: anywhere;
  }

  .share-box button {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .share-box button:disabled {
    opacity: 0.45;
  }

  .x-post-actions {
    display: flex;
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
      max-width: 920px;
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
      padding: 12px 0 56px;
    }

    .task-panel,
    .x-post-panel {
      padding: 14px;
    }

    .share-box {
      grid-template-columns: 1fr;
    }

    .section-label {
      padding: 0 2px;
    }
  }
</style>
