/**
 * Convert parsed steward Discord XP search filters to API query parameters.
 */

function findContributionType(value, contributionTypes) {
  const typeValue = String(value || '').toLowerCase();
  return contributionTypes.find(t =>
    t.slug?.toLowerCase() === typeValue ||
    t.name?.toLowerCase() === typeValue ||
    t.name?.toLowerCase().replace(/\s+/g, '-') === typeValue ||
    String(t.id) === String(value)
  );
}

/**
 * @param {Object} parsed - Output from parseSearch()
 * @param {Object} options
 * @param {Array} options.contributionTypes
 * @returns {Object}
 */
export function xpSearchToParams(parsed, options = {}) {
  const { contributionTypes = [] } = options;
  const { filters } = parsed;
  const params = {};

  if (filters.type) {
    const type = findContributionType(filters.type.value, contributionTypes);
    if (type) {
      if (filters.type.negated) {
        params.exclude_contribution_type = type.id;
      } else {
        params.contribution_type = type.id;
      }
    }
  }

  if (filters.from) {
    params.username_search = filters.from.value;
  }

  if (filters.freeText && filters.freeText.length > 0 && !params.username_search) {
    params.search = filters.freeText.join(' ');
  }

  if (filters.include && filters.include.length > 0) {
    params.include_content = filters.include.join(',');
  }

  if (filters.exclude && filters.exclude.length > 0) {
    params.exclude_content = filters.exclude.join(',');
  }

  if (filters.sort) {
    const sortMap = {
      created: 'contribution__created_at',
      '-created': '-contribution__created_at',
      date: 'contribution__contribution_date',
      '-date': '-contribution__contribution_date',
      points: 'contribution__frozen_global_points',
      '-points': '-contribution__frozen_global_points',
      distributed: 'distributed_at',
      '-distributed': '-distributed_at',
    };
    params.ordering = sortMap[filters.sort.value] || filters.sort.value;
  }

  return params;
}
