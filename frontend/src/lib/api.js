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
  getUserCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.participant_count }
  })),
  getParticipantCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.participant_count }
  })),
  getCurrentUser: () => api.get('/users/me/'),
  updateUserProfile: (data) => api.patch('/users/me/', data)
};

// API endpoints for contributions
export const contributionsAPI = {
  getContributions: (params) => api.get('/contributions/', { params }),
  getContribution: (id) => api.get(`/contributions/${id}/`),
  getContributionsByUser: (address) => api.get(`/contributions/?user_address=${address}`),
  getContributionTypes: (params) => api.get('/contribution-types/', { params }),
  getContributionType: (id) => api.get(`/contribution-types/${id}/`),
  getContributionTypeStatistics: (params) => api.get('/contribution-types/statistics/', { params }),
  getContributionCount: () => api.get('/leaderboard/stats/').then(res => ({
    data: { count: res.data.contribution_count }
  }))
};

// API endpoints for leaderboard
export const leaderboardAPI = {
  getLeaderboard: (params) => api.get('/leaderboard/', { params }),
  getLeaderboardEntry: (address) => api.get(`/leaderboard/?user_address=${address}`),
  getMultipliers: () => api.get('/multipliers/'),
  getMultiplierPeriods: (multiplier_id) => api.get(`/multiplier-periods/?multiplier=${multiplier_id}`),
  getStats: () => api.get('/leaderboard/stats/')
};

// Stats API
export const statsAPI = {
  getDashboardStats: () => api.get('/leaderboard/stats/'),
  getUserStats: (address) => api.get(`/leaderboard/user_stats/by-address/${address}/`)
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