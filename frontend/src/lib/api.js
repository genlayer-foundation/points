import axios from 'axios';
import { API_BASE_URL } from './config.js';
import { attachCsrfToken } from './csrf.js';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000, // Increased timeout to 30 seconds for slow endpoints
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // Enable cookies for session-based auth
});

// Add request interceptor to ensure credentials are always sent
api.interceptors.request.use(
  async (config) => {
    // Ensure withCredentials is always true
    config.withCredentials = true;
    
    // Don't override Content-Type for FormData
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    
    return attachCsrfToken(config);
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 403 || error.response?.status === 401) {
      // If we get an auth error, verify auth status
      import('./auth.js').then(({ verifyAuth }) => {
        verifyAuth();
      });
    }
    return Promise.reject(error);
  }
);

// API endpoints for users
export const usersAPI = {
  getUsers: (params) => api.get('/users/', { params }),
  getUser: (address) => api.get(`/users/${address}/`),
  getUserByAddress: (address) => api.get(`/users/by-address/${address}/`),
  getUserHighlights: (address, params) => api.get(`/users/by-address/${address}/highlights/`, { params }),
  getUserMissions: (address, params) => api.get(`/users/by-address/${address}/missions/`, { params }),
  getUserCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.participant_count }
  })),
  getParticipantCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.participant_count }
  })),
  getCurrentUser: () => api.get('/users/me/'),
  updateUserProfile: (data) => api.patch('/users/me/', data),
  getAccountBalance: () => api.get('/users/balance/'),
  getActiveValidators: () => api.get('/users/validators/'),
  getReferrals: () => api.get('/users/referrals/'),
  getReferralPoints: () => api.get('/users/referral_points/'),
  searchUsers: (query) => api.get('/users/search/', { params: { q: query } })
};

// API endpoints for contributions
export const contributionsAPI = {
  getContributions: (params) => api.get('/contributions/', { params }),
  getContribution: (id) => api.get(`/contributions/${id}/`),
  getContributionsByUser: (address) => api.get(`/contributions/?user_address=${address}`),
  getContributionTypes: (params) => {
    // Set a high page_size to get all contribution types in one request
    const enhancedParams = {
      page_size: 100,
      ...params
    };
    return api.get('/contribution-types/', { params: enhancedParams });
  },
  getContributionType: (id) => api.get(`/contribution-types/${id}/`),
  getContributionTypeMultipliers: (typeId) => api.get(`/contribution-type-multipliers/?contribution_type=${typeId}`),
  getContributionTypeStatistics: (params) => api.get('/contribution-types/statistics/', { params }),
  getContributionTypeTopContributors: (id) => api.get(`/contribution-types/${id}/top_contributors/`),
  getContributionTypeRecentContributions: (id) => api.get(`/contribution-types/${id}/recent_contributions/`),
  getContributionTypeHighlights: (id) => api.get(`/contribution-types/${id}/highlights/`),
  getAllHighlights: (params) => api.get('/contributions/highlights/', { params }),
  getContributionCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.contribution_count }
  })),
  getMissions: (params) => api.get('/missions/', { params }),
  getMission: (id) => api.get(`/missions/${id}/`),
  /** @param {string | number} id */
  getMissionStats: (id) => api.get(`/missions/${id}/stats/`),
  getStartupRequests: () => api.get('/startup-requests/'),
  getStartupRequest: (id) => api.get(`/startup-requests/${id}/`)
};

// API endpoints for the submitter-side submission flows
export const submissionsAPI = {
  appeal: (id, reason) => api.post(`/submissions/${id}/appeal/`, { reason }),
  getAcceptedProjects: () => api.get('/submissions/accepted-projects/')
};

// Portal notifications API
export const notificationsAPI = {
  list: (params = {}) => api.get('/notifications/', { params }),
  unreadCount: () => api.get('/notifications/unread-count/'),
  markRead: (id) => api.post(`/notifications/${id}/mark-read/`),
  markAllRead: () => api.post('/notifications/mark-all-read/')
};

// Curated What's New announcements API
export const whatsNewAPI = {
  list: (params = {}) => api.get('/whats-new/', { params }),
  unseenCount: () => api.get('/whats-new/unseen-count/'),
  markSeen: (ids, action = 'seen') => api.post('/whats-new/mark-seen/', { ids, action })
};


