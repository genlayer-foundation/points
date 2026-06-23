import { createPublicClient, http } from 'viem';

// Contract configuration - frontend-only
const CONTRACT_INFO = {
  rpc_url: import.meta.env.VITE_VALIDATOR_RPC_URL || 'https://rpc.testnet-chain.genlayer.com',
};

/**
 * Get validator contract information
 * @returns {Promise<{rpc_url: string}>}
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
