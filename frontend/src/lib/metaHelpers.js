export function truncateMetaDescription(value) {
  const text = String(value ?? '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  return text.length > 155 ? `${text.slice(0, 152).trim()}...` : text;
}
