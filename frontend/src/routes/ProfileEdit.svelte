<script>
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import { getCurrentUser, updateUserProfile, imageAPI } from "../lib/api";
  import { authState } from "../lib/auth";
  import Icon from "../components/Icons.svelte";
  import ImageCropper from "../components/ImageCropper.svelte";
  import { userStore } from "../lib/userStore";
  import { showSuccess, showError } from "../lib/toastStore";
  import GitHubLink from "../components/GitHubLink.svelte";

  // State management
  let user = $state(null);
  let authChecked = $state(false);
  let loading = $state(true);
  let error = $state("");
  let isSaving = $state(false);

  // Form fields
  let name = $state("");

  // New profile fields
  let email = $state("");
  let description = $state("");
  let website = $state("");
  let twitterHandle = $state("");
  let discordHandle = $state("");
  let telegramHandle = $state("");
  let linkedinHandle = $state("");
  let profileImageUrl = $state("");
  let bannerImageUrl = $state("");

  // Image upload states
  let showImageCropper = $state(false);
  let cropperImage = $state(null);
  let cropperAspectRatio = $state(1);
  let cropperTitle = $state("");
  let cropperCallback = $state(null);
  let uploadingImage = $state(false);

  // Validation state
  let nameError = $state("");
  let emailError = $state("");

  // Track if any field has changed
  let hasChanges = $derived(
    user &&
      (name !== (user.name || "") ||
        email !== (user.email || "") ||
        description !== (user.description || "") ||
        website !== (user.website || "") ||
        twitterHandle !== (user.twitter_handle || "") ||
        discordHandle !== (user.discord_handle || "") ||
        telegramHandle !== (user.telegram_handle || "") ||
        linkedinHandle !== (user.linkedin_handle || "")),
  );

  // Form validation
  let isFormValid = $derived(
    !nameError && !emailError && name.trim() !== "" && email.trim() !== "",
  );

  async function loadUserData() {
    // Check if user is authenticated
    if (!$authState.isAuthenticated) {
      // Redirect to home page if not authenticated
      push("/");
      return;
    }

    try {
      const userData = await getCurrentUser();
      user = userData;
      name = userData.name || "";

      // Load profile fields
      // Always show the email if it exists, regardless of verification status
      email = userData.email || "";
      description = userData.description || "";
      website = userData.website || "";
      twitterHandle = userData.twitter_handle || "";
      discordHandle = userData.discord_handle || "";
      telegramHandle = userData.telegram_handle || "";
      linkedinHandle = userData.linkedin_handle || "";
      profileImageUrl = userData.profile_image_url || "";
      bannerImageUrl = userData.banner_image_url || "";

      // Check for journey success message
      const journeySuccess = sessionStorage.getItem("journeySuccess");
      if (journeySuccess) {
        showSuccess(journeySuccess);
        sessionStorage.removeItem("journeySuccess");
      }
    } catch (err) {
      error = "Failed to load profile";
    } finally {
      authChecked = true;
    }
  }

  // React to auth state changes
  $effect(() => {
    loadUserData();
  });

  onMount(async () => {
    // Give auth state a moment to initialize
    await new Promise((resolve) => setTimeout(resolve, 100));
    loadUserData();
  });

  // Validation functions
  function validateName() {
    const trimmedName = name.trim();
    if (trimmedName === "") {
      nameError = "Display name is required";
      return false;
    }
    nameError = "";
    return true;
  }

  function validateEmail() {
    const trimmedEmail = email.trim();
    if (trimmedEmail === "") {
      emailError = "Email is required";
      return false;
    }
    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      emailError = "Please enter a valid email";
      return false;
    }
    emailError = "";
    return true;
  }

  async function handleSave() {
    if (!hasChanges) return;

    // Validate required fields
    const nameValid = validateName();
    const emailValid = validateEmail();

    if (!nameValid || !emailValid) {
      return; // Don't save if validation fails
    }

    error = "";
    isSaving = true;

    try {
      const updateData = {
        name: name.trim(),
        description: description.trim(),
        website: website.trim(),
        twitter_handle: twitterHandle.trim(),
        discord_handle: discordHandle.trim(),
        telegram_handle: telegramHandle.trim(),
        linkedin_handle: linkedinHandle.trim(),
      };

      // Only include email if it has changed
      const trimmedEmail = email.trim();
      if (trimmedEmail && trimmedEmail !== user.email) {
        updateData.email = trimmedEmail;
      }

      const updatedUser = await updateUserProfile(updateData);
      // Update the user store with new data
      userStore.updateUser(updatedUser);
      // Store success message in sessionStorage to show on profile page
      sessionStorage.setItem(
        "profileUpdateSuccess",
        "Profile updated successfully!",
      );
      // Redirect to public profile
      push(`/participant/${$authState.address}`);
    } catch (err) {
      // Handle field-specific errors from backend
      if (err.response?.data) {
        const data = err.response.data;

        // Check for field-specific errors and set appropriate error state
        if (data.email) {
          emailError = data.email; // Shows under email field with red border
        } else if (data.name) {
          nameError = data.name; // Shows under name field with red border
        } else {
          // General error (shows at top of form)
          error = data.error || err.message || "Failed to update profile";
        }
      } else {
        error = err.message || "Failed to update profile";
      }

      isSaving = false;
    }
  }

  function handleCancel() {
    // Go back to public profile without saving
    push(`/participant/${$authState.address}`);
  }

  function handleProfileImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      cropperImage = e.target.result;
      cropperAspectRatio = 1; // 1:1 for profile image
      cropperTitle = "Crop Profile Image";
      cropperCallback = uploadProfileImage;
      showImageCropper = true;
    };
    reader.readAsDataURL(file);
  }

  function handleBannerImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      cropperImage = e.target.result;
      cropperAspectRatio = 3; // 3:1 for banner (1500x500)
      cropperTitle = "Crop Banner Image";
      cropperCallback = uploadBannerImage;
      showImageCropper = true;
    };
    reader.readAsDataURL(file);
  }

  async function uploadProfileImage(blob) {
    showImageCropper = false;
    uploadingImage = true;
    error = "";

    try {
      const formData = new FormData();
      formData.append("image", blob, "profile.jpg");

      const response = await imageAPI.uploadProfileImage(formData);
      profileImageUrl = response.data.profile_image_url;
      user.profile_image_url = response.data.profile_image_url;

      // Update user store
      userStore.updateUser({
        profile_image_url: response.data.profile_image_url,
      });
    } catch (err) {
      error = err.response?.data?.error || "Failed to upload profile image";
    } finally {
      uploadingImage = false;
    }
  }

  async function uploadBannerImage(blob) {
    showImageCropper = false;
    uploadingImage = true;
    error = "";

    try {
      const formData = new FormData();
      formData.append("image", blob, "banner.jpg");

      const response = await imageAPI.uploadBannerImage(formData);
      bannerImageUrl = response.data.banner_image_url;
      user.banner_image_url = response.data.banner_image_url;

      // Update user store
      userStore.updateUser({
        banner_image_url: response.data.banner_image_url,
      });
    } catch (err) {
      error = err.response?.data?.error || "Failed to upload banner image";
    } finally {
      uploadingImage = false;
    }
  }

  function handleCropCancel() {
    showImageCropper = false;
    cropperImage = null;
  }

  async function handleGitHubLinked(updatedUser) {
    // Update local user state with the updated GitHub info
    user = updatedUser;
  }
