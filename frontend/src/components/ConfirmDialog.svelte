<script>
  let {
    isOpen = false,
    title = "Confirm",
    message = "Are you sure?",
    confirmText = "Confirm",
    cancelText = "Cancel",
    onConfirm = () => {},
    onCancel = () => {}
  } = $props();

  function handleConfirm() {
    onConfirm();
  }

  function handleCancel() {
    onCancel();
  }

  function handleBackdropClick(event) {
    if (event.target === event.currentTarget) {
      handleCancel();
    }
  }
</script>

{#if isOpen}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    onclick={handleBackdropClick}
  >
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">{title}</h3>
      </div>

      <!-- Body -->
      <div class="px-6 py-4">
        <p class="text-sm text-gray-600">{message}</p>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
        <button
          onclick={handleCancel}
          class="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700"
        >
          {cancelText}
        </button>
        <button
          onclick={handleConfirm}
          class="px-4 py-2 text-sm border border-red-300 rounded-md bg-red-50 hover:bg-red-100 text-red-700"
        >
          {confirmText}
        </button>
      </div>
    </div>
  </div>
{/if}
