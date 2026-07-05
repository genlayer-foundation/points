/**
 * Convert parsed search filters to API query parameters.
 */

/**
 * Map parsed search filters to API parameters.
 * @param {Object} parsed - Output from parseSearch()
 * @param {Object} options - Additional context
 * @param {Array} [options.contributionTypes] - List of contribution types for name/slug lookup
 * @param {Array} [options.stewardsList] - List of stewards for name lookup
 * @param {string|number|null} [options.currentUserId] - Current user's ID for "me" resolution
 * @param {Array} [options.templates] - List of review templates for label lookup
 * @param {Array} [options.missions] - List of missions for name/ID lookup
 * @returns {Object} API query parameters
 */
export function searchToParams(parsed, options = {}) {
  const { contributionTypes = [], stewardsList = [], currentUserId = null } = options;
  /** @type {Record<string, any>} */
  const params = {};

  const { filters } = parsed;
  /** @param {any} value */
  const normalizeLookup = value => String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ');
  /** @param {any} value */
  const normalizeListValue = value => String(value || '').trim();
  /** @param {any} filter */
  const splitFilterValues = filter => {
    if (!filter) return [];
    const filters = Array.isArray(filter) ? filter : [filter];
    return filters.flatMap(item =>
      String(item.value || '')
        .split(',')
        .map(value => ({ value: normalizeListValue(value), negated: item.negated }))
        .filter(item => item.value)
    );
  };
  /**
   * @param {any} source
   * @param {any} query
   */
  const includesNormalized = (source, query) => {
    const normalizedSource = normalizeLookup(source);
    const normalizedQuery = normalizeLookup(query);
    return Boolean(
      normalizedSource &&
      normalizedQuery &&
      normalizedSource.includes(normalizedQuery)
    );
  };
  /**
   * @param {any} source
   * @param {any} query
   */
  const exactId = (source, query) => String(source) === String(query);
  /**
   * @param {string} key
   * @param {any} value
   */
  const setParamValue = (key, value) => {
    if (!value) return;
    if (params[key]) {
      const existing = String(params[key]).split(',').filter(Boolean);
      if (!existing.includes(String(value))) {
        params[key] = [...existing, value].join(',');
      }
    } else {
      params[key] = value;
    }
  };
  const hasValue = (values, candidates) => (
    values || []
  ).some(value => candidates.includes(String(value).toLowerCase()));

  // status → state (handle negation as exclude_state)
  if (filters.status) {
    const statusMap = {
      more_info: 'more_info_needed',
      'more-info': 'more_info_needed',
      info: 'more_info_needed',
      canceled: 'canceled',
      cancelled: 'canceled',
    };
    const state = statusMap[filters.status.value.toLowerCase()] || filters.status.value;
    if (filters.status.negated) {
      params.exclude_state = state;
    } else {
      params.state = state;
    }
  }

  // category → category / exclude_category (by slug)
  if (filters.category) {
    if (filters.category.negated) {
      params.exclude_category = filters.category.value.toLowerCase();
    } else {
      params.category = filters.category.value.toLowerCase();
    }
  }

  // type → contribution_type (by name, slug, or ID)
  if (filters.type) {
    const typeValue = normalizeLookup(filters.type.value);
    const type = contributionTypes.find(t =>
      t.slug?.toLowerCase() === typeValue ||
      normalizeLookup(t.name) === typeValue ||
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
    const usernameValue = normalizeListValue(filters.from.value);
    if (filters.from.negated) {
      params.exclude_username = usernameValue;
    } else {
      params.username_search = usernameValue;
    }
  }

  // Free text (untagged) → search across submitter, title, notes, and evidence
  if (filters.freeText && filters.freeText.length > 0) {
    params.search = filters.freeText.join(' ');
  }

  // assigned → assigned_to
  for (const assignedFilter of splitFilterValues(filters.assigned)) {
    const val = normalizeLookup(assignedFilter.value);
    let assignedValue = null;

    if (val === 'me' && currentUserId) {
      assignedValue = currentUserId;
    } else if (val === 'unassigned' || val === 'none') {
      assignedValue = 'unassigned';
    } else {
      // Find steward by name
      const steward = stewardsList.find(s =>
        exactId(s.user_id, assignedFilter.value) ||
        includesNormalized(s.name, assignedFilter.value) ||
        includesNormalized(s.user_name, assignedFilter.value) ||
        includesNormalized(s.address, assignedFilter.value)
      );
      if (steward) {
        assignedValue = steward.user_id;
      }
    }

    if (assignedValue) {
      if (assignedFilter.negated) {
        setParamValue('exclude_assigned_to', assignedValue);
      } else {
        setParamValue('assigned_to', assignedValue);
      }
    }
  }

  // reviewed → reviewed_by (the steward who actually accepted/rejected/requested info)
  for (const reviewedFilter of splitFilterValues(filters.reviewed)) {
    const val = normalizeLookup(reviewedFilter.value);
    let reviewedValue = null;

    if (val === 'me' && currentUserId) {
      reviewedValue = currentUserId;
    } else {
      const steward = stewardsList.find(s =>
        exactId(s.user_id, reviewedFilter.value) ||
        includesNormalized(s.name, reviewedFilter.value) ||
        includesNormalized(s.user_name, reviewedFilter.value) ||
        includesNormalized(s.address, reviewedFilter.value)
      );
      if (steward) {
        reviewedValue = steward.user_id;
      }
    }

    if (reviewedValue) {
      if (reviewedFilter.negated) {
        setParamValue('exclude_reviewed_by', reviewedValue);
      } else {
        setParamValue('reviewed_by', reviewedValue);
      }
    }
  }

  // proposed-by → proposed_by (the steward/agent who created the active proposal)
  for (const proposedByFilter of splitFilterValues(filters['proposed-by'])) {
    const val = normalizeLookup(proposedByFilter.value);
    let proposedByValue = null;

    if (val === 'ai') {
      proposedByValue = 'ai';
    } else if (val === 'me' && currentUserId) {
      proposedByValue = currentUserId;
    } else if (val === 'none' || val === 'unproposed') {
      proposedByValue = 'none';
    } else {
      const steward = stewardsList.find(s =>
        exactId(s.user_id, proposedByFilter.value) ||
        includesNormalized(s.name, proposedByFilter.value) ||
        includesNormalized(s.user_name, proposedByFilter.value) ||
        includesNormalized(s.address, proposedByFilter.value)
      );
      if (steward) {
        proposedByValue = steward.user_id;
      }
    }

    if (proposedByValue) {
      if (proposedByFilter.negated) {
        setParamValue('exclude_proposed_by', proposedByValue);
      } else {
        setParamValue('proposed_by', proposedByValue);
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
  if (hasValue(filters.no, ['url', 'evidence'])) {
    params.only_empty_evidence = true;
  } else if (hasValue(filters.has, ['url', 'evidence'])) {
    params.exclude_empty_evidence = true;
  }

  // has:proposal / no:proposal → proposal filter
  if (hasValue(filters.has, ['proposal'])) {
    params.has_proposal = true;
  } else if (hasValue(filters.no, ['proposal'])) {
    params.has_proposal = false;
  }

  // has:appeal / no:appeal and is:appealed / not:appealed → appeal filter
  if (
    hasValue(filters.has, ['appeal']) ||
    hasValue(filters.is, ['appealed'])
  ) {
    params.has_appeal = true;
  } else if (
    hasValue(filters.no, ['appeal']) ||
    hasValue(filters.not, ['appealed'])
  ) {
    params.has_appeal = false;
  }

  // is:interesting / not:interesting → is_interesting filter
  if (hasValue(filters.is, ['interesting'])) {
    params.is_interesting = true;
  } else if (hasValue(filters.not, ['interesting'])) {
    params.is_interesting = false;
  }

  const resubmittedAliases = ['resubmitted', 'more-info-resubmitted', 'more_info_resubmitted'];
  // is:resubmitted / not:resubmitted → pending submissions edited after more-info was requested
  if (hasValue(filters.is, resubmittedAliases)) {
    params.resubmitted_more_info = true;
  } else if (hasValue(filters.not, resubmittedAliases)) {
    params.resubmitted_more_info = false;
  }

  // min-contributions
  if (filters.minContributions !== null && filters.minContributions > 0) {
    params.min_accepted_contributions = filters.minContributions;
  }

  // proposal → proposed_action (accept, reject, more_info)
  if (filters.proposal) {
    const actionMap = {
      'accept': 'accept',
      'reject': 'reject',
      'more_info': 'more_info',
      'more-info': 'more_info',
      'info': 'more_info',
    };
    const mapped = actionMap[filters.proposal.value.toLowerCase()];
    if (mapped) {
      params.proposed_action = mapped;
    }
  }

  // proposal-status → proposal_review_status
  if (filters['proposal-status']) {
    const statusMap = {
      pending: 'pending_review',
      'pending-review': 'pending_review',
      pending_review: 'pending_review',
      questioned: 'questioned',
    };
    const mapped = statusMap[filters['proposal-status'].value.toLowerCase()];
    if (mapped) {
      params.proposal_review_status = mapped;
    }
  }

  // confidence → proposed_confidence
  if (filters.confidence) {
    params.proposed_confidence = filters.confidence.value.toLowerCase();
  }

  // template → proposed_template (by name/label → ID lookup)
  if (filters.template) {
    const { templates = [] } = options;
    const templateValue = normalizeLookup(filters.template.value);
    const template = templates.find(t =>
      normalizeLookup(t.label) === templateValue ||
      String(t.id) === filters.template.value
    );
    if (template) {
      params.proposed_template = template.id;
    }
  }

  // mission → mission (by name → ID lookup, or 'none' for no mission)
  if (filters.mission) {
    const missionValue = normalizeLookup(filters.mission.value);
    if (missionValue === 'none' || missionValue === 'null') {
      if (filters.mission.negated) {
        params.exclude_mission = 'none';
      } else {
        params.mission = 'none';
      }
    } else {
      const { missions = [] } = options;
      const mission = missions.find(m =>
        normalizeLookup(m.name) === missionValue ||
        String(m.id) === filters.mission.value
      );
      if (mission) {
        if (filters.mission.negated) {
          params.exclude_mission = mission.id;
        } else {
          params.mission = mission.id;
        }
      }
    }
  }

  // sort → ordering
  if (filters.sort) {
    const sortMap = {
      'created': 'created_at',
      '-created': '-created_at',
      'date': 'contribution_date',
      '-date': '-contribution_date',
      'reviewed': 'reviewed_at',
      '-reviewed': '-reviewed_at',
      'points': 'converted_contribution__frozen_global_points',
      '-points': '-converted_contribution__frozen_global_points'
    };
    const sortValue = filters.sort.value;
    params.ordering = sortMap[sortValue] || sortValue;
  }

  return params;
}