</script>

<div class="max-w-[1024px] mx-auto px-4 py-8">
  {#if error}
    <div class="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
      <p class="text-red-700">{error}</p>
    </div>
  {/if}

  {#if user}
    <div
      class="bg-white rounded-[16px] overflow-hidden border border-[#f7f7f7] shadow-[0px_4px_12px_rgba(0,0,0,0.02)] mb-8"
    >
      <!-- Banner Image -->
      <div
        class="h-[200px] relative overflow-hidden bg-gradient-to-r from-purple-600 via-indigo-500 to-sky-400 group flex items-center justify-center"
      >
        {#if bannerImageUrl}
          <img
            src={bannerImageUrl}
            alt="Banner"
            class="w-full h-full object-cover mix-blend-overlay opacity-80"
          />
        {/if}
        <label
          class="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer"
        >
          <div
            class="bg-black/50 px-4 py-2 rounded-full text-white backdrop-blur-sm flex gap-2 items-center font-medium text-sm"
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
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            Edit Banner
          </div>
          <input
            type="file"
            accept="image/*"
            class="hidden"
            onchange={handleBannerImageSelect}
            disabled={uploadingImage}
          />
        </label>
      </div>

      <div class="p-[32px] bg-white relative">
        <div class="flex flex-col md:flex-row gap-10">
          <!-- Left Column (Avatar & Save Actions) -->
          <div
            class="flex-shrink-0 flex flex-col items-center transform -translate-y-[80px] w-full md:w-[240px]"
          >
            <div
              class="bg-black border-[4px] border-white rounded-full w-[160px] h-[160px] overflow-hidden relative group shadow-sm"
            >
              {#if profileImageUrl}
                <img
                  src={profileImageUrl}
                  alt="Profile"
                  class="w-full h-full object-cover"
                />
              {:else}
                <div
                  class="w-full h-full bg-gray-100 flex items-center justify-center text-gray-400"
                >
                  <svg
                    class="w-16 h-16 opacity-50"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    ><path
                      fill-rule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clip-rule="evenodd"
                    /></svg
                  >
                </div>
              {/if}
              <label
                class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer"
              >
                <svg
                  class="w-8 h-8 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  onchange={handleProfileImageSelect}
                  disabled={uploadingImage}
                />
              </label>
            </div>

            <!-- Save Actions -->
            <div class="w-full flex flex-col gap-3 mt-4">
              <button
                onclick={handleSave}
                disabled={!hasChanges || !isFormValid || isSaving}
                class="w-full px-4 py-3 bg-black text-white rounded-[8px] hover:bg-gray-800 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
                style="letter-spacing: 0.2px;"
              >
                {isSaving ? "Saving..." : "Save Changes"}
              </button>
              <button
                onclick={handleCancel}
                disabled={isSaving}
                class="w-full px-4 py-3 border border-gray-200 text-gray-700 bg-white rounded-[8px] hover:bg-gray-50 font-medium transition-colors"
              >
                Cancel
              </button>
            </div>

            <!-- Address field below save actions for convenience -->
            <div
              class="w-full mt-6 bg-[#f7f8f9] rounded-[8px] p-4 border border-[#f0f0f0]"
            >
              <span
                class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2"
                >Connected Wallet</span
              >
              <p class="text-black font-mono text-xs break-all opacity-80">
                {user.address || "Not connected"}
              </p>
            </div>
          </div>

          <!-- Right Column (Form Fields) -->
          <div class="flex-1 flex flex-col gap-8 md:pt-4">
            <!-- Basic Info Section -->
            <div class="flex flex-col gap-4">
              <h3
                class="text-[20px] font-semibold text-black tracking-[-0.36px]"
              >
                General Information
              </h3>

              <div class="space-y-4">
                <div>
                  <label
                    for="name"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >Display Name *</label
                  >
                  <input
                    id="name"
                    type="text"
                    bind:value={name}
                    oninput={validateName}
                    class="w-full px-4 py-3 bg-[#FCFCFC] border {nameError
                      ? 'border-red-300 focus:ring-red-500 rounded-[8px]'
                      : 'border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black'} transition-colors"
                    placeholder="Enter your display name"
                    disabled={isSaving}
                  />
                  {#if nameError}
                    <p class="mt-1 text-sm text-red-600">{nameError}</p>
                  {/if}
                </div>

                <div>
                  <label
                    for="email"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >Email *</label
                  >
                  <input
                    id="email"
                    type="email"
                    bind:value={email}
                    oninput={validateEmail}
                    class="w-full px-4 py-3 bg-[#FCFCFC] border {emailError
                      ? 'border-red-300 focus:ring-red-500 rounded-[8px]'
                      : 'border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black'} transition-colors"
                    placeholder="Enter your email"
                    disabled={isSaving}
                  />
                  {#if emailError}
                    <p class="mt-1 text-sm text-red-600">{emailError}</p>
                  {:else if user.email && user.email.endsWith("@ethereum.address")}
                    <p class="mt-1 text-xs text-orange-500">
                      Your current email is auto-generated. Enter a real email.
                    </p>
                  {:else if !user.is_email_verified}
                    <p class="mt-1 text-xs text-orange-500">
                      Email not verified
                    </p>
                  {/if}
                </div>

                <div>
                  <label
                    for="description"
                    class="block text-sm font-medium text-gray-600 mb-1.5 flex justify-between"
                  >
                    <span>Bio</span>
                    <span class="text-gray-400 font-normal"
                      >{description.length}/500</span
                    >
                  </label>
                  <textarea
                    id="description"
                    bind:value={description}
                    maxlength="500"
                    rows="4"
                    class="w-full px-4 py-3 bg-[#FCFCFC] border border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-colors resize-y"
                    placeholder="Tell us about yourself"
                    disabled={isSaving}
                  ></textarea>
                </div>
              </div>
            </div>

            <hr class="border-[#f0f0f0]" />

            <!-- Links & Socials Section -->
            <div class="flex flex-col gap-4">
              <h3
                class="text-[20px] font-semibold text-black tracking-[-0.36px]"
              >
                Links & Socials
              </h3>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label
                    for="website"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >Website</label
                  >
                  <input
                    id="website"
                    type="text"
                    bind:value={website}
                    class="w-full px-4 py-3 bg-[#FCFCFC] border border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-colors"
                    placeholder="yourwebsite.com"
                    disabled={isSaving}
                  />
                </div>

                <div>
                  <label
                    for="twitter"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >X (Twitter)</label
                  >
                  <div class="relative">
                    <span
                      class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-medium"
                      >@</span
                    >
                    <input
                      id="twitter"
                      type="text"
                      bind:value={twitterHandle}
                      class="w-full pl-9 pr-4 py-3 bg-[#FCFCFC] border border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-colors"
                      placeholder="username"
                      disabled={isSaving}
                    />
                  </div>
                </div>

                <div>
                  <label
                    for="discord"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >Discord</label
                  >
                  <input
                    id="discord"
                    type="text"
                    bind:value={discordHandle}
                    class="w-full px-4 py-3 bg-[#FCFCFC] border border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-colors"
                    placeholder="username"
                    disabled={isSaving}
                  />
                </div>

                <div>
                  <label
                    for="telegram"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >Telegram</label
                  >
                  <div class="relative">
                    <span
                      class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-medium"
                      >@</span
                    >
                    <input
                      id="telegram"
                      type="text"
                      bind:value={telegramHandle}
                      class="w-full pl-9 pr-4 py-3 bg-[#FCFCFC] border border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-colors"
                      placeholder="username"
                      disabled={isSaving}
                    />
                  </div>
                </div>

                <div>
                  <label
                    for="linkedin"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >LinkedIn</label
                  >
                  <input
                    id="linkedin"
                    type="text"
                    bind:value={linkedinHandle}
                    class="w-full px-4 py-3 bg-[#FCFCFC] border border-[#EAEAEA] rounded-[8px] focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-colors"
                    placeholder="linkedin.com/in/username"
                    disabled={isSaving}
                  />
                </div>

                <div>
                  <label
                    for="github"
                    class="block text-sm font-medium text-gray-600 mb-1.5"
                    >GitHub</label
                  >
                  {#if user.github_username}
                    <div class="flex items-center gap-2">
                      <div
                        class="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-[8px] text-gray-700 flex items-center gap-2"
                      >
                        <svg
                          class="w-5 h-5 opacity-70"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                          ><path
                            d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"
                          /></svg
                        >
                        <span class="font-medium">{user.github_username}</span>
                      </div>
                    </div>
                    {#if user.github_linked_at}
                      <p class="text-xs text-gray-400 mt-1">
                        Linked on {new Date(
                          user.github_linked_at,
                        ).toLocaleDateString()}
                      </p>
                    {/if}
                  {:else}
                    <div
                      class="h-[50px] w-full border border-gray-200 rounded-[8px] bg-[#FCFCFC] flex items-center px-4 justify-between"
                    >
                      <span class="text-sm text-gray-500">Not linked</span>
                      <GitHubLink onLinked={handleGitHubLinked} />
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {:else if !authChecked}
    <div
      class="bg-white rounded-[16px] overflow-hidden border border-[#f7f7f7] shadow-[0px_4px_12px_rgba(0,0,0,0.02)] mb-8 animate-pulse"
    >
      <!-- Banner skeleton -->
      <div
        class="h-[200px] bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200"
      ></div>

      <div class="p-[32px] bg-white relative">
        <div class="flex flex-col md:flex-row gap-10">
          <!-- Left Column skeleton -->
          <div
            class="flex-shrink-0 flex flex-col items-center transform -translate-y-[80px] w-full md:w-[240px]"
          >
            <div
              class="bg-gray-200 border-[4px] border-white rounded-full w-[160px] h-[160px]"
            ></div>
            <div class="w-full flex flex-col gap-3 mt-4">
              <div class="h-[48px] bg-gray-200 rounded-[8px]"></div>
              <div class="h-[48px] bg-gray-100 rounded-[8px]"></div>
            </div>
            <div
              class="w-full mt-6 bg-[#f7f8f9] rounded-[8px] p-4 border border-[#f0f0f0]"
            >
              <div class="h-3 w-28 bg-gray-200 rounded mb-2"></div>
              <div class="h-3 w-full bg-gray-200 rounded"></div>
            </div>
          </div>

          <!-- Right Column skeleton -->
          <div class="flex-1 flex flex-col gap-8 md:pt-4">
            <!-- General Information -->
            <div class="flex flex-col gap-4">
              <div class="h-6 w-48 bg-gray-200 rounded"></div>
              <div class="space-y-4">
                <div>
                  <div class="h-4 w-24 bg-gray-100 rounded mb-1.5"></div>
                  <div class="h-[48px] bg-gray-100 rounded-[8px]"></div>
                </div>
                <div>
                  <div class="h-4 w-16 bg-gray-100 rounded mb-1.5"></div>
                  <div class="h-[48px] bg-gray-100 rounded-[8px]"></div>
                </div>
                <div>
                  <div class="h-4 w-12 bg-gray-100 rounded mb-1.5"></div>
                  <div class="h-[96px] bg-gray-100 rounded-[8px]"></div>
                </div>
              </div>
            </div>

            <hr class="border-[#f0f0f0]" />

            <!-- Links & Socials -->
            <div class="flex flex-col gap-4">
              <div class="h-6 w-36 bg-gray-200 rounded"></div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {#each [1, 2, 3, 4, 5, 6] as _}
                  <div>
                    <div class="h-4 w-20 bg-gray-100 rounded mb-1.5"></div>
                    <div class="h-[48px] bg-gray-100 rounded-[8px]"></div>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  @font-face {
    font-family: "Switzer";
    src: url("/fonts/Switzer-Variable.woff2") format("woff2");
    font-weight: 100 900;
    font-style: normal;
  }
  .switzer-font {
    font-family: "Switzer", sans-serif;
  }
</style>
