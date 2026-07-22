// Role funnel state, derived from the /users/me/ payload (userStore.user).
//
// Journeys grant the ROLE (a profile row), never points — so "earned" is the
// presence of the role's profile object on the user, and "started" is a cheap
// best-effort signal that the user took a first journey step. No parallel
// backend state is kept; everything here reads fields already on /users/me/.

// The builder journey's single points-bearing step. Kept in sync with the
// backend seed (social_tasks migration 0004 / settings.BUILDER_JOURNEY_TASK_SLUG).
export const STAR_BOILERPLATE_TASK_SLUG = 'star-genlayer-boilerplate';

const ROUTE_BASE = {
  builder: '/builders',
  validator: '/validators',
  community: '/community',
};

const VIEWABLE_ROLE_CATEGORIES = new Set(['builder', 'validator', 'community']);

export function rolePath(category) {
  return ROUTE_BASE[category] || '/';
}

export function journeyPath(category) {
  return ROUTE_BASE[category] ? `${ROUTE_BASE[category]}/journey` : '/';
}

export function hasEarnedRole(user, category) {
  if (!user) return false;
  if (category === 'builder') return !!user.builder;
  if (category === 'validator') return !!user.validator;
  if (category === 'community') return !!user.creator;
  return false;
}

// Admin-managed read access is deliberately separate from role membership.
// The backend returns the flag to its owner only; keeping it out of
// hasEarnedRole prevents funnels, submissions, points, and stats from treating
// a viewer as a Builder, Validator, Creator, or Steward.
/**
 * @param {Record<string, any> | null | undefined} user
 * @param {string} category
 */
export function hasRoleSectionAccess(user, category) {
  if (hasEarnedRole(user, category)) return true;
  return VIEWABLE_ROLE_CATEGORIES.has(category)
    && user?.can_view_role_sections === true;
}

/**
 * @param {Record<string, any> | null | undefined} user
 * @param {string} category
 */
export function hasReadOnlyRoleSectionAccess(user, category) {
  return VIEWABLE_ROLE_CATEGORIES.has(category)
    && user?.can_view_role_sections === true
    && !hasEarnedRole(user, category);
}

// "Started but not earned", from durable point-free `<role>-welcome` markers set
// when the user clicks "Start the journey" (plus the role's deeper signals for
// back-compat: validator waitlist, community social links).
export function hasStartedJourney(user, category) {
  if (!user || hasEarnedRole(user, category)) return false;
  if (category === 'builder') return !!user.has_builder_welcome;
  if (category === 'validator') return !!(user.has_validator_welcome || user.has_validator_waitlist);
  if (category === 'community') {
    return !!(user.has_community_welcome || user.has_community_link_x || user.has_community_link_discord);
  }
  return false;
}

// 'unauthenticated' | 'none' | 'started' | 'earned'
export function roleFunnelState(isAuthenticated, user, category) {
  if (!isAuthenticated) return 'unauthenticated';
  if (hasEarnedRole(user, category)) return 'earned';
  if (hasStartedJourney(user, category)) return 'started';
  return 'none';
}

// Map an entry route's category (incl. 'global'/'steward') to a funnel role,
// for onboarding preselect. Anything non-role defaults to community.
export function roleForCategory(category) {
  if (category === 'builder' || category === 'validator') return category;
  return 'community';
}

// "Engaged member" — past a fresh signup: earned a role, started a journey,
// linked a community social, is a steward, or in a working group. Used to gate
// first-run UI (What's New) away from brand-new accounts still in onboarding.
export function hasAnyRoleOrJourney(user) {
  if (!user) return false;
  if (user.steward || (user.working_groups && user.working_groups.length)) return true;
  return ['builder', 'validator', 'community'].some(
    (c) => hasEarnedRole(user, c) || hasStartedJourney(user, c),
  );
}
