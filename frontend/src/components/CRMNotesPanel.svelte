<script>
  import { formatDistanceToNow } from 'date-fns';

  let {
    submissionId,
    notes = [],
    onAddNote = null,
    loading = false
  } = $props();

  let newNote = $state('');
  let submitting = $state(false);

  function formatDate(dateString) {
    if (!dateString) return '';
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch {
      return dateString;
    }
  }

  async function handleAddNote() {
    if (!newNote.trim() || !onAddNote) return;
    submitting = true;
    try {
      await onAddNote(submissionId, newNote.trim());
      newNote = '';
    } finally {
      submitting = false;
    }
  }
</script>

<div class="border border-gray-200 rounded-lg flex flex-col flex-1 min-h-0">
  <div class="px-4 py-2.5 bg-gray-50 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
    <h4 class="text-sm font-medium text-gray-700">Internal Notes</h4>
    <span class="text-xs text-gray-500">{notes.length} note{notes.length !== 1 ? 's' : ''}</span>
  </div>

  <div class="flex-1 min-h-0 overflow-y-auto notes-scroll">
    {#if loading}
      <div class="p-4 text-center text-sm text-gray-500">Loading notes...</div>
    {:else if notes.length === 0}
      <div class="p-4 text-center text-sm text-gray-400">No notes yet</div>
    {:else}
      <div class="divide-y divide-gray-100">
        {#each notes as note}
          <div class="px-4 py-2.5">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-medium text-gray-700">{note.user_name}</span>
              {#if note.is_proposal}
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">Proposal</span>
              {/if}
              <span class="text-[10px] text-gray-400 ml-auto">{formatDate(note.created_at)}</span>
            </div>
            <p class="text-sm text-gray-600 whitespace-pre-wrap">{note.message}</p>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Add Note Form -->
  <div class="px-4 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0">
    <div class="flex gap-2">
      <input
        type="text"
        bind:value={newNote}
        placeholder="Add a note..."
        class="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
        onkeydown={(e) => { if (e.key === 'Enter' && newNote.trim()) handleAddNote(); }}
      />
      <button
        onclick={handleAddNote}
        disabled={!newNote.trim() || submitting}
        class="px-3 py-1.5 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {submitting ? '...' : 'Add'}
      </button>
    </div>
  </div>
</div>

<style>
  .notes-scroll {
    scrollbar-width: thin;
    scrollbar-color: #d1d5db transparent;
  }

  .notes-scroll::-webkit-scrollbar {
    width: 6px;
  }

  .notes-scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .notes-scroll::-webkit-scrollbar-thumb {
    background-color: #d1d5db;
    border-radius: 3px;
  }

  .notes-scroll::-webkit-scrollbar-thumb:hover {
    background-color: #9ca3af;
  }
</style>
