import { createPublicClient, http } from 'viem';
import { ethers } from 'ethers';

// Contract configuration - frontend-only
const CONTRACT_INFO = {
  contract_address: import.meta.env.VITE_VALIDATOR_CONTRACT_ADDRESS || '0x10eCB157734c8152f1d84D00040c8AA46052CB27',
  rpc_url: import.meta.env.VITE_VALIDATOR_RPC_URL || 'https://genlayer-testnet.rpc.caldera.xyz/http',
  abi: [
    // Essential functions for validator management
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
    },
    {
      inputs: [],
      name: 'getValidatorsAtCurrentEpoch',
      outputs: [{ type: 'address[]', name: '' }],
      stateMutability: 'view',
      type: 'function'
    }
  ]
};

// Asimov network configuration for unbanning
const ASIMOV_NETWORK = {
  chainId: '0x107D', // 4221 in hex
  chainName: 'GenLayer Asimov Testnet',
  nativeCurrency: {
    name: 'GEN',
    symbol: 'GEN',
    decimals: 18
  },
  rpcUrls: ['https://genlayer-testnet.rpc.caldera.xyz/http'],
  blockExplorerUrls: ['https://genlayer-testnet.explorer.caldera.xyz']
};

/**
 * Ensure the wallet is connected to the Asimov network
 * @returns {Promise<void>}
 */
async function ensureAsimovNetwork() {
  if (!window.ethereum) {
    throw new Error('MetaMask is not installed');
  }

  try {
    // Get current chain ID
    const chainId = await window.ethereum.request({ method: 'eth_chainId' });

    // If already on Asimov, return
    if (chainId === ASIMOV_NETWORK.chainId) {
      return;
    }

    // Try to switch to Asimov network
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: ASIMOV_NETWORK.chainId }],
    });
  } catch (error) {
    // If network doesn't exist (error 4902), add it first
    if (error.code === 4902) {
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [ASIMOV_NETWORK],
      });
    } else {
      throw error;
    }
  }
}

/**
 * Get validator contract information
 * @returns {Promise<{contract_address: string, abi: Array, rpc_url: string}>}
 */
async function getContractInfo() {
  return CONTRACT_INFO;
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

    // Ensure wallet is on Asimov network
    await ensureAsimovNetwork();

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
    // If user rejected, re-throw the original error for UI to handle
    if (error.code === 'ACTION_REJECTED' || error.code === 4001) {
      throw error;
    }

    let errorMessage = 'Failed to unban validator';
    if (error.message?.includes('insufficient funds')) {
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

    // Ensure wallet is on Asimov network
    await ensureAsimovNetwork();

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
    // If user rejected, re-throw the original error for UI to handle
    if (error.code === 'ACTION_REJECTED' || error.code === 4001) {
      throw error;
    }

    let errorMessage = 'Failed to unban all validators';
    if (error.message?.includes('insufficient funds')) {
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