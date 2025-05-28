import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // Enable cookies for session-based auth
});

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
  }))
};

// API endpoints for contributions
export const contributionsAPI = {
  getContributions: (params) => api.get('/contributions/', { params }),
  getContribution: (id) => api.get(`/contributions/${id}/`),
  getContributionsByUser: (address) => api.get(`/contributions/?user_address=${address}`),
  getContributionTypes: () => api.get('/contribution-types/'),
  getContributionTypeStatistics: () => api.get('/contribution-types/statistics/'),
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

export default api;