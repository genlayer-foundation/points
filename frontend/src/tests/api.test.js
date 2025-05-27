import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte/svelte5';
import { leaderboardAPI, contributionsAPI, usersAPI, statsAPI } from '../lib/api';
import Dashboard from '../routes/Dashboard.svelte';
import Contributions from '../routes/Contributions.svelte';
import ContributionsList from '../components/ContributionsList.svelte';
import LeaderboardTable from '../components/LeaderboardTable.svelte';
import ParticipantProfile from '../routes/ParticipantProfile.svelte';

// Mock data for tests
const mockLeaderboardData = {
  data: {
    results: [
      { rank: 1, user: { name: 'Leader 1', email: 'leader1@example.com' }, total_points: 100 },
      { rank: 2, user: { name: 'Leader 2', email: 'leader2@example.com' }, total_points: 90 },
      { rank: 3, user: { name: 'Leader 3', email: 'leader3@example.com' }, total_points: 80 }
    ],
    count: 3
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
      },
      { 
        id: 2,
        user: { name: 'User 2', email: 'user2@example.com' }, 
        contribution_type_name: 'Documentation', 
        contribution_date: '2023-01-02', 
        points: 5, 
        frozen_global_points: 10,
        multiplier_at_creation: 2,
        evidence_items: []
      }
    ],
    count: 2
  }
};

// Set up mocks before each test
beforeEach(() => {
  vi.resetAllMocks();
  
  // For Svelte 5 testing, we need to use mockImplementation instead of mockResolvedValue
  leaderboardAPI.getLeaderboard.mockImplementation(() => Promise.resolve(mockLeaderboardData));
  contributionsAPI.getContributions.mockImplementation(() => Promise.resolve(mockContributionsData));
});

describe('Component Rendering Tests', () => {
  describe('Dashboard Page', () => {
    it('renders the Dashboard header', () => {
      render(Dashboard);
      expect(screen.getByText('Dashboard')).toBeDefined();
    });
    
    it('shows Total Participants section', () => {
      render(Dashboard);
      expect(screen.getByText('Total Participants')).toBeDefined();
    });
  });
  
  describe('Contributions Page', () => {
    it('renders the contributions page title', () => {
      render(Contributions);
      expect(screen.getByText('Contributions')).toBeDefined();
    });
  });
  
  describe('Component-level Integration', () => {
    it('LeaderboardTable component displays leaderboard entries correctly', async () => {
      render(LeaderboardTable, { 
        props: { 
          entries: mockLeaderboardData.data.results,
          loading: false,
          error: null
        } 
      });
      
      // Check leaderboard entries are displayed
      expect(screen.getByText('Leader 1')).toBeDefined();
      expect(screen.getByText('Leader 2')).toBeDefined();
      expect(screen.getByText('Leader 3')).toBeDefined();
      
      // Check ranks are displayed
      expect(screen.getByText('1')).toBeDefined();
      expect(screen.getByText('2')).toBeDefined();
      expect(screen.getByText('3')).toBeDefined();
      
      // Check points are displayed
      expect(screen.getByText('100')).toBeDefined();
      expect(screen.getByText('90')).toBeDefined();
      expect(screen.getByText('80')).toBeDefined();
    });
    
    it('ContributionsList component displays contributions correctly', async () => {
      render(ContributionsList, { 
        props: { 
          contributions: mockContributionsData.data.results,
          loading: false,
          error: null,
          showUser: true
        } 
      });
      
      // Check contribution details are displayed
      expect(screen.getByText('User 1')).toBeDefined();
      expect(screen.getByText('User 2')).toBeDefined();
      expect(screen.getByText('Code')).toBeDefined();
      expect(screen.getByText('Documentation')).toBeDefined();
      
      // Check evidence is displayed
      expect(screen.getByText('PR Link')).toBeDefined();
      
      // Check "None" is displayed when no evidence
      expect(screen.getByText('None')).toBeDefined();
    });
  });
});