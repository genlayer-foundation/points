import { createPublicClient, http } from 'viem';
import { ethers } from 'ethers';

// Contract info cache - fetched from backend on first use
let contractInfoCache = null;
let contractInfoPromise = null;

/**
 * Fetch validator contract information from the backend
 * @returns {Promise<{contract_address: string, abi: Array, rpc_url: string}>}
 */
async function getContractInfo() {
  // Return cached info if available
  if (contractInfoCache) {
    return contractInfoCache;
  }

  // If a request is already in progress, wait for it
  if (contractInfoPromise) {
    return contractInfoPromise;
  }

  // Start new request
  contractInfoPromise = (async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/validators/contract-info/`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contractInfo = await response.json();

      // Validate response structure
      if (!contractInfo.contract_address || !contractInfo.abi || !contractInfo.rpc_url) {
        throw new Error('Invalid contract info response structure');
      }

      // Cache the result
      contractInfoCache = contractInfo;
      return contractInfo;

    } catch (error) {
      console.error('Failed to fetch contract info from backend:', error);

      // Fallback to environment variables with hardcoded minimal ABI
      const fallbackInfo = {
        contract_address: import.meta.env.VITE_VALIDATOR_CONTRACT_ADDRESS || '0x0000000000000000000000000000000000000000',
        rpc_url: import.meta.env.VITE_VALIDATOR_RPC_URL || 'http://localhost:8545',
        abi: [
          // Minimal fallback ABI with essential functions
          {
            inputs: [],
            name: 'getAllBannedValidators',
            outputs: [{ type: 'address[]', name: '' }],
            stateMutability: 'view',
            type: 'function'
          },
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
        ]
      };

      console.warn('Using fallback contract configuration due to backend error');
      contractInfoCache = fallbackInfo;
      return fallbackInfo;
    } finally {
      // Clear the promise so future calls can retry
      contractInfoPromise = null;
    }
  })();

  return contractInfoPromise;
}

/**
 * Create a public client for reading from the blockchain
 * @returns {Promise<Object>} Viem public client
 */
async function getPublicClient() {
  const contractInfo = await getContractInfo();
  return createPublicClient({
    transport: http(contractInfo.rpc_url),
  });
}

/**
 * Get the list of banned validators from the blockchain
 * @returns {Promise<string[]>} Array of banned validator addresses
 */
export async function getBannedValidators() {
  try {
    const contractInfo = await getContractInfo();
    const publicClient = await getPublicClient();

    // Get all banned validators in a single call
    const bannedAddresses = await publicClient.readContract({
      address: contractInfo.contract_address,
      abi: contractInfo.abi,
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
    const contractInfo = await getContractInfo();
    const publicClient = await getPublicClient();

    const validators = await publicClient.readContract({
      address: contractInfo.contract_address,
      abi: contractInfo.abi,
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
    const publicClient = await getPublicClient();
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

    // Get contract info from backend
    const contractInfo = await getContractInfo();

    // Get provider and signer
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();

    // Create contract instance using fetched ABI
    const contract = new ethers.Contract(contractInfo.contract_address, contractInfo.abi, signer);

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

    // Get contract info from backend
    const contractInfo = await getContractInfo();

    // Get provider and signer
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();

    // Create contract instance using fetched ABI
    const contract = new ethers.Contract(contractInfo.contract_address, contractInfo.abi, signer);

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