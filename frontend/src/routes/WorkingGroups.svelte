<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI } from '../lib/api.js';
  import { categoryTheme } from '../stores/category.js';
  import Avatar from '../components/Avatar.svelte';
  import { showSuccess, showError } from '../lib/toastStore.js';

  let workingGroups = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let isSteward = $derived($userStore.user?.steward ? true : false);

  // Split groups into left and right columns (alternating for left-to-right order)
  let leftColumnGroups = $derived(workingGroups.filter((_, i) => i % 2 === 0));
  let rightColumnGroups = $derived(workingGroups.filter((_, i) => i % 2 === 1));

  // Create modal state
  let showCreateModal = $state(false);
  let createForm = $state({ name: '', discord_url: '' });
  let creating = $state(false);

  // Add participant state
  let showAddParticipantModal = $state(false);
  let addParticipantGroupId = $state(null);
  let searchQuery = $state('');
  let searchResults = $state([]);
  let searching = $state(false);
  let addingParticipant = $state(false);

  // Delete confirmation state
  let showDeleteModal = $state(false);
  let deleteGroupId = $state(null);
  let deleting = $state(false);

  onMount(async () => {
    await loadWorkingGroups();
  });

  async function loadWorkingGroups() {
    try {
      loading = true;
      error = null;
      const response = await stewardAPI.getWorkingGroups();
      // API returns paginated response with results array
      const groups = response.data?.results || response.data || [];

      // Load details for all groups to get participants
      const detailedGroups = await Promise.all(
        groups.map(async (group) => {
          try {
            const detailResponse = await stewardAPI.getWorkingGroup(group.id);
            return { ...group, ...detailResponse.data };
          } catch {
            return group;
          }
        })
      );

      workingGroups = detailedGroups;
    } catch (err) {
      error = 'Failed to load working groups';
    } finally {
      loading = false;
    }
  }

  async function handleCreateGroup() {
    if (!createForm.name.trim()) {
      showError('Name is required');
      return;
    }

    try {
      creating = true;
      await stewardAPI.createWorkingGroup(createForm);
      showSuccess('Working group created');
      showCreateModal = false;
      createForm = { name: '', discord_url: '' };
      await loadWorkingGroups();
    } catch (err) {
      console.error('Create working group error:', err);
      if (err.response?.status === 403) {
        showError('You do not have permission to create working groups');
      } else if (err.response?.status === 401) {
        showError('Please log in to create working groups');
      } else if (err.response?.data?.detail) {
        showError(err.response.data.detail);
      } else if (err.response?.data?.name) {
        showError(`Name: ${err.response.data.name.join(', ')}`);
      } else {
        showError('Failed to create working group');
      }
    } finally {
      creating = false;
    }
  }

  async function handleDeleteGroup() {
    if (!deleteGroupId) return;

    try {
      deleting = true;
      await stewardAPI.deleteWorkingGroup(deleteGroupId);
      showSuccess('Working group deleted');
      showDeleteModal = false;
      deleteGroupId = null;
      await loadWorkingGroups();
    } catch (err) {
      console.error('Delete working group error:', err);
      if (err.response?.status === 403) {
        showError('You do not have permission to delete working groups');
      } else if (err.response?.status === 401) {
        showError('Please log in to delete working groups');
      } else if (err.response?.data?.detail) {
        showError(err.response.data.detail);
      } else {
        showError('Failed to delete working group');
      }
    } finally {
      deleting = false;
    }
  }

  async function searchUsers() {
    if (searchQuery.length < 2) {
      searchResults = [];
      return;
    }

    try {
      searching = true;
      const response = await stewardAPI.searchUsersForGroup(searchQuery);
      searchResults = response.data || [];
    } catch (err) {
      searchResults = [];
    } finally {
      searching = false;
    }
  }

  async function handleAddParticipant(userId) {
    if (!addParticipantGroupId) return;

    try {
      addingParticipant = true;
      await stewardAPI.addParticipant(addParticipantGroupId, userId);
      showSuccess('Participant added');
      showAddParticipantModal = false;
      addParticipantGroupId = null;
      searchQuery = '';
      searchResults = [];
      await loadWorkingGroups();
    } catch (err) {
      showError(err.response?.data?.error || 'Failed to add participant');
    } finally {
      addingParticipant = false;
    }
  }

  async function handleRemoveParticipant(groupId, userId) {
    try {
      await stewardAPI.removeParticipant(groupId, userId);
      showSuccess('Participant removed');
      await loadWorkingGroups();
    } catch (err) {
      showError('Failed to remove participant');
    }
  }

  function openAddParticipantModal(groupId) {
    addParticipantGroupId = groupId;
    showAddParticipantModal = true;
    searchQuery = '';
    searchResults = [];
  }

  function openDeleteModal(groupId) {
    deleteGroupId = groupId;
    showDeleteModal = true;
  }

  $effect(() => {
    if (searchQuery.length >= 2) {
      const timeout = setTimeout(searchUsers, 300);
      return () => clearTimeout(timeout);
    } else {
      searchResults = [];
    }
  });
