import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`,
  timeout: 30000, // Increased timeout to 30 seconds for slow endpoints
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // Enable cookies for session-based auth
});

// Add request interceptor to ensure credentials are always sent
api.interceptors.request.use(
  (config) => {
    // Ensure withCredentials is always true
    config.withCredentials = true;
    
    // Don't override Content-Type for FormData
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    
    return config;
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
  getUserCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.participant_count }
  })),
  getParticipantCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.participant_count }
  })),
  getCurrentUser: () => api.get('/users/me/'),
  updateUserProfile: (data) => api.patch('/users/me/', data),
  getAccountBalance: () => api.get('/users/balance/'),
  checkDeployments: () => api.get('/users/check_deployments/'),
  getDeploymentStatus: () => api.get('/users/deployment_status/')
};

// API endpoints for contributions
export const contributionsAPI = {
  getContributions: (params) => {
    // Add group_consecutive parameter by default for better UX
    const enhancedParams = {
      group_consecutive: true,
      ...params
    };
    return api.get('/contributions/', { params: enhancedParams });
  },
  getContribution: (id) => api.get(`/contributions/${id}/`),
  getContributionsByUser: (address) => api.get(`/contributions/?user_address=${address}&group_consecutive=true`),
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
  getHighlights: (params) => api.get('/contributions/highlights/', { params }),
  getContributionTypeRecentContributions: (id) => api.get(`/contribution-types/${id}/recent_contributions/`),
  getContributionTypeHighlights: (id) => api.get(`/contribution-types/${id}/highlights/`),
  getAllHighlights: (params) => api.get('/contributions/highlights/', { params }),
  getContributionCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.contribution_count }
  }))
};

// API endpoints for leaderboard
export const leaderboardAPI = {
  getLeaderboard: (params) => api.get('/leaderboard/', { params }),
  getLeaderboardByType: (type, order = 'asc') => 
    api.get('/leaderboard/', { params: { type, order } }),
  getLeaderboardEntry: (address) => api.get(`/leaderboard/?user_address=${address}`),
  getMultipliers: () => api.get('/multipliers/'),
  getActiveMultipliers: () => api.get('/multipliers/active/'),
  getMultiplierPeriods: (multiplier_id) => api.get(`/multiplier-periods/?multiplier=${multiplier_id}`),
  getStats: () => api.get('/leaderboard/stats/'),
  getWaitlistStats: () => api.get('/leaderboard/validator-waitlist-stats/'),
  getTypes: () => api.get('/leaderboard/types/'),
  recalculateAll: () => api.post('/leaderboard/recalculate/')
};

// Stats API
export const statsAPI = {
  getDashboardStats: () => api.get('/leaderboard/stats/'),
  getUserStats: (address, category = null) => {
    const params = category ? { category } : {};
    return api.get(`/leaderboard/user_stats/by-address/${address}/`, { params });
  }
};

// Validators API
export const validatorsAPI = {
  getNewestValidators: (limit = 5) => api.get('/validators/newest/', { params: { limit } }),
  getActiveValidators: () => api.get('/users/validators/')
};

// Journey API
export const journeyAPI = {
  startValidatorJourney: () => api.post('/users/start_validator_journey/'),
  startBuilderJourney: () => api.post('/users/start_builder_journey/'),
  completeBuilderJourney: () => api.post('/users/complete_builder_journey/')
};

// Steward API
export const stewardAPI = {
  // Get all submissions for review
  getSubmissions: (params = {}) => api.get('/steward-submissions/', { params }),
  
  // Get a single submission
  getSubmission: (id) => api.get(`/steward-submissions/${id}/`),
  
  // Review a submission (accept, reject, or request more info)
  reviewSubmission: (id, data) => api.post(`/steward-submissions/${id}/review/`, data),
  
  // Get all users for reassignment dropdown
  getUsers: () => api.get('/steward-submissions/users/'),
  
  // Get steward statistics
  getStats: () => api.get('/steward-submissions/stats/'),

  // Get list of all stewards
  getStewards: () => api.get('/stewards/'),

  // Get banned validators for management
  getBannedValidators: () => api.get('/stewards/banned-validators/'),

  // Get specific banned validator details
  getBannedValidatorDetails: (address) => api.get(`/stewards/banned-validators/${address}/`),

  // Future: Unban a single validator
  unbanValidator: (address) => api.post(`/stewards/banned-validators/${address}/unban/`),

  // Future: Unban all validators
  unbanAllValidators: () => api.post('/stewards/banned-validators/unban-all/')
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

export default api;