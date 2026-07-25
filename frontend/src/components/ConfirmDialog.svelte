<script>
  import { tick } from "svelte";
  import { fade, fly } from "svelte/transition";

  let {
    isOpen = false,
    title = "Confirm",
    message = "Are you sure?",
    confirmText = "Confirm",
    cancelText = "Cancel",
    loading = false,
    onConfirm = () => {},
    onCancel = () => {},
  } = $props();

  /** @type {HTMLButtonElement | null} */
  let cancelButton = $state(null);

  $effect(() => {
    if (!isOpen) return;
    tick().then(() => cancelButton?.focus());
  });

  function handleCancel() {
    if (!loading) onCancel();
  }

  /** @param {KeyboardEvent} event */
  function handleKeydown(event) {
    if (isOpen && event.key === "Escape") {
      event.preventDefault();
      handleCancel();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
  <div
    class="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 px-4 backdrop-blur-[2px]"
    in:fade={{ duration: 150 }}
    out:fade={{ duration: 120 }}
  >
    <button
      type="button"
      class="absolute inset-0 cursor-default"
      aria-label="Close confirmation dialog"
      onclick={handleCancel}
      disabled={loading}
    ></button>
    <dialog
      open
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-description"
      class="relative m-0 w-full max-w-[420px] overflow-hidden rounded-[20px] border-0 bg-white p-0 text-left shadow-[0_0_0_1px_rgba(0,0,0,0.08),0_24px_70px_rgba(0,0,0,0.18)]"
      in:fly={{ y: 12, duration: 220 }}
      out:fly={{ y: -8, duration: 120 }}
    >
      <div class="flex items-start gap-4 p-6 pb-5">
        <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-[13px] bg-red-50 text-red-600 shadow-[inset_0_0_0_1px_rgba(220,38,38,0.10)]">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v3.75m9-1.875a9 9 0 11-18 0 9 9 0 0118 0zM12 16.5h.008v.008H12V16.5z" />
          </svg>
        </span>
        <div class="min-w-0 pt-0.5">
          <h2 id="confirm-dialog-title" class="text-balance font-heading text-[19px] font-semibold leading-6 text-[#1a1c1d]">
            {title}
          </h2>
          <p id="confirm-dialog-description" class="mt-1.5 text-pretty font-body text-[14px] leading-5 text-[#6b6b6b]">
            {message}
          </p>
        </div>
      </div>

      <div class="flex flex-col-reverse gap-2 bg-[#fafafa] p-4 sm:flex-row sm:justify-end">
        <button
          type="button"
          bind:this={cancelButton}
          onclick={handleCancel}
          disabled={loading}
          class="flex min-h-10 items-center justify-center rounded-full bg-white px-5 font-body text-[14px] font-medium text-[#1a1c1d] shadow-[0_0_0_1px_rgba(0,0,0,0.08)] transition-[background-color,box-shadow,scale,opacity] duration-150 ease-out hover:bg-gray-50 hover:shadow-[0_0_0_1px_rgba(0,0,0,0.12)] active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
        >
          {cancelText}
        </button>
        <button
          type="button"
          onclick={() => onConfirm()}
          disabled={loading}
          class="flex min-h-10 min-w-[132px] items-center justify-center gap-2 rounded-full bg-red-600 px-5 font-body text-[14px] font-medium text-white transition-[background-color,scale,opacity] duration-150 ease-out hover:bg-red-700 active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100"
        >
          {#if loading}
            <svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle class="opacity-25" cx="12" cy="12" r="9" stroke="currentColor" stroke-width="3"></circle>
              <path class="opacity-90" fill="currentColor" d="M21 12a9 9 0 00-9-9v3a6 6 0 016 6h3z"></path>
            </svg>
            Removing...
          {:else}
            {confirmText}
          {/if}
        </button>
      </div>
    </dialog>
  </div>
{/if}
