<script>
  import { onMount } from 'svelte';

  onMount(() => {
    try {
      // Extract query params from hash
      const hash = window.location.hash;
      const queryStartIndex = hash.indexOf('?');

      if (queryStartIndex !== -1) {
        const queryString = hash.substring(queryStartIndex + 1);
        const urlParams = new URLSearchParams(queryString);

        const success = urlParams.get('success') === 'true';
        const error = urlParams.get('error') || '';

        // Use BroadcastChannel to notify parent window (same origin)
        const channel = new BroadcastChannel('twitter_oauth');

        const message = success
          ? { type: 'twitter_oauth_success' }
          : { type: 'twitter_oauth_error', error: error };

        channel.postMessage(message);

        // Close popup quickly
        setTimeout(() => {
          channel.close();
          window.close();
        }, 500);
      }
    } catch (e) {
      // Error processing OAuth callback silently handled
    }
  });
</script>

<div class="min-h-screen flex items-center justify-center bg-gray-50">
  <div class="text-center">
    <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-black mb-4"></div>
    <p class="text-gray-600 text-lg">Completing Twitter connection...</p>
  </div>
</div>
