/**
 * Convert parsed search filters to API query parameters.
 */

/**
 * Map parsed search filters to API parameters.
 * @param {Object} parsed - Output from parseSearch()
 * @param {Object} options - Additional context
 * @param {Array} options.contributionTypes - List of contribution types for name/slug lookup
 * @param {Array} options.stewardsList - List of stewards for name lookup
 * @param {string} options.currentUserId - Current user's ID for "me" resolution
 * @returns {Object} API query parameters
 */
export function searchToParams(parsed, options = {}) {
  const { contributionTypes = [], stewardsList = [], currentUserId = null } = options;
  const params = {};

  const { filters } = parsed;

  // status → state (handle negation as exclude_state)
  if (filters.status) {
    if (filters.status.negated) {
      params.exclude_state = filters.status.value;
    } else {
      params.state = filters.status.value;
    }
  }

  // type → contribution_type (by name, slug, or ID)
  if (filters.type) {
    const typeValue = filters.type.value.toLowerCase();
    const type = contributionTypes.find(t =>
      t.slug?.toLowerCase() === typeValue ||
      t.name?.toLowerCase() === typeValue ||
      t.name?.toLowerCase().replace(/\s+/g, '-') === typeValue ||
      String(t.id) === filters.type.value
    );
    if (type) {
      if (filters.type.negated) {
        params.exclude_contribution_type = type.id;
      } else {
        params.contribution_type = type.id;
      }
    }
  }

  // from → username_search (or exclude_username if negated)
  if (filters.from) {
    if (filters.from.negated) {
      params.exclude_username = filters.from.value;
    } else {
      params.username_search = filters.from.value;
    }
  }

  // assigned → assigned_to
  if (filters.assigned) {
    const val = filters.assigned.value.toLowerCase();
    let assignedValue = null;

    if (val === 'me' && currentUserId) {
      assignedValue = currentUserId;
    } else if (val === 'unassigned' || val === 'none') {
      assignedValue = 'unassigned';
    } else {
      // Find steward by name
      const steward = stewardsList.find(s =>
        s.name?.toLowerCase().includes(val) ||
        s.user_name?.toLowerCase().includes(val)
      );
      if (steward) {
        assignedValue = steward.user_id;
      }
    }

    if (assignedValue) {
      if (filters.assigned.negated) {
        params.exclude_assigned_to = assignedValue;
      } else {
        params.assigned_to = assignedValue;
      }
    }
  }

  // exclude → exclude_content (comma-separated for multiple values)
  if (filters.exclude && filters.exclude.length > 0) {
    params.exclude_content = filters.exclude.join(',');
  }

  // include → include_content (comma-separated for multiple values)
  if (filters.include && filters.include.length > 0) {
    params.include_content = filters.include.join(',');
  }

  // has:url / no:url → evidence filters
  if (filters.no && (filters.no.includes('url') || filters.no.includes('evidence'))) {
    params.only_empty_evidence = true;
  } else if (filters.has && (filters.has.includes('url') || filters.has.includes('evidence'))) {
    params.exclude_empty_evidence = true;
  }

  // has:proposal / no:proposal → proposal filter
  if (filters.has && filters.has.includes('proposal')) {
    params.has_proposal = true;
  } else if (filters.no && filters.no.includes('proposal')) {
    params.has_proposal = false;
  }

  // min-contributions
  if (filters.minContributions !== null && filters.minContributions > 0) {
    params.min_accepted_contributions = filters.minContributions;
  }

  // sort → ordering
  if (filters.sort) {
    const sortMap = {
      'created': 'created_at',
      '-created': '-created_at',
      'date': 'contribution_date',
      '-date': '-contribution_date'
    };
    const sortValue = filters.sort.value;
    params.ordering = sortMap[sortValue] || sortValue;
  }

  return params;
}
