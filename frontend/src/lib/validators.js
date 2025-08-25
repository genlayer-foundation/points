// Shared utility for fetching and processing validator data
import { validatorsAPI, usersAPI, leaderboardAPI } from './api';
import { getBannedValidators } from './blockchain';

/**
 * Fetches all validator data including active, banned, and user information
 * Shows data immediately from API, then enhances with RPC data
 * @param {string} category - Optional category filter for leaderboard data
 * @param {function} onRpcDataReady - Callback when RPC data is ready
 * @returns {Object} Object containing validators array and stats
 */
export async function fetchValidatorsData(category = 'validator', onRpcDataReady = null) {
  // First, fetch all users without pagination (set high page_size)
  const usersRes = await usersAPI.getUsers({ page_size: 1000 });
  const allUsers = usersRes.data.results || [];
  
  // Get leaderboard data for category
  const leaderboardParams = category !== 'global' ? { category, page_size: 1000 } : { page_size: 1000 };
  const leaderboardRes = await leaderboardAPI.getLeaderboard(leaderboardParams);
  const leaderboardEntries = leaderboardRes.data.results || leaderboardRes.data || [];
  
  // Process initial data with users who have validator profiles
  const validatorsWithStatus = allUsers
    .filter(user => user.validator && user.address) // Only users with validator profiles
    .map(user => {
      const addressLower = user.address.toLowerCase();
      
      // Find leaderboard entry
      const leaderboardEntry = leaderboardEntries.find(entry => {
        const userAddress = entry.user_details?.address || entry.user?.address;
        return userAddress && userAddress.toLowerCase() === addressLower;
      });
      
      return {
        address: user.address,
        isActive: false, // Will be updated when RPC data arrives
        isBanned: false, // Will be updated when RPC data arrives
        isWhitelisted: false, // Will be updated when RPC data arrives
        user: user,
        score: leaderboardEntry?.total_points || null,
        rank: leaderboardEntry?.rank || null,
        nodeVersion: user.validator?.node_version || null,
        matchesTarget: user.validator?.matches_target || false,
        targetVersion: user.validator?.target_version || null,
        pendingRpcData: true // Flag to show data is being loaded
      };
    });
  
  // Sort initial data by rank/score
  const initialValidators = validatorsWithStatus.sort((a, b) => {
    // By rank if available
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
  
  // Calculate initial stats
  const initialStats = {
    totalValidators: 0, // Will be updated when RPC data arrives
    totalBanned: 0, // Will be updated when RPC data arrives
    totalWithProfiles: validatorsWithStatus.length,
    totalWhitelisted: 0, // Will be updated when RPC data arrives
    totalNotWhitelisted: validatorsWithStatus.length // Initially all are not whitelisted
  };
  
  // Fetch RPC data in the background
  if (onRpcDataReady) {
    Promise.all([
      validatorsAPI.getActiveValidators(),
      getBannedValidators()
    ]).then(([activeRes, bannedValidators]) => {
      const activeValidators = activeRes.data || [];
      
      // Filter out invalid addresses from RPC data (banned validators)
      const isValidAddress = (addr) => {
        return addr && 
               addr.toLowerCase() !== '0x0000000000000000000000000000000000000000' &&
               addr.toLowerCase() !== '0x000' &&
               addr.toLowerCase() !== '0x0';
      };
      
      const filteredBannedValidators = bannedValidators.filter(isValidAddress);
      
      // Create sets for quick lookups
      const activeValidatorsSet = new Set(activeValidators.map(addr => addr.toLowerCase()));
      const bannedValidatorsSet = new Set(filteredBannedValidators.map(addr => addr.toLowerCase()));
      
      // Update existing validators with RPC data
      const updatedValidators = initialValidators.map(validator => {
        const addressLower = validator.address.toLowerCase();
        const isActive = activeValidatorsSet.has(addressLower);
        const isBanned = bannedValidatorsSet.has(addressLower);
        const isWhitelisted = isActive || isBanned;
        
        return {
          ...validator,
          isActive,
          isBanned,
          isWhitelisted,
          pendingRpcData: false
        };
      });
      
      // Find validators from blockchain that don't have user profiles yet
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
            isWhitelisted: true,
            user: null,
            score: leaderboardEntry?.total_points || null,
            rank: leaderboardEntry?.rank || null,
            nodeVersion: null,
            matchesTarget: false,
            targetVersion: null,
            pendingRpcData: false
          };
        });
      
      // Combine and sort all validators
      const allValidators = [...updatedValidators, ...validatorsWithoutProfiles].sort((a, b) => {
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
      
      // Calculate updated stats
      const stats = {
        totalValidators: activeValidators.length,
        totalBanned: filteredBannedValidators.length,
        totalWithProfiles: updatedValidators.filter(v => v.user).length,
        totalWhitelisted: allValidators.filter(v => v.isWhitelisted).length,
        totalNotWhitelisted: allValidators.filter(v => !v.isWhitelisted).length
      };
      
      // Call the callback with enhanced data
      onRpcDataReady({
        validators: allValidators,
        stats,
        activeValidators,
        bannedValidators: filteredBannedValidators
      });
    }).catch(error => {
      console.error('Error fetching RPC data:', error);
      // Even on error, remove the pending flag
      const updatedValidators = initialValidators.map(v => ({
        ...v,
        pendingRpcData: false
      }));
      
      if (onRpcDataReady) {
        onRpcDataReady({
          validators: updatedValidators,
          stats: initialStats,
          activeValidators: [],
          bannedValidators: []
        });
      }
    });
  }
  
  return {
    validators: initialValidators,
    stats: initialStats,
    activeValidators: [],
    bannedValidators: []
  };
}

/**
 * Get status display properties for a validator
 */
export function getValidatorStatus(validator) {
  // If RPC data is still pending, show loading state
  if (validator.pendingRpcData) {
    return {
      text: 'Loading...',
      class: 'bg-gray-100 text-gray-500',
      color: 'gray'
    };
  }
  
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
