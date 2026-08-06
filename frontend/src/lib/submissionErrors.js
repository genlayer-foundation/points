/**
 * Return the first useful message from DRF's nested validation-error shapes.
 *
 * @param {unknown} value
 * @returns {string}
 */
function firstErrorMessage(value) {
  if (typeof value === 'string') return value.trim();

  if (Array.isArray(value)) {
    for (const item of value) {
      const message = firstErrorMessage(item);
      if (message) return message;
    }
    return '';
  }

  if (value && typeof value === 'object') {
    const record = /** @type {Record<string, unknown>} */ (value);
    if (typeof record.message === 'string') {
      const message = record.message.trim();
      if (message) return message;
    }

    for (const nestedValue of Object.values(record)) {
      const message = firstErrorMessage(nestedValue);
      if (message) return message;
    }
  }

  return '';
}

/**
 * Extract a submitter-facing message from an API or network error.
 *
 * @param {any} error
 * @param {string} fallback
 * @returns {string}
 */
export function submissionErrorMessage(error, fallback) {
  const responseData = error?.response?.data || {};
  const fields = [
    responseData.more_info_response,
    responseData.evidence_items,
    responseData.error,
    responseData.detail,
  ];

  for (const field of fields) {
    const message = firstErrorMessage(field);
    if (message) return message;
  }

  if (!error?.response && typeof error?.message === 'string') {
    const message = error.message.trim();
    if (message) return message;
  }

  return fallback;
}
