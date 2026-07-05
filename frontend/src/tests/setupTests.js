// setupTests.js - Testing environment setup for frontend tests
import { vi } from 'vitest';
import { cleanup } from '@testing-library/svelte/svelte5';
import { flushSync } from 'svelte';

// Export Svelte 5 testing utilities
export const testUtils = {
  // Flush reactive updates synchronously
  flush: () => flushSync(),
  
  // Wait for component to update and flush changes
  waitAndFlush: async (ms = 0) => {
    await new Promise(resolve => setTimeout(resolve, ms));
    flushSync();
  }
};

// Add global utility for creating test subscriptions
global.createTestSubscription = (value) => {
  return {
    subscribe: vi.fn(fn => {
      fn(value);
      return { 
        unsubscribe: vi.fn() 
      };
    })
  };
};

// Cleanup DOM after each test
afterEach(() => {
  cleanup();
});

// Create a mock for fetch/API requests
global.fetch = vi.fn();

// Mock svelte-spa-router with proper subscription pattern
vi.mock('svelte-spa-router', () => {
  return {
    default: vi.fn(),
    push: vi.fn(),
    pop: vi.fn(),
    location: vi.fn(),
    querystring: vi.fn(),
    params: createTestSubscription({ address: '0x123' }) // Always provide an address parameter
  };
});

