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
    name: 'getAllBannedValidators',
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
    // Get all banned validators in a single call
    const bannedAddresses = await publicClient.readContract({
      address: CONTRACT_ADDRESS,
      abi: VALIDATOR_CONTRACT_ABI,
      functionName: 'getAllBannedValidators',
    });
    
    // Filter out any zero addresses (keep original case)
    return bannedAddresses
      .filter(addr => addr.toLowerCase() !== '0x0000000000000000000000000000000000000000');
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

    // Filter out any zero addresses (keep original case)
    return validators
      .filter(addr => addr.toLowerCase() !== '0x0000000000000000000000000000000000000000');
  } catch (error) {
    console.error('Error fetching active validators:', error);
    throw error;
  }
}