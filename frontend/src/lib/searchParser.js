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
 * - sort:created|-created|date|-date|reviewed|-reviewed|points|-points
 *
 * Negation: -tag:value or NOT tag:value
 * Quoted values: tag:"value with spaces"
 */

const SINGLE_VALUE_TAGS = ['status', 'type', 'category', 'from', 'assigned', 'reviewed', 'proposed-by', 'sort', 'confidence', 'template', 'proposal', 'mission'];
const MULTI_VALUE_TAGS = ['exclude', 'include', 'has', 'no', 'is', 'not'];
const NUMERIC_TAGS = ['min-contributions'];
const KNOWN_TAGS = [...SINGLE_VALUE_TAGS, ...MULTI_VALUE_TAGS, ...NUMERIC_TAGS];
const COMPOUND_SINGLE_VALUE_TAGS = ['assigned', 'reviewed', 'proposed-by'];
const SPACE_VALUE_TAGS = ['type', 'from', 'assigned', 'reviewed', 'proposed-by', 'template', 'mission'];
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

function isKnownTagToken(token) {
  const match = token.match(/^-?([a-z-]+):/i);
  return Boolean(match && KNOWN_TAGS.includes(match[1].toLowerCase()));
}

function isSpaceValueContinuation(token) {
  return /^[A-Za-z0-9][A-Za-z0-9.'-]*$/.test(String(token || ''));
}

function shouldConsumeSpaceValue(tag, value, nextToken = '') {
  if (!SPACE_VALUE_TAGS.includes(tag)) return false;
  const normalized = String(value || '').toLowerCase();
  const next = String(nextToken || '');
  const exactAliases = {
    assigned: ['me', 'unassigned', 'none', 'null'],
    reviewed: ['me'],
    'proposed-by': ['ai', 'me', 'none', 'null', 'unproposed'],
    mission: ['none', 'null'],
  };
  const canContinueLowercaseName = (
    ['assigned', 'reviewed', 'proposed-by'].includes(tag) &&
    /^[A-Z0-9]/.test(String(value || '')) &&
    /^[a-z0-9]/.test(next)
  );
  return (
    !(exactAliases[tag] || []).includes(normalized) &&
    isSpaceValueContinuation(next) &&
    (/^[A-Z0-9]/.test(next) || canContinueLowercaseName)
  );
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

  for (let i = 0; i < tokens.length; i++) {
    let token = tokens[i];

    // Handle "NOT tag:value" as two tokens
    if (token.toUpperCase() === 'NOT') {
      negateNext = true;
      continue; // Will be handled with next token
    }

    const danglingTagMatch = token.match(/^(-?)([a-z-]+):$/i);
    if (
      danglingTagMatch &&
      KNOWN_TAGS.includes(danglingTagMatch[2].toLowerCase()) &&
      i + 1 < tokens.length
    ) {
      if (isKnownTagToken(tokens[i + 1])) {
        negateNext = false;
        continue;
      }
      const tagName = danglingTagMatch[2].toLowerCase();
      const valueParts = [tokens[i + 1]];
      i += 1;
      if (shouldConsumeSpaceValue(tagName, valueParts[0], tokens[i + 1])) {
        while (
          i + 1 < tokens.length &&
          !isKnownTagToken(tokens[i + 1]) &&
          isSpaceValueContinuation(tokens[i + 1])
        ) {
          valueParts.push(tokens[i + 1]);
          i += 1;
        }
      }
      token = `${token}${valueParts.join(' ')}`;
    } else if (
      danglingTagMatch &&
      KNOWN_TAGS.includes(danglingTagMatch[2].toLowerCase())
    ) {
      negateNext = false;
      continue;
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

    if (shouldConsumeSpaceValue(tag, parsed.value, tokens[i + 1])) {
      while (
        i + 1 < tokens.length &&
        !isKnownTagToken(tokens[i + 1]) &&
        isSpaceValueContinuation(tokens[i + 1])
      ) {
        parsed.value += ` ${tokens[i + 1]}`;
        i += 1;
      }
    }

    // Handle single-value tags
    if (SINGLE_VALUE_TAGS.includes(tag)) {
      const filter = { value: parsed.value, negated };
      if (COMPOUND_SINGLE_VALUE_TAGS.includes(tag)) {
        const existing = filters[tag];
        filters[tag] = existing
          ? (Array.isArray(existing) ? [...existing, filter] : [existing, filter])
          : filter;
      } else {
        filters[tag] = filter;
      }
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
    } else {
      // Unknown tag-like tokens, including URLs such as https://x.com/..., are
      // treated as plain text so they still participate in general search.
      filters.freeText.push(token);
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
    const filterItems = Array.isArray(filter) ? filter : (filter ? [filter] : []);
    for (const item of filterItems) {
      if (!item?.value) continue;
      const prefix = item.negated ? '-' : '';
      const value = item.value.includes(' ') ? `"${item.value}"` : item.value;
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
