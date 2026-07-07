<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';
  import { socialTasksAPI, journeyAPI } from '../lib/api.js';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { showError, showSuccess, showWarning } from '../lib/toastStore.js';
  import { m } from '../lib/paraglide/messages.js';
  import { STAR_BOILERPLATE_TASK_SLUG } from '../lib/roleState.js';
  import { FAUCET_URL } from '../lib/config.js';
  import { getValidatorBalance } from '../lib/blockchain.js';
  import {
    getAnalyticsContext,
    getFunnelDurationMs,
    getLifecycleDurations,
    markLifecycleTime,
    markFunnelTime,
    setConnectWalletIntent,
    trackEvent,
  } from '../lib/analytics.js';
  import SocialLink from '../components/SocialLink.svelte';
  import SocialTaskCard from '../components/social-tasks/SocialTaskCard.svelte';
  import JourneyWelcome from '../components/funnel/journeys/JourneyWelcome.svelte';
  import JourneyHeroCard from '../components/funnel/journeys/JourneyHeroCard.svelte';
  import JourneyStepRow from '../components/funnel/journeys/JourneyStepRow.svelte';
  import JourneyUnlockCard from '../components/funnel/journeys/JourneyUnlockCard.svelte';

  const TOTAL_STEPS = 6;
  const POINTS_PER_GITHUB_STEP = 25;
  const STUDIO_URL = 'https://studio.genlayer.com';
  const REQUIRED_STEP_IDS = ['wallet', 'github', 'star'];
  const VERIFICATION_MODES = {
    wallet: 'wallet_session',
    github: 'oauth_github',
    star: 'social_task',
    networks: 'wallet_client',
    topup: 'client_balance',
    deploy: 'backend_deployment_status',
  };

  const BRADBURY_NETWORK = {
    chainId: '0x107D',
    chainName: 'GenLayer Bradbury',
    nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
    rpcUrls: ['https://rpc-bradbury.genlayer.com'],
    blockExplorerUrls: ['https://explorer-bradbury.genlayer.com'],
  };

  const ASIMOV_NETWORK = {
    chainId: '0x107D',
    chainName: 'GenLayer Asimov',
    nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
    rpcUrls: ['https://rpc-asimov.genlayer.com'],
    blockExplorerUrls: ['https://explorer-asimov.genlayer.com'],
  };

  const STUDIO_NETWORK = {
    chainId: '0xF22F',
    chainName: 'GenLayer Studio',
    nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
    rpcUrls: ['https://studio.genlayer.com/api'],
    blockExplorerUrls: [],
  };

  const NETWORKS = [
    { kind: 'bradbury', label: 'Bradbury', detail: m.bj_network_detail_bradbury(), config: BRADBURY_NETWORK },
    { kind: 'asimov', label: 'Asimov', detail: m.bj_network_detail_asimov(), config: ASIMOV_NETWORK },
    { kind: 'studio', label: 'Studio', detail: m.bj_network_detail_studio(), config: STUDIO_NETWORK },
  ];

  let tasks = $state([]);
  let loading = $state(true);
  let completing = $state(false);
  let loadError = $state('');
  let hasBradburyNetwork = $state(false);
  let hasAsimovNetwork = $state(false);
  let hasStudioNetwork = $state(false);
  let isCheckingNetworks = $state(false);
  let isAddingBradbury = $state(false);
  let isAddingAsimov = $state(false);
  let isAddingStudio = $state(false);
  let isAddingAllNetworks = $state(false);
  let claimingGithub = $state(false);
  let testnetBalance = $state(null);
  let balanceLoading = $state(false);
  let balanceError = $state('');
  let hasDeployedContract = $state(false);
  let deploymentLoading = $state(false);
  let deploymentError = $state('');
  let lastJourneyViewKey = $state('');
  let lastStepViewKey = $state('');
  let lastJourneyExitKey = $state('');

  let user = $derived($userStore.user);
  let address = $derived($authState.address);
  let provider = $derived($authState.provider);

  let starTask = $derived(tasks.find((t) => t.slug === STAR_BOILERPLATE_TASK_SLUG) || null);
  let starred = $derived(starTask?.status === 'completed');
  let githubConnection = $derived(user?.github_connection || null);
  let githubRewarded = $derived(Boolean(user?.has_community_link_github));
  let githubStepDone = $derived(Boolean(githubConnection && githubRewarded));
  let githubHandle = $derived(githubConnection?.platform_username ? `@${githubConnection.platform_username}` : '');
  let walletDetail = $derived(address ? `${address.slice(0, 6)}...${address.slice(-4)}` : m.bj_wallet_detail_connect());
  let hasTestnetBalance = $derived(isPositiveBalance(testnetBalance));
  let networkItems = $derived(
    NETWORKS.map((network) => ({
      ...network,
      done: networkDone(network.kind),
      busy: networkBusy(network.kind),
    }))
  );
  let addedNetworkCount = $derived(networkItems.filter((network) => network.done).length);
  let allNetworksAdded = $derived(addedNetworkCount === NETWORKS.length);
  let networkDetail = $derived(
    allNetworksAdded ? m.bj_networks_all_added() : m.bj_networks_added({ added: addedNetworkCount, total: NETWORKS.length })
  );
  let balanceDetail = $derived(
    hasTestnetBalance
      ? m.bj_gen_available({ amount: testnetBalance.formatted })
      : balanceError || m.bj_topup_detail_get_tokens()
  );

  let stepStates = $derived([
    { id: 'wallet', title: m.bj_step_wallet_title(), done: Boolean(address) },
    { id: 'github', title: m.bj_step_github_title(), done: githubStepDone },
    { id: 'star', title: m.bj_step_star_title(), done: starred },
    { id: 'networks', title: m.bj_step_networks_title(), done: allNetworksAdded },
    { id: 'topup', title: m.bj_step_topup_title(), done: hasTestnetBalance },
    { id: 'deploy', title: m.bj_step_deploy_title(), done: hasDeployedContract },
  ]);

  let activeStep = $derived(stepStates.find((step) => !step.done) || null);
  let activeStepId = $derived(activeStep?.id || 'done');
  let completedSteps = $derived(stepStates.filter((step) => step.done).length);
  let remainingSteps = $derived(Math.max(0, TOTAL_STEPS - completedSteps));
  // Only connecting GitHub and starring the boilerplate gate the Builder role:
  // this mirrors the backend (complete_builder_journey checks the star task,
  // which itself requires the GitHub link). Wallet is implied by being signed
  // in; networks, top-up, and deploy are recommended onboarding, not role gates.
  let requiredStepsComplete = $derived(
    stepStates.filter((step) => REQUIRED_STEP_IDS.includes(step.id)).every((step) => step.done)
  );
  let recommendedStepsComplete = $derived(
    stepStates.filter((step) => !REQUIRED_STEP_IDS.includes(step.id) && step.done).length
  );
  let displayName = $derived(user?.name?.trim() || '');
  let welcomeTitle = $derived(displayName ? m.common_welcome_name({ name: displayName }) : m.bj_welcome_title_default());
  let welcomeMessage = $derived(
    requiredStepsComplete
      ? m.bj_welcome_message_ready()
      : m.bj_welcome_message_start()
  );
  let welcomeAlert = $derived(loadError && activeStepId === 'star' ? loadError : '');
  let welcomeChips = $derived([
    { label: m.bj_chip_progress(), value: `${completedSteps}/${TOTAL_STEPS}` },
    { label: m.bj_chip_left(), value: remainingSteps === 1 ? m.bj_steps_left_one() : m.bj_steps_left_other({ n: remainingSteps }) },
    { label: m.bj_chip_next(), value: activeStep?.title || m.bj_claim_role() },
  ]);
  let heroHelper = $derived(
    requiredStepsComplete
      ? m.bj_hero_helper_ready()
      : m.bj_hero_helper_start()
  );

  const unlocks = [
    {
      title: m.nav_contributions(),
      body: m.bj_unlock_contributions_body(),
      label: m.bj_unlock_contributions_label(),
      icon: 'folder',
    },
    {
      title: m.nav_leaderboard(),
      body: m.bj_unlock_leaderboard_body(),
      label: m.bj_unlock_leaderboard_label(),
      icon: 'leaderboard',
    },
    {
      title: m.nav_resources(),
      body: m.bj_unlock_resources_body(),
      label: m.bj_unlock_resources_label(),
      icon: 'resources',
    },
  ];

  let hydratedAddress = '';

  $effect(() => {
    if (user?.builder) replace('/builders');
  });

  $effect(() => {
    const currentAddress = address || '';
    if (currentAddress === hydratedAddress) return;
    hydratedAddress = currentAddress;
    loadWalletProgress();
    if (currentAddress) {
      checkNetworks();
      refreshBalance();
      refreshDeploymentStatus();
    } else {
      testnetBalance = null;
      hasBradburyNetwork = false;
      hasAsimovNetwork = false;
      hasStudioNetwork = false;
      hasDeployedContract = false;
    }
  });

  $effect(() => {
    persistCurrentStep();
  });

  $effect(() => {
    if (loading) return;
    const viewKey = `builder:${completedSteps}:${requiredStepsComplete}`;
    if (viewKey === lastJourneyViewKey) return;
    lastJourneyViewKey = viewKey;
    trackEvent('journey_view', getAnalyticsContext({
      role_context: 'builder',
      selected_role: 'builder',
      role_funnel_state: user?.builder ? 'earned' : 'started',
      journey_state: user?.builder ? 'earned' : (requiredStepsComplete ? 'completed' : 'started'),
      surface: 'journey',
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
    }));
  });

  $effect(() => {
    if (loading || !activeStepId || activeStepId === 'done') return;
    const viewKey = `builder:${activeStepId}`;
    if (viewKey === lastStepViewKey) return;
    lastStepViewKey = viewKey;
    markFunnelTime(`journey_step_visible:builder:${activeStepId}`);
    trackBuilderStepEvent('journey_step_view', activeStepId);
  });

  onMount(() => {
    markFunnelTime('journey_visible:builder');
    const handlePageHide = () => trackJourneyExit('pagehide');
    window.addEventListener('pagehide', handlePageHide);

    if (!user?.has_builder_welcome && !user?.builder) {
      journeyAPI
        .startBuilderJourney()
        .then((res) => {
          if (res.data?.user) userStore.updateUser(res.data.user);
          else userStore.loadUser?.();
          markFunnelTime('journey_start:builder');
          markLifecycleTime('first_journey_start:builder');
          trackEvent('journey_started', getAnalyticsContext({
            role_context: 'builder',
            selected_role: 'builder',
            surface: 'journey',
            journey_state: 'started',
            time_from_role_landing_ms: getFunnelDurationMs('role_landing:builder'),
            time_from_wallet_click_ms: getFunnelDurationMs('wallet_click'),
            time_from_wallet_auth_success_ms: getFunnelDurationMs('wallet_auth_success'),
            time_from_profile_completion_ms: getFunnelDurationMs('profile_completion'),
          }));
        })
        .catch((err) => {
          trackEvent('journey_start_error', getAnalyticsContext({
            role_context: 'builder',
            selected_role: 'builder',
            surface: 'journey',
            error_stage: err.response?.status ? 'backend' : 'network',
          }));
          showWarning(m.bj_toast_start_error());
        });
    }
    loadTasks({ showLoading: true });
    return () => {
      window.removeEventListener('pagehide', handlePageHide);
      trackJourneyExit('route_leave');
    };
  });

  function isPositiveBalance(result) {
    if (!result) return false;
    try {
      return BigInt(result.balance || 0) > 0n;
    } catch {
      return Number(result.formatted || 0) > 0;
    }
  }

  function getStorageKey(kind) {
    if (!address) return null;
    return `genlayer_${kind}_network_added_${address.toLowerCase()}`;
  }

  function getCurrentStepStorageKey() {
    if (!address) return null;
    return `genlayer_builder_current_step_${address.toLowerCase()}`;
  }

  function loadWalletProgress() {
    if (typeof window === 'undefined' || !address) return;
    const bradburyKey = getStorageKey('bradbury');
    const asimovKey = getStorageKey('asimov');
    const studioKey = getStorageKey('studio');
    hasBradburyNetwork = bradburyKey ? localStorage.getItem(bradburyKey) === 'true' : false;
    hasAsimovNetwork = asimovKey ? localStorage.getItem(asimovKey) === 'true' : false;
    hasStudioNetwork = studioKey ? localStorage.getItem(studioKey) === 'true' : false;
  }

  function persistCurrentStep() {
    if (typeof window === 'undefined' || !address) return;
    const key = getCurrentStepStorageKey();
    if (key) localStorage.setItem(key, activeStepId);
  }

  function markNetworkAdded(kind) {
    if (kind === 'bradbury') hasBradburyNetwork = true;
    if (kind === 'asimov') hasAsimovNetwork = true;
    if (kind === 'studio') hasStudioNetwork = true;
    const key = getStorageKey(kind);
    if (key && typeof window !== 'undefined') localStorage.setItem(key, 'true');
  }

  function statusFor(id) {
    const step = stepStates.find((item) => item.id === id);
    if (step?.done) return 'done';
    if (activeStepId === id) {
      return id === 'star' && loadError ? 'error' : 'active';
    }
    return 'locked';
  }

  function isActive(id) {
    return statusFor(id) === 'active';
  }

  function isLocked(id) {
    return statusFor(id) === 'locked';
  }

  function stepIndex(stepId) {
    return stepStates.findIndex((step) => step.id === stepId) + 1;
  }

  function stepRequired(stepId) {
    return REQUIRED_STEP_IDS.includes(stepId);
  }

  function trackBuilderStepEvent(name, stepId, extra = {}) {
    trackEvent(name, getAnalyticsContext({
      role_context: 'builder',
      selected_role: 'builder',
      surface: 'journey',
      step_id: stepId,
      step_index: stepIndex(stepId),
      step_required: stepRequired(stepId),
      verification_mode: VERIFICATION_MODES[stepId] || 'unknown',
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
      ...extra,
    }));
  }

  function trackJourneyExit(exitReason) {
    if (loading || user?.builder) return;
    const stepId = activeStepId || 'unknown';
    const exitKey = `${stepId}:${completedSteps}:${requiredStepsComplete}`;
    if (exitKey === lastJourneyExitKey) return;
    lastJourneyExitKey = exitKey;
    trackEvent('journey_exit', getAnalyticsContext({
      role_context: 'builder',
      selected_role: 'builder',
      surface: 'journey',
      exit_reason: exitReason,
      step_id: stepId,
      step_index: stepIndex(stepId),
      step_required: stepRequired(stepId),
      journey_state: requiredStepsComplete ? 'claim_ready' : 'started',
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
      required_steps_complete: REQUIRED_STEP_IDS.filter((id) => stepStates.find((step) => step.id === id)?.done).length,
      recommended_steps_complete: recommendedStepsComplete,
      time_on_journey_ms: getFunnelDurationMs('journey_visible:builder'),
      time_on_step_ms: getFunnelDurationMs(`journey_step_visible:builder:${stepId}`),
    }));
  }

  function journeyErrorCode(err) {
    const value = String(err?.response?.data?.error || '').toLowerCase();
    if (['social_account_not_linked', 'token_invalid_relink_required', 'verification_failed', 'verification_unavailable'].includes(value)) {
      return value;
    }
    if (err?.response?.status) return 'backend_error';
    return 'unknown_error';
  }

  function networkDone(kind) {
    if (kind === 'bradbury') return hasBradburyNetwork;
    if (kind === 'asimov') return hasAsimovNetwork;
    if (kind === 'studio') return hasStudioNetwork;
    return false;
  }

  function networkBusy(kind) {
    if (kind === 'bradbury') return isAddingBradbury;
    if (kind === 'asimov') return isAddingAsimov;
    if (kind === 'studio') return isAddingStudio;
    return false;
  }

  function isAlreadyAddedNetworkError(error) {
    const message = `${error?.message || ''} ${error?.data?.message || ''}`.toLowerCase();
    return message.includes('already') && (message.includes('add') || message.includes('exist') || message.includes('known'));
  }

  async function loadTasks({ showLoading = false } = {}) {
    if (showLoading) loading = true;
    loadError = '';
    try {
      const res = await socialTasksAPI.list({ category: 'builder' });
      tasks = Array.isArray(res.data) ? res.data : [];
      if (!tasks.some((t) => t.slug === STAR_BOILERPLATE_TASK_SLUG)) {
        loadError = m.bj_error_star_task_unavailable();
      }
    } catch {
      if (showLoading) {
        tasks = [];
        loadError = m.bj_error_load_task();
      }
    } finally {
      if (showLoading) loading = false;
    }
  }

  async function checkNetworks() {
    if (typeof window === 'undefined' || !address) return;
    const walletProvider = provider || window.ethereum;
    if (!walletProvider) return;
    isCheckingNetworks = true;
    try {
      const currentChainId = await walletProvider.request({ method: 'eth_chainId' });
      if (currentChainId === BRADBURY_NETWORK.chainId) {
        // Bradbury and Asimov share the GenLayer testnet chain id; wallet APIs
        // do not expose which RPC label the user selected after the fact.
        markNetworkAdded('bradbury');
        markNetworkAdded('asimov');
      }
      if (currentChainId === STUDIO_NETWORK.chainId) markNetworkAdded('studio');
    } catch {
      // Wallet network checks are best-effort; explicit add buttons remain available.
    } finally {
      isCheckingNetworks = false;
    }
  }

  async function addNetwork(network, kind, { silent = false } = {}) {
    if (typeof window === 'undefined') return;
    const walletProvider = provider || window.ethereum;
    if (!walletProvider) {
      showWarning(m.bj_toast_connect_wallet_first());
      return false;
    }

    if (kind === 'bradbury') isAddingBradbury = true;
    if (kind === 'asimov') isAddingAsimov = true;
    if (kind === 'studio') isAddingStudio = true;

    if (!silent) {
      trackBuilderStepEvent('journey_step_action_click', 'networks');
    }

    try {
      await walletProvider.request({
        method: 'wallet_addEthereumChain',
        params: [network],
      });
      markNetworkAdded(kind);
      if (!silent) showSuccess(m.bj_network_added({ network: network.chainName }));
      return true;
    } catch (error) {
      if (isAlreadyAddedNetworkError(error)) {
        markNetworkAdded(kind);
        if (!silent) showSuccess(m.bj_network_already_exists({ network: network.chainName }));
        return true;
      }
      trackBuilderStepEvent('journey_step_error', 'networks', {
        error_code: error?.code === 4001 ? 'user_rejected' : 'wallet_error',
        error_stage: 'wallet_add_chain',
      });
      if (error?.code !== 4001) {
        showError(m.bj_network_add_failed({ network: network.chainName }));
      }
      return false;
    } finally {
      if (kind === 'bradbury') isAddingBradbury = false;
      if (kind === 'asimov') isAddingAsimov = false;
      if (kind === 'studio') isAddingStudio = false;
    }
  }

  async function addMissingNetworks() {
    if (isAddingAllNetworks) return;
    trackBuilderStepEvent('journey_step_action_click', 'networks');
    isAddingAllNetworks = true;
    try {
      for (const network of NETWORKS) {
        if (!networkDone(network.kind)) {
          const added = await addNetwork(network.config, network.kind, { silent: true });
          if (!added) break;
        }
      }
      if (NETWORKS.every((network) => networkDone(network.kind))) {
        trackBuilderStepEvent('journey_step_verified', 'networks');
        showSuccess(m.bj_toast_networks_added());
      }
    } finally {
      isAddingAllNetworks = false;
    }
  }

  async function refreshBalance({ notify = false } = {}) {
    if (!address) return;
    if (notify) trackBuilderStepEvent('journey_step_action_click', 'topup');
    balanceLoading = true;
    balanceError = '';
    try {
      testnetBalance = await getValidatorBalance(address);
      if (notify && isPositiveBalance(testnetBalance)) {
        trackBuilderStepEvent('journey_step_verified', 'topup');
      }
      if (notify && !isPositiveBalance(testnetBalance)) {
        showWarning(m.bj_toast_no_gen_yet());
      }
    } catch {
      balanceError = m.bj_error_balance_unavailable();
      if (notify) {
        trackBuilderStepEvent('journey_step_error', 'topup', {
          error_code: 'verification_unavailable',
          error_stage: 'balance_check',
        });
      }
      if (notify) showError(m.bj_toast_balance_check_failed());
    } finally {
      balanceLoading = false;
    }
  }

  async function refreshDeploymentStatus({ notify = false } = {}) {
    if (notify) trackBuilderStepEvent('journey_step_action_click', 'deploy');
    deploymentLoading = true;
    deploymentError = '';
    try {
      const res = await journeyAPI.deploymentStatus();
      hasDeployedContract = Boolean(res.data?.has_deployments);
      if (notify && hasDeployedContract) {
        trackBuilderStepEvent('journey_step_verified', 'deploy');
      }
      if (notify && !hasDeployedContract) {
        showWarning(m.bj_toast_no_deployment_yet());
      }
    } catch {
      hasDeployedContract = false;
      deploymentError = m.bj_error_deployment_unavailable();
      if (notify) {
        trackBuilderStepEvent('journey_step_error', 'deploy', {
          error_code: 'verification_unavailable',
          error_stage: 'deployment_status',
        });
      }
      if (notify) showError(m.bj_toast_deployment_check_failed());
    } finally {
      deploymentLoading = false;
    }
  }

  async function claimGithubReward() {
    if (claimingGithub || !githubConnection) return;
    trackBuilderStepEvent('journey_step_action_click', 'github');
    claimingGithub = true;
    try {
      const res = await journeyAPI.linkGithubAccount();
      if (res.data?.user) userStore.updateUser(res.data.user);
      else await userStore.loadUser?.();
      trackBuilderStepEvent('journey_step_verified', 'github');
      showSuccess(m.bj_toast_github_linked());
    } catch (err) {
      trackBuilderStepEvent('journey_step_error', 'github', {
        error_code: journeyErrorCode(err),
        error_stage: err.response?.status ? 'backend' : 'network',
      });
      showError(err.response?.data?.error || m.bj_toast_github_claim_failed());
    } finally {
      claimingGithub = false;
    }
  }

  function handleGithubLinked(updatedUser) {
    if (updatedUser) userStore.updateUser(updatedUser);
    else userStore.loadUser?.();
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
    loadTasks({ showLoading: false });
    userStore.loadUser?.();
  }

  function triggerWalletConnect() {
    trackBuilderStepEvent('journey_step_action_click', 'wallet');
    setConnectWalletIntent({
      surface: 'journey',
      cta_id: 'builder_wallet_step',
      selected_role: 'builder',
    });
    document.querySelector('[data-auth-button]')?.click();
  }

  async function completeJourney() {
    if (completing || !requiredStepsComplete || user?.builder) return;
    const claimParams = {
      role_context: 'builder',
      selected_role: 'builder',
      surface: 'journey',
      required_steps_complete: REQUIRED_STEP_IDS.filter((id) => stepStates.find((step) => step.id === id)?.done).length,
      recommended_steps_complete: recommendedStepsComplete,
      completed_step_count: completedSteps,
      total_step_count: TOTAL_STEPS,
      time_from_role_landing_ms: getFunnelDurationMs('role_landing:builder'),
      time_from_journey_start_ms: getFunnelDurationMs('journey_start:builder'),
      ...getLifecycleDurations('builder'),
    };
    trackEvent('builder_role_claim_attempt', getAnalyticsContext(claimParams));
    completing = true;
    try {
      await journeyAPI.completeBuilderJourney();
      await userStore.loadUser();
      markLifecycleTime('role_unlocked:builder');
      trackEvent('builder_role_claim_success', getAnalyticsContext(claimParams));
      trackEvent('journey_completed', getAnalyticsContext({
        ...claimParams,
        journey_state: 'completed',
      }));
      trackEvent('role_unlocked', getAnalyticsContext({
        ...claimParams,
        role_context: 'builder',
        selected_role: 'builder',
        surface: 'journey',
        unlock_source: 'journey',
      }));
      showSuccess(m.bj_toast_role_claimed());
      replace('/builders');
    } catch (err) {
      trackEvent('builder_role_claim_error', getAnalyticsContext({
        ...claimParams,
        error_code: journeyErrorCode(err),
        error_stage: err.response?.status ? 'backend' : 'network',
      }));
      showError(err.response?.data?.error || m.bj_toast_complete_failed());
    } finally {
      completing = false;
    }
  }
