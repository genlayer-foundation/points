<script>
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { updateUserProfile } from '../lib/api.js';

  // Form state
  let email = $state('');
  let name = $state('');
  let submittingProfile = $state(false);
  let profileError = $state('');

  // Track which fields were pre-filled
  let hasExistingName = $state(false);
  let hasExistingEmail = $state(false);

  // Determine if profile is incomplete
  let showGuard = $derived(() => {
    // Don't show while loading
    if ($authState.loading || $userStore.loading) return false;

    // Only show if authenticated
    if (!$authState.isAuthenticated) return false;

    // Only show if we have user data
    const user = $userStore.user;
    if (!user) return false;

    // Check if profile is incomplete
    const needsName = !user.name || user.name.trim() === '';
    const needsEmail = !user.email ||
                       user.email.trim() === '' ||
                       user.email.endsWith('@ethereum.address');

    return needsName || needsEmail;
  });

  // Pre-fill form fields when user data is available
  $effect(() => {
    const user = $userStore.user;
    if (user && showGuard()) {
      // Pre-fill name if it exists
      if (user.name && user.name.trim() !== '') {
        name = user.name;
        hasExistingName = true;
      } else {
        name = '';
        hasExistingName = false;
      }

      // Pre-fill email if it exists and is not auto-generated
      if (user.email && user.email.trim() !== '' && !user.email.endsWith('@ethereum.address')) {
        email = user.email;
        hasExistingEmail = true;
      } else {
        email = '';
        hasExistingEmail = false;
      }
    }
  });

  async function handleProfileSubmit() {
    // Validate inputs
    if (!email || !name) {
      profileError = 'Please provide both email and display name';
      return;
    }

    if (!isValidEmail(email)) {
      profileError = 'Please enter a valid email address';
      return;
    }

    submittingProfile = true;
    profileError = '';

    try {
      // Prepare update data
      const updateData = {};
      if (email) updateData.email = email;
      if (name) updateData.name = name;

      // Submit to backend
      await updateUserProfile(updateData);

      // Update the user store
      userStore.updateUser(updateData);

      // Reload user data to ensure we have the latest
      await userStore.loadUser();

      // Modal will close automatically when user data updates
    } catch (err) {
      console.error('Profile update error:', err);
      // Handle field-specific errors from Django REST Framework
      if (err.response?.data) {
        const data = err.response.data;
        if (data.email) {
          profileError = data.email;
        } else if (data.name) {
          profileError = data.name;
        } else if (data.error) {
          profileError = data.error;
        } else {
          profileError = err.message || 'Failed to update profile';
        }
      } else {
        profileError = err.message || 'Failed to update profile';
      }
    } finally {
      submittingProfile = false;
    }
  }

  function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
</script>

{#if showGuard()}
  <div class="profile-guard-backdrop">
    <div class="profile-guard-modal">
      <div class="profile-guard-header">
        <h2 class="profile-guard-title">Complete Your Profile</h2>
      </div>

      <div class="profile-guard-body">
        <div class="profile-completion-form">
          <!-- Welcome Icon -->
          <div class="flex justify-center mb-4">
            <div class="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center">
              <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
              </svg>
            </div>
          </div>

          <p class="text-gray-700 text-sm mb-2 text-center font-medium">
            Welcome to GenLayer Points!
          </p>
          <p class="text-gray-600 text-sm mb-6 text-center">
            Let's get started with the basics.
          </p>

          {#if profileError}
            <div class="profile-error">
              {profileError}
            </div>
          {/if}

          <div class="form-group">
            <label for="name" class="form-label">
              Display Name
              {#if hasExistingName}
                <span class="text-green-600 text-xs ml-1.5 font-normal">✓ Already set</span>
              {/if}
            </label>
            <input
              id="name"
              type="text"
              bind:value={name}
              placeholder="e.g., John Doe"
              class="form-input {hasExistingName ? 'bg-green-50' : ''}"
              disabled={submittingProfile}
            />
            <p class="text-xs text-gray-500 mt-1">This is how you'll appear to other participants</p>
          </div>

          <div class="form-group">
            <label for="email" class="form-label">
              Email Address
              {#if hasExistingEmail}
                <span class="text-green-600 text-xs ml-1.5 font-normal">✓ Already set</span>
              {/if}
            </label>
            <input
              id="email"
              type="email"
              bind:value={email}
              placeholder="your@email.com"
              class="form-input {hasExistingEmail ? 'bg-green-50' : ''}"
              disabled={submittingProfile}
            />
            <p class="text-xs text-gray-500 mt-1">We'll use this to send you important updates about your contributions</p>
          </div>

          <button
            onclick={handleProfileSubmit}
            disabled={submittingProfile || !email.trim() || !name.trim()}
            class="profile-submit-button"
          >
            {#if submittingProfile}
              <div class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Saving...
            {:else}
              Save
            {/if}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .profile-guard-backdrop {
    position: fixed;
    inset: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    animation: fadeIn 0.15s ease-out;
    backdrop-filter: blur(4px);
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .profile-guard-modal {
    background-color: white;
    border-radius: 1rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    width: 420px;
    max-width: 90vw;
    max-height: 85vh;
    overflow: hidden;
    animation: slideUp 0.2s ease-out;
  }

  @keyframes slideUp {
    from {
      transform: translateY(10px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .profile-guard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 1.5rem 0;
  }

  .profile-guard-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
    letter-spacing: -0.01em;
  }

  .profile-guard-body {
    padding: 1.5rem;
  }

  /* Profile Completion Form Styles */
  .profile-completion-form {
    padding: 0.5rem 0;
  }

  .profile-error {
    background-color: #FEE2E2;
    border: 1px solid #F87171;
    color: #B91C1C;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  .form-label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: #374151;
    margin-bottom: 0.5rem;
  }

  .form-input {
    width: 100%;
    padding: 0.875rem 1rem;
    font-size: 0.9375rem;
    color: #111827;
    background-color: #FAFAFA;
    border: 1px solid #E5E7EB;
    border-radius: 0.75rem;
    transition: all 0.15s;
  }

  .form-input:focus {
    outline: none;
    background-color: #FFFFFF;
    border-color: #2563EB;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }

  .form-input:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .form-input::placeholder {
    color: #9CA3AF;
  }

  .profile-submit-button {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.875rem 1rem;
    font-size: 0.9375rem;
    font-weight: 500;
    color: white;
    background-color: #2563EB;
    border: none;
    border-radius: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
    margin-top: 0.5rem;
  }

  .profile-submit-button:hover:not(:disabled) {
    background-color: #1D4ED8;
    transform: translateY(-1px);
  }

  .profile-submit-button:disabled {
    opacity: 0.6;
    cursor: default;
    transform: none;
  }

  /* Responsive design */
  @media (max-width: 640px) {
    .profile-guard-modal {
      width: calc(100vw - 2rem);
      max-height: 90vh;
    }

    .profile-guard-header {
      padding: 1.25rem 1.25rem 0;
    }

    .profile-guard-body {
      padding: 1.25rem;
    }
  }
</style>
