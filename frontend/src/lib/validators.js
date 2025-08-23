// Shared utility for fetching and processing validator data
import { validatorsAPI, usersAPI, leaderboardAPI } from './api';
import { getBannedValidators } from './blockchain';

/**
 * Fetches all validator data including active, banned, and user information
 * @param {string} category - Optional category filter for leaderboard data
 * @returns {Object} Object containing validators array and stats
 */
export async function fetchValidatorsData(category = 'validator') {
  // Fetch active validators from backend and banned validators from blockchain in parallel
  const [activeRes, bannedValidators, usersRes] = await Promise.all([
    validatorsAPI.getActiveValidators(),
    getBannedValidators(),
    usersAPI.getUsers()
  ]);
  
  const activeValidators = activeRes.data || [];
  const allUsers = usersRes.data.results || [];
  
  // Filter out invalid addresses from RPC data (banned validators)
  const isValidAddress = (addr) => {
    return addr && 
           addr.toLowerCase() !== '0x0000000000000000000000000000000000000000' &&
           addr.toLowerCase() !== '0x000' &&
           addr !== '0x0';
  };
  
  // Backend API already filters active validators, only filter RPC banned validators
  const filteredBannedValidators = bannedValidators.filter(isValidAddress);
  
  // Get leaderboard data for category
  const leaderboardParams = category !== 'global' ? { category } : {};
  const leaderboardRes = await leaderboardAPI.getLeaderboard(leaderboardParams);
  const leaderboardEntries = leaderboardRes.data || [];
  
  // Create a map for quick lookups (ensure all addresses are lowercase for comparison)
  const activeValidatorsSet = new Set(activeValidators.map(addr => addr.toLowerCase()));
  const bannedValidatorsSet = new Set(filteredBannedValidators.map(addr => addr.toLowerCase()));
  
  // Process all users who have validator profiles
  const validatorsWithStatus = allUsers
    .filter(user => user.validator && user.address) // Only users with validator profiles
    .map(user => {
      const addressLower = user.address.toLowerCase();
      const isActive = activeValidatorsSet.has(addressLower);
      const isBanned = bannedValidatorsSet.has(addressLower);
      const isWhitelisted = isActive || isBanned; // Either active or banned means they're on the whitelist
      
      // Find leaderboard entry
      const leaderboardEntry = leaderboardEntries.find(entry => {
        const userAddress = entry.user_details?.address || entry.user?.address;
        return userAddress && userAddress.toLowerCase() === addressLower;
      });
      
      return {
        address: user.address,
        isActive,
        isBanned,
        isWhitelisted,
        user: user,
        score: leaderboardEntry?.total_points || null,
        rank: leaderboardEntry?.rank || null,
        nodeVersion: user.validator?.node_version || null,
        matchesTarget: user.validator?.matches_target || false,
        targetVersion: user.validator?.target_version || null
      };
    });
  
  // Also include validators from blockchain that don't have user profiles yet
  const allValidatorAddresses = [...new Set([...activeValidators, ...filteredBannedValidators])];
  const usersWithProfiles = new Set(allUsers.map(u => u.address?.toLowerCase()).filter(Boolean));
  
  const validatorsWithoutProfiles = allValidatorAddresses
    .filter(address => !usersWithProfiles.has(address.toLowerCase()))
    .map(address => {
      const addressLower = address.toLowerCase();
      const isActive = activeValidatorsSet.has(addressLower);
      const isBanned = bannedValidatorsSet.has(addressLower);
      
      // Find leaderboard entry
      const leaderboardEntry = leaderboardEntries.find(entry => {
        const userAddress = entry.user_details?.address || entry.user?.address;
        return userAddress && userAddress.toLowerCase() === addressLower;
      });
      
      return {
        address,
        isActive,
        isBanned,
        isWhitelisted: true, // They're on blockchain so they're whitelisted
        user: null,
        score: leaderboardEntry?.total_points || null,
        rank: leaderboardEntry?.rank || null,
        nodeVersion: null,
        matchesTarget: false,
        targetVersion: null
      };
    });
  
  // Combine and sort
  const allValidators = [...validatorsWithStatus, ...validatorsWithoutProfiles].sort((a, b) => {
    // Whitelisted validators first
    if (a.isWhitelisted !== b.isWhitelisted) {
      return a.isWhitelisted ? -1 : 1;
    }
    
    // Active validators first
    if (a.isActive !== b.isActive) {
      return a.isActive ? -1 : 1;
    }
    
    // Then banned
    if (a.isBanned !== b.isBanned) {
      return a.isBanned ? -1 : 1;
    }
    
    // Then by rank if available
    if (a.rank && b.rank) {
      return a.rank - b.rank;
    }
    if (a.rank) return -1;
    if (b.rank) return 1;
    
    // Then by score
    if (a.score !== b.score) {
      return (b.score || 0) - (a.score || 0);
    }
    
    // Finally by address
    return (a.address || '').localeCompare(b.address || '');
  });
  
  // Calculate stats
  const stats = {
    totalValidators: activeValidators.length,
    totalBanned: filteredBannedValidators.length,
    totalWithProfiles: validatorsWithStatus.length,
    totalWhitelisted: allValidators.filter(v => v.isWhitelisted).length,
    totalNotWhitelisted: allValidators.filter(v => !v.isWhitelisted).length
  };
  
  return {
    validators: allValidators,
    stats,
    activeValidators,
    bannedValidators: filteredBannedValidators
  };
}

/**
 * Get status display properties for a validator
 */
export function getValidatorStatus(validator) {
  if (!validator.isWhitelisted) {
    return {
      text: 'Not in Whitelist',
      class: 'bg-gray-100 text-gray-600',
      color: 'gray'
    };
  }
  if (validator.isBanned) {
    return {
      text: 'Banned',
      class: 'bg-red-100 text-red-800',
      color: 'red'
    };
  }
  if (validator.isActive) {
    return {
      text: 'Active',
      class: 'bg-green-100 text-green-800',
      color: 'green'
    };
  }
  return {
    text: 'Inactive',
    class: 'bg-yellow-100 text-yellow-800',
    color: 'yellow'
  };
}