</script>

<div class="container mx-auto px-4 py-8 min-h-screen {$categoryTheme.bg}" style="margin: -2rem -1rem; padding: 2rem 3rem;">
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-bold text-gray-900">Working Groups</h1>
    {#if isSteward}
      <button
        onclick={() => showCreateModal = true}
        class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
        </svg>
        Create Group
      </button>
    {/if}
  </div>

  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-green-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border-l-4 border-red-400 p-4">
      <p class="text-sm text-red-700">{error}</p>
    </div>
  {:else if workingGroups.length === 0}
    <div class="bg-white shadow rounded-lg p-8 text-center">
      <svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
      </svg>
      <p class="text-gray-500">No working groups yet</p>
      {#if isSteward}
        <button
          onclick={() => showCreateModal = true}
          class="mt-4 text-green-600 hover:text-green-700 font-medium"
        >
          Create the first one
        </button>
      {/if}
    </div>
  {:else}
    {#snippet groupCard(group)}
      <div class="bg-white shadow rounded-lg overflow-hidden">
        <!-- Group Header -->
        <div class="px-6 py-4 flex items-center justify-between border-b border-gray-100">
          <div class="flex items-center gap-3">
            <div class="p-2 bg-green-100 rounded-lg">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
              </svg>
            </div>
            <div>
              <h3 class="font-semibold text-gray-900">{group.name}</h3>
              <p class="text-sm text-gray-500">{group.participant_count} participant{group.participant_count !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <!-- Discord URL (only for members or stewards) -->
          {#if group.discord_url}
            <a
              href={group.discord_url}
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-700"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
              </svg>
              <span class="hidden sm:inline">Discord</span>
            </a>
          {/if}
        </div>

        <!-- Group Content -->
        <div class="px-6 py-4">
          <!-- Participants Table -->
          {#if group.participants && group.participants.length > 0}
            <table class="w-full">
              <thead>
                <tr class="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th class="pb-3">Participant</th>
                  <th class="pb-3 text-right">Builder</th>
                  <th class="pb-3 text-right">Validator</th>
                  {#if isSteward}
                    <th class="pb-3 w-8"></th>
                  {/if}
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                {#each group.participants as participant}
                  <tr class="hover:bg-gray-50">
                    <td class="py-3">
                      <div class="flex items-center gap-3">
                        <Avatar
                          user={participant}
                          size="sm"
                          clickable={true}
                        />
                        <button
                          onclick={() => push(`/participant/${participant.address}`)}
                          class="text-sm font-medium text-gray-900 hover:text-green-600 transition-colors"
                        >
                          {participant.name || participant.address?.slice(0, 8) + '...'}
                        </button>
                      </div>
                    </td>
                    <td class="py-3 text-right">
                      <span class="text-sm {participant.builder_points > 0 ? 'text-orange-600 font-medium' : 'text-gray-400'}">
                        {participant.builder_points > 0 ? participant.builder_points.toLocaleString() : '-'}
                      </span>
                    </td>
                    <td class="py-3 text-right">
                      <span class="text-sm {participant.validator_points > 0 ? 'text-sky-600 font-medium' : 'text-gray-400'}">
                        {participant.validator_points > 0 ? participant.validator_points.toLocaleString() : '-'}
                      </span>
                    </td>
                    {#if isSteward}
                      <td class="py-3 text-right">
                        <button
                          onclick={() => handleRemoveParticipant(group.id, participant.id)}
                          class="text-red-500 hover:text-red-700 p-1"
                          title="Remove participant"
                        >
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                          </svg>
                        </button>
                      </td>
                    {/if}
                  </tr>
                {/each}
              </tbody>
            </table>
          {:else}
            <p class="text-sm text-gray-500">No participants yet</p>
          {/if}

          <!-- Steward Actions -->
          {#if isSteward}
            <div class="mt-4 pt-4 border-t border-gray-200 flex gap-2">
              <button
                onclick={() => openAddParticipantModal(group.id)}
                class="flex-1 px-3 py-2 text-sm bg-green-50 text-green-700 rounded-md hover:bg-green-100 transition-colors"
              >
                Add Participant
              </button>
              <button
                onclick={() => openDeleteModal(group.id)}
                class="px-3 py-2 text-sm bg-red-50 text-red-700 rounded-md hover:bg-red-100 transition-colors"
              >
                Delete
              </button>
            </div>
          {/if}
        </div>
      </div>
    {/snippet}

    <!-- Two-column masonry layout with left-to-right ordering -->
    <div class="flex flex-col lg:flex-row gap-6">
      <!-- Left column (items 0, 2, 4, ...) -->
      <div class="flex-1 flex flex-col gap-6">
        {#each leftColumnGroups as group (group.id)}
          {@render groupCard(group)}
        {/each}
      </div>
      <!-- Right column (items 1, 3, 5, ...) -->
      <div class="flex-1 flex flex-col gap-6">
        {#each rightColumnGroups as group (group.id)}
          {@render groupCard(group)}
        {/each}
      </div>
    </div>
  {/if}
</div>

<!-- Create Group Modal -->
{#if showCreateModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Create Working Group</h3>
      </div>
      <div class="px-6 py-4 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            type="text"
            bind:value={createForm.name}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
            placeholder="Working Group Name"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Discord URL</label>
          <input
            type="url"
            bind:value={createForm.discord_url}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
            placeholder="https://discord.gg/..."
          />
        </div>
      </div>
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
        <button
          onclick={() => showCreateModal = false}
          class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={handleCreateGroup}
          disabled={creating}
          class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors disabled:opacity-50"
        >
          {creating ? 'Creating...' : 'Create'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Add Participant Modal -->
{#if showAddParticipantModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Add Participant</h3>
      </div>
      <div class="px-6 py-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">Search by name or address</label>
        <input
          type="text"
          bind:value={searchQuery}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500"
          placeholder="Type to search..."
        />
        {#if searching}
          <p class="mt-2 text-sm text-gray-500">Searching...</p>
        {:else if searchResults.length > 0}
          <div class="mt-2 border border-gray-200 rounded-md max-h-60 overflow-y-auto">
            {#each searchResults as user}
              <button
                onclick={() => handleAddParticipant(user.id)}
                disabled={addingParticipant}
                class="w-full px-3 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <Avatar
                  user={{ name: user.name, address: user.address, profile_image_url: user.profile_image_url }}
                  size="sm"
                />
                <div class="text-left">
                  <p class="text-sm font-medium text-gray-900">{user.name || 'Anonymous'}</p>
                  <p class="text-xs text-gray-500">{user.address?.slice(0, 10)}...{user.address?.slice(-6)}</p>
                </div>
              </button>
            {/each}
          </div>
        {:else if searchQuery.length >= 2}
          <p class="mt-2 text-sm text-gray-500">No users found</p>
        {/if}
      </div>
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end">
        <button
          onclick={() => { showAddParticipantModal = false; searchQuery = ''; searchResults = []; }}
          class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Delete Working Group</h3>
      </div>
      <div class="px-6 py-4">
        <p class="text-gray-600">Are you sure you want to delete this working group? This action cannot be undone.</p>
      </div>
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
        <button
          onclick={() => { showDeleteModal = false; deleteGroupId = null; }}
          class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={handleDeleteGroup}
          disabled={deleting}
          class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors disabled:opacity-50"
        >
          {deleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
    </div>
  </div>
{/if}