// Mock API services - in Svelte 5 components with onMount, 
// we need to make these return promises immediately to work with lifecycle
vi.mock('../lib/api', () => {
  // Mock data for immediate responses
  const mockLeaderboardData = {
    data: {
      results: [
        { rank: 1, user: { name: 'Leader 1', email: 'leader1@example.com' }, total_points: 100 },
        { rank: 2, user: { name: 'Leader 2', email: 'leader2@example.com' }, total_points: 90 },
      ]
    }
  };
  
  const mockContributionsData = {
    data: {
      results: [
        { 
          id: 1, 
          user: { name: 'User 1', email: 'user1@example.com' }, 
          contribution_type_name: 'Code', 
          contribution_date: '2023-01-01', 
          points: 10, 
          frozen_global_points: 20,
          multiplier_at_creation: 2,
          evidence_items: [{ description: 'PR Link', url: 'https://github.com/example/repo/pull/1' }]
        }
      ],
      count: 1
    }
  };
  
  const mockStatsData = {
    data: {
      participant_count: 10,
      contribution_count: 50,
      total_points: 1000
    }
  };
  
  const mockUserData = {
    data: {
      name: 'Test User',
      email: 'test@example.com',
      address: '0x123',
      created_at: '2023-01-01',
      leaderboard_entry: {
        rank: 3,
        total_points: 75
      }
    }
  };
  
  const mockContributionTypes = {
    data: {
      results: [
        { id: 1, name: 'Code', description: 'Code contributions' },
        { id: 2, name: 'Documentation', description: 'Documentation contributions' }
      ]
    }
  };
  
  const mockUserStats = {
    data: {
      totalContributions: 25,
      totalPoints: 75,
      contributionTypes: [
        { id: 1, name: 'Code', count: 15, total_points: 50, percentage: 66.7 }
      ]
    }
  };

  const mockProject = {
    id: 1,
    slug: 'cognocracy',
    title: 'Cognocracy',
    description: 'A governance project built on GenLayer.',
    author: 'Cognocracy Team',
    hero_image_url: 'https://example.com/cognocracy.jpg',
    url: 'https://cognocracy.example.com',
    github_url: '',
    x_url: '',
    telegram_url: '',
    discord_url: '',
    demo_url: '',
    details: 'Project details.',
    user_name: 'Builder',
    user_profile_image_url: '',
    related_contributions: []
  };

  return {
    usersAPI: {
      getUsers: vi.fn().mockResolvedValue({ data: { results: [] } }),
      getUser: vi.fn().mockResolvedValue(mockUserData),
      getUserByAddress: vi.fn().mockResolvedValue(mockUserData),
      getUserCount: vi.fn().mockResolvedValue({ data: { count: 10 } }),
      getParticipantCount: vi.fn().mockResolvedValue({ data: { count: 10 } }),
      getCurrentUser: vi.fn().mockResolvedValue(mockUserData.data),
      updateUserProfile: vi.fn().mockResolvedValue(mockUserData.data),
      getReferrals: vi.fn().mockResolvedValue({ data: { total_referrals: 0, builder_points: 0, validator_points: 0, referrals: [] } }),
      getReferralPoints: vi.fn().mockResolvedValue({ data: { builder_points: 0, validator_points: 0 } }),
      searchUsers: vi.fn().mockResolvedValue({ data: { results: [] } })
    },
    contributionsAPI: {
      getContributions: vi.fn().mockResolvedValue(mockContributionsData),
	      getContribution: vi.fn().mockResolvedValue({ data: {} }),
	      getContributionsByUser: vi.fn().mockResolvedValue(mockContributionsData),
	      getContributionTypes: vi.fn().mockResolvedValue(mockContributionTypes),
	      getAllContributionTypes: vi.fn().mockResolvedValue({ data: mockContributionTypes.data.results }),
	      getMissions: vi.fn().mockResolvedValue({ data: { results: [] } }),
	      getAllMissions: vi.fn().mockResolvedValue({ data: [] }),
	      getContributionTypeStatistics: vi.fn().mockResolvedValue({ data: {} }),
	      getContributionCount: vi.fn().mockResolvedValue({ data: { count: 50 } }),
	      getAllHighlights: vi.fn().mockResolvedValue({ data: [] })
    },
    leaderboardAPI: {
      getLeaderboard: vi.fn().mockResolvedValue(mockLeaderboardData),
      getLeaderboardEntry: vi.fn().mockResolvedValue({ data: { results: [{ rank: 3, total_points: 75 }] } }),
      getMultipliers: vi.fn().mockResolvedValue({ data: { results: [] } }),
      getMultiplierPeriods: vi.fn().mockResolvedValue({ data: { results: [] } }),
      getStats: vi.fn().mockResolvedValue(mockStatsData),
      getMonthlyLeaderboardByType: vi.fn().mockResolvedValue(mockLeaderboardData),
      getCommunity: vi.fn().mockResolvedValue({ data: { results: [] } }),
      getReferrals: vi.fn().mockResolvedValue({ data: { results: [] } }),
      getWaitlistTop: vi.fn().mockResolvedValue({ data: [] }),
      getTrending: vi.fn().mockResolvedValue({ data: [] })
    },
    statsAPI: {
      getDashboardStats: vi.fn().mockResolvedValue(mockStatsData),
      getUserStats: vi.fn().mockResolvedValue(mockUserStats)
    },
    buildersAPI: {
      getNewestBuilders: vi.fn().mockResolvedValue({ data: [] })
    },
    validatorsAPI: {
      getNewestValidators: vi.fn().mockResolvedValue({ data: [] }),
      getAllValidators: vi.fn().mockResolvedValue({ data: [] })
    },
    stewardAPI: {
      getFeatureReviewAccess: vi.fn().mockResolvedValue({ data: { can_review: false, can_admin: false } }),
      getFeatureReviewCandidates: vi.fn().mockResolvedValue({ data: { results: [], progress: { scored: 0, total: 0 } } }),
      scoreFeatureReviewCandidate: vi.fn().mockResolvedValue({ data: {} }),
      getFeatureReviewAdmin: vi.fn().mockResolvedValue({ data: { results: [] } }),
      getMyPermissions: vi.fn().mockResolvedValue({ data: {} }),
      getStewards: vi.fn().mockResolvedValue({ data: [] }),
      getStats: vi.fn().mockResolvedValue({ data: {} }),
      getTemplates: vi.fn().mockResolvedValue({ data: [] })
    },
    projectsAPI: {
      list: vi.fn().mockResolvedValue({ data: [mockProject] }),
      get: vi.fn().mockResolvedValue({ data: mockProject }),
      updateProfile: vi.fn().mockResolvedValue({ data: mockProject }),
      uploadImage: vi.fn().mockResolvedValue({ data: { url: 'https://example.com/project-image.png' } }),
    },
	    featuredAPI: {
	      getFeatured: vi.fn().mockResolvedValue({ data: [] }),
	      getHero: vi.fn().mockResolvedValue({ data: [] }),
	      getCommunity: vi.fn().mockResolvedValue({ data: [] }),
	      getValidatorsStewards: vi.fn().mockResolvedValue({ data: [] })
	    },
	    partnersAPI: {
	      list: vi.fn().mockResolvedValue({ data: [] }),
	      listAll: vi.fn().mockResolvedValue({ data: [] }),
	      get: vi.fn().mockResolvedValue({ data: {} })
	    },
    // Add convenience exports for the new functions
    getCurrentUser: vi.fn().mockResolvedValue(mockUserData.data),
    updateUserProfile: vi.fn().mockResolvedValue(mockUserData.data)
  };
});
