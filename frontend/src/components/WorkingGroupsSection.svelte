<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI } from '../lib/api.js';
  import Avatar from './Avatar.svelte';
  import { showSuccess, showError } from '../lib/toastStore.js';
  import { categoryTheme } from '../stores/category.js';
  import { parseMarkdown } from '../lib/markdownLoader.js';

  let isSteward = $derived($userStore.user?.steward ? true : false);

  // Working groups state
  let workingGroups = $state([]);
  let loading = $state(true);

  // Create/Edit modal state
  let showGroupModal = $state(false);
  let editingGroup = $state(null);
  let groupForm = $state({ name: '', icon: '', description: '', discord_url: '' });
  let savingGroup = $state(false);

  // Add participant modal state
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
      const response = await stewardAPI.getWorkingGroups();
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
      workingGroups = [];
    } finally {
      loading = false;
    }
  }

  function openCreateModal() {
    editingGroup = null;
    groupForm = { name: '', icon: '', description: '', discord_url: '' };
    showGroupModal = true;
  }

  function openEditModal(group) {
    editingGroup = group;
    groupForm = {
      name: group.name,
      icon: group.icon || '',
      description: group.description || '',
      discord_url: group.discord_url || ''
    };
    showGroupModal = true;
  }

  async function handleSaveGroup() {
    if (!groupForm.name.trim()) {
      showError('Name is required');
      return;
    }

    try {
      savingGroup = true;
      if (editingGroup) {
        await stewardAPI.updateWorkingGroup(editingGroup.id, groupForm);
        showSuccess('Working group updated');
      } else {
        await stewardAPI.createWorkingGroup(groupForm);
        showSuccess('Working group created');
      }
      showGroupModal = false;
      editingGroup = null;
      groupForm = { name: '', icon: '', description: '', discord_url: '' };
      await loadWorkingGroups();
    } catch (err) {
      if (err.response?.status === 403) {
        showError('You do not have permission to manage working groups');
      } else if (err.response?.data?.detail) {
        showError(err.response.data.detail);
      } else {
        showError(editingGroup ? 'Failed to update working group' : 'Failed to create working group');
      }
    } finally {
      savingGroup = false;
    }
  }

  function openDeleteModal(groupId) {
    deleteGroupId = groupId;
    showDeleteModal = true;
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
      if (err.response?.status === 403) {
        showError('You do not have permission to delete working groups');
      } else {
        showError('Failed to delete working group');
      }
    } finally {
      deleting = false;
    }
  }

  function openAddParticipantModal(groupId) {
    addParticipantGroupId = groupId;
    showAddParticipantModal = true;
    searchQuery = '';
    searchResults = [];
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

  $effect(() => {
    if (searchQuery.length >= 2) {
      const timeout = setTimeout(searchUsers, 300);
      return () => clearTimeout(timeout);
    } else {
      searchResults = [];
    }
  });
</script>

<!-- Working Groups Container -->
<div class="space-y-4">
  <!-- Section Header -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      <div class="p-1.5 {$categoryTheme.bgSecondary} rounded-lg">
        <svg class="w-4 h-4 {$categoryTheme.text}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
        </svg>
      </div>
      <h2 class="text-lg font-semibold text-gray-900">Working Groups</h2>
    </div>
    {#if isSteward}
      <button
        onclick={openCreateModal}
        class="px-3 py-1.5 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 transition-colors flex items-center gap-1.5"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
        </svg>
        Create Group
      </button>
    {/if}
  </div>

  <!-- Description (no container) -->
  <p class="text-gray-600 text-sm">
    Join specialized teams focused on different aspects of the GenLayer ecosystem.
    Collaborate on technical proposals, standards, and implementations.
  </p>

  <!-- Interested in joining? (full width container) -->
  <div class="{$categoryTheme.bgSecondary} rounded-lg p-3 border {$categoryTheme.border}">
    <p class="text-sm text-gray-600">
      <span class="mr-1">💡</span> <strong>Interested in joining?</strong> Contact <span class="font-mono {$categoryTheme.bgSecondary} px-1.5 py-0.5 rounded {$categoryTheme.text} font-semibold">@ras</span> on <a href="https://discord.com/invite/qjCU4AWnKE" target="_blank" rel="noopener noreferrer" class="{$categoryTheme.text} hover:text-green-700 underline font-semibold">Discord</a> to learn more.
    </p>
  </div>

  <!-- Working Groups List -->
  {#if loading}
    <div class="bg-white rounded-lg shadow-sm border {$categoryTheme.border} p-8">
      <div class="flex justify-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    </div>
  {:else if workingGroups.length === 0}
    <div class="bg-white rounded-lg shadow-sm border {$categoryTheme.border} p-6">
      <div class="text-center text-gray-500">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
        </svg>
        <p>No working groups yet</p>
        {#if isSteward}
          <button
            onclick={openCreateModal}
            class="mt-3 {$categoryTheme.text} hover:text-green-700 font-medium"
          >
            Create the first one
          </button>
        {/if}
      </div>
    </div>
  {:else}
    <div class="bg-white rounded-lg shadow-sm border {$categoryTheme.border} divide-y divide-gray-200">
      {#each workingGroups as group (group.id)}
        <div class="overflow-hidden">
          <!-- Group Header Row -->
          <div class="p-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <span class="text-xl flex-shrink-0">{group.icon || '👥'}</span>
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900 truncate">{group.name}</span>
                    <span class="text-xs text-gray-500 flex items-center gap-1 flex-shrink-0">
                      {group.participant_count || group.participants?.length || 0}
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
                      </svg>
                    </span>
                  </div>
                  {#if group.description}
                    <div class="markdown-content text-xs text-gray-500 mt-1">
                      {@html parseMarkdown(group.description)}
                    </div>
                  {/if}
                </div>
              </div>
              {#if isSteward}
                <div class="flex items-center gap-2 flex-shrink-0">
                  <button
                    onclick={() => openAddParticipantModal(group.id)}
                    class="p-1.5 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                    title="Add participant"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
                    </svg>
                  </button>
                  <button
                    onclick={() => openEditModal(group)}
                    class="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                    title="Edit group"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                    </svg>
                  </button>
                  <button
                    onclick={() => openDeleteModal(group.id)}
                    class="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Delete group"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                    </svg>
                  </button>
                </div>
              {/if}
            </div>
          </div>

          <!-- Participants List (always visible) -->
          {#if group.participants && group.participants.length > 0}
            <div class="px-4 pb-4">
              <div class="rounded-lg border border-gray-200 divide-y divide-gray-200">
                {#each group.participants as participant}
                  <div class="p-3 hover:bg-gray-50 transition-colors">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-3">
                        <Avatar
                          user={participant}
                          size="sm"
                          clickable={true}
                        />
                        <div class="min-w-0">
                          <button
                            onclick={() => push(`/participant/${participant.address}`)}
                            class="text-sm font-medium text-gray-900 hover:{$categoryTheme.text} transition-colors truncate"
                          >
                            {participant.name || `${participant.address?.slice(0, 6)}...${participant.address?.slice(-4)}`}
                          </button>
                        </div>
                      </div>
                      <div class="flex items-center gap-2">
                        <button
                          onclick={() => push(`/participant/${participant.address}`)}
                          class="text-xs {$categoryTheme.text} hover:text-green-700 font-medium"
                        >
                          View →
                        </button>
                        {#if isSteward}
                          <button
                            onclick={() => handleRemoveParticipant(group.id, participant.id)}
                            class="text-red-500 hover:text-red-700 p-1"
                            title="Remove participant"
                          >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                          </button>
                        {/if}
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {:else}
            <p class="px-4 pb-4 text-sm text-gray-500">No participants yet</p>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Create/Edit Group Modal -->
{#if showGroupModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b {$categoryTheme.border} {$categoryTheme.bgSecondary}">
        <h3 class="text-lg font-semibold text-gray-800">{editingGroup ? 'Edit' : 'Create'} Working Group</h3>
      </div>
      <div class="px-6 py-4 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            type="text"
            bind:value={groupForm.name}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            placeholder="Working Group Name"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Icon (Emoji)</label>
          <input
            type="text"
            bind:value={groupForm.icon}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            placeholder="👥"
            maxlength="10"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            bind:value={groupForm.description}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            placeholder="Brief description of the working group"
            rows="2"
          ></textarea>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Discord URL</label>
          <input
            type="url"
            bind:value={groupForm.discord_url}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            placeholder="https://discord.gg/..."
          />
        </div>
      </div>
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
        <button
          onclick={() => { showGroupModal = false; editingGroup = null; }}
          class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={handleSaveGroup}
          disabled={savingGroup}
          class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors disabled:opacity-50"
        >
          {savingGroup ? 'Saving...' : (editingGroup ? 'Save Changes' : 'Create')}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Add Participant Modal -->
{#if showAddParticipantModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b {$categoryTheme.border} {$categoryTheme.bgSecondary}">
        <h3 class="text-lg font-semibold text-gray-800">Add Participant</h3>
      </div>
      <div class="px-6 py-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">Search by name or address</label>
        <input
          type="text"
          bind:value={searchQuery}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
          placeholder="Type to search..."
        />
        {#if searching}
          <p class="mt-2 text-sm text-gray-500">Searching...</p>
        {:else if searchResults.length > 0}
          <div class="mt-2 border {$categoryTheme.border} rounded-md max-h-60 overflow-y-auto">
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
      <div class="px-6 py-4 border-b border-red-100 bg-red-50">
        <h3 class="text-lg font-semibold text-red-800">Delete Working Group</h3>
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

<style>
  .markdown-content :global(ul) {
    list-style-type: disc;
    margin-left: 1.5rem;
  }

  .markdown-content :global(ol) {
    list-style-type: decimal;
    margin-left: 1.5rem;
  }

  .markdown-content :global(a) {
    color: #059669;
    text-decoration: underline;
  }

  .markdown-content :global(a:hover) {
    color: #047857;
  }

  .markdown-content :global(p) {
    margin: 0;
  }

  .markdown-content :global(p + p) {
    margin-top: 0.5rem;
  }
</style>
