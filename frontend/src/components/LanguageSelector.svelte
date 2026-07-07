<script>
  import { m } from '../lib/paraglide/messages.js';
  import { SUPPORTED_LOCALES, getLocale, setPortalLocale } from '../lib/i18n.js';

  // ponytail: native <select> instead of a custom dropdown — accessible,
  // works identically in the navbar and the mobile sidebar, zero popup JS.
  const current = getLocale();
</script>

<label class="language-selector" title={m.language_label()}>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20" />
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
  <select
    value={current}
    onchange={(e) => setPortalLocale(e.currentTarget.value)}
    aria-label={m.language_label()}
  >
    {#each SUPPORTED_LOCALES as locale (locale.code)}
      <option value={locale.code}>{locale.label}</option>
    {/each}
  </select>
</label>

<style>
  .language-selector {
    align-items: center;
    border-radius: 8px;
    color: #656567;
    cursor: pointer;
    display: inline-flex;
    gap: 5px;
    min-height: 28px;
    padding: 0 7px;
    transition: background-color 160ms ease, color 160ms ease;
  }

  .language-selector:hover {
    background: #f5f5f5;
    color: #131214;
  }

  .language-selector:focus-within {
    outline: 2px solid #8d81e1;
    outline-offset: 2px;
  }

  .language-selector svg {
    flex: 0 0 auto;
    height: 16px;
    width: 16px;
  }

  .language-selector select {
    appearance: none;
    background: transparent;
    border: none;
    color: inherit;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    outline: none;
    padding-right: 2px;
  }
</style>
