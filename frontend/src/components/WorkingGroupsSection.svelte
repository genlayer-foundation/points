<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI } from '../lib/api.js';
  import Avatar from './Avatar.svelte';
  import CategoryIcon from './portal/CategoryIcon.svelte';
  import { showSuccess, showError } from '../lib/toastStore.js';
  import { categoryTheme } from '../stores/category.js';
  import { parseMarkdown } from '../lib/markdownLoader.js';

  let isSteward = $derived($userStore.user?.steward ? true : false);

  // Working groups state
  let workingGroups = $state([]);
  let loading = $state(true);
  let expandedGroupIds = $state(new Set());
  let totalParticipantCount = $derived(
    workingGroups.reduce((total, group) => total + memberCount(group), 0)
  );

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
      expandedGroupIds = new Set();
    } catch (err) {
      workingGroups = [];
      expandedGroupIds = new Set();
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

  function memberCount(group) {
    return group?.participant_count || group?.participants?.length || 0;
  }

  function participantName(participant) {
    if (participant?.name) return participant.name;
    if (participant?.address) return `${participant.address.slice(0, 6)}...${participant.address.slice(-4)}`;
    return 'Unnamed member';
  }

  function openParticipant(participant) {
    if (participant?.address) {
      push(`/participant/${participant.address}`);
    }
  }

  function isGroupExpanded(groupId) {
    return expandedGroupIds.has(groupId);
  }

  function toggleGroup(groupId) {
    const nextExpandedGroupIds = new Set(expandedGroupIds);
    if (nextExpandedGroupIds.has(groupId)) {
      nextExpandedGroupIds.delete(groupId);
    } else {
      nextExpandedGroupIds.add(groupId);
    }
    expandedGroupIds = nextExpandedGroupIds;
  }
</script>

<section class="working-groups-shell rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
  <div class="mb-5 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
    <div class="flex items-start gap-3">
      <CategoryIcon category="steward" mode="hexagon" size={42} />
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-3">
          <h2 class="text-[22px] font-semibold font-display leading-none text-black sm:text-[25px]">Working Groups</h2>
          <span class="inline-flex h-[25px] items-center rounded-full border border-[#d8f3e4] bg-white px-3 text-[12px] font-semibold text-[#137f4c]">
            {workingGroups.length} groups
          </span>
          <span class="inline-flex h-[25px] items-center rounded-full border border-[#e8ebf2] bg-white px-3 text-[12px] font-semibold text-[#506078]">
            {totalParticipantCount} members
          </span>
        </div>
        <p class="mt-2 max-w-2xl text-[13px] text-[#506078] sm:text-[14px]">
          Focused steward groups with member rosters and private coordination links where available.
        </p>
      </div>
    </div>

    {#if isSteward}
      <button
        type="button"
        onclick={openCreateModal}
        class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[8px] border border-[#19A663] bg-[#19A663] px-3.5 text-[13px] font-semibold text-white shadow-[0_8px_22px_rgba(25,166,99,0.22)] transition-transform hover:-translate-y-0.5 active:scale-[0.96] sm:w-auto"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
        </svg>
        Create Group
      </button>
    {/if}
  </div>

  <div class="mb-5 rounded-[8px] border border-[#d8f3e4] bg-white/70 px-3 py-2 text-[13px] text-[#506078]">
    Contact <span class="font-mono font-semibold text-[#137f4c]">@ras</span> on
    <a href="https://discord.gg/genlayerlabs" target="_blank" rel="noopener noreferrer" class="font-semibold text-[#137f4c] underline">Discord</a>
    to join.
  </div>

  <div>
    {#if loading}
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {#each [1, 2] as _}
          <div class="h-[236px] animate-pulse rounded-[8px] border border-[#eef1f4] bg-white/80 p-4">
            <div class="h-5 w-40 rounded bg-gray-200"></div>
            <div class="mt-4 h-4 w-full rounded bg-gray-100"></div>
            <div class="mt-6 grid grid-cols-2 gap-2">
              <div class="h-12 rounded bg-gray-100"></div>
              <div class="h-12 rounded bg-gray-100"></div>
            </div>
          </div>
        {/each}
      </div>
    {:else if workingGroups.length === 0}
      <div class="rounded-[8px] border border-dashed border-[#d8f3e4] bg-white/70 p-8 text-center">
        <div class="mx-auto flex w-fit">
          <CategoryIcon category="steward" mode="hexagon" size={54} />
        </div>
        <p class="mt-4 text-sm font-medium text-gray-900">No working groups yet</p>
        {#if isSteward}
          <button
            onclick={openCreateModal}
            class="mt-3 text-sm font-semibold text-[#137f4c] transition-colors hover:text-[#0f6b40]"
          >
            Create the first one
          </button>
        {/if}
      </div>
    {:else}
      <div class="space-y-3">
        {#each workingGroups as group (group.id)}
          <article class="working-group-card overflow-hidden rounded-[8px] bg-white/86">
            <div class="p-4">
              <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div class="flex min-w-0 items-start gap-3">
                  <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-[8px] bg-white text-lg shadow-[0_8px_18px_rgba(25,166,99,0.10)]">
                    {#if group.icon}
                      <span aria-hidden="true">{group.icon}</span>
                    {:else}
                      <CategoryIcon category="steward" mode="hexagon" size={30} />
                    {/if}
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <h3 class="truncate text-base font-semibold text-gray-950">{group.name}</h3>
                      <span class="rounded-full bg-[#fbfbfb] px-2 py-0.5 text-xs font-semibold text-gray-500">
                        {memberCount(group)} members
                      </span>
                    </div>
                    {#if group.description}
                      <div class="markdown-content working-group-description mt-2 text-sm leading-6 text-[#6b6b6b]" title={group.description}>
                        {@html parseMarkdown(group.description)}
                      </div>
                    {/if}
                  </div>
                </div>

                <div class="flex shrink-0 flex-wrap items-center gap-1 lg:justify-end">
                  {#if group.discord_url}
                    <a
                      href={group.discord_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-[#d8f3e4] bg-white px-3 text-sm font-semibold text-[#137f4c] shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition-colors hover:bg-[#f0fdf4]"
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.5 6H18m0 0v4.5M18 6l-7.5 7.5M6 8.25v9A1.75 1.75 0 007.75 19h8.5A1.75 1.75 0 0018 17.25v-3"></path>
                      </svg>
                      Discord
                    </a>
                  {/if}

                  {#if isSteward}
                    <button
                      onclick={() => openAddParticipantModal(group.id)}
                      class="inline-flex h-10 w-10 items-center justify-center rounded-[8px] text-gray-500 transition-colors hover:bg-[#f0fdf4] hover:text-[#137f4c]"
                      title="Add member"
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
                      </svg>
                    </button>
                    <button
                      onclick={() => openEditModal(group)}
                      class="inline-flex h-10 w-10 items-center justify-center rounded-[8px] text-gray-500 transition-colors hover:bg-[#f4f9ff] hover:text-[#2563eb]"
                      title="Edit group"
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                      </svg>
                    </button>
                    <button
                      onclick={() => openDeleteModal(group.id)}
                      class="inline-flex h-10 w-10 items-center justify-center rounded-[8px] text-gray-500 transition-colors hover:bg-red-50 hover:text-red-600"
                      title="Delete group"
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                      </svg>
                    </button>
                  {/if}

                  <button
                    type="button"
                    onclick={() => toggleGroup(group.id)}
                    aria-expanded={isGroupExpanded(group.id)}
                    aria-controls="working-group-members-{group.id}"
                    class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-[#d8f3e4] bg-white px-3 text-sm font-semibold text-[#137f4c] shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition-colors hover:bg-[#f0fdf4]"
                  >
                    {isGroupExpanded(group.id) ? 'Hide members' : 'View members'}
                    <svg class="h-4 w-4 transition-transform {isGroupExpanded(group.id) ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 9l6 6 6-6"></path>
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            {#if isGroupExpanded(group.id)}
              <div id="working-group-members-{group.id}" class="border-t border-[#eef1f4] bg-white/45 p-3 sm:p-4">
                {#if group.participants && group.participants.length > 0}
                  <div class="space-y-2">
                    {#each group.participants as participant}
                      <div class="member-card flex items-center justify-between gap-2 rounded-[8px] bg-white/78 p-2">
                        <button
                          onclick={() => openParticipant(participant)}
                          class="flex min-w-0 flex-1 items-center gap-3 text-left"
                        >
                          <Avatar user={{ ...participant, steward: true }} size="sm" clickable={false} />
                          <span class="truncate text-sm font-medium text-gray-900">{participantName(participant)}</span>
                        </button>

                        {#if isSteward}
                          <button
                            onclick={() => handleRemoveParticipant(group.id, participant.id)}
                            class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-[8px] text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600"
                            title="Remove member"
                          >
                            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                          </button>
                        {/if}
                      </div>
                    {/each}
                  </div>
                {:else}
                  <div class="rounded-[8px] border border-dashed border-[#e5e7eb] bg-white/70 p-3 text-sm text-gray-500">
                    No members yet
                  </div>
                {/if}
              </div>
            {/if}
          </article>
        {/each}
      </div>
    {/if}
  </div>
</section>

<!-- Create/Edit Group Modal -->
{#if showGroupModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b {$categoryTheme.border} {$categoryTheme.bgSecondary}">
        <h3 class="text-lg font-semibold text-gray-800">{editingGroup ? 'Edit' : 'Create'} Working Group</h3>
      </div>
      <div class="px-6 py-4 space-y-4">
        <div>
          <label for="working-group-name" class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            id="working-group-name"
            type="text"
            bind:value={groupForm.name}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-[#19A663] focus:border-[#19A663]"
            placeholder="Working Group Name"
          />
        </div>
        <div>
          <label for="working-group-icon" class="block text-sm font-medium text-gray-700 mb-1">Icon (Emoji)</label>
          <input
            id="working-group-icon"
            type="text"
            bind:value={groupForm.icon}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-[#19A663] focus:border-[#19A663]"
            placeholder="👥"
            maxlength="10"
          />
        </div>
        <div>
          <label for="working-group-description" class="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            id="working-group-description"
            bind:value={groupForm.description}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-[#19A663] focus:border-[#19A663]"
            placeholder="Brief description of the working group"
            rows="2"
          ></textarea>
        </div>
        <div>
          <label for="working-group-discord-url" class="block text-sm font-medium text-gray-700 mb-1">Discord URL</label>
          <input
            id="working-group-discord-url"
            type="url"
            bind:value={groupForm.discord_url}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-[#19A663] focus:border-[#19A663]"
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
          class="px-4 py-2 bg-[#19A663] text-white rounded-md transition-colors hover:bg-[#137f4c] disabled:opacity-50"
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
        <label for="working-group-user-search" class="block text-sm font-medium text-gray-700 mb-1">Search by name or address</label>
        <input
          id="working-group-user-search"
          type="text"
          bind:value={searchQuery}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-[#19A663] focus:border-[#19A663]"
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
  .working-groups-shell {
    -webkit-backdrop-filter: blur(12px);
  }

  .working-group-card {
    box-shadow:
      0 0 0 1px rgba(232, 235, 242, 0.9),
      0 8px 18px rgba(31, 42, 68, 0.06);
    transition-property: transform, box-shadow;
    transition-duration: 160ms;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .working-group-card:hover {
    transform: translateY(-1px);
    box-shadow:
      0 0 0 1px rgba(216, 243, 228, 0.95),
      0 14px 26px rgba(31, 42, 68, 0.12);
  }

  .member-card {
    transition-property: background-color;
    transition-duration: 160ms;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .member-card:hover {
    background-color: #f0fdf4;
  }

  .member-card :global(img) {
    outline: 1px solid rgba(0, 0, 0, 0.1);
  }

  .working-group-description {
    max-width: min(720px, 100%);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .working-group-description :global(*) {
    display: inline;
  }

  .working-group-description :global(br) {
    display: none;
  }

  .working-group-description :global(p + p) {
    margin-top: 0;
  }

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
