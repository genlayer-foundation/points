<script>
  import { onMount } from 'svelte';
  import { alertsAPI } from '../../lib/api.js';
  import AlertBanner from './AlertBanner.svelte';

  let alerts = $state([]);
  let dismissedIds = $state([]);

  const STORAGE_KEY = 'dismissed-alerts';

  function loadDismissed() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  function saveDismissed(ids) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    } catch {
      // localStorage unavailable
    }
  }

  function dismiss(id) {
    dismissedIds = [...dismissedIds, id];
    saveDismissed(dismissedIds);
  }

  let visibleAlerts = $derived(
    alerts.filter(a => !dismissedIds.includes(a.id))
  );

  onMount(async () => {
    dismissedIds = loadDismissed();
    try {
      const response = await alertsAPI.getAlerts();
      alerts = response.data || [];

      // Clean up stale dismissed IDs
      const activeIds = new Set(alerts.map(a => a.id));
      const cleaned = dismissedIds.filter(id => activeIds.has(id));
      if (cleaned.length !== dismissedIds.length) {
        dismissedIds = cleaned;
        saveDismissed(cleaned);
      }
    } catch {
      // Silently fail — alerts are non-critical
    }
  });
</script>

{#if visibleAlerts.length > 0}
  <div class="space-y-2 mb-3">
    {#each visibleAlerts as alert (alert.id)}
      <AlertBanner
        id={alert.id}
        alertType={alert.alert_type}
        text={alert.text}
        icon={alert.icon}
        onDismiss={dismiss}
      />
    {/each}
  </div>
{/if}
