<script>
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import api from "../../../lib/api.js";
  import { contributionsAPI } from "../../../lib/api.js";
  import { getContributionTypes } from "../../../lib/api/contributions.js";
  import { getMissions } from "../../../lib/missionsStore.js";
  import { authState } from "../../../lib/auth.js";
  import { userStore } from "../../../lib/userStore";
  import SocialLink from "../../SocialLink.svelte";

  // Props for routing/initialization state
  let { missionId = null, initialTypeId = null } = $props();

  let loading = $state(false);
  let submitting = $state(false);
  let error = $state("");

  // reCAPTCHA state
  let recaptchaToken = $state("");
  let recaptchaWidgetId = $state(null);
  const RECAPTCHA_SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY;

  // Selection & Types
  let types = $state([]);
  let missions = $state([]);
  let loadingTypes = $state(true);
  let selectedCategory = $state("builder"); // Default to builder
  let selectedType = $state(null);
  let selectedMission = $state(null);
  let selectedMissionData = $state(null);
  let showTypeDropdown = $state(false);
  let searchQuery = $state("");

  // Form Data
  let formData = $state({
    contribution_type: "",
    contribution_date: new Date().toISOString().split("T")[0],
    title: "",
    notes: "",
  });

  // Evidence Slots
  let evidenceSlots = $state([]);
  // All evidence URL types loaded from any contribution type's accepted list
  let allEvidenceUrlTypes = $state([]);

  // Load types and missions
  onMount(async () => {
    try {
      loadingTypes = true;
      const allTypes = await getContributionTypes({ is_submittable: "true" });

      types = allTypes;

      // Collect all unique evidence URL types from contribution types
      const urlTypeMap = new Map();
      for (const ct of allTypes) {
        for (const ut of ct.accepted_evidence_url_types || []) {
          if (!urlTypeMap.has(ut.slug)) urlTypeMap.set(ut.slug, ut);
        }
      }
      allEvidenceUrlTypes = Array.from(urlTypeMap.values()).sort(
        (a, b) => (a.order || 0) - (b.order || 0),
      );

      // Load missions
      try {
        missions = await getMissions({ is_active: true });
      } catch (err) {
        missions = [];
      }

      // Handle pre-selection from URL params
      if (missionId) {
        // Load the specific mission and pre-select it
        try {
          const response = await contributionsAPI.getMission(missionId);
          const mission = response.data;
          if (mission) {
            const parentType = types.find((t) => t.id === mission.contribution_type);
            if (parentType) {
              selectedType = parentType;
              selectedMission = mission.id;
              selectedMissionData = mission;
              selectedCategory = parentType.category || "builder";
              formData.contribution_type = parentType.id;
              searchQuery = mission.name;
            }
          }
        } catch (err) {
          console.error("Failed to load mission:", err);
        }
      } else if (initialTypeId) {
        // Load the specific type and pre-select it
        const type = types.find((t) => t.id === parseInt(initialTypeId));
        if (type) {
          selectedType = type;
          selectedCategory = type.category || "builder";
          formData.contribution_type = type.id;
          searchQuery = type.name;
        } else {
          // Type not in submittable list, try fetching directly
          try {
            const response = await contributionsAPI.getContributionType(initialTypeId);
            const type = response.data;
            if (type) {
              selectedCategory = type.category || "builder";
              selectedType = type;
              formData.contribution_type = type.id;
              searchQuery = type.name;
            }
          } catch (err) {
            console.error("Failed to load contribution type:", err);
          }
        }
      }
    } catch (err) {
      error = "Failed to load contribution categories.";
      console.error(err);
    } finally {
      loadingTypes = false;
    }

    // Initialize reCAPTCHA
    const checkRecaptcha = () => {
      if (renderRecaptcha()) return;
      setTimeout(checkRecaptcha, 100);
    };
    checkRecaptcha();

    return () => {
      if (recaptchaWidgetId !== null && window.grecaptcha) {
        try {
          window.grecaptcha.reset(recaptchaWidgetId);
        } catch (e) {}
      }
    };
  });

  // Map from ownership_social_account to the social platform info
  const ownershipPlatformMap = {
    twitter: { platform: "twitter", label: "X", field: "twitter_connection", initiateUrl: "/api/auth/twitter/" },
    github: { platform: "github", label: "GitHub", field: "github_connection", initiateUrl: "/api/auth/github/" },
  };

  // Detect which social accounts are required by evidence URLs but not linked
  let evidenceRequiredAccounts = $derived.by(() => {
    const user = $userStore.user;
    if (!user) return [];
    const needed = new Set();
    for (const slot of evidenceSlots) {
      const type = slot.selectedType;
      if (!type || type.is_generic) continue;
      const slugToAccount = {
        "x-post": "twitter",
        "github-repo": "github",
        "github-file": "github",
      };
      const account = slugToAccount[type.slug];
      if (account) {
        const info = ownershipPlatformMap[account];
        if (info && !user[info.field]) {
          needed.add(account);
        }
      }
    }
    return Array.from(needed);
  });

  function handleEvidenceSocialLinked(updatedUser) {
    userStore.setUser(updatedUser);
  }

  // Check if selected type requires social accounts the user hasn't linked
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

  // Build filtered items list (types + missions) based on category and search
  let filteredItems = $derived.by(() => {
    const categoryTypes = types.filter((t) => t.category === selectedCategory);
    const categoryMissions = missions.filter((m) => {
      const mType = types.find((t) => t.id === m.contribution_type);
      return mType && mType.category === selectedCategory;
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
        matchingMissions.map((m) => m.contribution_type),
      );
      matchingTypes = categoryTypes.filter(
        (t) => matchingTypes.includes(t) || typeIdsWithMatchingMissions.has(t.id),
      );
    }

    // Build flat list: types followed by their missions
    const items = [];
    matchingTypes.forEach((type) => {
      items.push({ itemType: "type", data: type });
      const typeMissions = matchingMissions.filter(
        (m) => m.contribution_type === type.id,
      );
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
      formData.contribution_type = "";
      searchQuery = "";
    }
  });

  function selectCategory(cat) {
    selectedCategory = cat;
    showTypeDropdown = false;
  }

  function selectType(t) {
    selectedType = t;
    selectedMission = null;
    selectedMissionData = null;
    formData.contribution_type = t.id;
    showTypeDropdown = false;
    searchQuery = t.name;
    if (error === "Please select a contribution type") error = "";
  }

  function selectItem(item) {
    if (item.itemType === "type") {
      selectType(item.data);
    } else if (item.itemType === "mission") {
      selectedType = item.parentType;
      selectedMission = item.data.id;
      selectedMissionData = item.data;
      formData.contribution_type = item.parentType.id;
      showTypeDropdown = false;
      searchQuery = item.data.name;
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

  // Evidence functions
  function addEvidenceSlot() {
    evidenceSlots = [
      ...evidenceSlots,
      { id: Date.now(), description: "", url: "", selectedType: null },
    ];
  }

  function removeEvidenceSlot(index) {
    evidenceSlots = evidenceSlots.filter((_, i) => i !== index);
  }

  function normalizeUrl(url) {
    if (!url || url.trim() === "") return url;
    return /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url) ? url : "https://" + url;
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

  function handleUrlBlur(index) {
    if (evidenceSlots[index]) {
      evidenceSlots[index].url = normalizeUrl(evidenceSlots[index].url);
      // Auto-detect and pre-select URL type if not already chosen
      const detected = detectUrlType(evidenceSlots[index].url);
      evidenceSlots[index].detectedType = detected;
      if (detected && !evidenceSlots[index].selectedType) {
        evidenceSlots[index].selectedType = detected;
      }
    }
  }

  function handleEvidenceTypeChange(index, slug) {
    const urlType = acceptedEvidenceTypes.find(t => t.slug === slug) || null;
    evidenceSlots[index].selectedType = urlType;
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
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  // Submission
  async function handleSubmit(e) {
    e.preventDefault();

    if (!formData.contribution_type) {
      error = "Please select a contribution type";
      return;
    }

    if (formData.notes.length > 1000) {
      error = "Notes cannot exceed 1000 characters";
      return;
    }

    for (let i = 0; i < evidenceSlots.length; i++) {
      const slot = evidenceSlots[i];
      const hasDescription =
        slot.description && slot.description.trim().length > 0;
      const hasUrl = slot.url && slot.url.trim().length > 0;

      if (hasDescription && !hasUrl) {
        error = `Evidence ${i + 1}: A URL is required for each evidence item`;
        return;
      }
      if (hasUrl && !hasDescription) {
        error = `Evidence ${i + 1}: Please provide a description along with the URL`;
        return;
      }
    }

    const filledSlots = evidenceSlots.filter(
      (s) => s.description?.trim() && s.url?.trim(),
    );

    if (filledSlots.length === 0) {
      error =
        "Please add at least one evidence item with a URL to support your contribution";
      return;
    }

    // Client-side: validate that selected evidence type matches the URL
    for (let i = 0; i < filledSlots.length; i++) {
      const slot = filledSlots[i];
      if (slot.selectedType && !slot.selectedType.is_generic) {
        const detected = detectUrlType(slot.url);
        if (detected && !detected.is_generic && detected.slug !== slot.selectedType.slug) {
          error = `Evidence ${i + 1}: The URL doesn't look like a ${slot.selectedType.name}. It was detected as ${detected.name}.`;
          return;
        }
      }
    }

    if (!recaptchaToken) {
      error = "Please complete the reCAPTCHA verification";
      return;
    }

    submitting = true;
    error = "";

    try {
      const submissionData = {
        contribution_type: formData.contribution_type,
        contribution_date: formData.contribution_date + "T00:00:00Z",
        title: formData.title,
        notes: formData.notes,
        recaptcha: recaptchaToken,
      };

      // Include mission if selected (from URL param or dropdown selection)
      const missionToSubmit = selectedMission || missionId;
      if (missionToSubmit) {
        submissionData.mission = missionToSubmit;
      }

      // Send evidence inline with the submission (atomic creation)
      submissionData.evidence_items = filledSlots.map((slot) => ({
        description: slot.description,
        url: normalizeUrl(slot.url),
      }));

      await api.post("/submissions/", submissionData);

      sessionStorage.setItem(
        "submissionUpdateSuccess",
        "Your contribution has been submitted successfully and is pending review.",
      );
      push("/my-submissions");
    } catch (err) {
      if (err.response?.data?.recaptcha) {
        error = Array.isArray(err.response.data.recaptcha)
          ? err.response.data.recaptcha[0]
          : err.response.data.recaptcha;
      } else if (err.response?.data?.evidence_items) {
        // Parse evidence validation errors from backend
        const evidenceErrors = err.response.data.evidence_items;
        if (Array.isArray(evidenceErrors) && evidenceErrors.length > 0) {
          const first = evidenceErrors[0];
          error = first.message || JSON.stringify(first);
        } else {
          error = typeof evidenceErrors === "string"
            ? evidenceErrors
            : JSON.stringify(evidenceErrors);
        }
      } else {
        error =
          err.response?.data?.error ||
          err.response?.data?.detail ||
          "Failed to submit contribution";
      }

      if (recaptchaWidgetId !== null && window.grecaptcha) {
        try {
          window.grecaptcha.reset(recaptchaWidgetId);
          recaptchaToken = "";
        } catch (e) {}
      }
    } finally {
      submitting = false;
    }
  }

  // Click outside listener for dropdown
  let dropdownRef;
  function handleClickOutside(event) {
    if (
      showTypeDropdown &&
      dropdownRef &&
      !dropdownRef.contains(event.target)
    ) {
      showTypeDropdown = false;
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div
  class="content-stretch flex flex-col gap-[12px] items-start relative shrink-0 w-full"
  style="max-width: 550px; margin: 0 auto;"
>
  <!-- Title -->
  <h1
    class="font-['F37_Lineca'] font-medium leading-[40px] text-[32px] text-black tracking-[-0.64px]"
  >
    Submit Contribution
  </h1>

  <form onsubmit={handleSubmit} class="w-full flex flex-col gap-[20px]">
    <!-- 1. Contribution Type Panel -->
    <div
      class="flex flex-col gap-[12px] items-start p-[24px] rounded-[16px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] bg-white border border-[#f5f5f5] w-full"
    >
      <h2
        class="font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
      >
        Contribution Type
      </h2>

      <!-- Category Tabs (Builder / Validator) -->
      <div
        class="border border-[#f5f5f5] flex gap-[4px] items-start p-[4px] rounded-[24px] w-full bg-white"
      >
        <button
          type="button"
          onclick={() => selectCategory("builder")}
          class="flex flex-[1_0_0] h-[40px] items-center justify-center p-[12px] rounded-[24px] transition-colors {selectedCategory ===
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
          class="flex flex-[1_0_0] h-[40px] items-center justify-center p-[12px] rounded-[24px] transition-colors {selectedCategory ===
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
          class="flex flex-[1_0_0] h-[40px] items-center justify-center p-[12px] rounded-[24px] transition-colors {selectedCategory ===
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

      <!-- Type Search/Dropdown Selection -->
      <div class="relative w-full" bind:this={dropdownRef}>
        <div
          class="border {error && !formData.contribution_type
            ? 'border-red-400'
            : showTypeDropdown
              ? 'border-gray-400'
              : 'border-[#f5f5f5]'} flex h-[44px] items-center p-[12px] rounded-[8px] w-full bg-white hover:border-gray-300 transition-colors"
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
            class="flex-1 bg-transparent font-['Switzer'] font-medium text-[14px] tracking-[0.28px] text-black placeholder-[#6b6b6b] focus:outline-none"
            placeholder={loadingTypes
              ? "Loading..."
              : "Search contribution type or mission..."}
            bind:value={searchQuery}
            oninput={handleSearchInput}
            onfocus={handleSearchFocus}
            onblur={handleSearchBlur}
            disabled={loadingTypes}
          />
          <button
            type="button"
            onclick={() => (showTypeDropdown = !showTypeDropdown)}
            class="flex-shrink-0 ml-1"
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
            class="absolute z-10 top-[48px] left-0 right-0 bg-white border border-[#f5f5f5] rounded-[8px] shadow-lg max-h-[300px] overflow-y-auto"
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
                <button
                  type="button"
                  onclick={() => selectItem(item)}
                  class="w-full text-left flex items-start flex-col p-[12px] hover:bg-gray-50 border-b border-[#f5f5f5] last:border-0 {(item.itemType === 'type' && selectedType?.id === item.data.id && !selectedMission) || (item.itemType === 'mission' && selectedMission === item.data.id)
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
                    </div>
                  {/if}
                </button>
              {/each}
            {/if}
          </div>
        {/if}
      </div>

      <!-- Selection Info (shows details of selected type or mission) -->
      {#if selectedType && !showTypeDropdown}
        <div
          class="bg-[#fafafa] border border-[#f0f0f0] rounded-[8px] p-[12px] w-full"
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
          {:else}
            <span
              class="font-['Switzer'] font-semibold text-[14px] text-black"
              >{selectedType.name}</span
            >
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

    <!-- 2. Contribution Details Panel -->
    <div
      class="flex flex-col gap-[16px] items-start p-[24px] rounded-[16px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] bg-white border border-[#f5f5f5] w-full"
    >
      <!-- Date Picker -->
      <div class="w-full flex flex-col gap-[12px]">
        <label
          for="contribution_date"
          class="font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
        >
          Contribution Date
        </label>
        <div
          class="border border-[#f5f5f5] flex h-[44px] items-center justify-between px-[12px] rounded-[8px] w-full bg-white relative hover:border-gray-300 focus-within:border-black transition-colors"
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
      <div class="w-full flex flex-col gap-[12px] mt-2">
        <label
          for="title"
          class="font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
        >
          Title <span class="text-[14px] font-normal text-[#ababab]">(optional)</span>
        </label>
        <div
          class="border border-[#f5f5f5] flex h-[44px] items-center px-[12px] rounded-[8px] w-full bg-white hover:border-gray-300 focus-within:border-black transition-colors"
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
      <div class="w-full flex flex-col gap-[12px] mt-2">
        <label
          for="notes"
          class="font-['Switzer'] font-semibold leading-[25px] text-[20px] text-black tracking-[0.4px]"
        >
          Notes / Description
        </label>
        <div
          class="border border-[#f5f5f5] flex flex-col items-start rounded-[8px] w-full bg-white hover:border-gray-300 focus-within:border-black transition-colors"
        >
          <textarea
            id="notes"
            bind:value={formData.notes}
            maxlength="1000"
            rows="5"
            class="w-full p-[16px] bg-transparent font-['Switzer'] text-[14px] text-black tracking-[0.24px] focus:outline-none focus:ring-0 outline-none resize-y min-h-[120px]"
            placeholder="Describe your contribution..."
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
      class="flex flex-col gap-[16px] items-start p-[24px] rounded-[16px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] bg-white border border-[#f5f5f5] w-full"
    >
      <!-- Header & Add Button -->
      <div
        class="flex flex-col md:flex-row md:items-center justify-between w-full gap-[12px]"
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
            Get highlighted. Submit impactful or pioneering work to get
            highlighted and earn extra recognition.
          </p>
        </div>

        <button
          type="button"
          onclick={addEvidenceSlot}
          class="bg-[#1a1c1d] flex gap-[8px] h-[40px] items-center justify-center px-[16px] rounded-[20px] hover:bg-black transition-colors shrink-0"
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

      <!-- Evidence Slots List -->
      <div class="w-full flex flex-col gap-4 mt-2">
        {#if evidenceSlots.length === 0}
          <div
            class="border border-[#f5f5f5] flex items-center justify-center p-[24px] w-full rounded-[8px] bg-gray-50/50"
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
              class="border border-[#e0e0e0] rounded-[12px] p-[16px] bg-[#fcfcfc] flex flex-col gap-[12px] relative transition-all group"
            >
              <!-- Evidence Type Selector -->
              {#if acceptedEvidenceTypes.length > 0}
                <div class="flex flex-col gap-1 pr-[30px]">
                  <label
                    class="font-['Switzer'] text-[12px] font-semibold text-gray-500 uppercase tracking-widest pl-1"
                    >Evidence Type</label
                  >
                  <select
                    value={slot.selectedType?.slug || ''}
                    onchange={(e) => handleEvidenceTypeChange(index, e.target.value)}
                    class="w-full px-3 py-2 border border-gray-200 rounded-[8px] text-[14px] focus:outline-none focus:border-gray-400 focus:bg-white bg-transparent transition-colors appearance-none"
                  >
                    <option value="">Select type...</option>
                    {#each acceptedEvidenceTypes as urlType}
                      {#if urlType.is_generic}
                        <option value={urlType.slug}>Other</option>
                      {:else}
                        <option value={urlType.slug}>{urlType.name}</option>
                      {/if}
                    {/each}
                  </select>
                </div>
              {/if}

              <!-- Description + URL side by side -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-[16px] pr-[30px]">
                <div class="flex flex-col gap-1">
                  <label
                    class="font-['Switzer'] text-[12px] font-semibold text-gray-500 uppercase tracking-widest pl-1"
                    >Description</label
                  >
                  <input
                    type="text"
                    bind:value={slot.description}
                    placeholder="e.g. My GenLayer intelligent contract"
                    class="w-full px-3 py-2 border border-gray-200 rounded-[8px] text-[14px] focus:outline-none focus:border-gray-400 focus:bg-white bg-transparent transition-colors"
                  />
                </div>
                <div class="flex flex-col gap-1">
                  <label
                    class="font-['Switzer'] text-[12px] font-semibold text-gray-500 uppercase tracking-widest pl-1"
                    >URL Link</label
                  >
                  <input
                    type="url"
                    bind:value={slot.url}
                    onblur={() => handleUrlBlur(index)}
                    placeholder="https://..."
                    class="w-full px-3 py-2 border border-gray-200 rounded-[8px] text-[14px] focus:outline-none focus:border-gray-400 focus:bg-white bg-transparent font-mono transition-colors"
                  />
                  {#if slot.detectedType && slot.selectedType && !slot.selectedType.is_generic && slot.detectedType.slug !== slot.selectedType.slug && !slot.detectedType.is_generic}
                    <p class="text-[11px] text-amber-600 font-['Switzer'] mt-1">
                      This URL looks like a {slot.detectedType.name}, not a {slot.selectedType.name}
                    </p>
                  {/if}
                </div>
              </div>

              <!-- Delete Button -->
              <button
                type="button"
                onclick={() => removeEvidenceSlot(index)}
                class="absolute top-[16px] right-[16px] w-[24px] h-[24px] flex justify-center items-center rounded-full text-red-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                title="Remove evidence"
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
        <div class="w-full bg-amber-50 border border-amber-200 rounded-[12px] p-[16px] flex flex-col gap-[12px] mt-2">
          <p class="font-['Switzer'] text-[14px] text-amber-800 leading-[21px]">
            Your evidence requires a linked account to verify ownership. Please link below to continue.
          </p>
          <div class="flex flex-wrap gap-3">
            {#each evidenceRequiredAccounts as account}
              {@const info = ownershipPlatformMap[account]}
              {#if info}
                <SocialLink
                  platform={info.platform}
                  platformLabel={info.label}
                  connection={$userStore.user?.[info.field]}
                  initiateUrl={info.initiateUrl}
                  onLinked={handleEvidenceSocialLinked}
                  compact={true}
                />
              {/if}
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <!-- recaptcha -->
    <div class="w-full">
      <div id="recaptcha-wrapper" class="flex justify-start"></div>
      {#if error && error.includes("reCAPTCHA")}
        <p class="text-red-500 text-[13px] mt-1 font-['Switzer']">{error}</p>
      {/if}
    </div>

    <!-- Error display -->
    {#if error}
      <div class="w-full bg-red-50 border-l-4 border-red-500 p-4 rounded-md">
        <p class="text-red-700 text-sm font-['Switzer']">{error}</p>
      </div>
    {/if}

    {#if missingSocialAccounts.length > 0}
      <div class="w-full bg-amber-50 border-l-4 border-amber-500 p-4 rounded-md">
        <p class="text-amber-700 text-sm font-['Switzer']">
          This contribution type requires a linked {missingSocialAccounts.join(" and ")} account. Please link your account in your profile before submitting.
        </p>
      </div>
    {/if}

    <!-- Actions -->
    <div class="flex gap-[8px] items-center mt-2 pb-[60px]">
      <button
        type="submit"
        disabled={submitting || missingSocialAccounts.length > 0 || evidenceRequiredAccounts.length > 0}
        class="bg-[#9e4bf6] flex gap-[8px] h-[40px] items-center justify-center px-[20px] rounded-[20px] hover:bg-[#8b3ced] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <span
          class="font-['Switzer'] font-medium leading-[21px] text-[14px] text-white tracking-[0.28px]"
        >
          {submitting ? "Submitting..." : "Submit Contribution"}
        </span>
        {#if !submitting}
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
              d="M14 5l7 7m0 0l-7 7m7-7H3"
            />
          </svg>
        {/if}
      </button>

      <button
        type="button"
        onclick={() => push("/")}
        disabled={submitting}
        class="bg-[#f5f5f5] flex h-[40px] items-center justify-center px-[20px] rounded-[20px] hover:bg-[#eaeaea] disabled:opacity-50 transition-colors"
      >
        <span
          class="font-['Switzer'] font-medium leading-[21px] text-[14px] text-[#1a1c1d] tracking-[0.28px]"
        >
          Cancel
        </span>
      </button>
    </div>
  </form>
</div>
