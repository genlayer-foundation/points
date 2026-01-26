/**
 * Parse a GitHub-style search query into structured filters.
 *
 * Supported tags:
 * - status:pending|accepted|rejected|more_info
 * - type:contribution-type-name
 * - from:username
 * - assigned:me|unassigned|steward-name
 * - exclude:text (multiple allowed)
 * - include:text (multiple allowed)
 * - has:url|evidence
 * - no:url|evidence
 * - min-contributions:number
 * - sort:created|-created|date|-date
 *
 * Negation: -tag:value or NOT tag:value
 * Quoted values: tag:"value with spaces"
 */

const SINGLE_VALUE_TAGS = ['status', 'type', 'from', 'assigned', 'sort'];
const MULTI_VALUE_TAGS = ['exclude', 'include', 'has', 'no'];
const NUMERIC_TAGS = ['min-contributions'];

/**
 * Tokenize the search query, respecting quoted strings.
 * @param {string} query
 * @returns {string[]}
 */
function tokenize(query) {
  const tokens = [];
  let current = '';
  let inQuotes = false;
  let quoteChar = '';

  for (let i = 0; i < query.length; i++) {
    const char = query[i];

    if ((char === '"' || char === "'") && !inQuotes) {
      inQuotes = true;
      quoteChar = char;
    } else if (char === quoteChar && inQuotes) {
      inQuotes = false;
      quoteChar = '';
    } else if (char === ' ' && !inQuotes) {
      if (current.trim()) {
        tokens.push(current.trim());
      }
      current = '';
    } else {
      current += char;
    }
  }

  if (current.trim()) {
    tokens.push(current.trim());
  }

  return tokens;
}

/**
 * Parse a single token into tag, value, and negation flag.
 * @param {string} token
 * @returns {{ tag: string, value: string, negated: boolean } | null}
 */
function parseToken(token) {
  let negated = false;
  let workingToken = token;

  // Check for negation prefix
  if (workingToken.startsWith('-')) {
    negated = true;
    workingToken = workingToken.slice(1);
  } else if (workingToken.toUpperCase().startsWith('NOT ')) {
    negated = true;
    workingToken = workingToken.slice(4);
  }

  // Check for tag:value pattern
  const colonIndex = workingToken.indexOf(':');
  if (colonIndex === -1) {
    return null; // Not a valid tag
  }

  const tag = workingToken.slice(0, colonIndex).toLowerCase();
  let value = workingToken.slice(colonIndex + 1);

  // Remove surrounding quotes from value
  if ((value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))) {
    value = value.slice(1, -1);
  }

  if (!value) {
    return null; // Empty value
  }

  return { tag, value, negated };
}

/**
 * Parse a search query string into structured filters.
 * @param {string} query
 * @returns {Object}
 */
export function parseSearch(query) {
  const filters = {
    status: null,
    type: null,
    from: null,
    assigned: null,
    exclude: [],
    include: [],
    has: [],
    no: [],
    minContributions: null,
    sort: null
  };

  if (!query || !query.trim()) {
    return { filters };
  }

  const tokens = tokenize(query);

  for (const token of tokens) {
    // Handle "NOT tag:value" as two tokens
    if (token.toUpperCase() === 'NOT') {
      continue; // Will be handled with next token
    }

    const parsed = parseToken(token);
    if (!parsed) {
      continue; // Ignore unrecognized tokens
    }

    const { tag, value, negated } = parsed;

    // Handle single-value tags
    if (SINGLE_VALUE_TAGS.includes(tag)) {
      filters[tag] = { value, negated };
    }
    // Handle multi-value tags
    else if (MULTI_VALUE_TAGS.includes(tag)) {
      filters[tag].push(value);
    }
    // Handle numeric tags
    else if (NUMERIC_TAGS.includes(tag)) {
      const num = parseInt(value, 10);
      if (!isNaN(num)) {
        if (tag === 'min-contributions') {
          filters.minContributions = num;
        }
      }
    }
  }

  return { filters };
}

/**
 * Convert parsed filters back to a query string.
 * Useful for URL sync and display.
 * @param {Object} filters
 * @returns {string}
 */
export function filtersToQuery(filters) {
  const parts = [];

  for (const tag of SINGLE_VALUE_TAGS) {
    const filter = filters[tag];
    if (filter && filter.value) {
      const prefix = filter.negated ? '-' : '';
      const value = filter.value.includes(' ') ? `"${filter.value}"` : filter.value;
      parts.push(`${prefix}${tag}:${value}`);
    }
  }

  for (const tag of MULTI_VALUE_TAGS) {
    const values = filters[tag] || [];
    for (const value of values) {
      const formattedValue = value.includes(' ') ? `"${value}"` : value;
      parts.push(`${tag}:${formattedValue}`);
    }
  }

  if (filters.minContributions !== null && filters.minContributions > 0) {
    parts.push(`min-contributions:${filters.minContributions}`);
  }

  return parts.join(' ');
}
