import DOMPurify from 'dompurify';

// Shared DOMPurify initialization. Import this module (for its side effect)
// before calling DOMPurify.sanitize anywhere, so link hardening does not
// depend on which module happened to load first.
//
// External links in sanitized HTML open in a new tab with a safe rel. The
// hook runs after sanitization, so target/rel never need to be allowed
// attributes (which would let content authors set arbitrary values).
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    const href = node.getAttribute('href') || '';
    if (/^https?:/i.test(href)) {
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', 'noopener noreferrer');
    }
  }
});

export default DOMPurify;
