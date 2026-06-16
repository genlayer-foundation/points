import DOMPurify from 'dompurify';
import { resolvePortalLink } from './links.js';

// Shared DOMPurify initialization. Import this module (for its side effect)
// before calling DOMPurify.sanitize anywhere, so link hardening does not
// depend on which module happened to load first.
//
// External links in sanitized HTML open in a new tab with a safe rel. The
// hook runs after sanitization, so target/rel never need to be allowed
// attributes (which would let content authors set arbitrary values).
// Same-origin absolute URLs (admins paste full portal URLs) are rewritten to
// in-app path routes, so they navigate within the SPA and keep browser history
// intact.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    const href = node.getAttribute('href') || '';
    if (/^https?:/i.test(href)) {
      const resolved = resolvePortalLink(href);
      if (resolved.external) {
        node.setAttribute('target', '_blank');
        node.setAttribute('rel', 'noopener noreferrer');
      } else {
        node.setAttribute('href', resolved.href);
        node.removeAttribute('target');
        node.removeAttribute('rel');
      }
    }
  }
});

export default DOMPurify;