// API endpoints for leaderboard
export const leaderboardAPI = {
  getLeaderboard: (params = {}) => {
    const { type, category, ...restParams } = params;
    const leaderboardType = type || category;

    if (leaderboardType === 'community') {
      return api.get('/leaderboard/community/', { params: restParams });
    }

    if (leaderboardType) {
      return api.get('/leaderboard/', { params: { type: leaderboardType, ...restParams } });
    }

    return api.get('/leaderboard/', { params: restParams });
  },
  getLeaderboardByType: (type, order = 'asc', additionalParams = {}) => {
    if (type === 'community') {
      return api.get('/leaderboard/community/', { params: { order, ...additionalParams } });
    }
    return api.get('/leaderboard/', { params: { type, order, ...additionalParams } });
  },
  getLeaderboardEntry: (address) => api.get(`/leaderboard/?user_address=${address}`),
  getMultipliers: () => api.get('/multipliers/'),
  getActiveMultipliers: () => api.get('/multipliers/active/'),
  getMultiplierPeriods: (multiplier_id) => api.get(`/multiplier-periods/?multiplier=${multiplier_id}`),
  getStats: () => api.get('/leaderboard/stats/'),
  getWaitlistStats: () => api.get('/leaderboard/validator-waitlist-stats/'),
  getWaitlistTop: (limit = 10) => api.get('/leaderboard/validator-waitlist/top/', { params: { limit } }),
  getMonthlyLeaderboardByType: (type, limit = 10, additionalParams = {}) =>
    api.get('/leaderboard/monthly/', { params: { type, limit, ...additionalParams } }),
  getCommunity: (params = {}) => leaderboardAPI.getLeaderboard({ type: 'community', ...params }),
  getCommunityContributors: (params = {}) => leaderboardAPI.getLeaderboard({ type: 'community', ...params }),
  getReferrals: (params = {}) => api.get('/leaderboard/referrals/', { params }),
  getTrending: (limit = 10, params = {}) => api.get('/leaderboard/trending/', { params: { limit, ...params } }),
  getTypes: () => api.get('/leaderboard/types/'),
  recalculateAll: () => api.post('/leaderboard/recalculate/')
};

// Stats API
export const statsAPI = {
  getDashboardStats: (type = null) => {
    const params = type && type !== 'global' ? { type } : {};
    return api.get('/leaderboard/stats/', { params });
  },
  getUserStats: (address, category = null) => {
    const params = category ? { category } : {};
    return api.get(`/leaderboard/user_stats/by-address/${address}/`, { params });
  }
};

let overviewMetricsResponse = null;
let overviewMetricsFetchedAt = 0;
let overviewMetricsRequest = null;
const OVERVIEW_METRICS_CACHE_MS = 30000;

// Metrics API
export const metricsAPI = {
  getOverview: () => {
    const now = Date.now();
    if (overviewMetricsResponse && now - overviewMetricsFetchedAt < OVERVIEW_METRICS_CACHE_MS) {
      return Promise.resolve(overviewMetricsResponse);
    }
    if (overviewMetricsRequest) return overviewMetricsRequest;

    overviewMetricsRequest = (async () => {
      try {
        const response = await api.get('/metrics/overview/');
        overviewMetricsResponse = response;
        overviewMetricsFetchedAt = Date.now();
        return response;
      } finally {
        overviewMetricsRequest = null;
      }
    })();

    return overviewMetricsRequest;
  },
  getNetworkActivity: () => api.get('/metrics/overview/network-activity/'),
};

// Validators API
export const validatorsAPI = {
  getNewestValidators: (limit = 5) => api.get('/validators/newest/', { params: { limit } }),
  getAllValidators: () => api.get('/validators/all/'),
  // Validator Wallets
  getAllValidatorWallets: (params = {}) => api.get('/validators/wallets/', { params }),
  getValidatorWalletsByOperator: (operatorAddress, network = null) => {
    const params = network ? { network } : {};
    return api.get(`/validators/wallets/by-operator/${operatorAddress}/`, { params });
  },
  getValidatorWalletsByUserAddress: (userAddress, network = null) => {
    const params = network ? { network } : {};
    return api.get(`/validators/wallets/by-user-address/${userAddress}/`, { params });
  },
  getMyValidatorWallets: () => api.get('/validators/my-wallets/'),
  linkValidatorWalletsByOperator: (operatorAddress) => api.post('/validators/link-by-operator/', { operator_address: operatorAddress }),
  getNetworks: () => api.get('/validators/wallets/networks/'),
  getWallOfShame: (params = {}) => api.get('/validators/wallets/wall-of-shame/', { params })
};

// Builders API
export const buildersAPI = {
  getNewestBuilders: (limit = 5) => api.get('/builders/newest/', { params: { limit } })
};

