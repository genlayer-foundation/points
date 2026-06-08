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
 * @param {Array} options.templates - List of review templates for label lookup
 * @param {Array} options.missions - List of missions for name/ID lookup
 * @returns {Object} API query parameters
 */
export function searchToParams(parsed, options = {}) {
  const { contributionTypes = [], stewardsList = [], currentUserId = null } = options;
  const params = {};

  const { filters } = parsed;
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

  // Free text (untagged) → search across submitter, title, notes, and evidence
  if (filters.freeText && filters.freeText.length > 0 && !params.username_search) {
    params.search = filters.freeText.join(' ');
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

  // reviewed → reviewed_by (the steward who actually accepted/rejected/requested info)
  if (filters.reviewed) {
    const val = filters.reviewed.value.toLowerCase();
    let reviewedValue = null;

    if (val === 'me' && currentUserId) {
      reviewedValue = currentUserId;
    } else {
      const steward = stewardsList.find(s =>
        String(s.user_id) === filters.reviewed.value ||
        s.name?.toLowerCase().includes(val) ||
        s.user_name?.toLowerCase().includes(val) ||
        s.address?.toLowerCase().includes(val)
      );
      if (steward) {
        reviewedValue = steward.user_id;
      }
    }

    if (reviewedValue) {
      if (filters.reviewed.negated) {
        params.exclude_reviewed_by = reviewedValue;
      } else {
        params.reviewed_by = reviewedValue;
      }
    }
  }

  // proposed-by → proposed_by (the steward/agent who created the active proposal)
  if (filters['proposed-by']) {
    const val = filters['proposed-by'].value.toLowerCase();
    let proposedByValue = null;

    if (val === 'ai') {
      proposedByValue = 'ai';
    } else if (val === 'me' && currentUserId) {
      proposedByValue = currentUserId;
    } else if (val === 'none' || val === 'unproposed') {
      proposedByValue = 'none';
    } else {
      const steward = stewardsList.find(s =>
        String(s.user_id) === filters['proposed-by'].value ||
        s.name?.toLowerCase().includes(val) ||
        s.user_name?.toLowerCase().includes(val) ||
        s.address?.toLowerCase().includes(val)
      );
      if (steward) {
        proposedByValue = steward.user_id;
      }
    }

    if (proposedByValue) {
      if (filters['proposed-by'].negated) {
        params.exclude_proposed_by = proposedByValue;
      } else {
        params.proposed_by = proposedByValue;
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

  // confidence → proposed_confidence
  if (filters.confidence) {
    params.proposed_confidence = filters.confidence.value.toLowerCase();
  }

  // template → proposed_template (by name/label → ID lookup)
  if (filters.template) {
    const { templates = [] } = options;
    const templateValue = filters.template.value.toLowerCase();
    const template = templates.find(t =>
      t.label?.toLowerCase() === templateValue ||
      t.label?.toLowerCase().replace(/\s+/g, '-') === templateValue ||
      String(t.id) === filters.template.value
    );
    if (template) {
      params.proposed_template = template.id;
    }
  }

  // mission → mission (by name → ID lookup, or 'none' for no mission)
  if (filters.mission) {
    const missionValue = filters.mission.value.toLowerCase();
    if (missionValue === 'none' || missionValue === 'null') {
      if (filters.mission.negated) {
        params.exclude_mission = 'none';
      } else {
        params.mission = 'none';
      }
    } else {
      const { missions = [] } = options;
      const mission = missions.find(m =>
        m.name?.toLowerCase() === missionValue ||
        m.name?.toLowerCase().replace(/\s+/g, '-') === missionValue ||
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
