/**
 * @param {string} hex
 */
function hexToRgb(hex) {
  const normalized = (hex || '#7f52e1').replace('#', '');
  const value = normalized.length === 3
    ? normalized.split('').map(/** @param {string} char */ (char) => char + char).join('')
    : normalized;

  const intValue = parseInt(value, 16);
  return {
    r: (intValue >> 16) & 255,
    g: (intValue >> 8) & 255,
    b: intValue & 255,
  };
}

/**
 * @param {string} hex
 * @param {number} alpha
 */
export function rgbaFromHex(hex, alpha) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * @param {string} category
 * @param {string} accentColor
 */
export function getCategoryGradientStyle(category, accentColor) {
  if (!category || category === 'global') return '';

  return [
    `background: radial-gradient(circle at 14% 8%, ${rgbaFromHex(accentColor, 0.38)} 0%, transparent 34%)`,
    `radial-gradient(circle at 82% 12%, ${rgbaFromHex(accentColor, 0.24)} 0%, transparent 32%)`,
    `linear-gradient(180deg, ${rgbaFromHex(accentColor, 0.16)} 0%, rgba(255, 255, 255, 0) 100%)`,
  ].join(', ');
}

/**
 * @param {string} accentColor
 */
export function getCategoryButtonStyle(accentColor) {
  return [
    `background-color: ${accentColor}`,
    `border-color: ${accentColor}`,
    `box-shadow: 0 8px 22px ${rgbaFromHex(accentColor, 0.22)}`,
  ].join('; ');
}
