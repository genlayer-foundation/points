<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { getCurrentUser, updateUserProfile, imageAPI } from '../lib/api';
  import { authState } from '../lib/auth';
  import { journeyAPI, creatorAPI, validatorsAPI } from '../lib/api';
  import Icon from '../components/Icons.svelte';
  import ImageCropper from '../components/ImageCropper.svelte';
  import { userStore } from '../lib/userStore';
  import { showSuccess, showError } from '../lib/toastStore';
  import GitHubLink from '../components/GitHubLink.svelte';
  
  // State management
  let user = $state(null);
  let authChecked = $state(false);
  let loading = $state(true);
  let error = $state('');
  let isSaving = $state(false);
  
  // Form fields
  let name = $state('');
  let nodeVersion = $state('');
  
  // New profile fields
  let email = $state('');
  let description = $state('');
  let website = $state('');
  let twitterHandle = $state('');
  let discordHandle = $state('');
  let telegramHandle = $state('');
  let linkedinHandle = $state('');
  let profileImageUrl = $state('');
  let bannerImageUrl = $state('');
  
  // Image upload states
  let showImageCropper = $state(false);
  let cropperImage = $state(null);
  let cropperAspectRatio = $state(1);
  let cropperTitle = $state('');
  let cropperCallback = $state(null);
  let uploadingImage = $state(false);

  // Operator address linking state
  let operatorAddress = $state('');
  let isLinkingWallets = $state(false);
  let validatorWallets = $state([]);

  // Validation state
  let nameError = $state('');
  let emailError = $state('');

  // Track if any field has changed
  let hasChanges = $derived(user && (
    name !== (user.name || '') ||
    (user.validator && nodeVersion !== (user.validator?.node_version || '')) ||
    email !== (user.email || '') ||
    description !== (user.description || '') ||
    website !== (user.website || '') ||
    twitterHandle !== (user.twitter_handle || '') ||
    discordHandle !== (user.discord_handle || '') ||
    telegramHandle !== (user.telegram_handle || '') ||
    linkedinHandle !== (user.linkedin_handle || '')
  ));

  // Form validation
  let isFormValid = $derived(!nameError && !emailError && name.trim() !== '' && email.trim() !== '');
  
  async function loadUserData() {
    // Check if user is authenticated
    if (!$authState.isAuthenticated) {
      // Redirect to home page if not authenticated
      push('/');
      return;
    }
    
    try {
      const userData = await getCurrentUser();
      user = userData;
      name = userData.name || '';
      nodeVersion = userData.validator?.node_version || '';
      
      // Load profile fields
      // Always show the email if it exists, regardless of verification status
      email = userData.email || '';
      description = userData.description || '';
      website = userData.website || '';
      twitterHandle = userData.twitter_handle || '';
      discordHandle = userData.discord_handle || '';
      telegramHandle = userData.telegram_handle || '';
      linkedinHandle = userData.linkedin_handle || '';
      profileImageUrl = userData.profile_image_url || '';
      bannerImageUrl = userData.banner_image_url || '';

      // Check for journey success message
      const journeySuccess = sessionStorage.getItem('journeySuccess');
      if (journeySuccess) {
        showSuccess(journeySuccess);
        sessionStorage.removeItem('journeySuccess');
      }

      // Load validator wallets if user is a validator
      if (userData.validator) {
        try {
          const walletsResponse = await validatorsAPI.getMyValidatorWallets();
          validatorWallets = walletsResponse.data.wallets || [];
        } catch (err) {
          validatorWallets = [];
        }
      }
    } catch (err) {
      error = 'Failed to load profile';
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
    await new Promise(resolve => setTimeout(resolve, 100));
    loadUserData();
  });

  // Validation functions
  function validateName() {
    const trimmedName = name.trim();
    if (trimmedName === '') {
      nameError = 'Display name is required';
      return false;
    }
    nameError = '';
    return true;
  }

  function validateEmail() {
    const trimmedEmail = email.trim();
    if (trimmedEmail === '') {
      emailError = 'Email is required';
      return false;
    }
    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      emailError = 'Please enter a valid email';
      return false;
    }
    emailError = '';
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

    error = '';
    isSaving = true;

    try {
      const updateData = {
        name: name.trim(),
        description: description.trim(),
        website: website.trim(),
        twitter_handle: twitterHandle.trim(),
        discord_handle: discordHandle.trim(),
        telegram_handle: telegramHandle.trim(),
        linkedin_handle: linkedinHandle.trim()
      };

      // Only include email if it has changed
      const trimmedEmail = email.trim();
      if (trimmedEmail && trimmedEmail !== user.email) {
        updateData.email = trimmedEmail;
      }
      
      // Only include node_version if it has changed
      if (nodeVersion !== (user.validator?.node_version || '')) {
        updateData.node_version = nodeVersion;
      }
      
      const updatedUser = await updateUserProfile(updateData);
      // Update the user store with new data
      userStore.updateUser(updatedUser);
      // Store success message in sessionStorage to show on profile page
      sessionStorage.setItem('profileUpdateSuccess', 'Profile updated successfully!');
      // Redirect to public profile
      push(`/participant/${$authState.address}`);
    } catch (err) {
      // Handle field-specific errors from backend
      if (err.response?.data) {
        const data = err.response.data;

        // Check for field-specific errors and set appropriate error state
        if (data.email) {
          emailError = data.email;  // Shows under email field with red border
        } else if (data.name) {
          nameError = data.name;    // Shows under name field with red border
        } else {
          // General error (shows at top of form)
          error = data.error || err.message || 'Failed to update profile';
        }
      } else {
        error = err.message || 'Failed to update profile';
      }

      isSaving = false;
    }
  }
  
  function handleCancel() {
    // Go back to public profile without saving
    push(`/participant/${$authState.address}`);
  }
  
  async function startValidatorJourney() {
    // Redirect to validator waitlist join page
    push('/validators/waitlist/join');
  }
  
  async function startBuilderJourney() {
    // Redirect to builder welcome page
    push('/builders/welcome');
  }

  async function startCreatorJourney() {
    try {
      const response = await creatorAPI.joinAsCreator();
      if (response.status === 201 || response.status === 200) {
        // Store success message and reload
        sessionStorage.setItem('journeySuccess', 'You are now a Supporter! Start growing the community through referrals.');
        loadUserData();
      }
    } catch (err) {
      error = err.response?.data?.message || 'Failed to join as supporter';
    }
  }

  async function handleLinkWallets() {
    if (!operatorAddress.trim()) {
      showError('Please enter an operator address');
      return;
    }

    isLinkingWallets = true;
    try {
      const response = await validatorsAPI.linkValidatorWalletsByOperator(operatorAddress.trim());
      const walletsLinked = response.data.wallets_linked;
      showSuccess(`Successfully linked ${walletsLinked} wallet${walletsLinked !== 1 ? 's' : ''}`);
      // Refresh data to update the UI
      await loadUserData();
      operatorAddress = '';
    } catch (err) {
      const message = err.response?.data?.error || 'Failed to link wallets';
      showError(message);
    } finally {
      isLinkingWallets = false;
    }
  }


  function handleProfileImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      cropperImage = e.target.result;
      cropperAspectRatio = 1; // 1:1 for profile image
      cropperTitle = 'Crop Profile Image';
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
      cropperTitle = 'Crop Banner Image';
      cropperCallback = uploadBannerImage;
      showImageCropper = true;
    };
    reader.readAsDataURL(file);
  }
  
  async function uploadProfileImage(blob) {
    showImageCropper = false;
    uploadingImage = true;
    error = '';
    
    try {
      const formData = new FormData();
      formData.append('image', blob, 'profile.jpg');
      
      const response = await imageAPI.uploadProfileImage(formData);
      profileImageUrl = response.data.profile_image_url;
      user.profile_image_url = response.data.profile_image_url;
      
      // Update user store
      userStore.updateUser({ profile_image_url: response.data.profile_image_url });
    } catch (err) {
      error = err.response?.data?.error || 'Failed to upload profile image';
    } finally {
      uploadingImage = false;
    }
  }
  
  async function uploadBannerImage(blob) {
    showImageCropper = false;
    uploadingImage = true;
    error = '';
    
    try {
      const formData = new FormData();
      formData.append('image', blob, 'banner.jpg');
      
      const response = await imageAPI.uploadBannerImage(formData);
      bannerImageUrl = response.data.banner_image_url;
      user.banner_image_url = response.data.banner_image_url;
      
      // Update user store
      userStore.updateUser({ banner_image_url: response.data.banner_image_url });
    } catch (err) {
      error = err.response?.data?.error || 'Failed to upload banner image';
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

<div class="container mx-auto px-4 py-8">
  {#if error}
    <div class="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
      <p class="text-red-700">{error}</p>
    </div>
  {/if}

  {#if user}
    <!-- Profile Information -->
    <div class="bg-white shadow rounded-lg p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-6">Profile Information</h2>
      
      <!-- Wallet Address -->
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2">Wallet Address</label>
        <p class="text-gray-900 font-mono text-sm break-all bg-gray-50 px-3 py-2 rounded">{user.address || 'Not connected'}</p>
      </div>
      
      <!-- Display Name -->
      <div class="mb-6">
        <label for="name" class="block text-sm font-medium text-gray-700 mb-2">Display Name *</label>
        <input
          id="name"
          type="text"
          bind:value={name}
          oninput={validateName}
          class="w-full px-3 py-2 border {nameError ? 'border-red-300 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'} rounded-md focus:outline-none focus:ring-2"
          placeholder="Enter your display name"
          disabled={isSaving}
        />
        {#if nameError}
          <p class="mt-1 text-sm text-red-600">{nameError}</p>
        {/if}
      </div>
      
      <!-- Bio -->
      <div class="mb-6">
        <label for="description" class="block text-sm font-medium text-gray-700 mb-2">
          Bio <span class="text-gray-500 text-xs">({description.length}/500)</span>
        </label>
        <textarea
          id="description"
          bind:value={description}
          maxlength="500"
          rows="4"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Tell us about yourself"
          disabled={isSaving}
        />
      </div>
      
      <!-- Images Section -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <!-- Profile Image -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Profile Image</label>
          <div class="flex items-center gap-3">
            <div class="w-20 h-20 rounded-full bg-gray-200 overflow-hidden flex-shrink-0">
              {#if profileImageUrl}
                <img src={profileImageUrl} alt="Profile" class="w-full h-full object-cover" />
              {:else}
                <div class="w-full h-full flex items-center justify-center text-gray-400">
                  <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" />
                  </svg>
                </div>
              {/if}
            </div>
            <div>
              <label>
                <input type="file" accept="image/*" class="hidden" onchange={handleProfileImageSelect} disabled={uploadingImage} />
                <span class="inline-block px-4 py-2 bg-blue-600 text-white rounded-md cursor-pointer hover:bg-blue-700 transition-colors text-sm">
                  {uploadingImage ? 'Uploading...' : 'Choose Image'}
                </span>
              </label>
              <p class="mt-1 text-xs text-gray-500">400x400px recommended</p>
            </div>
          </div>
        </div>
        
        <!-- Banner Image -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Banner Image</label>
          <div class="flex items-center gap-3">
            <div class="w-20 h-20 bg-gray-200 rounded overflow-hidden flex-shrink-0">
              {#if bannerImageUrl}
                <img src={bannerImageUrl} alt="Banner" class="w-full h-full object-cover" />
              {:else}
                <div class="w-full h-full flex items-center justify-center text-gray-400">
                  <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              {/if}
            </div>
            <div>
              <label>
                <input type="file" accept="image/*" class="hidden" onchange={handleBannerImageSelect} disabled={uploadingImage} />
                <span class="inline-block px-4 py-2 bg-blue-600 text-white rounded-md cursor-pointer hover:bg-blue-700 transition-colors text-sm">
                  {uploadingImage ? 'Uploading...' : 'Choose Image'}
                </span>
              </label>
              <p class="mt-1 text-xs text-gray-500">1500x500px recommended</p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Separator -->
      <hr class="my-6 border-gray-200" />
      
      <!-- Contact Information Section -->
      <h3 class="text-md font-semibold text-gray-900 mb-4">Contact Information</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Email -->
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-2">
            Email *
          </label>
          <input
            id="email"
            type="email"
            bind:value={email}
            oninput={validateEmail}
            class="w-full px-3 py-2 border {emailError ? 'border-red-300 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'} rounded-md focus:outline-none focus:ring-2"
            placeholder="Enter your email"
            disabled={isSaving}
          />
          {#if emailError}
            <p class="mt-1 text-sm text-red-600">{emailError}</p>
          {:else if user.email && user.email.endsWith('@ethereum.address')}
            <p class="mt-1 text-xs text-gray-500">Your current email is auto-generated. Enter a real email to update it.</p>
          {:else if !user.is_email_verified}
            <p class="mt-1 text-xs text-gray-500">Email not verified</p>
          {/if}
        </div>
        
        <!-- Website -->
        <div>
          <label for="website" class="block text-sm font-medium text-gray-700 mb-2">Website</label>
          <input
            id="website"
            type="text"
            bind:value={website}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="yourwebsite.com"
            disabled={isSaving}
          />
          <p class="text-xs text-gray-500 mt-1">You can enter with or without https://</p>
        </div>
        
        <!-- Twitter/X -->
        <div>
          <label for="twitter" class="block text-sm font-medium text-gray-700 mb-2">Twitter/X</label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">@</span>
            <input
              id="twitter"
              type="text"
              bind:value={twitterHandle}
              class="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="username"
              disabled={isSaving}
            />
          </div>
        </div>
        
        <!-- Discord -->
        <div>
          <label for="discord" class="block text-sm font-medium text-gray-700 mb-2">Discord</label>
          <input
            id="discord"
            type="text"
            bind:value={discordHandle}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="username"
            disabled={isSaving}
          />
        </div>
        
        <!-- Telegram -->
        <div>
          <label for="telegram" class="block text-sm font-medium text-gray-700 mb-2">Telegram</label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">@</span>
            <input
              id="telegram"
              type="text"
              bind:value={telegramHandle}
              class="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="username"
              disabled={isSaving}
            />
          </div>
        </div>
        
        <!-- LinkedIn -->
        <div>
          <label for="linkedin" class="block text-sm font-medium text-gray-700 mb-2">LinkedIn</label>
          <input
            id="linkedin"
            type="text"
            bind:value={linkedinHandle}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="linkedin.com/in/username"
            disabled={isSaving}
          />
          <p class="text-xs text-gray-500 mt-1">Enter your LinkedIn username or profile URL</p>
        </div>

        <!-- GitHub -->
        <div>
          <label for="github" class="block text-sm font-medium text-gray-700 mb-2">GitHub</label>
          {#if user.github_username}
            <div class="flex items-center gap-2">
              <div class="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-gray-700 flex items-center gap-2">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 0C4.477 0 0 4.477 0 10c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.341-3.369-1.341-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0110 4.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C17.137 18.163 20 14.418 20 10c0-5.523-4.477-10-10-10z" clip-rule="evenodd"/>
                </svg>
                {user.github_username}
              </div>
              <a
                href="https://github.com/{user.github_username}"
                target="_blank"
                rel="noopener noreferrer"
                class="px-3 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md flex items-center gap-1"
                title="View GitHub profile"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
              </a>
            </div>
            {#if user.github_linked_at}
              <p class="text-xs text-gray-500 mt-1">Linked on {new Date(user.github_linked_at).toLocaleDateString()}</p>
            {/if}
          {:else}
            <GitHubLink
              onLinked={handleGitHubLinked}
            />
            <p class="text-xs text-gray-500 mt-1">Link your GitHub to participate in builder programs</p>
          {/if}
        </div>
      </div>
    </div>
    
    <!-- Removed Validator Settings - moved to profile section below -->
    
    <!-- Profile Sections -->
      <!-- Active Profiles (100% width) -->
      
      <!-- Steward (Always first if active) -->
      {#if user.steward}
        <div class="bg-green-100 shadow rounded-lg p-6 border border-green-300 mt-6">
          <h2 class="text-lg font-semibold text-green-900 mb-4 flex items-center">
            <Icon name="steward" className="mr-2 text-green-700" />
            Steward
          </h2>
          <div class="text-sm">
            <p class="text-green-800 font-medium">
              Thanks for keeping things running smoothly around here 🛡️
            </p>
            <p class="text-gray-700 mt-2">
              Your steward profile is active. You have access to review and manage community submissions.
            </p>
            <p class="text-xs text-green-700 mt-3">Profile created: {user.steward.created_at ? new Date(user.steward.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : ''}</p>
          </div>
        </div>
      {/if}
      
      <!-- Builder (Active profile) -->
      {#if user.builder}
        <div class="bg-orange-100 shadow rounded-lg p-6 border border-orange-300 mt-6" data-profile-type="builder">
          <h2 class="text-lg font-semibold text-orange-900 mb-4 flex items-center">
            <Icon name="builder" className="mr-2 text-orange-700" />
            Builder
          </h2>
          <div class="text-sm text-orange-800">
            <p>You're building on GenLayer! Keep creating.</p>
          </div>
        </div>
      {/if}
      
      <!-- Validator (Active profile) -->
      {#if user.validator}
        <div class="bg-sky-100 shadow rounded-lg p-6 border border-sky-300 mt-6" data-profile-type="validator">
          <h2 class="text-lg font-semibold text-sky-900 mb-4 flex items-center">
            <Icon name="validator" className="mr-2 text-sky-700" />
            Validator
          </h2>
          <div class="text-sm text-sky-800">
            <p class="mb-4">You're running a validator node! Keep it up.</p>
            
            <!-- Node Version Field -->
            <div>
              <label for="nodeVersion" class="block text-sm font-medium text-sky-900 mb-2">
                Node Version
              </label>
              
              {#if user?.validator?.target_version}
                {#if user?.validator?.matches_target}
                  <div class="bg-green-50 border border-green-200 rounded-md p-3 mb-3 text-sm">
                    <span class="text-green-800">✓ Your node is up to date with target version {user.validator.target_version}</span>
                  </div>
                {:else}
                  <div class="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-3 text-sm">
                    <span class="text-yellow-800">⚠ Please update your node to version {user.validator.target_version}</span>
                  </div>
                {/if}
              {/if}
              
              <div class="flex gap-3 items-start">
                <div class="flex-1">
                  <input
                    id="nodeVersion"
                    type="text"
                    bind:value={nodeVersion}
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
                    placeholder="e.g., 0.3.9"
                    disabled={isSaving}
                  />
                  <p class="mt-2 text-xs text-sky-700">Enter your current GenLayer node version</p>
                </div>

                {#if user.validator && nodeVersion !== (user.validator?.node_version || '')}
                  <button
                    onclick={handleSave}
                    disabled={!isFormValid || isSaving}
                    class="px-4 py-2 bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSaving ? 'Saving...' : 'Save'}
                  </button>
                {/if}
              </div>
            </div>

            <!-- Link Validator Wallets (only show if no wallets linked) -->
            {#if validatorWallets.length === 0}
              <div class="mt-6 pt-4 border-t border-sky-200">
                <label for="operatorAddress" class="block text-sm font-medium text-sky-900 mb-2">
                  Link to Operator Wallet
                </label>
                <p class="text-xs text-sky-700 mb-3">
                  Enter the operator wallet address you used when creating your validator on GenLayer.
                </p>
                <div class="flex gap-3 items-start">
                  <div class="flex-1">
                    <input
                      id="operatorAddress"
                      type="text"
                      bind:value={operatorAddress}
                      class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white font-mono text-sm"
                      placeholder="0x..."
                      maxlength="42"
                      disabled={isLinkingWallets}
                    />
                  </div>
                  <button
                    onclick={handleLinkWallets}
                    disabled={isLinkingWallets || !operatorAddress.trim()}
                    class="px-4 py-2 bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLinkingWallets ? 'Linking...' : 'Link Wallets'}
                  </button>
                </div>
              </div>
            {/if}
          </div>
        </div>
      {/if}
      
      <!-- Waitlist/Welcome Profiles -->
      {#if user.has_builder_welcome && !user.builder}
        <div class="bg-orange-100 shadow rounded-lg p-6 border border-orange-300 mt-6" data-profile-type="builder">
          <h2 class="text-lg font-semibold text-orange-900 mb-4 flex items-center">
            <Icon name="builder" className="mr-2 text-orange-700" />
            Builder Welcome
          </h2>
          <p class="text-sm text-orange-800">You've started building! Keep deploying contracts to level up.</p>
        </div>
      {/if}
      
      {#if user.has_validator_waitlist && !user.validator}
        <div class="bg-sky-100 shadow rounded-lg p-6 border border-sky-300 mt-6" data-profile-type="validator">
          <h2 class="text-lg font-semibold text-sky-900 mb-4 flex items-center">
            <Icon name="validator" className="mr-2 text-sky-700" />
            Validator Waitlist
          </h2>
          <p class="text-sm text-sky-800">You're on the waitlist! Keep earning points to become a validator.</p>
        </div>
      {/if}
      
      <!-- Remaining Inactive Profiles (2 columns or 100% if only one) -->
      {@const needsBuilder = !user.builder && !user.has_builder_welcome}
      {@const needsValidator = !user.validator && !user.has_validator_waitlist}
      {@const needsSteward = !user.steward}
      {@const needsSupporter = !user.creator}
      {@const inactiveCount = [needsBuilder, needsValidator, needsSteward, needsSupporter].filter(Boolean).length}

      {#if needsBuilder || needsValidator}
        <div class="{(needsBuilder && needsValidator) ? 'grid grid-cols-1 md:grid-cols-2 gap-4 mt-6' : 'mt-6'}">
          {#if needsBuilder}
            <div class="bg-orange-50 shadow rounded-lg p-6 border border-orange-200">
              <h2 class="text-lg font-semibold text-orange-900 mb-4 flex items-center">
                <Icon name="builder" className="mr-2 text-orange-500" />
                Builder
              </h2>
              <p class="text-sm text-orange-700 mb-2">Start building on GenLayer. Deploy contracts, earn points, and join our growing developer community.</p>
              <p class="text-sm text-orange-700 mb-4">Top contributors get special rewards.</p>
              <button
                onclick={startBuilderJourney}
                class="px-3 py-1.5 bg-orange-600 text-white rounded text-sm hover:bg-orange-700 transition-colors"
              >
                Start Builder Journey →
              </button>
            </div>
          {/if}

          {#if needsValidator}
            <div class="bg-sky-50 shadow rounded-lg p-6 border border-sky-200">
              <h2 class="text-lg font-semibold text-sky-900 mb-4 flex items-center">
                <Icon name="validator" className="mr-2 text-sky-500" />
                Validator
              </h2>
              <p class="text-sm text-sky-700 mb-2">Want to become a GenLayer Validator? Join the waitlist, start earning points, and climb the ranks.</p>
              <p class="text-sm text-sky-700 mb-4">Top contributors will be invited to run nodes on Testnet Asimov.</p>
              <button
                onclick={startValidatorJourney}
                class="px-3 py-1.5 bg-sky-600 text-white rounded text-sm hover:bg-sky-700 transition-colors"
              >
                Join the Waitlist →
              </button>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Steward and Supporter Grid -->
      {#if needsSteward || needsSupporter}
        {@const bothStewardSupporter = needsSteward && needsSupporter}
        <div class="{bothStewardSupporter ? 'grid grid-cols-1 md:grid-cols-2 gap-4 mt-6' : 'mt-6'}">
          <!-- Inactive Steward -->
          {#if needsSteward}
            <div class="bg-green-50 shadow rounded-lg p-6 border border-green-200">
              <h2 class="text-lg font-semibold text-green-900 mb-4 flex items-center">
                <Icon name="steward" className="mr-2 text-green-600" />
                Steward
              </h2>
              <p class="text-sm text-green-700 mb-2">Steward positions are earned through exceptional contribution.</p>
              <p class="text-sm text-green-700">Keep building, validating, and supporting the community to unlock this role.</p>
            </div>
          {/if}

          <!-- Supporter Profile Card -->
          {#if needsSupporter}
            <div class="bg-purple-50 shadow rounded-lg p-6 border border-purple-200">
              <h2 class="text-lg font-semibold text-purple-900 mb-4 flex items-center">
                <svg class="w-5 h-5 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                </svg>
                Supporter
              </h2>
              <p class="text-sm text-purple-700 mb-2">Focus on growing the community through referrals.</p>
              <p class="text-sm text-purple-700 mb-4">Earn 10% of points from every contribution your referrals make.</p>
              <button
                onclick={startCreatorJourney}
                class="px-3 py-1.5 bg-purple-600 text-white rounded text-sm hover:bg-purple-700 transition-colors"
              >
                Become a Supporter →
              </button>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Active Supporter Profile Card (full width when user is already a supporter) -->
      {#if user.creator}
        <div class="bg-purple-100 shadow rounded-lg p-6 border border-purple-300 mt-6">
          <h2 class="text-lg font-semibold text-purple-900 mb-4 flex items-center">
            <svg class="w-5 h-5 mr-2 text-purple-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
            Supporter
          </h2>
          <p class="text-sm text-purple-800 mb-2">You're a Supporter! Focus on growing the community through referrals.</p>
          <p class="text-sm text-purple-700">Earn 10% of points from every contribution your referrals make.</p>
        </div>
      {/if}

    <!-- Save/Cancel Buttons -->
    <div class="flex gap-4 mt-6">
      <button
        onclick={handleSave}
        disabled={!hasChanges || !isFormValid || isSaving}
        class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {isSaving ? 'Saving...' : 'Save Changes'}
      </button>
      <button
        onclick={handleCancel}
        disabled={isSaving}
        class="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
      >
        Cancel
      </button>
    </div>
  {:else if !authChecked}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
    </div>
  {/if}
</div>

<!-- Image Cropper Modal -->
{#if showImageCropper && cropperImage}
  <ImageCropper
    image={cropperImage}
    aspectRatio={cropperAspectRatio}
    title={cropperTitle}
    onCrop={cropperCallback}
    onCancel={handleCropCancel}
  />
{/if}