// Journey API
export const journeyAPI = {
  startValidatorJourney: () => api.post('/users/start_validator_journey/'),
  startBuilderJourney: () => api.post('/users/start_builder_journey/'),
  completeBuilderJourney: () => api.post('/users/complete_builder_journey/'),
  deploymentStatus: () => api.get('/users/deployment_status/'),
  linkXAccount: () => api.post('/users/link_x_account/'),
  linkDiscordAccount: () => api.post('/users/link_discord_account/'),
  linkGithubAccount: () => api.post('/users/link_github_account/'),
  // Point-free "started" marker for any role (builder|validator|community).
  startRoleJourney: (role) => api.post('/users/start_role_journey/', { role }),
  // Creator journey (5 steps -> Creator role)
  communityJourney: () => api.get('/users/community_journey/'),
  verifyCommunityPost: (postUrl) => api.post('/users/verify_community_post/', { post_url: postUrl }),
  completeCommunityJourney: () => api.post('/users/complete_community_journey/')
};

// Social connections API
export const socialAPI = {
  refreshGitHubUsername: () => api.post('/users/github/refresh/'),
  refreshTwitterUsername: () => api.post('/users/twitter/refresh/'),
  refreshDiscordUsername: () => api.post('/users/discord/refresh/'),
  refreshDiscordRoles: () => api.post('/users/discord/sync-roles/me/'),
  checkDiscordGuild: () => api.get('/users/discord/check-guild/'),
};

// Social tasks API
export const socialTasksAPI = {
  list: (params = {}) => api.get('/social-tasks/', { params }),
  complete: (slug) => api.post(`/social-tasks/${slug}/complete/`),
};

// Steward API
export const stewardAPI = {
  // Get all submissions for review
  getSubmissions: (params = {}) => api.get('/steward-submissions/', { params }),

  // Get community Discord XP states (contributions + social task completions), keyed by state id
  getDiscordXP: (params = {}) => api.get('/steward-discord-xp/', { params }),

  // Record that a steward copied the manual Discord XP command
  recordDiscordXPCopy: (stateId) => api.post(`/steward-discord-xp/${stateId}/record-copy/`),

  // Mark or unset manual Discord XP distribution
  markDiscordXPDistributed: (stateId) => api.post(`/steward-discord-xp/${stateId}/mark-distributed/`),
  unsetDiscordXPDistributed: (stateId) => api.post(`/steward-discord-xp/${stateId}/unset-distributed/`),

  // Get a single submission
  getSubmission: (id) => api.get(`/steward-submissions/${id}/`),

  // Review a submission (accept, reject, or request more info)
  reviewSubmission: (id, data) => api.post(`/steward-submissions/${id}/review/`, data),

  /**
   * Correct points or feature an already accepted submission.
   * @param {string | number} id
   * @param {{ points: number, create_highlight?: boolean, remove_highlight?: boolean, highlight_title?: string, highlight_description?: string }} data
   */
  updateAcceptedSubmission: (id, data) => api.post(`/steward-submissions/${id}/update-accepted/`, data),

  // Get all users for reassignment dropdown
  getUsers: () => api.get('/steward-submissions/users/'),

  // Get accepted Projects contributions for a selected award user
  getAcceptedProjectsForUser: (userId, submissionId = null) =>
    api.get('/steward-submissions/accepted-projects/', {
      params: {
        user: userId,
        ...(submissionId ? { submission: submissionId } : {})
      }
    }),

  // Get steward statistics
  getStats: () => api.get('/steward-submissions/stats/'),

  // Get list of all stewards
  getStewards: () => api.get('/stewards/'),

  // Assign submission to a steward
  assignSubmission: (id, data) => api.post(`/steward-submissions/${id}/assign/`, data),

  // Toggle the internal "interesting" flag on a submission
  toggleInteresting: (id, isInteresting) =>
    api.post(`/steward-submissions/${id}/toggle-interesting/`, { is_interesting: isInteresting }),

  // Change a pending submission's contribution type without reviewing it
  changeSubmissionType: (id, contributionType) =>
    api.post(`/steward-submissions/${id}/change-type/`, { contribution_type: contributionType }),

  // Bulk reject multiple submissions
  bulkRejectSubmissions: (submissionIds, staffReply) =>
    api.post('/steward-submissions/bulk-reject/', { submission_ids: submissionIds, staff_reply: staffReply }),

  // Steward permissions and templates
  getMyPermissions: () => api.get('/steward-submissions/my-permissions/'),
  getTemplates: () => api.get('/steward-submissions/templates/'),

  // Proposals
  proposeSubmission: (id, data) => api.post(`/steward-submissions/${id}/propose/`, data),
  questionProposal: (id, message) =>
    api.post(`/steward-submissions/${id}/question-proposal/`, { message }),

  // CRM Notes
  getNotes: (id) => api.get(`/steward-submissions/${id}/notes/`),
  addNote: (id, message) => api.post(`/steward-submissions/${id}/notes/`, { message }),
  /**
   * Edit the active generated proposal note on a pending submission.
   * @param {string | number} submissionId
   * @param {string | number} noteId
   * @param {string} message
   */
  updateNote: (submissionId, noteId, message) =>
    api.patch(`/steward-submissions/${submissionId}/notes/${noteId}/`, { message }),

  // Working Groups
  getWorkingGroups: () => api.get('/stewards/working-groups/'),
  getWorkingGroup: (id) => api.get(`/stewards/working-groups/${id}/`),
  createWorkingGroup: (data) => api.post('/stewards/working-groups/', data),
  updateWorkingGroup: (id, data) => api.patch(`/stewards/working-groups/${id}/`, data),
  deleteWorkingGroup: (id) => api.delete(`/stewards/working-groups/${id}/`),
  addParticipant: (groupId, userId) => api.post(`/stewards/working-groups/${groupId}/add_participant/`, { user_id: userId }),
  removeParticipant: (groupId, userId) => api.post(`/stewards/working-groups/${groupId}/remove_participant/`, { user_id: userId }),
  searchUsersForGroup: (query) => api.get('/stewards/working-groups/search_users/', { params: { q: query } }),

  // Feature candidate scoring
  getFeatureReviewAccess: () => api.get('/stewards/feature-reviews/access/'),
  getFeatureReviewCandidates: () => api.get('/stewards/feature-reviews/'),
  scoreFeatureReviewCandidate: (id, score, reason = '') => api.post(`/stewards/feature-reviews/${id}/score/`, { score, reason }),
  getFeatureReviewAdmin: () => api.get('/stewards/feature-reviews/admin/')
};

