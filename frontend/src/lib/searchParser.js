/**
 * Parse a GitHub-style search query into structured filters.
 *
 * Supported tags:
 * - status:pending|accepted|rejected|canceled|more_info
 * - type:contribution-type-name
 * - from:username
 * - assigned:me|unassigned|steward-name
 * - reviewed:me|steward-name
 * - proposed-by:ai|me|none|steward-name
 * - exclude:text (multiple allowed)
 * - include:text (multiple allowed)
 * - has:url|evidence|proposal|appeal
 * - no:url|evidence|proposal|appeal
 * - is:interesting|appealed|resubmitted
 * - not:interesting|appealed|resubmitted
 * - min-contributions:number
 * - sort:created|-created|date|-date
 *
 * Negation: -tag:value or NOT tag:value
 * Quoted values: tag:"value with spaces"
 */

const SINGLE_VALUE_TAGS = ['status', 'type', 'category', 'from', 'assigned', 'reviewed', 'proposed-by', 'sort', 'confidence', 'template', 'proposal', 'mission'];
const MULTI_VALUE_TAGS = ['exclude', 'include', 'has', 'no', 'is', 'not'];
const NUMERIC_TAGS = ['min-contributions'];
const NEGATED_MULTI_VALUE_TAGS = {
  exclude: 'include',
  include: 'exclude',
  has: 'no',
  no: 'has',
  is: 'not',
  not: 'is'
};

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
    category: null,
    from: null,
    assigned: null,
    reviewed: null,
    'proposed-by': null,
    exclude: [],
    include: [],
    has: [],
    no: [],
    is: [],
    not: [],
    minContributions: null,
    sort: null,
    freeText: []
  };

  if (!query || !query.trim()) {
    return { filters };
  }

  const tokens = tokenize(query);
  let negateNext = false;

  for (const token of tokens) {
    // Handle "NOT tag:value" as two tokens
    if (token.toUpperCase() === 'NOT') {
      negateNext = true;
      continue; // Will be handled with next token
    }

    const parsed = parseToken(token);
    if (!parsed) {
      // Untagged text — collect as free-text search terms
      filters.freeText.push(token);
      negateNext = false;
      continue;
    }

    const { tag, value } = parsed;
    const negated = parsed.negated || negateNext;
    negateNext = false;

    // Handle single-value tags
    if (SINGLE_VALUE_TAGS.includes(tag)) {
      filters[tag] = { value, negated };
    }
    // Handle multi-value tags
    else if (MULTI_VALUE_TAGS.includes(tag)) {
      const targetTag = negated ? NEGATED_MULTI_VALUE_TAGS[tag] : tag;
      filters[targetTag].push(value);
    }
    // Handle numeric tags
    else if (NUMERIC_TAGS.includes(tag)) {
      const num = parseInt(value, 10);
      if (!isNaN(num)) {
        filters.minContributions = num;
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
