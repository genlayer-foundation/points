import { createPublicClient, http } from 'viem';
import { ethers } from 'ethers';

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
  },
  // Unban functions
  {
    inputs: [{ type: 'address', name: '_validator' }],
    name: 'removeValidatorBan',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function'
  },
  {
    inputs: [],
    name: 'removeAllValidatorBans',
    outputs: [],
    stateMutability: 'nonpayable',
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

/**
 * Get the balance of a validator address
 * @param {string} address - The validator's wallet address
 * @returns {Promise<{balance: bigint, formatted: string}>} Balance in wei and formatted in GEN
 */
export async function getValidatorBalance(address) {
  try {
    const balance = await publicClient.getBalance({ address });
    
    // Format balance to GEN (divide by 10^18, same decimals as ETH)
    const formatted = (Number(balance) / 1e18).toFixed(4);
    
    return {
      balance, // BigInt value in wei
      formatted // String value in GEN
    };
  } catch (error) {
    console.error('Error fetching validator balance:', error);
    throw error;
  }
}

/**
 * Unban a specific validator using wallet signing
 * @param {string} address - The validator's address to unban
 * @returns {Promise<{success: boolean, transaction_hash?: string, error?: string}>}
 */
export async function unbanValidator(address) {
  try {
    if (!window.ethereum) {
      throw new Error('MetaMask is not installed');
    }

    // Get provider and signer
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();

    // Create contract instance
    const contract = new ethers.Contract(CONTRACT_ADDRESS, VALIDATOR_CONTRACT_ABI, signer);

    // Estimate gas
    const estimatedGas = await contract.removeValidatorBan.estimateGas(address);

    // Send transaction with 10% buffer for gas limit
    const gasLimit = estimatedGas * 110n / 100n;
    const tx = await contract.removeValidatorBan(address, {
      gasLimit: gasLimit
    });

    console.log('Unban transaction sent:', tx.hash);

    // Wait for transaction confirmation
    const receipt = await tx.wait();

    if (receipt.status === 1) {
      return {
        success: true,
        transaction_hash: tx.hash,
        message: 'Validator unbanned successfully',
        gas_used: receipt.gasUsed.toString()
      };
    } else {
      return {
        success: false,
        error: 'Transaction failed'
      };
    }
  } catch (error) {
    console.error('Error unbanning validator:', error);

    let errorMessage = 'Failed to unban validator';

    // Handle specific error types
    if (error.code === 'ACTION_REJECTED' || error.code === 4001) {
      errorMessage = 'Transaction was rejected by user';
    } else if (error.message?.includes('insufficient funds')) {
      errorMessage = 'Insufficient funds to pay for gas';
    } else if (error.message?.includes('execution reverted')) {
      errorMessage = 'Transaction failed: ' + (error.reason || 'Contract execution reverted');
    } else if (error.message) {
      errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage
    };
  }
}

/**
 * Unban all validators using wallet signing
 * @returns {Promise<{success: boolean, transaction_hash?: string, error?: string}>}
 */
export async function unbanAllValidators() {
  try {
    if (!window.ethereum) {
      throw new Error('MetaMask is not installed');
    }

    // Get provider and signer
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();

    // Create contract instance
    const contract = new ethers.Contract(CONTRACT_ADDRESS, VALIDATOR_CONTRACT_ABI, signer);

    // Estimate gas
    const estimatedGas = await contract.removeAllValidatorBans.estimateGas();

    // Send transaction with 10% buffer for gas limit
    const gasLimit = estimatedGas * 110n / 100n;
    const tx = await contract.removeAllValidatorBans({
      gasLimit: gasLimit
    });

    console.log('Unban all transaction sent:', tx.hash);

    // Wait for transaction confirmation
    const receipt = await tx.wait();

    if (receipt.status === 1) {
      return {
        success: true,
        transaction_hash: tx.hash,
        message: 'All validators unbanned successfully',
        gas_used: receipt.gasUsed.toString()
      };
    } else {
      return {
        success: false,
        error: 'Transaction failed'
      };
    }
  } catch (error) {
    console.error('Error unbanning all validators:', error);

    let errorMessage = 'Failed to unban all validators';

    // Handle specific error types
    if (error.code === 'ACTION_REJECTED' || error.code === 4001) {
      errorMessage = 'Transaction was rejected by user';
    } else if (error.message?.includes('insufficient funds')) {
      errorMessage = 'Insufficient funds to pay for gas';
    } else if (error.message?.includes('execution reverted')) {
      errorMessage = 'Transaction failed: ' + (error.reason || 'Contract execution reverted');
    } else if (error.message) {
      errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage
    };
  }
}