// Image upload API
export const imageAPI = {
  uploadProfileImage: (formData) => api.post('/users/upload_profile_image/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }),
  uploadBannerImage: (formData) => api.post('/users/upload_banner_image/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }),
  getCloudinaryConfig: (type) => api.get('/users/cloudinary_config/', { params: { type } })
};

// Convenience exports for profile functions
export const getCurrentUser = async () => {
  const response = await usersAPI.getCurrentUser();
  return response.data;
};

export const updateUserProfile = async (data) => {
  const response = await usersAPI.updateUserProfile(data);
  return response.data;
};


// Featured content API
export const featuredAPI = {
  getFeatured: (params) => api.get('/featured/', { params }),
  getHero: (params = {}) => api.get('/featured/', { params: { type: 'hero', ...params } }),
  getCommunity: () => api.get('/featured/', { params: { type: 'community' } }),
  getValidatorsStewards: () => api.get('/featured/', { params: { type: 'validator_steward' } }),
};

// Project profile API
export const projectsAPI = {
  list: (params) => api.get('/projects/', { params }),
  /** @param {string} slug */
  get: (slug) => api.get(`/projects/${slug}/`),
  /** @param {string} slug @param {Record<string, any>} data */
  updateProfile: (slug, data) => api.patch(`/projects/${slug}/profile/`, data),
  /** @param {string} slug @param {FormData} formData */
  uploadImage: (slug, formData) => api.post(`/projects/${slug}/upload-image/`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
};

// Alerts API
export const alertsAPI = {
  getAlerts: () => api.get('/alerts/'),
};

// Ecosystem Partners API
export const partnersAPI = {
  list: (params) => api.get('/partners/', { params }),
  get: (slug) => api.get(`/partners/${slug}/`),
};

// Gen TV API
export const genTvAPI = {
  list: (params) => api.get('/gen-tv/streams/', { params }),
  get: (slug) => api.get(`/gen-tv/streams/${slug}/`),
  categories: (params) => api.get('/gen-tv/categories/', { params }),
};

// POAP API
/** @typedef {Record<string, any>} PoapApiPayload */
export const poapsAPI = {
  /** @param {PoapApiPayload} [params] */
  list: (params) => api.get('/poaps/', { params }),
  /** @param {string} slug */
  get: (slug) => api.get(`/poaps/${slug}/`),
  /** @param {string} slug @param {PoapApiPayload} [params] */
  getClaims: (slug, params) => api.get(`/poaps/${slug}/claims/`, { params }),
  /** @param {string} address @param {PoapApiPayload} [params] */
  getUserPoaps: (address, params) => api.get(`/users/by-address/${address}/poaps/`, { params }),
  /** @param {string} slug @param {string} secret */
  claimSecret: (slug, secret) => api.post(`/poaps/${slug}/claim-secret/`, { secret }),
  /** @param {string} token */
  claimLink: (token) => api.post('/poaps/claim-link/', { token }),
  /** @param {{ address: string, message: string, signature: string }} payload */
  verifyWallet: (payload) => api.post('/poaps/verify-wallet/', payload),
};

export default api;
