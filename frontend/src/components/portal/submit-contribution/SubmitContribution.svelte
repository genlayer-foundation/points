<script>
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import api from "../../../lib/api.js";
  import { contributionsAPI, submissionsAPI } from "../../../lib/api.js";
  import { getMissions } from "../../../lib/missionsStore.js";
  import { authState } from "../../../lib/auth.js";
  import { submissionErrorMessage } from "../../../lib/submissionErrors.js";
  import { userStore } from "../../../lib/userStore";
  import { isProjectContributionType } from "../../../lib/contributionGuidelines.js";
  import ConfirmDialog from "../../ConfirmDialog.svelte";
  import ContributionGuidelines from "../ContributionGuidelines.svelte";
  import { parseMarkdown } from "../../../lib/markdownLoader.js";
  import {
    getAnalyticsContext,
    getLifecycleDurationMs,
    getLifecycleDurations,
    markLifecycleTime,
    trackEvent,
  } from "../../../lib/analytics.js";

  // Passing a submission turns this into the canonical edit form so create
  // and edit share category, evidence, mission, and validation behavior.
  let {
    missionId = null,
    initialTypeId = null,
    submission = null,
    resubmitSource = null,
  } = $props();

  let submitting = $state(false);
  let deleting = $state(false);
  let showDeleteDialog = $state(false);
  let error = $state("");

  let isValidator = $derived(!!$userStore.user?.validator);
  let isBuilder = $derived(!!$userStore.user?.builder);
  let isCreator = $derived(!!$userStore.user?.creator);
  let editMode = $derived(Boolean(submission?.id));
  let resubmitMode = $derived(!editMode && Boolean(resubmitSource?.id));
  let cloneContextWarning = $state("");

  // reCAPTCHA state
  let recaptchaToken = $state("");
  let recaptchaWidgetId = $state(null);
  const RECAPTCHA_SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY;

  // Selection & Types
  let types = $state([]);
  let missions = $state([]);
  let loadingTypes = $state(true);
  let selectedCategory = $state("builder");
  let hasCurrentCategoryRole = $derived.by(() => {
    if (selectedCategory === "validator") return isValidator;
    if (selectedCategory === "builder") return isBuilder;
    if (selectedCategory === "community") return isCreator;
    return true;
  });

  let journeysHref = $derived(
    $userStore.user?.address
      ? `/participant/${$userStore.user.address}`
      : "/",
  );

  let gatingTheme = $derived.by(() => {
    if (selectedCategory === "validator") {
      return {
        bg: "bg-blue-50",
        border: "border-blue-200",
        icon: "text-blue-500",
        title: "text-blue-900",
        body: "text-blue-800",
        link: "text-blue-700 hover:text-blue-900",
      };
    }
    if (selectedCategory === "builder") {
      return {
        bg: "bg-orange-50",
        border: "border-orange-200",
        icon: "text-orange-500",
        title: "text-orange-900",
        body: "text-orange-800",
        link: "text-orange-700 hover:text-orange-900",
      };
    }
    return {
      bg: "bg-purple-50",
      border: "border-purple-200",
      icon: "text-purple-500",
      title: "text-purple-900",
      body: "text-purple-800",
      link: "text-purple-700 hover:text-purple-900",
    };
  });
  let selectedType = $state(null);
  let originalContributionTypeId = $derived(
    submission?.contribution_type ?? null,
  );
  let resubmitSourceProjectId = $derived(
    resubmitSource?.project_contribution?.id ??
      resubmitSource?.project_contribution ??
      "",
  );
  let keepsOriginalContributionType = $derived(
    editMode &&
    selectedType &&
    String(selectedType.id) === String(originalContributionTypeId),
  );
  let hasLegacyCommunityEditAccess = $derived(
    editMode &&
    submission?.state !== "more_info_needed" &&
    submission?.contribution_type_details?.category === "community",
  );
  let canAccessCurrentCategory = $derived(
    hasCurrentCategoryRole ||
    (
      selectedCategory === "community" &&
      hasLegacyCommunityEditAccess
    ),
  );
  // The API intentionally lets a pre-Creator Community submission keep its
  // existing type. Other category changes still require the live role.
  let canSubmitCurrentCategory = $derived(
    hasCurrentCategoryRole ||
    (
      keepsOriginalContributionType &&
      selectedCategory === "community" &&
      hasLegacyCommunityEditAccess
    ),
  );
  let selectedMission = $state(null);
  let selectedMissionData = $state(null);
  let missionLocked = $derived(editMode && Boolean(selectedMission));
  let appealLocked = $derived(
    editMode && submission?.has_appeal && submission?.state === "pending",
  );
  let selectionLocked = $derived(missionLocked || appealLocked);
  let latestMoreInfoRequest = $derived(
    submission?.more_info_requests?.find(
      (/** @type {Record<string, any>} */ request) => !request?.response,
    ) ||
      submission?.more_info_requests?.[0] ||
      null,
  );
  let reviewFeedback = $derived(
    latestMoreInfoRequest?.message || submission?.staff_reply || "",
  );
  let requiresMoreInfoResponse = $derived(
    editMode && submission?.state === "more_info_needed",
  );
  let acceptedProjects = $state([]);
  let loadingProjects = $state(false);
  let projectsError = $state(false);
  let selectedProject = $state("");
  let showProjectDropdown = $state(false);
  let focusedProjectIndex = $state(-1);
  let showTypeDropdown = $state(false);
  let searchQuery = $state("");

  // Form Data
  let formData = $state({
    contribution_type: "",
    contribution_date: new Date().toISOString().split("T")[0],
    title: "",
    notes: "",
  });
  let moreInfoResponse = $state("");

  // Evidence Slots
  let evidenceSlots = $state([]);
  // Dedicated required-evidence slot (shown when the selected contribution
  // type declares required_evidence_url_types). Tracked separately so its
  // position and styling are distinct from optional extras.
  let requiredEvidenceSlot = $state(emptyEvidenceSlot());
  // All evidence URL types loaded from any contribution type's accepted list
  let allEvidenceUrlTypes = $state([]);
  let recaptchaRetryTimeout = null;

  function emptyEvidenceSlot() {
    return {
      description: "",
      url: "",
      selectedType: null,
      typeManuallySet: false,
      error: "",
    };
  }

  function collectEvidenceUrlTypes(contributionTypes) {
    const urlTypeMap = new Map();
    for (const contributionType of contributionTypes) {
      for (const urlType of contributionType.accepted_evidence_url_types || []) {
        if (!urlTypeMap.has(urlType.slug)) {
          urlTypeMap.set(urlType.slug, urlType);
        }
      }
    }
    return Array.from(urlTypeMap.values()).sort(
      (first, second) => (first.order || 0) - (second.order || 0),
    );
  }

  function evidenceSlotFromItem(item) {
    const declaredType = item?.url_type
      ? allEvidenceUrlTypes.find(
          (type) =>
            String(type.id) === String(item.url_type.id) ||
            type.slug === item.url_type.slug,
        )
      : null;
    return {
      ...(item?.id ? { id: item.id } : {}),
      description: item?.description || "",
      url: item?.url || "",
      selectedType: declaredType || detectUrlType(item?.url || ""),
      typeManuallySet: false,
      error: "",
    };
  }

  /** @param {Array<Record<string, any>> | null | undefined} items */
  function evidenceItemsWithoutIds(items) {
    return (items || []).map((/** @type {Record<string, any>} */ item) => ({
      description: item?.description || "",
      url: item?.url || "",
      url_type: item?.url_type || null,
    }));
  }

  function evidenceMatchesRequiredType(slot, contributionType) {
    const requiredTypes = contributionType?.required_evidence_url_types || [];
    if (!slot?.selectedType || requiredTypes.length === 0) return false;
    return requiredTypes.some(
      (requiredType) =>
        String(requiredType.id) === String(slot.selectedType.id) ||
        requiredType.slug === slot.selectedType.slug,
    );
  }

  function partitionEvidenceForType(contributionType, sourceItems = null) {
    const slots = sourceItems
      ? sourceItems.map(evidenceSlotFromItem)
      : [
          ...(requiredEvidenceSlot.id || requiredEvidenceSlot.url
            ? [{ ...requiredEvidenceSlot }]
            : []),
          ...evidenceSlots.map((slot) => ({ ...slot })),
        ].map((slot) => ({
          ...slot,
          selectedType: detectUrlType(slot.url) || slot.selectedType || null,
          typeManuallySet: false,
          error: "",
        }));

    const requiredIndex = slots.findIndex((slot) =>
      evidenceMatchesRequiredType(slot, contributionType),
    );
    if (
      contributionType?.required_evidence_url_types?.length &&
      requiredIndex >= 0
    ) {
      requiredEvidenceSlot = slots[requiredIndex];
      evidenceSlots = slots.filter((_, index) => index !== requiredIndex);
    } else {
      requiredEvidenceSlot = emptyEvidenceSlot();
      evidenceSlots = slots;
    }
  }

  // Load types and missions
  onMount(() => {
    let disposed = false;

    async function initializeForm() {
      if (editMode || resubmitMode) {
        const source = editMode ? submission : resubmitSource;
        selectedCategory =
          source.contribution_type_details?.category || "builder";
        selectedMission =
          source.mission?.id ?? source.mission ?? null;
        selectedProject =
          source.project_contribution?.id ??
          source.project_contribution ??
          "";
        searchQuery =
          source.contribution_type_name ||
          source.contribution_type_details?.name ||
          "";
        formData = {
          contribution_type: source.contribution_type || "",
          contribution_date:
            source.contribution_date?.split("T")[0] ||
            new Date().toISOString().split("T")[0],
          title: source.title || "",
          notes: source.notes || "",
        };
      }

      try {
        loadingTypes = true;
        const typesResponse = await contributionsAPI.getAllContributionTypes();
        const allTypes = typesResponse.data || [];

        types = allTypes;

        // Collect all unique evidence URL types from contribution types.
        allEvidenceUrlTypes = collectEvidenceUrlTypes(allTypes);

        // Load missions
        try {
          missions = await getMissions(
            editMode ? { include_inactive: true } : { is_active: true },
          );
        } catch (err) {
          missions = [];
        }

        await loadAcceptedProjects();

        if (editMode) {
          let currentType = types.find(
            (type) =>
              String(type.id) === String(submission.contribution_type),
          );
          if (!currentType) {
            try {
              const response = await contributionsAPI.getContributionType(
                submission.contribution_type,
              );
              currentType = response.data;
              if (currentType) {
                types = [...types, currentType];
                allEvidenceUrlTypes = collectEvidenceUrlTypes(types);
              }
            } catch (err) {
              currentType = null;
            }
          }

          if (!currentType) {
            error = "This submission's contribution type could not be loaded.";
          } else {
            selectedType = currentType;
            selectedCategory =
              currentType.category ||
              submission.contribution_type_details?.category ||
              "builder";
            formData.contribution_type = currentType.id;
            searchQuery = currentType.name;
            partitionEvidenceForType(
              currentType,
              submission.evidence_items || [],
            );

            if (selectedMission) {
              selectedMissionData =
                missions.find(
                  (mission) =>
                    String(mission.id) === String(selectedMission),
                ) || null;
              if (!selectedMissionData) {
                try {
                  const response = await contributionsAPI.getMission(
                    selectedMission,
                  );
                  selectedMissionData = response.data || null;
                } catch (err) {
                  selectedMissionData = null;
                }
              }
              if (selectedMissionData) {
                searchQuery = selectedMissionData.name;
              }
            }
          }
          // Handle rejected-submission cloning before ordinary URL
          // preselection. The cloned text/evidence always stays populated,
          // while an unavailable type or mission is deliberately left for
          // the user to replace.
        } else if (resubmitMode) {
          const clonedEvidence = evidenceItemsWithoutIds(
            resubmitSource.evidence_items,
          );
          let sourceType = types.find(
            (type) =>
              String(type.id) === String(resubmitSource.contribution_type),
          );
          if (!sourceType) {
            try {
              const response = await contributionsAPI.getContributionType(
                resubmitSource.contribution_type,
              );
              sourceType = response.data || null;
              if (sourceType) {
                types = [...types, sourceType];
                allEvidenceUrlTypes = collectEvidenceUrlTypes(types);
              }
            } catch (err) {
              sourceType = null;
            }
          }

          partitionEvidenceForType(sourceType, clonedEvidence);
          if (!sourceType) {
            selectedType = null;
            selectedMission = null;
            selectedMissionData = null;
            formData.contribution_type = "";
            searchQuery = "";
            showTypeDropdown = true;
            cloneContextWarning = `The original contribution type, ${resubmitSource.contribution_type_name || "Unknown type"}, is no longer available. Choose a current type to continue.`;
          } else {
            selectedCategory = sourceType.category || selectedCategory;
            const sourceMissionId =
              resubmitSource.mission?.id ?? resubmitSource.mission ?? null;

            if (sourceMissionId) {
              let sourceMission = missions.find(
                (mission) => String(mission.id) === String(sourceMissionId),
              );
              if (!sourceMission) {
                try {
                  const response = await contributionsAPI.getMission(
                    sourceMissionId,
                  );
                  sourceMission = response.data || null;
                } catch (err) {
                  sourceMission = null;
                }
              }

              if (
                sourceMission &&
                String(sourceMission.contribution_type) ===
                  String(sourceType.id) &&
                isMissionSubmittable(sourceMission) &&
                !isTypeFull(sourceType)
              ) {
                selectedType = sourceType;
                selectedMission = sourceMission.id;
                selectedMissionData = sourceMission;
                formData.contribution_type = sourceType.id;
                searchQuery = sourceMission.name;
              } else {
                selectedType = null;
                selectedMission = null;
                selectedMissionData = null;
                formData.contribution_type = "";
                searchQuery = "";
                showTypeDropdown = true;
                const missionName =
                  sourceMission?.name ||
                  resubmitSource.mission?.name ||
                  "The original mission";
                cloneContextWarning = isTypeFull(sourceType)
                  ? `${sourceType.name} is currently full. Your copied details are intact; choose an available contribution type or mission.`
                  : `${missionName} is no longer accepting submissions. Your copied details are intact; choose a current contribution type or mission.`;
              }
            } else if (sourceType.is_submittable && !isTypeFull(sourceType)) {
              selectedType = sourceType;
              selectedMission = null;
              selectedMissionData = null;
              formData.contribution_type = sourceType.id;
              searchQuery = sourceType.name;
            } else {
              selectedType = null;
              selectedMission = null;
              selectedMissionData = null;
              formData.contribution_type = "";
              searchQuery = "";
              showTypeDropdown = true;
              cloneContextWarning = isTypeFull(sourceType)
                ? `${sourceType.name} is currently full. Your copied details are intact; choose an available contribution type or mission.`
                : `${sourceType.name} no longer accepts direct submissions. Your copied details are intact; choose a current contribution type or mission.`;
            }

            if (selectedType && isMilestoneType(selectedType)) {
              const sourceProjectId =
                resubmitSource.project_contribution?.id ??
                resubmitSource.project_contribution ??
                "";
              const projectStillAvailable = acceptedProjects.some(
                (project) => String(project.id) === String(sourceProjectId),
              );
              selectedProject = projectStillAvailable
                ? String(sourceProjectId)
                : "";
              if (sourceProjectId && !projectStillAvailable) {
                const projectWarning =
                  "The originally linked project is no longer available for a milestone submission. Select one of your current highlighted projects.";
                cloneContextWarning = cloneContextWarning
                  ? `${cloneContextWarning} ${projectWarning}`
                  : projectWarning;
              }
            }
          }
        } else if (missionId) {
          // Load the specific mission and pre-select it
          try {
            const response = await contributionsAPI.getMission(missionId);
            const mission = response.data;
            if (mission) {
              const parentType = types.find(
                (type) => type.id === mission.contribution_type,
              );
              if (parentType) {
                selectedCategory = parentType.category || "builder";
                if (isTypeFull(parentType)) {
                  selectedType = null;
                  selectedMission = null;
                  selectedMissionData = null;
                  formData.contribution_type = "";
                  searchQuery = "";
                  showTypeDropdown = true;
                  error = typeLimitError(parentType);
                } else if (isMissionSubmittable(mission)) {
                  selectedType = parentType;
                  selectedMission = mission.id;
                  selectedMissionData = mission;
                  formData.contribution_type = parentType.id;
                  searchQuery = mission.name;
                } else {
                  selectedType = null;
                  selectedMission = null;
                  selectedMissionData = null;
                  formData.contribution_type = "";
                  searchQuery = "";
                  showTypeDropdown = true;
                  error = isMissionFull(mission)
                    ? missionLimitError(mission)
                    : "This mission is not currently accepting submissions.";
                }
              }
            }
          } catch (err) {
            console.error("Failed to load mission:", err);
          }
        } else if (initialTypeId) {
          // Load the specific type and pre-select it
          const type = types.find(
            (candidate) => candidate.id === parseInt(initialTypeId),
          );
          if (type) {
            selectedCategory = type.category || "builder";
            searchQuery = type.name;
            if (type.is_submittable && !isTypeFull(type)) {
              selectedType = type;
              formData.contribution_type = type.id;
            } else if (isTypeFull(type)) {
              selectedType = null;
              formData.contribution_type = "";
              searchQuery = "";
              showTypeDropdown = true;
              error = typeLimitError(type);
            } else {
              showTypeDropdown = true;
            }
          } else {
            // Type not in the catalog response, try fetching it directly.
            try {
              const response =
                await contributionsAPI.getContributionType(initialTypeId);
              const fetchedType = response.data;
              if (fetchedType) {
                if (
                  !types.some(
                    (candidate) =>
                      String(candidate.id) === String(fetchedType.id),
                  )
                ) {
                  types = [...types, fetchedType];
                  allEvidenceUrlTypes = collectEvidenceUrlTypes(types);
                }
                selectedCategory = fetchedType.category || "builder";
                searchQuery = fetchedType.name;
                if (fetchedType.is_submittable && !isTypeFull(fetchedType)) {
                  selectedType = fetchedType;
                  formData.contribution_type = fetchedType.id;
                } else if (isTypeFull(fetchedType)) {
                  selectedType = null;
                  formData.contribution_type = "";
                  searchQuery = "";
                  showTypeDropdown = true;
                  error = typeLimitError(fetchedType);
                } else {
                  showTypeDropdown = true;
                }
              }
            } catch (err) {
              console.error("Failed to load contribution type:", err);
            }
          }
        }
      } catch (err) {
        error = editMode
          ? "Failed to load this submission's form."
          : resubmitMode
            ? "Failed to prepare this rejected submission. Please try again."
            : "Failed to load contribution categories.";
        console.error(err);
      } finally {
        if (!disposed) loadingTypes = false;
      }

      if (disposed) return;
      trackEvent(
        editMode ? "contribution_edit_view" : "contribution_form_view",
        getAnalyticsContext({
          surface: editMode ? "edit_form" : "form",
          role_context: selectedCategory,
          contribution_category: selectedCategory,
        }),
      );

      if (!editMode) {
        const checkRecaptcha = () => {
          if (disposed || renderRecaptcha()) return;
          recaptchaRetryTimeout = window.setTimeout(checkRecaptcha, 100);
        };
        checkRecaptcha();
      }
    }

    initializeForm();

    return () => {
      disposed = true;
      if (recaptchaRetryTimeout !== null) {
        window.clearTimeout(recaptchaRetryTimeout);
        recaptchaRetryTimeout = null;
      }
      if (recaptchaWidgetId !== null && window.grecaptcha) {
        try {
          window.grecaptcha.reset(recaptchaWidgetId);
        } catch (e) {}
      }
    };
  });

  const socialAccountLabels = {
    twitter: "X (Twitter)",
    discord: "Discord",
    github: "GitHub",
  };
  const socialConnectionFields = {
    twitter: "twitter_connection",
    discord: "discord_connection",
    github: "github_connection",
  };
  const evidenceSlugToAccount = {
    "x-post": "twitter",
    "github-repo": "github",
    "github-file": "github",
  };

  // Detect which social accounts are required by evidence URLs but not linked.
  // Walks both the optional evidenceSlots AND the dedicated requiredEvidenceSlot
  // so a required github-pr / x-post URL also gates submission on the matching
  // social account being linked.
  let evidenceRequiredAccounts = $derived.by(() => {
    const user = $userStore.user;
    if (!user) return [];
    const needed = new Set();
    const slotsToCheck = [...evidenceSlots];
    if (requiredEvidenceTypes.length > 0) slotsToCheck.push(requiredEvidenceSlot);
    for (const slot of slotsToCheck) {
      const type = slot.selectedType;
      if (!type || type.is_generic) continue;
      const account = evidenceSlugToAccount[type.slug];
      const field = account && socialConnectionFields[account];
      if (field && !user[field]) {
        needed.add(account);
      }
    }
    return Array.from(needed);
  });
  let missingSocialAccounts = $derived.by(() => {
    if (!selectedType?.required_social_accounts?.length) return [];
    const user = $userStore.user;
    if (!user) return selectedType.required_social_accounts.map((a) => socialAccountLabels[a] || a);
    return selectedType.required_social_accounts
      .filter((account) => {
        const field = socialConnectionFields[account];
        return field && !user[field];
      })
      .map((a) => socialAccountLabels[a] || a);
  });
  let missingDiscordRoles = $derived.by(() => {
    const requiredRoles = selectedType?.required_discord_roles || [];
    if (requiredRoles.length === 0) return [];

    const userRoles = $userStore.user?.discord_connection?.roles || [];
    const userRoleIds = new Set(userRoles.map((role) => String(role.role_id)));
    const hasRequiredRole = requiredRoles.some((role) => userRoleIds.has(String(role.role_id)));
    return hasRequiredRole ? [] : requiredRoles.map((role) => role.name);
  });

  // True when ALL non-generic accepted evidence types require an unlinked social account
  let allEvidenceTypesBlocked = $derived.by(() => {
    if (!selectedType || acceptedEvidenceTypes.length === 0) return false;
    const user = $userStore.user;
    if (!user) return false;
    const nonGenericTypes = acceptedEvidenceTypes.filter(t => !t.is_generic);
    if (nonGenericTypes.length === 0) return false;
    return nonGenericTypes.every(t => {
      const account = evidenceSlugToAccount[t.slug];
      const field = account && socialConnectionFields[account];
      return field && !user[field];
    });
  });

  // Combined list of social account labels the user must link before the form
  // can be shown: both type-level required_social_accounts AND the accounts
  // implied by accepted evidence types when ALL of them are blocked.
  let gateRequiredSocialAccounts = $derived.by(() => {
    const user = $userStore.user;
    const labels = new Set(missingSocialAccounts);
    if (allEvidenceTypesBlocked) {
      for (const t of acceptedEvidenceTypes) {
        if (t.is_generic) continue;
        const account = evidenceSlugToAccount[t.slug];
        const field = account && socialConnectionFields[account];
        if (field && (!user || !user[field])) {
          labels.add(socialAccountLabels[account] || account);
        }
      }
    }
    return Array.from(labels);
  });

  function isMissionActive(mission) {
    if (!mission) return false;
    if (mission.is_active === false) return false;
    const now = new Date();
    if (mission.start_date && now < new Date(mission.start_date)) return false;
    if (mission.end_date && now > new Date(mission.end_date)) return false;
    return true;
  }

  function isMissionFull(mission) {
    if (!mission) return false;
    if (mission.user_is_full === true) return true;
    if (mission.is_full === true) return true;
    return (
      mission.max_submissions !== null &&
      mission.max_submissions !== undefined &&
      mission.submissions_remaining !== null &&
      mission.submissions_remaining !== undefined &&
      Number(mission.submissions_remaining) <= 0
    );
  }

  function missionLimitError(mission) {
    if (mission?.user_is_full === true) {
      return "You have reached your submission limit for this mission.";
    }
    return "This mission has reached its submission limit.";
  }

  function isMissionSubmittable(mission) {
    return isMissionActive(mission) && !isMissionFull(mission);
  }

  function isTypeFull(type) {
    if (!type) return false;
    if (type.user_weekly_is_full === true) return true;
    if (type.is_full === true) return true;
    return (
      type.max_submissions !== null &&
      type.max_submissions !== undefined &&
      type.submissions_remaining !== null &&
      type.submissions_remaining !== undefined &&
      Number(type.submissions_remaining) <= 0
    );
  }

  function typeLimitError(type) {
    if (type?.user_weekly_is_full === true) {
      return "You have reached your weekly submission limit for this contribution type.";
    }
    return "This contribution type has reached its submission limit.";
  }

  function canSubmitTypeDirectly(type) {
    return isOriginalType(type) || (type.is_submittable && !isTypeFull(type));
  }

  function isOriginalType(type) {
    return Boolean(
      editMode &&
      type &&
      String(type.id) === String(originalContributionTypeId),
    );
  }

  function isMilestoneType(type) {
    return type?.slug === "milestones";
  }

  function isProjectType(type) {
    return isProjectContributionType(type);
  }

  /** @param {Record<string, any> | null} type */
  function clonedProjectForType(type) {
    if (!resubmitMode || !isMilestoneType(type) || !resubmitSourceProjectId) {
      return "";
    }
    return acceptedProjects.some(
      (project) => String(project.id) === String(resubmitSourceProjectId),
    )
      ? String(resubmitSourceProjectId)
      : "";
  }

  async function loadAcceptedProjects() {
    if (!$authState.isAuthenticated) return;
    loadingProjects = true;
    projectsError = false;
    try {
      const response = await submissionsAPI.getAcceptedProjects(
        editMode ? submission.id : null,
      );
      acceptedProjects = response.data || [];
    } catch (err) {
      // Keep failures distinct from "no highlighted projects" so a transient
      // error never tells a builder they are not eligible for milestones.
      projectsError = true;
    } finally {
      loadingProjects = false;
    }
  }

  // null while loading or after a fetch error so the guidance panel never
  // tells a builder they are ineligible off transient state.
  let milestoneEligible = $derived(
    loadingProjects || projectsError ? null : acceptedProjects.length > 0,
  );

  let selectedProjectData = $derived(
    acceptedProjects.find((project) => String(project.id) === String(selectedProject)) || null
  );
  let selectedProjectIsOriginal = $derived(
    editMode &&
    submission?.project_contribution &&
    String(
      submission.project_contribution?.id ??
      submission.project_contribution,
    ) === String(selectedProject),
  );
  let selectedProjectVersion = $derived(
    selectedProjectIsOriginal && submission?.milestone_version
      ? submission.milestone_version
      : selectedProjectData?.next_milestone_version || 1,
  );
  let selectedProjectLabel = $derived(
    selectedProjectData
      ? `${selectedProjectData.title} (${selectedProjectIsOriginal ? "milestone" : "next"} v${selectedProjectVersion})`
      : "Select highlighted project..."
  );
  let selectedProjectIndex = $derived(
    acceptedProjects.findIndex((project) => String(project.id) === String(selectedProject))
  );

  function spotsLeftLabel(count) {
    return `${count} ${Number(count) === 1 ? "spot" : "spots"} left`;
  }

  function activeMissionsForType(typeId) {
    if (editMode) return [];
    const type = types.find((t) => String(t.id) === String(typeId));
    if (isTypeFull(type)) return [];

    return missions.filter(
      (mission) =>
        String(mission.contribution_type) === String(typeId) &&
        isMissionSubmittable(mission),
    );
  }

  function typeCanBeSelected(type) {
    if (
      selectedCategory === "community" &&
      hasLegacyCommunityEditAccess &&
      !isCreator &&
      !isOriginalType(type)
    ) {
      return false;
    }
    return (
      isOriginalType(type) ||
      canSubmitTypeDirectly(type) ||
      activeMissionsForType(type.id).length > 0
    );
  }

  // Master gate: should the form details (date/title/notes/evidence/submit) be shown?
  let canShowFormDetails = $derived(
    selectedType &&
    missingSocialAccounts.length === 0 &&
    missingDiscordRoles.length === 0 &&
    !allEvidenceTypesBlocked &&
    (!isMilestoneType(selectedType) || !!selectedProject)
  );

  // True if any evidence slot has a URL that doesn't match its selected type
  let hasEvidencePatternMismatch = $derived.by(() => {
    return evidenceSlots.some(slot =>
      slot.url && slot.selectedType && !slot.selectedType.is_generic && !urlMatchesType(slot.url, slot.selectedType)
    );
  });

  // Auto-add first evidence slot when form details become visible.
  // Skip this when the type declares required URL types; the required slot
  // is shown separately and users don't need an extra empty slot by default.
  $effect(() => {
    if (
      canShowFormDetails &&
      evidenceSlots.length === 0 &&
      !(selectedType?.required_evidence_url_types?.length)
    ) {
      addEvidenceSlot();
    }
  });

  // Build filtered items list (types + missions) based on category and search
  let filteredItems = $derived.by(() => {
    const categoryTypes = types.filter(
      (t) => t.category === selectedCategory && typeCanBeSelected(t),
    );
    const categoryMissions = missions.filter((m) => {
      if (editMode) return false;
      const mType = types.find((t) => String(t.id) === String(m.contribution_type));
      return mType && mType.category === selectedCategory && isMissionSubmittable(m);
    });

    let matchingTypes = categoryTypes;
    let matchingMissions = categoryMissions;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      matchingTypes = categoryTypes.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          (t.description && t.description.toLowerCase().includes(query)),
      );
      matchingMissions = categoryMissions.filter(
        (m) =>
          m.name.toLowerCase().includes(query) ||
          (m.description && m.description.toLowerCase().includes(query)),
      );
      // Also include types that have matching missions
      const typeIdsWithMatchingMissions = new Set(
        matchingMissions.map((m) => String(m.contribution_type)),
      );
      matchingTypes = categoryTypes.filter(
        (t) => matchingTypes.includes(t) || typeIdsWithMatchingMissions.has(String(t.id)),
      );
    }

    // Build flat list: types followed by their missions
    const items = [];
    matchingTypes.forEach((type) => {
      const query = searchQuery?.toLowerCase() || "";
      const typeMatchesQuery =
        query &&
        (type.name.toLowerCase().includes(query) ||
          (type.description && type.description.toLowerCase().includes(query)));
      const sourceMissions = typeMatchesQuery ? categoryMissions : matchingMissions;
      const typeMissions = sourceMissions.filter(
        (m) => String(m.contribution_type) === String(type.id),
      );

      if (canSubmitTypeDirectly(type)) {
        items.push({ itemType: "type", data: type });
      } else if (typeMissions.length > 0) {
        items.push({ itemType: "typeHeader", data: type });
      }

      typeMissions.forEach((mission) => {
        items.push({ itemType: "mission", data: mission, parentType: type });
      });
    });
    return items;
  });

  $effect(() => {
    if (selectedType && selectedType.category !== selectedCategory) {
      // If we switch categories, clear the specific type selection
      selectedType = null;
      selectedMission = null;
      selectedMissionData = null;
      selectedProject = "";
      formData.contribution_type = "";
      searchQuery = "";
    }
  });

  function selectCategory(cat) {
    if (selectionLocked || loadingTypes) return;
    selectedCategory = cat;
    showTypeDropdown = false;
    showProjectDropdown = false;
  }

  /** @param {string} slug */
  function routeToType(slug) {
    const target = slug === "projects"
      ? types.find((type) => isProjectContributionType(type))
      : types.find((type) => type.slug === slug);
    if (target) selectType(target);
  }

  function selectType(t) {
    if (selectionLocked) return;
    if (!isOriginalType(t) && isTypeFull(t)) {
      error = typeLimitError(t);
      return;
    }

    if (!isOriginalType(t) && !t.is_submittable) {
      searchQuery = t.name;
      showTypeDropdown = true;
      return;
    }

    if (!selectedType || String(selectedType.id) !== String(t.id)) {
      partitionEvidenceForType(t);
    }
    selectedType = t;
    selectedMission = null;
    selectedMissionData = null;
    selectedProject = clonedProjectForType(t);
    showProjectDropdown = false;
    formData.contribution_type = t.id;
    showTypeDropdown = false;
    searchQuery = t.name;
    if (resubmitMode) cloneContextWarning = "";
    if (error === "Please select a contribution type") error = "";
  }

  function selectItem(item) {
    if (selectionLocked) return;
    if (item.itemType === "type") {
      selectType(item.data);
    } else if (item.itemType === "mission") {
      if (editMode) return;
      if (isTypeFull(item.parentType)) {
        error = typeLimitError(item.parentType);
        return;
      }
      if (!isMissionSubmittable(item.data)) {
        error = isMissionFull(item.data)
          ? missionLimitError(item.data)
          : "This mission is not currently accepting submissions.";
        return;
      }
      if (
        !selectedType ||
        String(selectedType.id) !== String(item.parentType.id)
      ) {
        partitionEvidenceForType(item.parentType);
      }
      selectedType = item.parentType;
      selectedMission = item.data.id;
      selectedMissionData = item.data;
      selectedProject = clonedProjectForType(item.parentType);
      showProjectDropdown = false;
      formData.contribution_type = item.parentType.id;
      showTypeDropdown = false;
      searchQuery = item.data.name;
      if (resubmitMode) cloneContextWarning = "";
      if (error === "Please select a contribution type") error = "";
    }
  }

  function handleSearchInput(event) {
    searchQuery = event.target.value;
    showTypeDropdown = true;
  }

  function handleSearchFocus() {
    // Clear search query to show all options
    if (selectedMissionData && searchQuery === selectedMissionData.name) {
      searchQuery = "";
    } else if (selectedType && searchQuery === selectedType.name) {
      searchQuery = "";
    }
    showTypeDropdown = true;
  }

  function handleSearchBlur() {
    setTimeout(() => {
      showTypeDropdown = false;
      // Restore name if search is empty
      if (!searchQuery) {
        if (selectedMissionData) {
          searchQuery = selectedMissionData.name;
        } else if (selectedType) {
          searchQuery = selectedType.name;
        }
      }
    }, 200);
  }

  let projectDropdownButtonRef = $state(null);
  let projectDropdownRef = $state(null);
  let projectOptionRefs = $state([]);

  function focusProjectOption(index, { defer = false } = {}) {
    if (acceptedProjects.length === 0) return;
    const nextIndex = (index + acceptedProjects.length) % acceptedProjects.length;
    focusedProjectIndex = nextIndex;

    const focusOption = () => {
      projectOptionRefs[nextIndex]?.focus();
    };

    if (defer) {
      requestAnimationFrame(focusOption);
    } else {
      focusOption();
    }
  }

  function openProjectDropdown(index = selectedProjectIndex >= 0 ? selectedProjectIndex : 0) {
    projectOptionRefs = [];
    showProjectDropdown = true;
    focusProjectOption(index, { defer: true });
  }

  function closeProjectDropdown({ focusTrigger = false } = {}) {
    showProjectDropdown = false;
    focusedProjectIndex = -1;
    if (focusTrigger) {
      requestAnimationFrame(() => {
        projectDropdownButtonRef?.focus();
      });
    }
  }

  function toggleProjectDropdown() {
    if (showProjectDropdown) {
      closeProjectDropdown();
    } else {
      openProjectDropdown();
    }
  }

  function selectProject(project, options = {}) {
    selectedProject = String(project.id);
    closeProjectDropdown({ focusTrigger: options.focusTrigger ?? true });
    if (error === "Please select the highlighted project this milestone belongs to.") {
      error = "";
    }
  }

  function handleProjectTriggerKeydown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openProjectDropdown(selectedProjectIndex >= 0 ? selectedProjectIndex : 0);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      openProjectDropdown(selectedProjectIndex >= 0 ? selectedProjectIndex : acceptedProjects.length - 1);
    } else if (event.key === "Escape" && showProjectDropdown) {
      event.preventDefault();
      closeProjectDropdown();
    }
  }

  function handleProjectOptionKeydown(event, index) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusProjectOption(index + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      focusProjectOption(index - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectProject(acceptedProjects[index]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeProjectDropdown({ focusTrigger: true });
    }
  }

  function handleProjectDropdownFocusOut() {
    setTimeout(() => {
      if (
        showProjectDropdown &&
        projectDropdownRef &&
        !projectDropdownRef.contains(document.activeElement)
      ) {
        closeProjectDropdown();
      }
    }, 0);
  }

  // Evidence functions
  function addEvidenceSlot() {
    evidenceSlots = [
      ...evidenceSlots,
      emptyEvidenceSlot(),
    ];
  }

  function removeEvidenceSlot(index) {
    evidenceSlots = evidenceSlots.filter((_, i) => i !== index);
  }

  function normalizeUrl(url) {
    if (!url) return url;
    const trimmed = url.trim();
    if (!trimmed) return trimmed;
    return /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed) ? trimmed : "https://" + trimmed;
  }

  function isValidUrl(url) {
    if (!url) return false;
    if (/\s/.test(url)) return false;
    try {
      const u = new URL(url);
      if (u.protocol !== "http:" && u.protocol !== "https:") return false;
      if (!u.hostname || !u.hostname.includes(".")) return false;
      return true;
    } catch (e) {
      return false;
    }
  }

  // Detect URL type from patterns
  function detectUrlType(url) {
    if (!url || !allEvidenceUrlTypes.length) return null;
    for (const urlType of allEvidenceUrlTypes) {
      if (urlType.is_generic) continue;
      for (const pattern of urlType.url_patterns || []) {
        try {
          if (new RegExp(pattern, "i").test(url)) {
            return urlType;
          }
        } catch (e) {
          continue;
        }
      }
    }
    // Return the generic "Other" type
    return allEvidenceUrlTypes.find((t) => t.is_generic) || null;
  }

  // Accepted evidence types for the selected contribution type
  let acceptedEvidenceTypes = $derived(
    selectedType?.accepted_evidence_url_types?.length
      ? selectedType.accepted_evidence_url_types
      : [],
  );

  // Required evidence types: at least one submitted URL must match one of these
  let requiredEvidenceTypes = $derived(
    selectedType?.required_evidence_url_types?.length
      ? selectedType.required_evidence_url_types
      : [],
  );

  // Human-readable list of required type names for labels/messages
  let requiredEvidenceLabel = $derived.by(() => {
    if (!requiredEvidenceTypes.length) return "";
    const names = requiredEvidenceTypes.map((t) => t.name);
    if (names.length === 1) return names[0];
    if (names.length === 2) return `${names[0]} or ${names[1]}`;
    return `${names.slice(0, -1).join(", ")}, or ${names[names.length - 1]}`;
  });

  // True when the required slot's detected type is in the required set
  let requiredSlotSatisfied = $derived.by(() => {
    if (!requiredEvidenceTypes.length) return true;
    const t = requiredEvidenceSlot.selectedType;
    if (!t) return false;
    return requiredEvidenceTypes.some((rt) => rt.id === t.id);
  });

  function handleRequiredUrlBlur() {
    requiredEvidenceSlot.url = normalizeUrl(requiredEvidenceSlot.url);
    if (!requiredEvidenceSlot.url) {
      requiredEvidenceSlot.error = "";
      requiredEvidenceSlot.selectedType = null;
      requiredEvidenceSlot.description = "";
      return;
    }
    if (!isValidUrl(requiredEvidenceSlot.url)) {
      requiredEvidenceSlot.error = "Please enter a valid URL.";
      requiredEvidenceSlot.selectedType = null;
      return;
    }
    requiredEvidenceSlot.error = "";
    const detected = detectUrlType(requiredEvidenceSlot.url);
    requiredEvidenceSlot.selectedType = detected;
    requiredEvidenceSlot.description = detected
      ? (detected.is_generic ? "Other" : detected.name)
      : "";
  }

  function handleRequiredUrlInput() {
    requiredEvidenceSlot.error = "";
    if (!requiredEvidenceSlot.url) {
      requiredEvidenceSlot.selectedType = null;
      requiredEvidenceSlot.description = "";
      return;
    }
    // Detect against the normalized form so users typing without an explicit
    // protocol (e.g. "github.com/org/repo") still match scheme-anchored
    // patterns. Critical when the form submits without a prior blur.
    const detected = detectUrlType(normalizeUrl(requiredEvidenceSlot.url));
    requiredEvidenceSlot.selectedType = detected;
    requiredEvidenceSlot.description = detected
      ? (detected.is_generic ? "Other" : detected.name)
      : "";
  }

  function getRequiredUrlPlaceholder() {
    if (!requiredEvidenceTypes.length) return "https://...";
    return urlPlaceholders[requiredEvidenceTypes[0].slug] || "https://...";
  }

  function handleUrlBlur(index) {
    const slot = evidenceSlots[index];
    if (!slot) return;
    slot.url = normalizeUrl(slot.url);
    if (!slot.url) {
      slot.error = "";
      slot.selectedType = null;
      slot.typeManuallySet = false;
      slot.description = "";
      return;
    }
    if (!isValidUrl(slot.url)) {
      slot.error = "Please enter a valid URL.";
      slot.selectedType = null;
      return;
    }
    slot.error = "";
    const detected = detectUrlType(slot.url);
    // Auto-correct: if URL matches a specific type, always upgrade to it.
    // If detected is generic ("Other"), don't override a specific manual selection.
    if (detected && !detected.is_generic) {
      slot.selectedType = detected;
      slot.description = detected.name;
      slot.typeManuallySet = false;
    } else if (!slot.selectedType) {
      slot.selectedType = detected;
      slot.description = detected?.is_generic ? "Other" : (detected?.name || "");
    } else if (!slot.typeManuallySet && !slot.description) {
      // Selected type was set by input handler but description never landed
      // (e.g. earlier code path) — backfill it from the current type.
      slot.description = slot.selectedType.is_generic ? "Other" : slot.selectedType.name;
    }
  }

  // Re-run detection as the user edits the URL so the detected type stays in
  // sync with what's typed. Skip when the user explicitly picked a type from
  // the override dropdown — their choice should stick until they reset it.
  function handleUrlInput(index) {
    const slot = evidenceSlots[index];
    if (!slot) return;
    slot.error = "";
    if (!slot.url) {
      slot.selectedType = null;
      slot.typeManuallySet = false;
      slot.description = "";
      return;
    }
    if (slot.typeManuallySet) return;
    // Detect against the normalized form so users typing without an explicit
    // protocol still match scheme-anchored patterns even if the form is
    // submitted before blur normalizes the visible value.
    const detected = detectUrlType(normalizeUrl(slot.url));
    slot.selectedType = detected;
    // Keep description aligned with the auto-detected type so it never lags
    // behind the URL the user is editing.
    slot.description = detected
      ? (detected.is_generic ? "Other" : detected.name)
      : "";
  }

  // URL placeholder hints per evidence type slug
  const urlPlaceholders = {
    "x-post": "https://x.com/username/status/123...",
    "github-repo": "https://github.com/username/repository",
    "github-file": "https://github.com/username/repo/blob/main/file.py",
    "github-pr": "https://github.com/org/repo/pull/123",
    "github-issue": "https://github.com/org/repo/issues/123",
    "studio-contract": "https://studio.genlayer.com/...",
  };

  function getUrlPlaceholder(slot) {
    return urlPlaceholders[slot.selectedType?.slug] || "https://...";
  }

  function handleEvidenceTypeChange(index, slug) {
    const urlType = acceptedEvidenceTypes.find(t => t.slug === slug) || null;
    evidenceSlots[index].selectedType = urlType;
    evidenceSlots[index].typeManuallySet = !!urlType;
    if (urlType) {
      evidenceSlots[index].description = urlType.is_generic ? "Other" : urlType.name;
    }
  }

  // Check if a URL matches a specific evidence type's patterns
  function urlMatchesType(url, urlType) {
    if (!url || !urlType || urlType.is_generic) return true;
    for (const pattern of urlType.url_patterns || []) {
      try {
        if (new RegExp(pattern, "i").test(url)) return true;
      } catch (e) { continue; }
    }
    return false;
  }

  // reCAPTCHA
  function renderRecaptcha() {
    if (
      typeof window === "undefined" ||
      !window.grecaptcha ||
      !window.grecaptcha.render
    )
      return false;
    try {
      recaptchaWidgetId = window.grecaptcha.render("recaptcha-wrapper", {
        sitekey: RECAPTCHA_SITE_KEY,
        callback: (token) => {
          recaptchaToken = token;
          if (error && error.includes("reCAPTCHA")) error = "";
        },
        "expired-callback": () => {
          recaptchaToken = "";
        },
        "error-callback": () => {
          recaptchaToken = "";
        },
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  function getRecaptchaToken() {
    if (recaptchaToken) return recaptchaToken;
    if (
      typeof window === "undefined" ||
      recaptchaWidgetId === null ||
      !window.grecaptcha ||
      !window.grecaptcha.getResponse
    ) {
      return "";
    }
    try {
      const token = window.grecaptcha.getResponse(recaptchaWidgetId);
      if (token) recaptchaToken = token;
      return token || "";
    } catch (e) {
      return "";
    }
  }

  // Submission
  async function handleSubmit(e) {
    e.preventDefault();
    trackEvent(editMode ? "contribution_edit_attempt" : "contribution_submit_attempt", getAnalyticsContext({
      surface: editMode ? "edit_form" : "form",
      role_context: selectedCategory,
      contribution_category: selectedCategory,
    }));

    if (appealLocked) {
      error = "Editing is paused while your appeal is under review.";
      return;
    }

    if (requiresMoreInfoResponse && !moreInfoResponse.trim()) {
      error = "Tell the steward what changed before resubmitting.";
      return;
    }

    if (!formData.contribution_type) {
      trackEvent(editMode ? "contribution_edit_error" : "contribution_submit_error", getAnalyticsContext({
        surface: editMode ? "edit_form" : "form",
        role_context: selectedCategory,
        contribution_category: selectedCategory,
        error_stage: "validation",
      }));
      error = "Please select a contribution type";
      return;
    }

    if (isMilestoneType(selectedType) && !selectedProject) {
      error = "Please select the highlighted project this milestone belongs to.";
      return;
    }

    if (isMilestoneType(selectedType) && !formData.notes.trim()) {
      error = "Please describe the changes and improvements in this milestone.";
      return;
    }

    if (formData.notes.length > 1000) {
      error = "Notes cannot exceed 1000 characters";
      return;
    }

    if (!canSubmitCurrentCategory) {
      error =
        selectedCategory === "community"
          ? "Complete the Creator journey to become a creator before submitting community contributions."
          : "Complete this role journey before submitting to this category.";
      return;
    }

    // Clear any previous inline URL errors
    requiredEvidenceSlot.error = "";
    for (const s of evidenceSlots) s.error = "";

    // Validate required evidence slot if the type declares required URL types
    if (requiredEvidenceTypes.length > 0) {
      const reqUrl = requiredEvidenceSlot.url?.trim();
      if (!reqUrl) {
        requiredEvidenceSlot.error = `Please provide a ${requiredEvidenceLabel} URL.`;
        return;
      }
      const normalizedReqUrl = normalizeUrl(reqUrl);
      if (!isValidUrl(normalizedReqUrl)) {
        requiredEvidenceSlot.error = "Please enter a valid URL.";
        return;
      }
      // Re-detect against the normalized URL at submit time so a form that
      // bypassed blur (Enter key, autofill) still matches scheme-anchored
      // patterns. Sync selectedType so requiredSlotSatisfied reflects reality.
      const reqDetected = detectUrlType(normalizedReqUrl);
      if (reqDetected) {
        requiredEvidenceSlot.selectedType = reqDetected;
        if (!requiredEvidenceSlot.description) {
          requiredEvidenceSlot.description = reqDetected.is_generic ? "Other" : reqDetected.name;
        }
      }
      if (!requiredSlotSatisfied) {
        requiredEvidenceSlot.error = `URL must be one of: ${requiredEvidenceLabel}.`;
        return;
      }
    }

    for (let i = 0; i < evidenceSlots.length; i++) {
      const slot = evidenceSlots[i];
      const hasUrl = slot.url && slot.url.trim().length > 0;
      // Slot description is auto-managed from URL detection — never user-typed —
      // so we only validate the URL here. Empty slots are silently skipped.
      if (!hasUrl) continue;
      if (!isValidUrl(normalizeUrl(slot.url))) {
        evidenceSlots[i].error = "Please enter a valid URL.";
        return;
      }
    }

    const filledSlots = evidenceSlots.filter((s) => s.url?.trim());

    // Build the combined evidence list: required slot first (if present),
    // then optional extras
    const allEvidence = [];
    if (requiredEvidenceTypes.length > 0) {
      const requiredEvidence = {
        description:
          requiredEvidenceSlot.description?.trim() ||
          requiredEvidenceSlot.selectedType?.name ||
          "Required evidence",
        url: normalizeUrl(requiredEvidenceSlot.url),
      };
      if (requiredEvidenceSlot.id) {
        requiredEvidence.id = requiredEvidenceSlot.id;
      }
      allEvidence.push(requiredEvidence);
    }
    for (const slot of filledSlots) {
      const evidence = {
        description:
          slot.description?.trim() ||
          slot.selectedType?.name ||
          "Evidence",
        url: normalizeUrl(slot.url),
      };
      if (slot.id) evidence.id = slot.id;
      allEvidence.push(evidence);
    }

    // Milestones are reviewed from the linked project's repository, so
    // extra evidence is optional for them.
    if (allEvidence.length === 0 && !isMilestoneType(selectedType)) {
      error =
        "Please add at least one evidence item with a URL to support your contribution";
      return;
    }

    const currentRecaptchaToken = editMode ? "" : getRecaptchaToken();
    if (!editMode && !currentRecaptchaToken) {
      error = "Please complete the reCAPTCHA verification";
      return;
    }

    submitting = true;
    error = "";

    try {
      if (!keepsOriginalContributionType && isTypeFull(selectedType)) {
        error = typeLimitError(selectedType);
        submitting = false;
        return;
      }

      const submissionData = {
        contribution_type: formData.contribution_type,
        contribution_date: formData.contribution_date + "T00:00:00Z",
        title: formData.title,
        notes: formData.notes,
      };
      if (requiresMoreInfoResponse) {
        submissionData.more_info_response = {
          request_id: latestMoreInfoRequest?.id ?? null,
          message: moreInfoResponse.trim(),
        };
      }
      if (!editMode) submissionData.recaptcha = currentRecaptchaToken;

      if (isMilestoneType(selectedType)) {
        submissionData.project_contribution = selectedProject;
      } else if (editMode) {
        submissionData.project_contribution = null;
      }

      // Include mission when selected from the URL preselection or dropdown.
      const missionToSubmit = selectedMission;
      if (missionToSubmit) {
        if (!editMode && isMissionFull(selectedMissionData)) {
          error = missionLimitError(selectedMissionData);
          submitting = false;
          return;
        }
        submissionData.mission = missionToSubmit;
      } else if (editMode) {
        submissionData.mission = null;
      }

      // Send evidence inline with the submission (atomic creation)
      submissionData.evidence_items = allEvidence;

      const savedResponse = editMode
        ? await api.put(`/submissions/${submission.id}/`, submissionData)
        : await api.post("/submissions/", submissionData);

      if (editMode) {
        trackEvent("contribution_edit_success", getAnalyticsContext({
          surface: "edit_form",
          role_context: selectedCategory,
          contribution_category: selectedCategory,
        }));
      } else {
        const firstContribution = markLifecycleTime("first_contribution_submitted");
        const successParams = {
          surface: "form",
          role_context: selectedCategory,
          contribution_category: selectedCategory,
          lifecycle_scope: "browser",
          contribution_sequence: firstContribution ? "first_known" : "repeat_known",
          time_from_first_contribution_ms: getLifecycleDurationMs("first_contribution_submitted"),
          ...getLifecycleDurations(selectedCategory),
        };
        trackEvent("contribution_submit_success", getAnalyticsContext(successParams));
        trackEvent("contribution_submitted", getAnalyticsContext(successParams));
        if (firstContribution) {
          trackEvent("first_contribution_submitted", getAnalyticsContext(successParams));
        } else {
          trackEvent("repeat_contribution_submitted", getAnalyticsContext(successParams));
        }
      }
      sessionStorage.setItem(
        "submissionUpdateSuccess",
        editMode
          ? requiresMoreInfoResponse
            ? "Your response was sent and the submission is back in review."
            : "Your submission has been saved successfully."
          : resubmitMode
            ? "Your corrected contribution has been submitted and is pending review."
            : "Your contribution has been submitted successfully and is pending review.",
      );
      const createdSubmissionId = resubmitMode ? savedResponse?.data?.id : null;
      push(
        createdSubmissionId
          ? `/my-submissions?submission=${encodeURIComponent(createdSubmissionId)}`
          : "/my-submissions",
      );
    } catch (err) {
      trackEvent(editMode ? "contribution_edit_error" : "contribution_submit_error", getAnalyticsContext({
        surface: editMode ? "edit_form" : "form",
        role_context: selectedCategory,
        contribution_category: selectedCategory,
        error_stage: err.response?.status ? "backend" : "network",
      }));
      if (err.response?.data?.recaptcha) {
        error = Array.isArray(err.response.data.recaptcha)
          ? err.response.data.recaptcha[0]
          : err.response.data.recaptcha;
      } else {
        error = submissionErrorMessage(
          err,
          editMode
            ? "Failed to save submission"
            : "Failed to submit contribution",
        );
      }

      if (!editMode && recaptchaWidgetId !== null && window.grecaptcha) {
        try {
          window.grecaptcha.reset(recaptchaWidgetId);
          recaptchaToken = "";
        } catch (e) {}
      }
    } finally {
      submitting = false;
    }
  }

  async function confirmDelete() {
    if (!editMode || deleting) return;
    deleting = true;
    error = "";
    try {
      await api.delete(`/submissions/${submission.id}/`);
      sessionStorage.setItem(
        "submissionUpdateSuccess",
        "Your submission has been removed.",
      );
      trackEvent("contribution_edit_removed", getAnalyticsContext({
        surface: "edit_form",
        role_context: selectedCategory,
        contribution_category: selectedCategory,
      }));
      push("/my-submissions");
    } catch (err) {
      showDeleteDialog = false;
      error =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        "Failed to remove submission";
    } finally {
      deleting = false;
    }
  }

  // Click outside listener for dropdown
  let dropdownRef = $state(null);
  function handleClickOutside(event) {
    if (
      showTypeDropdown &&
      dropdownRef &&
      !dropdownRef.contains(event.target)
    ) {
      showTypeDropdown = false;
    }
    if (
      showProjectDropdown &&
      projectDropdownRef &&
      !projectDropdownRef.contains(event.target)
    ) {
      closeProjectDropdown();
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div
  class="submit-form-shell content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full"
  class:with-guidelines={!editMode}
  style="max-width: {editMode || resubmitMode ? 620 : 550}px; margin: 0 auto;"
>
  {#if editMode}
    <header class="edit-page-header flex w-full flex-col gap-4 pb-2">
      <button
        type="button"
        onclick={() => push("/my-submissions")}
        class="edit-back-link group inline-flex min-h-10 w-fit items-center gap-2 rounded-full px-1 pr-3 font-['Switzer'] text-[13px] font-medium text-[#6b6b6b] transition-[color,scale] duration-150 ease-out hover:text-black active:scale-[0.96]"
      >
        <span class="flex h-8 w-8 items-center justify-center rounded-full bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.06),0_1px_2px_rgba(0,0,0,0.06)] transition-[box-shadow] duration-150 ease-out group-hover:shadow-[0_0_0_1px_rgba(0,0,0,0.1),0_2px_5px_rgba(0,0,0,0.08)]">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </span>
        My submissions
      </button>

      <div class="flex w-full flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div class="min-w-0">
          <p class="mb-1 font-['Switzer'] text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8a8a8a]">
            Submission <span class="tabular-nums">#{submission.id}</span>
          </p>
          <h1
            class="submit-page-title text-balance font-['F37_Lineca'] text-[36px] font-medium leading-[42px] tracking-[-0.72px] text-black"
          >
            Edit submission
          </h1>
          <p class="mt-2 max-w-[470px] text-pretty font-['Switzer'] text-[14px] leading-[21px] tracking-[0.14px] text-[#6b6b6b]">
            Refine the details and evidence while this contribution is still under review.
          </p>
        </div>
        <span class="inline-flex h-8 w-fit shrink-0 items-center rounded-full bg-[#fff7df] px-3 font-['Switzer'] text-[12px] font-semibold text-[#8a5d00] shadow-[inset_0_0_0_1px_rgba(138,93,0,0.12)]">
          {appealLocked
            ? "Appeal under review"
            : submission.state === "more_info_needed"
              ? "Update requested"
              : "Pending review"}
        </span>
      </div>
    </header>

    {#if appealLocked}
      <section class="review-feedback-card flex w-full items-start gap-3 rounded-[16px] bg-[#fff8e8] p-5 text-[#6f4d00] shadow-[0_0_0_1px_rgba(180,120,0,0.12),0_8px_24px_rgba(138,93,0,0.05)]">
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-white shadow-[0_0_0_1px_rgba(138,93,0,0.10),0_2px_6px_rgba(138,93,0,0.06)]">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 6v6l4 2m5-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </span>
        <div class="min-w-0">
          <p class="font-['Switzer'] text-[13px] font-semibold">Editing is paused</p>
          <p class="mt-1 text-pretty font-['Switzer'] text-[13px] leading-5 text-[#7c5a12]">
            This submission stays unchanged while stewards review your appeal.
            You can still remove it, or return when a steward requests more information.
          </p>
        </div>
      </section>
    {/if}

    {#if reviewFeedback}
      <section class="review-feedback-card w-full overflow-hidden rounded-[16px] bg-[#f3f7ff] shadow-[0_0_0_1px_rgba(37,99,235,0.10),0_8px_24px_rgba(37,99,235,0.06)]">
        <div class="flex items-start gap-3 p-5">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-white text-blue-600 shadow-[0_0_0_1px_rgba(37,99,235,0.10),0_2px_6px_rgba(37,99,235,0.08)]">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a10.6 10.6 0 01-4.7-1.08L3 20l1.24-3.72A7.45 7.45 0 013 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </span>
          <div class="min-w-0 flex-1">
            <p class="font-['Switzer'] text-[13px] font-semibold text-blue-950">
              {submission.state === "more_info_needed" ? "Changes requested" : "Steward feedback"}
            </p>
            {#if latestMoreInfoRequest?.user_name}
              <p class="mt-0.5 font-['Switzer'] text-[11px] text-blue-700/70">
                From {latestMoreInfoRequest.user_name}
              </p>
            {/if}
            <div class="feedback-markdown mt-2 text-pretty font-['Switzer'] text-[14px] leading-[21px] text-blue-950/80">
              {@html parseMarkdown(reviewFeedback)}
            </div>
          </div>
        </div>
      </section>
    {/if}

    {#if requiresMoreInfoResponse}
      <section class="w-full rounded-[16px] bg-[#effcf6] p-5 shadow-[0_0_0_1px_rgba(5,150,105,0.16),0_8px_24px_rgba(5,150,105,0.05)]">
        <label for="edit-more-info-response" class="font-['Switzer'] text-[14px] font-semibold text-emerald-950">
          What did you change?
        </label>
        <p id="edit-more-info-response-help" class="mt-1 text-pretty font-['Switzer'] text-[12px] leading-5 text-emerald-800">
          This response is sent separately from your original submission notes, so the steward can see exactly how you addressed the request.
        </p>
        <textarea
          id="edit-more-info-response"
          bind:value={moreInfoResponse}
          aria-describedby="edit-more-info-response-help"
          required
          maxlength="1000"
          rows="4"
          placeholder="Updated the repository and added the requested documentation."
          class="mt-3 w-full rounded-[12px] border border-emerald-200 bg-white px-3 py-2 font-['Switzer'] text-[14px] leading-5 text-black outline-none transition-[border-color,box-shadow] focus:border-emerald-500 focus:shadow-[0_0_0_3px_rgba(5,150,105,0.12)]"
        ></textarea>
        <p class="mt-1 text-right font-['Switzer'] text-[11px] tabular-nums text-emerald-700">
          {moreInfoResponse.length}/1000
        </p>
      </section>
    {/if}
  {:else if resubmitMode}
    <header class="flex w-full flex-col gap-4 pb-2">
      <button
        type="button"
        onclick={() => push("/my-submissions")}
        class="group inline-flex min-h-10 w-fit items-center gap-2 rounded-full px-1 pr-3 text-[13px] font-medium text-[#6b6b6b] transition-[color,scale] hover:text-black active:scale-[0.96]"
      >
        <span class="flex h-8 w-8 items-center justify-center rounded-full bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.06),0_1px_2px_rgba(0,0,0,0.06)]">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </span>
        My submissions
      </button>
      <div>
        <p class="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-600">
          Corrected submission
        </p>
        <h1 class="submit-page-title text-balance text-[36px] font-medium leading-[42px] tracking-[-0.72px] text-black">
          Resubmit contribution
        </h1>
        <p class="mt-2 max-w-[500px] text-pretty text-[14px] leading-[21px] text-[#6b6b6b]">
          Review and update this copied content before creating a new submission. The rejected original and its appeal history remain unchanged.
        </p>
      </div>
    </header>

    {#if resubmitSource.staff_reply}
      <section class="w-full rounded-[16px] bg-red-50 p-5 shadow-[0_0_0_1px_rgba(220,38,38,0.14),0_8px_24px_rgba(220,38,38,0.04)]">
        <p class="font-['Switzer'] text-[12px] font-semibold uppercase tracking-[0.12em] text-red-800">Original rejection reason</p>
        <div class="feedback-markdown mt-2 font-['Switzer'] text-[14px] leading-[21px] text-red-950/80">
          {@html parseMarkdown(resubmitSource.staff_reply)}
        </div>
      </section>
    {/if}

    {#if cloneContextWarning}
      <section class="flex w-full items-start gap-3 rounded-[16px] bg-amber-50 p-4 shadow-[0_0_0_1px_rgba(217,119,6,0.16)]" role="status">
        <svg class="mt-0.5 h-5 w-5 shrink-0 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v3.75m9-1.875a9 9 0 11-18 0 9 9 0 0118 0zM12 16.5h.008v.008H12V16.5z" />
        </svg>
        <p class="text-pretty font-['Switzer'] text-[13px] leading-5 text-amber-900">{cloneContextWarning}</p>
      </section>
    {/if}
  {:else}
    <h1
      class="submit-page-title text-balance font-['F37_Lineca'] font-medium leading-[40px] text-[32px] text-black tracking-[-0.64px]"
    >
      Submit Contribution
    </h1>
  {/if}

  {#if !editMode}
    <div class="mobile-guidelines-slot w-full xl:hidden">
      <ContributionGuidelines
        contributionType={selectedType}
        mobile={true}
        onRoute={routeToType}
        {milestoneEligible}
      />
    </div>
  {/if}

  <form
    onsubmit={handleSubmit}
    class="w-full flex flex-col gap-[20px]"
    class:edit-form-content={editMode}
  >
    <!-- 1. Contribution Type Panel -->
    <div
      class="submit-panel flex flex-col gap-[12px] items-start p-[24px] rounded-[16px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] bg-white border border-[#f5f5f5] w-full"
    >
      <h2
        class="font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
      >
        Contribution Type
      </h2>

      <!-- Category Tabs -->
      <div
        class="category-tabs border border-[#f5f5f5] flex gap-[4px] items-start p-[4px] rounded-[24px] w-full bg-white"
      >
        <button
          type="button"
          onclick={() => selectCategory("builder")}
          disabled={selectionLocked || loadingTypes}
          aria-pressed={selectedCategory === "builder"}
          class="category-tab-button flex flex-[1_0_0] h-[40px] items-center justify-center p-[12px] rounded-[24px] transition-[background-color,color,scale,opacity] duration-150 ease-out active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100 {selectedCategory ===
          'builder'
            ? 'bg-[#e99322] text-white'
            : 'bg-[#f5f5f5] text-[#1a1c1d] hover:bg-gray-200'}"
        >
          <span
            class="font-['Switzer'] font-medium leading-[21px] text-[14px] tracking-[0.28px]"
            >Builder</span
          >
        </button>
        <button
          type="button"
          onclick={() => selectCategory("validator")}
          disabled={selectionLocked || loadingTypes}
          aria-pressed={selectedCategory === "validator"}
          class="category-tab-button flex flex-[1_0_0] h-[40px] items-center justify-center p-[12px] rounded-[24px] transition-[background-color,color,scale,opacity] duration-150 ease-out active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100 {selectedCategory ===
          'validator'
            ? 'bg-[#3b82f6] text-white'
            : 'bg-[#f5f5f5] text-[#1a1c1d] hover:bg-gray-200'}"
        >
          <span
            class="font-['Switzer'] font-medium leading-[21px] text-[14px] tracking-[0.28px]"
            >Validator</span
          >
        </button>
        <button
          type="button"
          onclick={() => selectCategory("community")}
          disabled={selectionLocked || loadingTypes}
          aria-pressed={selectedCategory === "community"}
          class="category-tab-button flex flex-[1_0_0] h-[40px] items-center justify-center p-[12px] rounded-[24px] transition-[background-color,color,scale,opacity] duration-150 ease-out active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100 {selectedCategory ===
          'community'
            ? 'bg-[#9333ea] text-white'
            : 'bg-[#f5f5f5] text-[#1a1c1d] hover:bg-gray-200'}"
        >
          <span
            class="font-['Switzer'] font-medium leading-[21px] text-[14px] tracking-[0.28px]"
            >Community</span
          >
        </button>
      </div>

      {#if missionLocked}
        <div class="flex w-full items-start gap-2 rounded-[10px] bg-indigo-50 px-3 py-2.5 text-indigo-900 shadow-[inset_0_0_0_1px_rgba(79,70,229,0.10)]">
          <svg class="mt-0.5 h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2h-1V9a4 4 0 00-8 0v2H6a2 2 0 00-2 2v6a2 2 0 002 2zm3-10V9a3 3 0 00-6 0v2h6z" />
          </svg>
          <p class="text-pretty font-['Switzer'] text-[12px] leading-[18px]">
            This contribution type is locked to <strong>{selectedMissionData?.name || "its original mission"}</strong>.
          </p>
        </div>
      {/if}

      {#if !canAccessCurrentCategory}
        <div
          class="flex items-start gap-3 rounded-[8px] border {gatingTheme.border} {gatingTheme.bg} p-4"
        >
          <svg
            class="h-5 w-5 flex-shrink-0 {gatingTheme.icon} mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M12 20a8 8 0 100-16 8 8 0 000 16z"
            />
          </svg>
          <div class="flex flex-col gap-1">
            {#if selectedCategory === "validator"}
              <p class="text-sm font-semibold {gatingTheme.title}">
                Validators only
              </p>
              <p class="text-sm {gatingTheme.body}">
                This category is reserved for selected validators. Start your
                validator journey from your profile to be considered.
              </p>
              <a
                href={journeysHref}
                class="text-sm font-medium underline {gatingTheme.link} mt-1"
                >Go to your journeys</a
              >
            {:else if selectedCategory === "builder"}
              <p class="text-sm font-semibold {gatingTheme.title}">
                Builders only
              </p>
              <p class="text-sm {gatingTheme.body}">
                Complete your Builder journey from your profile to unlock
                builder submissions.
              </p>
              <a
                href={journeysHref}
                class="text-sm font-medium underline {gatingTheme.link} mt-1"
                >Go to your journeys</a
              >
            {:else if selectedCategory === "community"}
              <p class="text-sm font-semibold {gatingTheme.title}">
                Creators only
              </p>
              <p class="text-sm {gatingTheme.body}">
                Complete the Creator journey to become a creator and unlock
                community submissions.
              </p>
              <a
                href="/community/journey"
                class="text-sm font-medium underline {gatingTheme.link} mt-1"
                >Go to Creator journey</a
              >
            {/if}
          </div>
        </div>
      {/if}

      <!-- Type Search/Dropdown Selection -->
      {#if canAccessCurrentCategory}
      <div class="relative w-full" bind:this={dropdownRef}>
        <div
          class="type-selector-control border {error && !formData.contribution_type
            ? 'border-red-400'
            : showTypeDropdown
              ? 'border-gray-400'
              : 'border-[#f5f5f5]'} flex h-[44px] items-center px-[8px] rounded-[8px] w-full bg-white hover:border-gray-300 transition-colors"
        >
          <svg
            class="w-4 h-4 text-gray-400 mr-2 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            class="type-search-input flex-1 bg-transparent font-['Switzer'] font-medium text-[14px] tracking-[0.28px] text-black placeholder-[#6b6b6b] focus:outline-none"
            placeholder={loadingTypes
              ? "Loading..."
              : selectionLocked
                ? appealLocked
                  ? "Editing paused"
                  : "Locked to mission"
              : "Search contribution type or mission..."}
            bind:value={searchQuery}
            oninput={handleSearchInput}
            onfocus={handleSearchFocus}
            onblur={handleSearchBlur}
            disabled={loadingTypes || selectionLocked}
          />
          <button
            type="button"
            onclick={() => (showTypeDropdown = !showTypeDropdown)}
            disabled={loadingTypes || selectionLocked}
            aria-label={showTypeDropdown ? "Close contribution type menu" : "Open contribution type menu"}
            class="ml-1 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full transition-[background-color,scale,opacity] duration-150 ease-out hover:bg-gray-100 active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:active:scale-100"
          >
            <svg
              class="w-4 h-4 text-gray-500 transform transition-transform {showTypeDropdown
                ? 'rotate-180'
                : ''}"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        </div>

        {#if showTypeDropdown}
          <div
            class="type-dropdown-menu absolute z-[60] top-[48px] left-0 right-0 bg-white border border-[#f5f5f5] rounded-[8px] shadow-lg max-h-[300px] overflow-y-auto"
          >
            {#if loadingTypes}
              <div class="p-4 text-center text-sm text-gray-500">
                Loading...
              </div>
            {:else if filteredItems.length === 0}
              <div class="p-4 text-center text-sm text-gray-500">
                No contribution types or missions found.
              </div>
            {:else}
              {#each filteredItems as item}
                {#if item.itemType === "typeHeader"}
                  <div
                    class="type-dropdown-item w-full text-left flex items-start flex-col p-[12px] bg-[#fafafa] border-b border-[#f5f5f5]"
                  >
                    <div class="flex items-center gap-2">
                      <span
                        class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.2px]"
                        >{item.data.name}</span
                      >
                      <span
                        class="bg-gray-100 text-gray-600 text-[11px] px-2 py-0.5 rounded-full font-medium"
                        >Mission only</span
                      >
                    </div>
                    <span
                      class="font-['Switzer'] text-[12px] text-gray-500 mt-1 text-left"
                    >
                      Select an active mission below to submit this contribution.
                    </span>
                  </div>
                {:else}
                  <button
                    type="button"
                    onclick={() => selectItem(item)}
                    class="type-dropdown-item w-full text-left flex items-start flex-col p-[12px] hover:bg-gray-50 border-b border-[#f5f5f5] last:border-0 {(item.itemType === 'type' && selectedType?.id === item.data.id && !selectedMission) || (item.itemType === 'mission' && selectedMission === item.data.id)
                      ? 'bg-[#f0f0ff]'
                      : ''}"
                  >
                    <div class="flex items-center gap-2">
                      <span
                        class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.2px]"
                        >{item.data.name}</span
                      >
                      {#if item.itemType === "mission"}
                        <span
                          class="bg-indigo-100 text-indigo-700 text-[11px] px-2 py-0.5 rounded-full font-medium"
                          >Mission</span
                        >
                      {/if}
                    </div>
                    {#if item.data.description}
                      <span
                        class="font-['Switzer'] text-[12px] text-gray-500 mt-1 text-left"
                      >
                        {#if item.data.description.length > 120}
                          {item.data.description.substring(0, 120)}...
                        {:else}
                          {item.data.description}
                        {/if}
                      </span>
                    {/if}
                    {#if item.itemType === "mission" && item.parentType}
                      <span
                        class="font-['Switzer'] text-[11px] text-gray-400 mt-0.5 italic"
                        >For: {item.parentType.name}</span
                      >
                    {/if}
                    {#if item.itemType === "mission" && item.data.max_submissions != null && item.data.submissions_remaining != null}
                      <span
                        class="font-['Switzer'] text-[11px] text-emerald-700 mt-0.5"
                        >{spotsLeftLabel(item.data.submissions_remaining)}</span
                      >
                    {/if}
                    {#if item.itemType === "type"}
                      <div class="mt-1 flex items-center gap-1">
                        <span
                          class="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded font-medium"
                          >{#if item.data.current_multiplier}{Math.round(
                              item.data.min_points * item.data.current_multiplier,
                            )} - {Math.round(
                              item.data.max_points * item.data.current_multiplier,
                            )} pts{:else}{item.data.min_points}
                            - {item.data.max_points} pts{/if}</span
                        >
                        {#if item.data.max_submissions != null && item.data.submissions_remaining != null}
                          <span
                            class="bg-emerald-100 text-emerald-700 text-xs px-2 py-0.5 rounded font-medium"
                            >{spotsLeftLabel(item.data.submissions_remaining)}</span
                          >
                        {/if}
                        {#if item.data.max_submissions_per_user_per_week != null && item.data.user_weekly_submissions_remaining != null}
                          <span
                            class="bg-indigo-100 text-indigo-700 text-xs px-2 py-0.5 rounded font-medium"
                            >{spotsLeftLabel(item.data.user_weekly_submissions_remaining)} this week</span
                          >
                        {/if}
                      </div>
                    {/if}
                  </button>
                {/if}
              {/each}
            {/if}
          </div>
        {/if}
      </div>
      {/if}

      <!-- Selection Info (shows details of selected type or mission) -->
      {#if selectedType && !showTypeDropdown}
        <div
          class="selection-info-card bg-[#fafafa] border border-[#f0f0f0] rounded-[8px] p-[12px] w-full"
        >
          {#if selectedMissionData}
            <div class="flex items-center gap-2 mb-1">
              <span
                class="font-['Switzer'] font-semibold text-[14px] text-black"
                >{selectedMissionData.name}</span
              >
              <span
                class="bg-indigo-100 text-indigo-700 text-[11px] px-2 py-0.5 rounded-full font-medium"
                >Mission</span
              >
            </div>
            {#if selectedMissionData.end_date}
              <p class="font-['Switzer'] text-[12px] text-gray-500">
                Ends: {new Date(selectedMissionData.end_date).toLocaleDateString(
                  "en-US",
                  { month: "long", day: "numeric", year: "numeric" },
                )}
              </p>
            {/if}
            <p class="font-['Switzer'] text-[12px] text-gray-500 mt-0.5">
              Type: {selectedType.name}
            </p>
            {#if selectedMissionData.max_submissions != null && selectedMissionData.submissions_remaining != null}
              <p class="font-['Switzer'] text-[12px] text-gray-500 mt-0.5">
                Mission capacity: {spotsLeftLabel(selectedMissionData.submissions_remaining)}
              </p>
            {/if}
          {:else}
            <span
              class="font-['Switzer'] font-semibold text-[14px] text-black"
              >{selectedType.name}</span
            >
            {#if isProjectType(selectedType)}
              <span
                class="ml-2 bg-orange-100 text-orange-700 text-[11px] px-2 py-0.5 rounded-full font-medium"
                >Project</span
              >
            {/if}
            {#if selectedType.max_submissions != null && selectedType.submissions_remaining != null}
              <p class="font-['Switzer'] text-[12px] text-gray-500 mt-0.5">
                Capacity: {spotsLeftLabel(selectedType.submissions_remaining)}
              </p>
            {/if}
            {#if selectedType.max_submissions_per_user_per_week != null && selectedType.user_weekly_submissions_remaining != null}
              <p class="font-['Switzer'] text-[12px] text-gray-500 mt-0.5">
                Your weekly capacity: {spotsLeftLabel(selectedType.user_weekly_submissions_remaining)}
              </p>
            {/if}
            {#if selectedType.description}
              <p class="font-['Switzer'] text-[12px] text-gray-500 mt-1">
                {selectedType.description}
              </p>
            {/if}
            <p class="font-['Switzer'] text-[12px] text-green-600 font-medium mt-1">
              {#if selectedType.current_multiplier}
                {Math.round(
                  selectedType.min_points * selectedType.current_multiplier,
                )} - {Math.round(
                  selectedType.max_points * selectedType.current_multiplier,
                )} pts
              {:else}
                {selectedType.min_points} - {selectedType.max_points} pts
              {/if}
            </p>
          {/if}
        </div>
      {/if}

    </div>

    {#if selectedType && isMilestoneType(selectedType) && !appealLocked}
      <div
        class="submit-panel linked-project-panel relative z-20 flex flex-col gap-[12px] items-start p-[24px] rounded-[16px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] bg-white border border-[#f5f5f5] w-full overflow-visible"
      >
        <div class="flex items-start justify-between gap-3 w-full">
          <div>
            <h2 class="font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]">
              Linked Project
            </h2>
            <p class="font-['Switzer'] text-[13px] text-[#6b6b6b] leading-[19px] tracking-[0.26px] mt-1">
              Milestones must belong to a highlighted project. Stewards review
              your project's GitHub repository for the changes you describe.
            </p>
          </div>
          {#if selectedProjectData}
            <span class="bg-indigo-100 text-indigo-700 text-[12px] px-2 py-1 rounded-full font-medium whitespace-nowrap">
              v{selectedProjectVersion}
            </span>
          {/if}
        </div>

        {#if loadingProjects}
          <div class="w-full rounded-[8px] border border-[#f5f5f5] bg-[#fafafa] p-[12px] text-[14px] text-[#6b6b6b] font-['Switzer']">
            Loading highlighted projects...
          </div>
        {:else if projectsError}
          <div class="w-full rounded-[8px] border border-red-200 bg-red-50 p-[12px]">
            <p class="font-['Switzer'] text-[14px] text-red-900 font-medium">
              We couldn't load your highlighted projects.
            </p>
            <button
              type="button"
              onclick={loadAcceptedProjects}
              class="mt-2 font-['Switzer'] text-[13px] font-medium text-red-700 underline hover:text-red-900"
            >
              Try again
            </button>
          </div>
        {:else if acceptedProjects.length === 0}
          <div class="w-full rounded-[12px] border border-orange-200 bg-orange-50 p-[16px]">
            <p class="text-pretty font-['Switzer'] text-[13px] leading-[19px] text-orange-900">
              Milestones are open only for highlighted projects. Highlighted projects are selected by the review team based on use case and real usage potential. Keep building your project through new submissions to get there.
            </p>
            <a
              href={`/contribution-type/${formData.contribution_type}`}
              class="mt-3 inline-flex min-h-10 items-center gap-1 font-['Switzer'] text-[13px] font-semibold text-orange-900 underline decoration-orange-300 underline-offset-4 transition-colors hover:text-orange-700 focus-visible:rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500"
            >
              Read full guidelines
              <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M3 8h10m-3-3 3 3-3 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </a>
          </div>
        {:else}
          <div
            class="project-dropdown-wrapper relative w-full"
            bind:this={projectDropdownRef}
            onfocusout={handleProjectDropdownFocusOut}
          >
            <button
              type="button"
              class="project-dropdown-trigger flex h-[44px] w-full items-center justify-between gap-3 rounded-[8px] border border-[#f5f5f5] bg-white px-[12px] text-left font-['Switzer'] text-[14px] text-black tracking-[0.28px] transition-[border-color,box-shadow,scale] duration-150 ease-out hover:border-gray-300 focus:border-black focus:outline-none active:scale-[0.96]"
              aria-haspopup="listbox"
              aria-expanded={showProjectDropdown}
              aria-controls="project-dropdown-menu"
              bind:this={projectDropdownButtonRef}
              onclick={toggleProjectDropdown}
              onkeydown={handleProjectTriggerKeydown}
            >
              <span class="min-w-0 truncate {selectedProject ? 'text-black' : 'text-[#6b6b6b]'}">
                {selectedProjectLabel}
              </span>
              <svg
                class="h-4 w-4 flex-shrink-0 text-gray-500 transition-transform {showProjectDropdown ? 'rotate-180' : ''}"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {#if showProjectDropdown}
              <div
                id="project-dropdown-menu"
                class="project-dropdown-menu absolute left-0 right-0 top-[48px] z-[60] max-h-[280px] overflow-y-auto rounded-[8px] border border-[#f0f0f0] bg-white shadow-[0_18px_48px_rgba(31,42,68,0.16)]"
                role="listbox"
              >
                {#each acceptedProjects as project, index}
                  <button
                    type="button"
                    class="project-dropdown-option flex min-h-10 w-full flex-col items-start border-b border-[#f5f5f5] p-[12px] text-left last:border-0 transition-[background-color] duration-150 ease-out hover:bg-gray-50 {String(project.id) === String(selectedProject) ? 'bg-[#f0f0ff]' : ''}"
                    role="option"
                    aria-selected={String(project.id) === String(selectedProject)}
                    tabindex={focusedProjectIndex === index ? 0 : -1}
                    bind:this={projectOptionRefs[index]}
                    onclick={() => selectProject(project)}
                    onkeydown={(event) => handleProjectOptionKeydown(event, index)}
                  >
                    <span class="font-['Switzer'] text-[14px] font-medium text-black tracking-[0.2px]">
                      {project.title}
                    </span>
                    <span class="mt-1 font-['Switzer'] text-[12px] text-[#6b6b6b]">
                      {#if editMode && submission?.project_contribution && String(submission.project_contribution?.id ?? submission.project_contribution) === String(project.id)}
                        Current milestone v{submission.milestone_version || 1}
                      {:else}
                        Next milestone v{project.next_milestone_version || 1}
                      {/if}
                    </span>
                    {#if project.github_url}
                      <span class="mt-0.5 max-w-full truncate font-['Switzer'] text-[11px] text-gray-400">
                        {project.github_url.replace(/^https?:\/\//, "")}
                      </span>
                    {/if}
                  </button>
                {/each}
              </div>
            {/if}
          </div>

          {#if selectedProjectData}
            <div class="w-full rounded-[8px] border border-[#f0f0f0] bg-[#fafafa] p-[12px]">
              <p class="font-['Switzer'] text-[13px] text-black font-medium">
                {selectedProjectData.title}
              </p>
              <p class="font-['Switzer'] text-[12px] text-[#6b6b6b] mt-1">
                {selectedProjectIsOriginal
                  ? `This submission remains milestone v${selectedProjectVersion}.`
                  : `This submission will be saved as milestone v${selectedProjectVersion}.`}
              </p>
              {#if selectedProjectData.github_url}
                <a
                  href={selectedProjectData.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 mt-2 font-['Switzer'] text-[12px] text-[#1a1c1d] font-medium hover:underline"
                >
                  <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                  </svg>
                  {selectedProjectData.github_url.replace(/^https?:\/\//, "")}
                </a>
                <p class="font-['Switzer'] text-[12px] text-[#6b6b6b] mt-1">
                  This repository will be reviewed for the changes in this milestone.
                </p>
              {:else}
                <p class="font-['Switzer'] text-[12px] text-orange-700 mt-2">
                  This project has no GitHub repository on file. Add the repository
                  link as evidence so stewards can verify your changes.
                </p>
              {/if}
            </div>
          {/if}
        {/if}
      </div>
    {/if}

    <!-- Social account linking gate: shown when type is selected but form can't be shown -->
    {#if selectedType && !canShowFormDetails && gateRequiredSocialAccounts.length > 0}
      <div
        class="gate-card flex flex-col gap-[8px] p-[20px] rounded-[12px] bg-[#fafafa] border border-[#e0e0e0] w-full"
      >
        <p class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.28px]">
          Link your {gateRequiredSocialAccounts.join(", ")} account{gateRequiredSocialAccounts.length > 1 ? "s" : ""} from your profile to submit this contribution.
        </p>
        <a
          href="/profile"
          class="font-['Switzer'] text-[13px] text-[#6b6b6b] hover:text-black transition-colors tracking-[0.26px]"
        >
          Go to profile →
        </a>
      </div>
    {/if}

    {#if selectedType && !canShowFormDetails && missingDiscordRoles.length > 0}
      <div
        class="gate-card flex flex-col gap-[8px] p-[20px] rounded-[12px] bg-[#fafafa] border border-[#e0e0e0] w-full"
      >
        <p class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.28px]">
          {$userStore.user?.discord_connection ? "You need one of these Discord roles to submit this contribution" : "Link Discord and make sure you have one of these roles"}: {missingDiscordRoles.join(", ")}.
        </p>
        <a
          href="/profile"
          class="font-['Switzer'] text-[13px] text-[#6b6b6b] hover:text-black transition-colors tracking-[0.26px]"
        >
          {$userStore.user?.discord_connection ? "Refresh Discord roles from profile" : "Go to profile"} →
        </a>
      </div>
    {/if}

    {#if canShowFormDetails && !appealLocked}
    <!-- 2. Contribution Details Panel -->
    <div
      class="submit-panel form-details-panel flex flex-col gap-[16px] items-start p-[24px] rounded-[16px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] bg-white border border-[#f5f5f5] w-full"
    >
      <!-- Date Picker -->
      <div class="field-section w-full flex flex-col gap-[12px]">
        <label
          for="contribution_date"
          class="field-label font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
        >
          Contribution Date
        </label>
        <div
          class="field-control border border-[#f5f5f5] flex h-[44px] items-center justify-between px-[12px] rounded-[8px] w-full bg-white relative hover:border-gray-300 focus-within:border-black transition-colors"
        >
          <input
            type="date"
            id="contribution_date"
            bind:value={formData.contribution_date}
            max={new Date().toISOString().split("T")[0]}
            class="w-full bg-transparent font-['Switzer'] font-medium text-[14px] text-black tracking-[0.28px] focus:outline-none focus:ring-0 outline-none"
            required
          />
        </div>
      </div>

      <!-- Title (optional) -->
      <div class="field-section w-full flex flex-col gap-[12px] mt-2">
        <label
          for="title"
          class="field-label font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
        >
          Title <span class="text-[14px] font-normal text-[#ababab]">(optional)</span>
        </label>
        <div
          class="field-control border border-[#f5f5f5] flex h-[44px] items-center px-[12px] rounded-[8px] w-full bg-white hover:border-gray-300 focus-within:border-black transition-colors"
        >
          <input
            type="text"
            id="title"
            bind:value={formData.title}
            maxlength="200"
            class="w-full bg-transparent font-['Switzer'] font-medium text-[14px] text-black tracking-[0.28px] placeholder-[#6b6b6b] focus:outline-none focus:ring-0 outline-none"
            placeholder="Give your contribution a title..."
          />
        </div>
      </div>

      <!-- Notes/Description -->
      <div class="field-section w-full flex flex-col gap-[12px] mt-2">
        <label
          for="notes"
          class="field-label font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
        >
          {#if isMilestoneType(selectedType)}
            Changes & Improvements <span class="text-[14px] font-normal text-[#e99322]">(required)</span>
          {:else}
            Notes / Description
          {/if}
        </label>
        {#if isMilestoneType(selectedType)}
          <p class="font-['Switzer'] text-[13px] text-[#6b6b6b] leading-[19px] tracking-[0.26px] -mt-1">
            This is the core of your milestone. Explain what you built, improved,
            or fixed; stewards verify it against your project's GitHub repository.
          </p>
        {/if}
        <div
          class="field-control border border-[#f5f5f5] flex flex-col items-start rounded-[8px] w-full bg-white hover:border-gray-300 focus-within:border-black transition-colors"
        >
          <textarea
            id="notes"
            bind:value={formData.notes}
            maxlength="1000"
            rows="5"
            class="w-full p-[16px] bg-transparent font-['Switzer'] text-[14px] text-black tracking-[0.24px] focus:outline-none focus:ring-0 outline-none resize-y min-h-[120px]"
            placeholder={isMilestoneType(selectedType)
              ? "Explain the changes and improvements in this milestone..."
              : "Describe your contribution..."}
            required={isMilestoneType(selectedType)}
          ></textarea>
        </div>
        <div class="flex items-center justify-end w-full">
          <span
            class="font-['Switzer'] text-[12px] tracking-[0.24px] {formData
              .notes.length === 1000
              ? 'text-red-500'
              : 'text-[#bababa]'}"
          >
            {formData.notes.length} / 1000
          </span>
        </div>
      </div>
    </div>

    <!-- 3. Evidence & Supporting Info -->
    <div
      class="submit-panel evidence-panel flex flex-col gap-[16px] items-start p-[24px] rounded-[16px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] bg-white border border-[#f5f5f5] w-full"
    >
      <!-- Header & Add Button -->
      <div
        class="evidence-header flex flex-col md:flex-row md:items-center justify-between w-full gap-[12px]"
      >
        <div class="flex flex-col gap-[4px] w-full md:max-w-[70%]">
          <h2
            class="font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
          >
            Evidence & Supporting Information
          </h2>
          <p
            class="font-['Switzer'] text-[14px] text-[#6b6b6b] leading-[21px] tracking-[0.28px]"
          >
            {#if isMilestoneType(selectedType)}
              Optional for milestones. Add links that support your update,
              like pull requests, demos, or posts.
            {:else}
              Get highlighted. Submit impactful or pioneering work to get
              highlighted and earn extra recognition.
            {/if}
          </p>
        </div>

        <button
          type="button"
          onclick={addEvidenceSlot}
          class="add-evidence-button bg-[#1a1c1d] flex gap-[8px] h-[40px] items-center justify-center px-[16px] rounded-[20px] hover:bg-black transition-[background-color,scale] duration-150 ease-out active:scale-[0.96] shrink-0"
        >
          <svg
            class="w-4 h-4 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
          <span
            class="font-['Switzer'] font-medium text-[14px] text-white tracking-[0.28px]"
          >
            Add Evidence
          </span>
        </button>
      </div>

      <!-- Required Evidence Slot (shown only when the contribution type requires specific URL types) -->
      {#if requiredEvidenceTypes.length > 0}
        <div
          class="required-evidence-card w-full border border-[#e99322] bg-[#fff8ee] rounded-[12px] p-[16px] flex flex-col gap-[10px] mt-2"
        >
          <div class="required-evidence-header flex items-center gap-2">
            <span
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#e99322] text-white text-[11px] font-['Switzer'] font-semibold uppercase tracking-wider"
              >Required</span
            >
            <span
              class="font-['Switzer'] text-[13px] text-[#1a1c1d] font-medium"
              >One of: {requiredEvidenceLabel}</span
            >
          </div>
          <div class="flex flex-col gap-1">
            <label
              for="required-evidence-url"
              class="font-['Switzer'] text-[12px] font-semibold text-gray-500 uppercase tracking-widest pl-1"
              >URL Link</label
            >
            <input
              id="required-evidence-url"
              type="url"
              bind:value={requiredEvidenceSlot.url}
              oninput={handleRequiredUrlInput}
              onblur={handleRequiredUrlBlur}
              placeholder={getRequiredUrlPlaceholder()}
              class="w-full px-3 py-2 border border-gray-200 rounded-[8px] text-[14px] focus:outline-none focus:border-gray-400 focus:bg-white bg-white font-mono transition-colors"
            />
          </div>
          <div class="evidence-status-row flex items-center gap-2">
            {#if requiredEvidenceSlot.selectedType}
              {#if requiredSlotSatisfied}
                <span
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-['Switzer'] font-medium bg-green-100 text-green-800"
                >
                  <svg
                    class="w-3 h-3"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  {requiredEvidenceSlot.selectedType.name}
                </span>
              {:else if requiredEvidenceSlot.url}
                <span
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-['Switzer'] font-medium bg-red-100 text-red-800"
                >
                  This URL isn't one of the required types
                </span>
              {/if}
            {:else}
              <span
                class="inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-['Switzer'] font-medium bg-gray-100 text-[#ababab]"
              >
                Paste a URL to auto-detect type
              </span>
            {/if}
          </div>
          {#if requiredEvidenceSlot.error}
            <p class="text-[12px] text-red-500 font-['Switzer'] pl-1">
              {requiredEvidenceSlot.error}
            </p>
          {/if}
        </div>
      {/if}

      <!-- Evidence Slots List -->
      <div class="w-full flex flex-col gap-4 mt-2">
        {#if evidenceSlots.length === 0}
          <div
            class="border border-[#f5f5f5] flex items-center justify-center p-[24px] w-full rounded-[8px] bg-gray-50/50"
            class:evidence-empty-state={true}
          >
            <p
              class="font-['Switzer'] font-medium text-[14px] text-[#ababab] tracking-[0.28px] text-center"
            >
              No evidence submitted yet. Click Add Evidence to attach links.
            </p>
          </div>
        {:else}
          {#each evidenceSlots as slot, index}
            <div
              class="evidence-slot-card border border-[#e0e0e0] rounded-[12px] p-[16px] bg-[#fcfcfc] flex flex-col gap-[12px] relative transition-[background-color,box-shadow] duration-150 ease-out group"
            >
              <!-- URL field (primary input) -->
              <div class="evidence-url-field flex flex-col gap-1 pr-[30px]">
                <label
                  for={`evidence-url-${index}`}
                  class="font-['Switzer'] text-[12px] font-semibold text-gray-500 uppercase tracking-widest pl-1"
                  >URL Link</label
                >
                <input
                  id={`evidence-url-${index}`}
                  type="url"
                  bind:value={slot.url}
                  oninput={() => handleUrlInput(index)}
                  onblur={() => handleUrlBlur(index)}
                  placeholder={getUrlPlaceholder(slot)}
                  class="w-full px-3 py-2 border border-gray-200 rounded-[8px] text-[14px] focus:outline-none focus:border-gray-400 focus:bg-white bg-transparent font-mono transition-colors"
                />
              </div>

              <!-- Detected type indicator + override dropdown -->
              {#if acceptedEvidenceTypes.length > 0}
                <div class="evidence-detected-row flex items-center gap-2 pr-[30px]">
                  {#if slot.selectedType}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-['Switzer'] font-medium bg-[#f0f0f0] text-[#1a1c1d]">
                      <svg class="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                      {slot.selectedType.is_generic ? "Other" : slot.selectedType.name}
                    </span>
                  {:else}
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-['Switzer'] font-medium bg-gray-100 text-[#ababab]">
                      Paste a URL to auto-detect type
                    </span>
                  {/if}
                  {#if acceptedEvidenceTypes.length > 1}
                    <select
                      value={slot.selectedType?.slug || ''}
                      onchange={(e) => handleEvidenceTypeChange(index, e.target.value)}
                      class="evidence-type-select text-[12px] font-['Switzer'] text-[#6b6b6b] bg-transparent border-none underline decoration-dotted underline-offset-2 cursor-pointer focus:outline-none appearance-none pr-0"
                    >
                      <option value="" disabled>Change type</option>
                      {#each acceptedEvidenceTypes as urlType}
                        {#if urlType.is_generic}
                          <option value={urlType.slug}>Other</option>
                        {:else}
                          <option value={urlType.slug}>{urlType.name}</option>
                        {/if}
                      {/each}
                    </select>
                  {/if}
                </div>
                <!-- Validation error if URL doesn't match selected type -->
                {#if slot.url && slot.selectedType && !slot.selectedType.is_generic && !urlMatchesType(slot.url, slot.selectedType)}
                  <p class="text-[12px] text-red-500 font-['Switzer'] pl-1 -mt-1">
                    This URL doesn't match the expected format for {slot.selectedType.name}.
                  </p>
                {/if}
              {/if}

              {#if slot.error}
                <p class="text-[12px] text-red-500 font-['Switzer'] pl-1 -mt-1">
                  {slot.error}
                </p>
              {/if}

              <!-- Delete Button -->
              <button
                type="button"
                onclick={() => removeEvidenceSlot(index)}
                class="absolute right-[8px] top-[8px] flex h-10 w-10 items-center justify-center rounded-full text-red-400 transition-[background-color,color,scale] duration-150 ease-out hover:bg-red-50 hover:text-red-600 active:scale-[0.96]"
                title="Remove evidence"
                aria-label="Remove evidence"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          {/each}
        {/if}
      </div>

      <!-- Social account linking banner for evidence URL types -->
      {#if evidenceRequiredAccounts.length > 0}
        <div class="gate-card w-full bg-[#fafafa] border border-[#e0e0e0] rounded-[12px] p-[16px] flex flex-col gap-[6px] mt-2">
          <p class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.28px]">
            Link your {evidenceRequiredAccounts.map((a) => socialAccountLabels[a] || a).join(", ")} account{evidenceRequiredAccounts.length > 1 ? "s" : ""} from your profile to verify evidence ownership.
          </p>
          <a
            href="/profile"
            class="font-['Switzer'] text-[13px] text-[#6b6b6b] hover:text-black transition-colors tracking-[0.26px]"
          >
            Go to profile →
          </a>
        </div>
      {/if}
    </div>

    {#if !editMode}
      <div class="recaptcha-area w-full">
        <div id="recaptcha-wrapper" class="flex justify-start"></div>
        {#if error && error.includes("reCAPTCHA")}
          <p class="text-red-500 text-[13px] mt-1 font-['Switzer']">{error}</p>
        {/if}
      </div>
    {/if}
    {/if}

    <!-- Error display -->
    {#if error && !error.includes("reCAPTCHA")}
      <div class="flex w-full items-start gap-3 rounded-[12px] bg-red-50 p-4 shadow-[inset_0_0_0_1px_rgba(220,38,38,0.12)]">
        <svg class="mt-0.5 h-5 w-5 shrink-0 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-1.875a9 9 0 11-18 0 9 9 0 0118 0zM12 16.5h.008v.008H12V16.5z" />
        </svg>
        <p class="text-pretty text-sm leading-5 text-red-700 font-['Switzer']">{error}</p>
      </div>
    {/if}

    {#if canShowFormDetails && !appealLocked}
    <!-- Actions -->
    <div class="form-actions flex gap-[8px] items-center mt-2 pb-[60px]">
      <button
        type="submit"
        disabled={submitting || deleting || !canSubmitCurrentCategory || evidenceRequiredAccounts.length > 0 || hasEvidencePatternMismatch}
        class="submit-action bg-[#9e4bf6] flex gap-[8px] h-[40px] items-center justify-center px-[20px] rounded-[20px] hover:bg-[#8b3ced] disabled:opacity-50 disabled:cursor-not-allowed transition-[background-color,scale,opacity] duration-150 ease-out active:scale-[0.96] disabled:active:scale-100"
      >
        <span
          class="font-['Switzer'] font-medium leading-[21px] text-[14px] text-white tracking-[0.28px]"
        >
          {#if submitting}
            {editMode
              ? requiresMoreInfoResponse
                ? "Resubmitting..."
                : "Saving..."
              : "Submitting..."}
          {:else}
            {editMode
              ? requiresMoreInfoResponse
                ? "Save and resubmit"
                : "Save changes"
              : resubmitMode
                ? "Resubmit Contribution"
                : "Submit Contribution"}
          {/if}
        </span>
        {#if !submitting}
          <svg
            class="w-4 h-4 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            {#if editMode}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            {:else}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            {/if}
          </svg>
        {/if}
      </button>

      <button
        type="button"
        onclick={() => push(editMode || resubmitMode ? "/my-submissions" : "/")}
        disabled={submitting || deleting}
        class="cancel-action bg-[#f5f5f5] flex h-[40px] items-center justify-center px-[20px] rounded-[20px] hover:bg-[#eaeaea] disabled:opacity-50 transition-[background-color,scale,opacity] duration-150 ease-out active:scale-[0.96] disabled:active:scale-100"
      >
        <span
          class="font-['Switzer'] font-medium leading-[21px] text-[14px] text-[#1a1c1d] tracking-[0.28px]"
        >
          Cancel
        </span>
      </button>

      {#if editMode}
        <button
          type="button"
          onclick={() => (showDeleteDialog = true)}
          disabled={submitting || deleting}
          class="remove-action flex h-[40px] items-center justify-center rounded-[20px] px-[16px] font-['Switzer'] text-[13px] font-medium text-red-600 transition-[background-color,color,scale,opacity] duration-150 ease-out hover:bg-red-50 hover:text-red-700 active:scale-[0.96] disabled:opacity-50 disabled:active:scale-100 sm:ml-auto"
        >
          Remove submission
        </button>
      {/if}
    </div>
    {/if}

    {#if editMode && !loadingTypes && (!canShowFormDetails || appealLocked)}
      <div class="form-actions flex w-full items-center gap-2 pb-[60px] pt-1">
        <button
          type="button"
          onclick={() => push("/my-submissions")}
          disabled={deleting}
          class="cancel-action flex h-10 items-center justify-center rounded-full bg-[#f5f5f5] px-5 font-['Switzer'] text-[14px] font-medium text-[#1a1c1d] transition-[background-color,scale,opacity] duration-150 ease-out hover:bg-[#eaeaea] active:scale-[0.96] disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onclick={() => (showDeleteDialog = true)}
          disabled={deleting}
          class="remove-action flex h-10 items-center justify-center rounded-full px-4 font-['Switzer'] text-[13px] font-medium text-red-600 transition-[background-color,color,scale,opacity] duration-150 ease-out hover:bg-red-50 hover:text-red-700 active:scale-[0.96] disabled:opacity-50 sm:ml-auto"
        >
          Remove submission
        </button>
      </div>
    {/if}
  </form>

  {#if !editMode}
    <aside class="desktop-guidelines-slot hidden xl:block" aria-label="Submission guidance">
      <ContributionGuidelines
        contributionType={selectedType}
        onRoute={routeToType}
        {milestoneEligible}
      />
    </aside>
  {/if}
</div>

<ConfirmDialog
  isOpen={showDeleteDialog}
  title="Remove submission?"
  message="This submission will be marked as canceled and can no longer be edited."
  confirmText="Remove submission"
  cancelText="Keep editing"
  loading={deleting}
  onConfirm={confirmDelete}
  onCancel={() => {
    if (!deleting) showDeleteDialog = false;
  }}
/>

<style>
  .submit-form-shell {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  @media (min-width: 1280px) {
    .submit-form-shell.with-guidelines {
      align-items: start;
      column-gap: 24px;
      display: grid;
      grid-template-columns: minmax(0, 550px) minmax(0, 360px);
      max-width: 934px !important;
      row-gap: 12px;
    }

    .submit-form-shell.with-guidelines > .submit-page-title {
      grid-column: 1;
      grid-row: 1;
    }

    .submit-form-shell.with-guidelines > form {
      grid-column: 1;
      grid-row: 2;
      min-width: 0;
    }

    .desktop-guidelines-slot {
      grid-column: 2;
      grid-row: 2;
      max-height: calc(100vh - 48px);
      min-width: 0;
      overflow-y: auto;
      position: sticky;
      top: 24px;
    }
  }

  .submit-panel {
    border-color: rgba(0, 0, 0, 0.055);
    box-shadow:
      0 1px 2px rgba(0, 0, 0, 0.025),
      0 8px 28px rgba(0, 0, 0, 0.035);
  }

  .edit-page-header,
  .review-feedback-card,
  .edit-form-content {
    animation: edit-content-enter 320ms cubic-bezier(0.22, 1, 0.36, 1)
      both;
  }

  .review-feedback-card {
    animation-delay: 60ms;
  }

  .edit-form-content {
    animation-delay: 110ms;
  }

  .feedback-markdown :global(p + p),
  .feedback-markdown :global(ul),
  .feedback-markdown :global(ol) {
    margin-top: 0.5rem;
  }

  .feedback-markdown :global(ul),
  .feedback-markdown :global(ol) {
    padding-left: 1.1rem;
  }

  .feedback-markdown :global(ul) {
    list-style: disc;
  }

  .feedback-markdown :global(ol) {
    list-style: decimal;
  }

  .feedback-markdown :global(a) {
    color: #1d4ed8;
    text-decoration: underline;
    text-decoration-color: rgba(29, 78, 216, 0.35);
    text-underline-offset: 2px;
  }

  @keyframes edit-content-enter {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .project-dropdown-wrapper {
    isolation: isolate;
  }

  .project-dropdown-menu {
    overscroll-behavior: contain;
  }

  @media (max-width: 767px) {
    .submit-form-shell {
      max-width: 100% !important;
      min-width: 0;
      /* clip, not hidden: overflow-x hidden forces computed overflow-y to
         auto, turning the shell into a scroll container that swallows the
         type dropdown (it opens below the shell's bottom edge when no type
         is selected yet). clip cuts horizontal bleed without capturing
         vertical overflow. */
      overflow-x: clip;
    }

    .submit-page-title {
      font-size: 28px;
      line-height: 32px;
      letter-spacing: 0 !important;
      overflow-wrap: anywhere;
    }

    .edit-page-header > div {
      align-items: flex-start;
      flex-direction: column;
    }

    .submit-panel {
      border-radius: 12px;
      gap: 12px;
      padding: 16px;
    }

    .submit-panel h2,
    .field-label {
      font-size: 17px;
      line-height: 22px;
      letter-spacing: 0 !important;
    }

    .category-tabs {
      border-radius: 14px;
      gap: 3px;
      padding: 3px;
    }

    .category-tab-button {
      border-radius: 12px;
      height: 36px;
      min-width: 0;
      padding: 8px 6px;
    }

    .category-tab-button span {
      display: block;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 12px;
      letter-spacing: 0 !important;
    }

    .type-selector-control,
    .project-dropdown-trigger,
    .field-control {
      min-width: 0;
    }

    .type-search-input {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 13px;
      letter-spacing: 0 !important;
    }

    .type-dropdown-menu {
      max-height: min(56vh, 320px);
      width: 100%;
    }

    .project-dropdown-menu {
      max-height: min(48vh, 280px);
    }

    .project-dropdown-option {
      min-width: 0;
    }

    .project-dropdown-option span {
      max-width: 100%;
      overflow-wrap: anywhere;
    }

    .type-dropdown-item {
      min-width: 0;
    }

    .type-dropdown-item > div,
    .type-dropdown-item span,
    .selection-info-card,
    .gate-card {
      max-width: 100%;
      min-width: 0;
      overflow-wrap: anywhere;
    }

    .selection-info-card {
      padding: 10px;
    }

    .gate-card {
      border-radius: 10px;
      padding: 14px;
    }

    .field-section {
      gap: 8px;
      margin-top: 0;
    }

    .field-control input,
    .field-control textarea,
    .required-evidence-card input,
    .evidence-slot-card input {
      min-width: 0;
      font-size: 13px;
      letter-spacing: 0 !important;
    }

    .field-control textarea {
      min-height: 108px;
      padding: 12px;
    }

    .evidence-header {
      gap: 14px;
    }

    .evidence-header > div {
      max-width: 100%;
    }

    .evidence-header p {
      font-size: 13px;
      line-height: 19px;
      letter-spacing: 0 !important;
    }

    .add-evidence-button {
      width: 100%;
      min-height: 40px;
      border-radius: 12px;
    }

    .required-evidence-card,
    .evidence-slot-card,
    .evidence-empty-state {
      border-radius: 10px;
      padding: 12px;
    }

    .required-evidence-header,
    .evidence-status-row,
    .evidence-detected-row {
      align-items: flex-start;
      flex-wrap: wrap;
      max-width: 100%;
    }

    .required-evidence-header span,
    .evidence-status-row span,
    .evidence-detected-row span {
      max-width: 100%;
      white-space: normal;
    }

    .evidence-url-field,
    .evidence-detected-row {
      padding-right: 28px;
    }

    .evidence-type-select {
      max-width: 100%;
      min-height: 32px;
      padding-right: 8px;
      white-space: normal;
    }

    .recaptcha-area {
      max-width: 100%;
      overflow: hidden;
    }

    .recaptcha-area :global(#recaptcha-wrapper) {
      transform: scale(0.86);
      transform-origin: left top;
      min-height: 68px;
    }

    .form-actions {
      align-items: stretch;
      flex-direction: column;
      padding-bottom: 24px;
      width: 100%;
    }

    .submit-action,
    .cancel-action,
    .remove-action {
      width: 100%;
      min-height: 42px;
    }

    .submit-action span,
    .cancel-action span {
      letter-spacing: 0 !important;
      white-space: nowrap;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .edit-page-header,
    .review-feedback-card,
    .edit-form-content {
      animation: none;
    }
  }
</style>
