export function stripPreviewMedia(html) {
  if (!html) return '';

  if (typeof DOMParser !== 'undefined') {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    doc.querySelectorAll('img, picture, source').forEach((node) => node.remove());
    return doc.body.innerHTML;
  }

  return html
    .replace(/<picture\b[\s\S]*?<\/picture>/gi, '')
    .replace(/<\s*(img|source)\b[^>]*>/gi, '');
}

export function isInteractiveTarget(event) {
  const interactiveTarget = event.target?.closest?.(
    'button, a, input, select, textarea, [role="button"], [role="link"]'
  );
  return Boolean(interactiveTarget && interactiveTarget !== event.currentTarget);
}
