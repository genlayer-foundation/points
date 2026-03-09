<script>
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import api from "../../../lib/api.js";
  import { getContributionTypes } from "../../../lib/api/contributions.js";
  import { authState } from "../../../lib/auth.js";
  import { userStore } from "../../../lib/userStore";

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
  let loadingTypes = $state(true);
  let selectedCategory = $state("builder"); // Default to builder
  let selectedType = $state(null);
  let showTypeDropdown = $state(false);

  // Form Data
  let formData = $state({
    contribution_type: "",
    contribution_date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  // Evidence Slots
  let evidenceSlots = $state([]);

  // Load types
  onMount(async () => {
    try {
      loadingTypes = true;
      const allTypes = await getContributionTypes({ is_submittable: "true" });

      // Filter out 'community' as requested
      types = allTypes.filter(
        /** @param {any} t */ (t) => t.category !== "community",
      );

      if (initialTypeId) {
        selectedType = types.find((t) => t.id === parseInt(initialTypeId));
        if (selectedType) {
          selectedCategory = selectedType.category;
          formData.contribution_type = selectedType.id;
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

  // Reactivity for category selection filtering
  let filteredTypes = $derived(
    types.filter((t) => t.category === selectedCategory),
  );

  $effect(() => {
    if (selectedType && selectedType.category !== selectedCategory) {
      // If we switch categories, clear the specific type selection
      selectedType = null;
      formData.contribution_type = "";
    }
  });

  function selectCategory(cat) {
    selectedCategory = cat;
    showTypeDropdown = false;
  }

  function selectType(t) {
    selectedType = t;
    formData.contribution_type = t.id;
    showTypeDropdown = false;
    if (error === "Please select a contribution type") error = "";
  }

  // Evidence functions
  function addEvidenceSlot() {
    evidenceSlots = [
      ...evidenceSlots,
      { id: Date.now(), description: "", url: "" },
    ];
  }

  function removeEvidenceSlot(index) {
    evidenceSlots = evidenceSlots.filter((_, i) => i !== index);
  }

  function normalizeUrl(url) {
    if (!url || url.trim() === "") return url;
    return /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url) ? url : "https://" + url;
  }

  function handleUrlBlur(index) {
    if (evidenceSlots[index]) {
      evidenceSlots[index].url = normalizeUrl(evidenceSlots[index].url);
    }
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
        error = `Evidence ${i + 1}: Please provide a URL along with the description`;
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
    const hasNotes = formData.notes?.trim().length > 0;

    if (!hasNotes && filledSlots.length === 0) {
      error =
        "Please provide either a description or evidence to support your contribution";
      return;
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
        notes: formData.notes,
        recaptcha: recaptchaToken,
      };

      if (missionId) {
        submissionData.mission = missionId;
      }

      const response = await api.post("/submissions/", submissionData);
      const submissionId = response.data.id;

      for (const slot of filledSlots) {
        await api.post(`/submissions/${submissionId}/add-evidence/`, {
          description: slot.description,
          url: normalizeUrl(slot.url),
        });
      }

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
      </div>

      <!-- Type Dropdown Selection -->
      <div class="relative w-full" bind:this={dropdownRef}>
        <button
          type="button"
          onclick={() => (showTypeDropdown = !showTypeDropdown)}
          class="border {error && !formData.contribution_type
            ? 'border-red-400'
            : 'border-[#f5f5f5]'} flex h-[44px] items-center justify-between p-[12px] rounded-[8px] w-full bg-white hover:border-gray-300 transition-colors"
        >
          <div class="flex gap-[8px] items-center">
            <svg
              class="w-4 h-4 text-gray-400"
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
            <span
              class="font-['Switzer'] font-medium text-[14px] tracking-[0.28px] {selectedType
                ? 'text-black'
                : 'text-[#6b6b6b]'}"
            >
              {selectedType ? selectedType.name : "Select contribution type"}
            </span>
          </div>
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

        {#if showTypeDropdown}
          <div
            class="absolute z-10 top-[48px] left-0 right-0 bg-white border border-[#f5f5f5] rounded-[8px] shadow-lg max-h-[250px] overflow-y-auto"
          >
            {#if loadingTypes}
              <div class="p-4 text-center text-sm text-gray-500">
                Loading...
              </div>
            {:else if filteredTypes.length === 0}
              <div class="p-4 text-center text-sm text-gray-500">
                No {selectedCategory} types available.
              </div>
            {:else}
              {#each filteredTypes as t}
                <button
                  type="button"
                  onclick={() => selectType(t)}
                  class="w-full text-left flex items-start flex-col p-[12px] hover:bg-gray-50 border-b border-[#f5f5f5] last:border-0"
                >
                  <span
                    class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.2px]"
                    >{t.name}</span
                  >
                  <span
                    class="font-['Switzer'] text-[12px] text-gray-500 mt-1 text-left"
                    >{t.description}</span
                  >
                  <div class="mt-1 flex items-center gap-1">
                    <span
                      class="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded font-medium"
                      >{#if t.current_multiplier}{Math.round(
                          t.min_points * t.current_multiplier,
                        )} - {Math.round(t.max_points * t.current_multiplier)} pts{:else}{t.min_points}
                        - {t.max_points} pts{/if}</span
                    >
                  </div>
                </button>
              {/each}
            {/if}
          </div>
        {/if}
      </div>
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
              <!-- Grid forces them to be responsive side by side -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-[16px] pr-[30px]">
                <div class="flex flex-col gap-1">
                  <label
                    class="font-['Switzer'] text-[12px] font-semibold text-gray-500 uppercase tracking-widest pl-1"
                    >Description</label
                  >
                  <input
                    type="text"
                    bind:value={slot.description}
                    placeholder="e.g. GitHub Pull Request"
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

    <!-- Actions -->
    <div class="flex gap-[8px] items-center mt-2 pb-[60px]">
      <button
        type="submit"
        disabled={submitting}
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
