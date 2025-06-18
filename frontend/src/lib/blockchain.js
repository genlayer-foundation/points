import { createPublicClient, http } from 'viem';

// Get configuration from environment variables or use defaults
const RPC_URL = import.meta.env.VITE_VALIDATOR_RPC_URL || 'http://localhost:8545';
const CONTRACT_ADDRESS = import.meta.env.VITE_VALIDATOR_CONTRACT_ADDRESS || '0x0000000000000000000000000000000000000000';

// Create a public client for reading from the blockchain
const publicClient = createPublicClient({
  transport: http(RPC_URL),
});

// ABI for the validator contract
const VALIDATOR_CONTRACT_ABI = [
  {
    inputs: [],
    name: 'getValidatorsAtCurrentEpoch',
    outputs: [{ type: 'address[]', name: '' }],
    stateMutability: 'view',
    type: 'function'
  },
  {
    inputs: [],
    name: 'getValidatorBansCount',
    outputs: [{ type: 'uint256', name: '' }],
    stateMutability: 'view',
    type: 'function'
  },
  {
    inputs: [{ type: 'uint256', name: 'index' }],
    name: 'validatorsBanned',
    outputs: [{ type: 'address', name: '' }],
    stateMutability: 'view',
    type: 'function'
  }
];

/**
 * Get the list of banned validators from the blockchain
 * @returns {Promise<string[]>} Array of banned validator addresses
 */
export async function getBannedValidators() {
  try {
    // Get the count of banned validators
    const banCount = await publicClient.readContract({
      address: CONTRACT_ADDRESS,
      abi: VALIDATOR_CONTRACT_ABI,
      functionName: 'getValidatorBansCount',
    });

    if (banCount === 0n) {
      return [];
    }

    // Fetch all banned validators in parallel
    const bannedPromises = [];
    for (let i = 0n; i < banCount; i++) {
      bannedPromises.push(
        publicClient.readContract({
          address: CONTRACT_ADDRESS,
          abi: VALIDATOR_CONTRACT_ABI,
          functionName: 'validatorsBanned',
          args: [i],
        })
      );
    }

    const bannedAddresses = await Promise.all(bannedPromises);
    
    // Filter out zero addresses and convert to lowercase
    return bannedAddresses
      .filter(addr => addr !== '0x0000000000000000000000000000000000000000')
      .map(addr => addr.toLowerCase());
  } catch (error) {
    console.error('Error fetching banned validators:', error);
    throw error;
  }
}

/**
 * Get the list of active validators from the blockchain
 * @returns {Promise<string[]>} Array of active validator addresses
 */
export async function getActiveValidators() {
  try {
    const validators = await publicClient.readContract({
      address: CONTRACT_ADDRESS,
      abi: VALIDATOR_CONTRACT_ABI,
      functionName: 'getValidatorsAtCurrentEpoch',
    });

    return validators.map(addr => addr.toLowerCase());
  } catch (error) {
    console.error('Error fetching active validators:', error);
    throw error;
  }
}