</script>

<svelte:head>
  <title>{m.bj_page_title()}</title>
</svelte:head>

<div class="journey-page builder-journey">
  <JourneyWelcome
    role="builder"
    title={welcomeTitle}
    message={welcomeMessage}
    chips={welcomeChips}
    alert={welcomeAlert}
  />

  <JourneyHeroCard
    role="builder"
    iconHex="/assets/icons/hexagon-builder.svg"
    iconGlyph="/assets/icons/terminal-fill-white.svg"
    iconPlacement="title"
    kickerIconHex="/assets/icons/hexagon-builder-light.svg"
    kickerIconGlyph="/assets/icons/terminal-line-orange.svg"
    eyebrow={m.bj_hero_eyebrow()}
    accentValue={TOTAL_STEPS}
    titleRest={m.bj_hero_title_rest()}
    description={m.bj_hero_description()}
    completed={loading ? 0 : completedSteps}
    total={TOTAL_STEPS}
    primaryLabel={completing ? m.bj_claiming() : m.bj_claim_builder_role()}
    primaryDisabled={loading || completing || !requiredStepsComplete}
    primaryBusy={completing}
    helper={heroHelper}
    onPrimary={completeJourney}
  />

  <section class="steps-card" aria-label={m.bj_steps_aria()}>
    {#if loading}
      {#each Array(TOTAL_STEPS) as _, i}
        <JourneyStepRow number={i + 1} loading={true} />
      {/each}
    {:else}
      <div class="step-block" data-step-active={isActive('wallet')}>
        <JourneyStepRow
          number={1}
          title={m.bj_step_wallet_title()}
          detail={walletDetail}
          status={statusFor('wallet')}
          actionLabel={isActive('wallet') ? m.bj_action_connect_wallet() : ''}
          actionTone="accent"
          onAction={triggerWalletConnect}
        />
      </div>

      <div class="step-block" data-step-active={isActive('github')}>
        <JourneyStepRow
          number={2}
          title={m.bj_step_github_title()}
          contributionLabel={isActive('github') ? m.bj_up_next() : ''}
          detail={githubStepDone ? githubHandle : githubConnection ? m.bj_github_connected_claim({ handle: githubHandle }) : m.bj_github_detail_link()}
          points={POINTS_PER_GITHUB_STEP}
          pointsLabel="BP"
          status={statusFor('github')}
          actionLabel={isActive('github') && githubConnection && !githubRewarded ? m.bj_action_claim_points() : ''}
          actionTone="accent"
          disabled={!githubConnection || claimingGithub}
          busy={claimingGithub}
          onAction={claimGithubReward}
        />

        {#if isActive('github') && !githubConnection}
          <div class="task-panel github-panel">
            <div class="task-panel-copy">
              <p>{m.bj_github_panel_copy()}</p>
            </div>
            <div class="social-link-frame">
              <SocialLink
                platform="github"
                platformLabel="GitHub"
                connection={githubConnection}
                initiateUrl="/api/auth/github/"
                onLinked={handleGithubLinked}
              />
            </div>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('star')}>
        <JourneyStepRow
          number={3}
          title={m.bj_step_star_title()}
          contributionLabel={isActive('star') ? m.bj_up_next() : ''}
          detail={starred ? m.bj_repo_verified() : 'genlayerlabs/genlayer-project-boilerplate'}
          points={POINTS_PER_GITHUB_STEP}
          pointsLabel="BP"
          status={statusFor('star')}
        />

        {#if isActive('star') && starTask && !starred}
          <div class="task-panel">
            <div class="task-panel-copy">
              <p>{m.bj_star_panel_copy()}</p>
            </div>
            <div class="task-card-frame">
              <SocialTaskCard task={starTask} pointsLabel="BP" onCompleted={handleTaskCompleted} />
            </div>
          </div>
        {:else if isActive('star') && loadError}
          <div class="task-panel task-panel-error">
            <p>{loadError}</p>
            <button type="button" class="landing-button landing-button-secondary" onclick={loadTasks}>
              {m.bj_reload_task()}
            </button>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('networks')}>
        <JourneyStepRow
          number={4}
          title={m.bj_step_networks_title()}
          contributionLabel={m.bj_recommended()}
          detail={networkDetail}
          status={statusFor('networks')}
          actionLabel={isActive('networks') ? m.bj_add_missing() : ''}
          actionTone="accent"
          disabled={isLocked('networks') || isAddingAllNetworks}
          busy={isAddingAllNetworks}
          onAction={addMissingNetworks}
        />

        {#if isActive('networks')}
          <div class="task-panel networks-panel">
            <div class="task-panel-copy">
              <p>{m.bj_networks_panel_copy()}</p>
            </div>
            <div class="network-list">
              {#each networkItems as network}
                <div class="network-item" class:network-item-done={network.done}>
                  <span class="network-check" aria-hidden="true">
                    {#if network.done}
                      <svg viewBox="0 0 20 20" fill="currentColor">
                        <path
                          fill-rule="evenodd"
                          d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.5 7.59a1 1 0 0 1-1.42.006L3.29 9.79a1 1 0 1 1 1.42-1.408l3.79 3.83 6.79-6.872a1 1 0 0 1 1.414-.06Z"
                          clip-rule="evenodd"
                        />
                      </svg>
                    {:else}
                      <span></span>
                    {/if}
                  </span>
                  <div class="network-copy">
                    <strong>{network.label}</strong>
                    <small>{network.detail}</small>
                  </div>
                  {#if network.done}
                    <em>{m.bj_added()}</em>
                  {:else}
                    <button
                      type="button"
                      class="network-button"
                      onclick={() => addNetwork(network.config, network.kind)}
                      disabled={network.busy || isAddingAllNetworks}
                    >
                      {network.busy ? m.bj_adding() : m.bj_add()}
                    </button>
                  {/if}
                </div>
              {/each}

              <div class="panel-actions network-actions">
                <button
                  type="button"
                  class="landing-button landing-button-secondary check-gradient-button"
                  onclick={checkNetworks}
                  disabled={isCheckingNetworks || isAddingAllNetworks}
                >
                  {isCheckingNetworks ? m.common_checking() : m.bj_sync_wallet()}
                </button>
                <button
                  type="button"
                  class="landing-button landing-button-primary"
                  onclick={addMissingNetworks}
                  disabled={isAddingAllNetworks || allNetworksAdded}
                >
                  {isAddingAllNetworks ? m.bj_adding() : m.bj_add_missing()}
                </button>
              </div>
            </div>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('topup')}>
        <JourneyStepRow
          number={5}
          title={m.bj_step_topup_title()}
          contributionLabel={m.bj_recommended()}
          detail={balanceDetail}
          status={statusFor('topup')}
          actionLabel={isActive('topup') ? m.bj_get_tokens() : ''}
          actionHref={isActive('topup') ? FAUCET_URL : ''}
          actionExternal={true}
          actionTone="accent"
          disabled={isLocked('topup')}
        />

        {#if isActive('topup')}
          <div class="task-panel compact-panel">
            <div class="task-panel-copy">
              <p>{m.bj_topup_panel_copy()}</p>
            </div>
            <div class="panel-actions">
              <button
                type="button"
                class="landing-button landing-button-secondary check-gradient-button"
                onclick={() => refreshBalance({ notify: true })}
                disabled={balanceLoading}
              >
                {balanceLoading ? m.common_checking() : m.bj_check_balance()}
              </button>
            </div>
          </div>
        {/if}
      </div>

      <div class="step-block" data-step-active={isActive('deploy')}>
        <JourneyStepRow
          number={6}
          title={m.bj_step_deploy_title()}
          contributionLabel={m.bj_recommended()}
          detail={hasDeployedContract ? m.bj_deploy_detail_verified() : deploymentError || m.bj_deploy_detail_prompt()}
          status={statusFor('deploy')}
          actionLabel={isActive('deploy') ? m.bj_open_studio() : ''}
          actionHref={isActive('deploy') ? STUDIO_URL : ''}
          actionExternal={true}
          actionTone="accent"
          disabled={isLocked('deploy')}
        />

        {#if isActive('deploy')}
          <div class="task-panel compact-panel">
            <div class="task-panel-copy">
              <p>{m.bj_deploy_panel_copy()}</p>
            </div>
            <div class="panel-actions">
              <button
                type="button"
                class="landing-button landing-button-secondary check-gradient-button"
                onclick={() => refreshDeploymentStatus({ notify: true })}
                disabled={deploymentLoading}
              >
                {deploymentLoading ? m.common_checking() : m.bj_check_deployment()}
              </button>
            </div>
          </div>
        {/if}
      </div>

      {#if requiredStepsComplete}
        <div class="completion-panel">
          <div>
            <p>{m.bj_completion_title()}</p>
            <span>{m.bj_completion_subtitle()}</span>
          </div>
        </div>
      {/if}
    {/if}
  </section>

  <section class="unlock-section" aria-labelledby="builder-unlocks-title">
    <div class="section-label">
      <p id="builder-unlocks-title">{m.bj_unlocks_title()}</p>
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
    --role-accent: #ee8521;
    --role-accent-hover: #d97518;
    --journey-active-bg: #fff7ec;
    --journey-black: #131214;
    --journey-border: #ededed;
    --journey-muted: #909090;
    --journey-hero-bg: linear-gradient(163deg, #fff 40%, #fff7ec 96%);
    --journey-hero-border: #f3e4cb;
    --journey-hero-glow: rgba(238, 133, 33, 0.16);
    --journey-points-bg: #fdf3e6;
    --builder-orange-gradient: linear-gradient(135deg, #fff 0%, #fff7ec 52%, #ffe3bd 100%);
    --builder-orange-gradient-hover: linear-gradient(135deg, #fffaf3 0%, #fff0dc 52%, #ffd7a3 100%);
    --builder-orange-gradient-ink: #c86513;
    --builder-orange-gradient-border: #f1d8b7;
    --journey-complete-gradient: var(--builder-orange-gradient);
    --journey-complete-border: var(--builder-orange-gradient-border);
    --journey-complete-color: var(--builder-orange-gradient-ink);
    --journey-complete-shadow: rgba(238, 133, 33, 0.14);
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

  .compact-panel {
    align-items: center;
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .task-panel-copy p,
  .task-panel-error p {
    color: #737373;
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 22px;
    margin: 0;
    max-width: 430px;
  }

  .task-card-frame,
  .social-link-frame {
    min-width: 0;
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

  .task-panel-error {
    align-items: center;
    display: flex;
    justify-content: space-between;
  }

  .panel-actions {
    align-items: center;
    display: flex;
    gap: 10px;
    justify-content: flex-end;
  }

  .network-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .network-item {
    align-items: center;
    background: #fff;
    border: 1px solid #f0f0f0;
    border-radius: 8px;
    display: grid;
    gap: 10px;
    grid-template-columns: 24px minmax(0, 1fr) auto;
    min-height: 52px;
    padding: 9px 10px;
  }

  .network-item-done {
    background: linear-gradient(90deg, rgba(238, 133, 33, 0.12) 0%, #fff 86%);
    border-color: #f0d7b7;
  }

  .network-check {
    align-items: center;
    border: 1px solid #e6e6e6;
    border-radius: 12px;
    color: var(--role-accent);
    display: inline-flex;
    height: 24px;
    justify-content: center;
    width: 24px;
  }

  .network-item-done .network-check {
    background: var(--builder-orange-gradient);
    border-color: var(--builder-orange-gradient-border);
    box-shadow: 0 7px 15px rgba(238, 133, 33, 0.14);
    color: var(--builder-orange-gradient-ink);
  }

  .network-check svg {
    height: 14px;
    width: 14px;
  }

  .network-check span {
    background: #d6d6d6;
    border-radius: 999px;
    height: 6px;
    width: 6px;
  }

  .network-copy {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .network-copy strong {
    color: var(--journey-black);
    font-family: var(--font-body);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
  }

  .network-copy small {
    color: #737373;
    font-family: var(--font-body);
    font-size: 12px;
    line-height: 17px;
  }

  .network-item em {
    color: var(--role-accent);
    font-family: var(--font-mono);
    font-size: 11px;
    font-style: normal;
    letter-spacing: 1.1px !important;
    text-transform: uppercase;
  }

  .network-button {
    align-items: center;
    background: #fff;
    border: 1px solid var(--journey-black);
    border-radius: 16px;
    color: var(--journey-black);
    display: inline-flex;
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 500;
    height: 32px;
    justify-content: center;
    padding: 0 13px;
    transition: background-color 160ms ease, opacity 160ms ease;
    white-space: nowrap;
  }

  .network-button:hover:not(:disabled) {
    background: #f5f5f5;
  }

  .network-button:disabled {
    cursor: not-allowed;
    opacity: 0.62;
  }

  .network-actions {
    justify-content: flex-end;
    padding-top: 4px;
  }

  .completion-panel {
    align-items: center;
    background: var(--builder-orange-gradient);
    border-top: 1px solid var(--builder-orange-gradient-border);
    display: flex;
    gap: 18px;
    justify-content: space-between;
    overflow: hidden;
    padding: 18px;
    position: relative;
  }

  .completion-panel::before {
    background:
      radial-gradient(circle at 10% 0%, rgba(255, 255, 255, 0.72), transparent 30%),
      radial-gradient(circle at 88% 100%, rgba(238, 133, 33, 0.12), transparent 32%);
    content: '';
    inset: 0;
    pointer-events: none;
    position: absolute;
  }

  .completion-panel > * {
    position: relative;
    z-index: 1;
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

  .landing-button.check-gradient-button {
    background: var(--builder-orange-gradient);
    border-color: var(--builder-orange-gradient-border);
    box-shadow: 0 8px 17px rgba(238, 133, 33, 0.12);
    color: var(--builder-orange-gradient-ink);
  }

  .landing-button.check-gradient-button:hover:not(:disabled) {
    background: var(--builder-orange-gradient-hover);
    color: var(--builder-orange-gradient-ink);
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
    letter-spacing: 0.28px;
    line-height: 21px;
    max-width: 100%;
    padding: 0 16px;
    transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, opacity 160ms ease;
    white-space: nowrap;
  }

  .landing-button:disabled {
    cursor: not-allowed;
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
    .compact-panel {
      grid-template-columns: 1fr;
      padding-left: 18px;
    }

    .panel-actions {
      justify-content: flex-start;
    }

    .completion-panel {
      align-items: flex-start;
      flex-direction: column;
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
    .compact-panel {
      padding: 14px;
    }

    .network-item {
      grid-template-columns: 24px minmax(0, 1fr);
    }

    .network-item em,
    .network-button {
      grid-column: 2;
      justify-self: flex-start;
    }

    .section-label {
      padding: 0 2px;
    }

    .completion-panel {
      padding: 16px 14px;
    }
  }
</style>
