import { ethers } from 'ethers';
import axios from 'axios';
import { writable } from 'svelte/store';
import { userStore } from './userStore';

// Create a Svelte store for authentication state
const createAuthStore = () => {
  // Default state
  const initialState = {
    isAuthenticated: false,
    address: null,
    provider: null,
    loading: false,
    error: null,
    hasVerified: false  // Track if we've verified in this session
  };

  // Try to load from localStorage
  try {
    const savedAuth = localStorage.getItem('tally-auth');
    if (savedAuth) {
      const { isAuthenticated, address } = JSON.parse(savedAuth);
      initialState.isAuthenticated = isAuthenticated;
      initialState.address = address;
      // If we have saved auth, restore the provider if available
      if (isAuthenticated && typeof window !== 'undefined' && window.ethereum) {
        initialState.provider = window.ethereum;
      }
    }
  } catch (e) {
    console.error('Error loading auth state from localStorage:', e);
  }
  
  // Create the store
  const { subscribe, set, update } = writable(initialState);
  
  return {
    subscribe,
    set,
    update,
    // Convenience getters/setters to use outside of Svelte components
    get: () => {
      let currentState;
      subscribe(state => { currentState = state })();
      return currentState;
    },
    setAuthenticated: (isAuthenticated, address = null) => {
      update(state => ({ ...state, isAuthenticated, address, hasVerified: true }));
      if (isAuthenticated && address) {
        localStorage.setItem('tally-auth', JSON.stringify({ isAuthenticated, address }));
      } else {
        localStorage.removeItem('tally-auth');
      }
    },
    resetVerification: () => {
      update(state => ({ ...state, hasVerified: false }));
    },
    setLoading: (loading) => update(state => ({ ...state, loading })),
    setError: (error) => {
      // Format error message if it's an object
      let errorMessage = error;
      
      if (error && typeof error === 'object') {
        if (error.message) {
          errorMessage = error.message;
        } else if (error.toString) {
          errorMessage = error.toString();
        }
      }
      
      // Create curated error message
      if (typeof errorMessage === 'string') {
        if (errorMessage.includes('MetaMask is not installed')) {
          errorMessage = 'Please install MetaMask to connect';
        } else if (errorMessage.includes('User rejected') || errorMessage.includes('User denied')) {
          errorMessage = 'Connection rejected';
        } else if (errorMessage.includes('signature')) {
          errorMessage = 'Signature verification failed';
        } else if (errorMessage.includes('nonce')) {
          errorMessage = 'Authentication expired, please try again';
        } else if (errorMessage.includes('network') || errorMessage.includes('Network Error')) {
          errorMessage = 'Network error, please try again';
        }
      }
      
      update(state => ({ ...state, error: errorMessage }));
    }
  };
};

const authState = createAuthStore();

// Create axios instance for auth endpoints with credentials
const authAxios = axios.create({
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Authentication API endpoints (relative to base URL, not api/v1)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_ENDPOINTS = {
  NONCE: `${API_BASE_URL}/api/auth/nonce/`,
  LOGIN: `${API_BASE_URL}/api/auth/login/`,
  VERIFY: `${API_BASE_URL}/api/auth/verify/`,
  LOGOUT: `${API_BASE_URL}/api/auth/logout/`,
  REFRESH: `${API_BASE_URL}/api/auth/refresh/`
};

/**
 * Restore provider reference if missing but user is authenticated
 * @returns {Object|null} Ethereum provider or null
 */
function restoreProvider() {
  const state = authState.get();
  if (state.isAuthenticated && !state.provider && typeof window !== 'undefined' && window.ethereum) {
    authState.update(currentState => ({ ...currentState, provider: window.ethereum }));
    return window.ethereum;
  }
  return state.provider;
}

/**
 * Connect to wallet with specific provider
 * @param {Object} provider - Ethereum provider (window.ethereum or specific wallet provider)
 * @param {string} walletName - Name of the wallet for error messages
 * @returns {Promise<string>} Ethereum address
 */
export async function connectWallet(provider = null, walletName = 'wallet') {
  authState.setLoading(true);
  authState.setError(null);
  
  try {
    // Use provided provider or default to window.ethereum
    const ethereumProvider = provider || window.ethereum;
    
    if (!ethereumProvider) {
      throw new Error(`No wallet detected. Please install ${walletName} to continue.`);
    }

    // First, try to request permissions to trigger account selection dialog
    // This works with MetaMask and wallets that support wallet_requestPermissions
    try {
      await ethereumProvider.request({
        method: 'wallet_requestPermissions',
        params: [{ eth_accounts: {} }]
      });
    } catch (permissionError) {
      // If the wallet doesn't support wallet_requestPermissions or user rejected,
      // we'll continue with the normal flow
      console.log('wallet_requestPermissions not supported or rejected:', permissionError);
    }

    // Now get the accounts (either newly selected or existing)
    let accounts = await ethereumProvider.request({ method: 'eth_accounts' });
    
    // If no accounts are connected, request access
    if (!accounts || accounts.length === 0) {
      accounts = await ethereumProvider.request({ method: 'eth_requestAccounts' });
    }
    
    // Always use the first account (currently selected)
    const address = accounts[0];
    
    if (!address) {
      throw new Error(`No Ethereum accounts found. Please unlock your ${walletName}.`);
    }
    
    // Store the provider for later use in signing
    authState.update(state => ({ ...state, address, provider: ethereumProvider }));
    return address;
  } catch (error) {
    // Pass the error object to let setError handle it
    authState.setError(error);
    throw error;
  } finally {
    authState.setLoading(false);
  }
}

/**
 * Fetch a nonce from the backend
 * @returns {Promise<string>} Nonce for SIWE message
 */
export async function getNonce() {
  try {
    const response = await authAxios.get(API_ENDPOINTS.NONCE);
    return response.data.nonce;
  } catch (error) {
    // Use a specific error message for this case
    authState.setError('Failed to connect to server');
    throw error;
  }
}

/**
 * Create and sign a SIWE message
 * @param {string} address - Ethereum address
 * @param {string} nonce - Server-provided nonce
 * @param {Object} provider - Ethereum provider to use for signing
 * @returns {Promise<Object>} Signed message and signature
 */
export async function createAndSignMessage(address, nonce, provider = null) {
  const domain = window.location.host;
  const origin = window.location.origin;
  
  // Create a message string directly instead of using SiweMessage
  const messageToSign = `${domain} wants you to sign in with your Ethereum account:
${address}

Sign in with Ethereum to GenLayer Testnet Contributions

URI: ${origin}
Version: 1
Chain ID: 1
Nonce: ${nonce}
Issued At: ${new Date().toISOString()}`;
  
  // Use provided provider or default to window.ethereum
  const ethereumProvider = provider || window.ethereum;
  
  // Request signature from wallet
  const ethersProvider = new ethers.BrowserProvider(ethereumProvider);
  const signer = await ethersProvider.getSigner();
  const signature = await signer.signMessage(messageToSign);
  
  return {
    message: messageToSign,
    signature
  };
}

/**
 * Sign in with Ethereum
 * @param {Object} provider - Ethereum provider to use
 * @param {string} walletName - Name of the wallet being used
 * @returns {Promise<Object>} Authentication result
 */
export async function signInWithEthereum(provider = null, walletName = 'wallet') {
  authState.setLoading(true);
  authState.setError(null);
  
  try {
    // Connect to wallet and get address
    const address = await connectWallet(provider, walletName);
    
    // Get the provider from state (was stored in connectWallet)
    const state = authState.get();
    const ethereumProvider = state.provider || provider || window.ethereum;
    
    // Get nonce from server
    const nonce = await getNonce();
    
    // Create and sign the message with the specific provider
    const { message, signature } = await createAndSignMessage(address, nonce, ethereumProvider);
    
    // Check for referral code in localStorage
    const referralCode = localStorage.getItem('referral_code');
    
    // Send to backend for verification
    console.log('Sending login request to:', API_ENDPOINTS.LOGIN);
    const loginData = {
      message,
      signature
    };
    
    // Add referral code if available
    if (referralCode) {
      loginData.referral_code = referralCode;
      console.log('Including referral code in login:', referralCode);
    }
    
    const response = await authAxios.post(API_ENDPOINTS.LOGIN, loginData);
    console.log('Login response:', response.data);
    
    // Clear referral code from localStorage after successful login
    if (referralCode) {
      localStorage.removeItem('referral_code');
      console.log('Referral code cleared from localStorage');
    }
    
    // Update auth state
    authState.setAuthenticated(true, address);
    
    // Store referral data from login response immediately
    if (response.data.referral_code || response.data.referred_by) {
      userStore.updateUser({
        referral_code: response.data.referral_code,
        referred_by_info: response.data.referred_by
      });
      console.log('Referral data stored from login:', {
        referral_code: response.data.referral_code,
        referred_by: response.data.referred_by
      });
    }
    
    // Set up wallet listeners after successful connection
    setupWalletListeners();
    
    // Load user data into the store
    try {
      await userStore.loadUser();
    } catch (err) {
      console.error('Failed to load user data after login:', err);
    }
    
    // Immediately verify the auth worked
    setTimeout(() => {
      verifyAuth();
    }, 100);
    
    // Check for redirect after login, default to user's public profile
    const redirectPath = sessionStorage.getItem('redirectAfterLogin');
    if (redirectPath) {
      sessionStorage.removeItem('redirectAfterLogin');
      // Import push dynamically to avoid circular dependencies
      import('svelte-spa-router').then(({ push }) => {
        push(redirectPath);
      });
    } else {
      // Default to user's public profile
      import('svelte-spa-router').then(({ push }) => {
        push(`/participant/${address}`);
      });
    }
    
    return response.data;
  } catch (error) {
    // Pass the error object to let setError handle it
    authState.setError(error);
    throw error;
  } finally {
    authState.setLoading(false);
  }
}

// Track verification promise to prevent duplicate calls
let verificationInProgress = null;

/**
 * Verify authentication status - only once per session
 * @returns {Promise<boolean>} Authentication status
 */
export async function verifyAuth() {
  const state = authState.get();
  
  // If we've already verified in this session, return the current state
  if (state.hasVerified) {
    return Promise.resolve(state.isAuthenticated);
  }
  
  // If verification is already in progress, return the existing promise
  if (verificationInProgress) {
    return verificationInProgress;
  }
  
  // Start new verification
  verificationInProgress = performVerification();
  
  try {
    const result = await verificationInProgress;
    return result;
  } finally {
    verificationInProgress = null;
  }
}

async function performVerification() {
  try {
    const response = await authAxios.get(API_ENDPOINTS.VERIFY);
    const isAuthenticated = response.data.authenticated;
    const address = response.data.address || null;

    // Update auth state with verification result
    authState.setAuthenticated(isAuthenticated, address);

    // If authenticated, restore provider if missing
    if (isAuthenticated) {
      restoreProvider();

      try {
        await userStore.loadUser();
      } catch (err) {
        console.error('Failed to load user data during auth verification:', err);
      }
    }

    return isAuthenticated;
  } catch (error) {
    console.error('Auth verification failed:', error);
    authState.setAuthenticated(false, null);
    return false;
  }
}

/**
 * Logout user
 * @returns {Promise<void>}
 */
export async function logout() {
  try {
    await authAxios.post(API_ENDPOINTS.LOGOUT);
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Clear auth state using our store method
    authState.setAuthenticated(false, null);
    // Reset verification flag so next session will verify
    authState.resetVerification();
    // Clear any cached provider
    authState.update(state => ({ ...state, provider: null }));
    // Clear user data from store
    userStore.clearUser();
  }
}

/**
 * Refresh authentication session
 * @returns {Promise<boolean>} Success status
 */
export async function refreshSession() {
  try {
    await authAxios.post(API_ENDPOINTS.REFRESH);
    return true;
  } catch (error) {
    // If refresh fails, verify auth state again
    await verifyAuth();
    return false;
  }
}

// Store listener functions for cleanup
let accountsChangedHandler = null;
let chainChangedHandler = null;

/**
 * Handle account changes from wallet
 */
async function handleAccountsChanged(accounts) {
  const state = authState.get();
  
  if (accounts.length === 0) {
    // User disconnected their wallet or revoked permissions
    await logout();
    authState.setError('Wallet disconnected. Please reconnect to continue.');
  } else if (state.isAuthenticated && accounts[0].toLowerCase() !== state.address?.toLowerCase()) {
    // User switched to a different account while authenticated
    const newAccount = accounts[0];
    
    // Since our backend session is tied to the signed message from the original account,
    // we need to re-authenticate with the new account
    try {
      // First logout the old session
      await logout();
      
      // Clear any cached provider state
      authState.update(state => ({ ...state, provider: null }));
      
      // Automatically start re-authentication with the new account
      // Get the current provider (should still be available)
      const provider = window.ethereum;
      
      if (provider) {
        // Show user-friendly message
        authState.setError(
          `Switched to ${newAccount.substring(0, 6)}...${newAccount.substring(newAccount.length - 4)}. Reconnecting...`
        );
        
        // Small delay to ensure state is cleared
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Re-authenticate with the new account
        await signInWithEthereum(provider, 'MetaMask');
      } else {
        // Fallback: prompt manual reconnection
        authState.setError(
          `Account changed to ${newAccount.substring(0, 6)}...${newAccount.substring(newAccount.length - 4)}. Please reconnect.`
        );
        
        // Open wallet selector after short delay
        setTimeout(() => {
          const authButton = document.querySelector('[data-auth-button]');
          if (authButton && !authState.get().isAuthenticated) {
            authButton.click();
          }
        }, 500);
      }
    } catch (error) {
      console.error('Failed to reconnect with new account:', error);
      authState.setError('Failed to connect with new account. Please try again.');
    }
  } else if (!state.isAuthenticated && accounts.length > 0) {
    // Account changed while not authenticated - just update the stored address
    // This ensures next connection attempt uses the current account
    authState.update(state => ({ ...state, address: null, provider: null }));
  }
}

/**
 * Handle chain/network changes
 */
function handleChainChanged(chainId) {
  // Reload the page to reset the app state with the new chain
  // This is recommended by MetaMask docs
  window.location.reload();
}

/**
 * Set up listeners for account and chain changes
 */
function setupWalletListeners() {
  if (!window.ethereum || accountsChangedHandler) return;
  
  // Create handlers
  accountsChangedHandler = handleAccountsChanged;
  chainChangedHandler = handleChainChanged;
  
  // Add listeners
  window.ethereum.on('accountsChanged', accountsChangedHandler);
  window.ethereum.on('chainChanged', chainChangedHandler);
}

/**
 * Remove wallet event listeners (cleanup)
 */
export function removeWalletListeners() {
  if (!window.ethereum) return;
  
  if (accountsChangedHandler) {
    window.ethereum.removeListener('accountsChanged', accountsChangedHandler);
    accountsChangedHandler = null;
  }
  
  if (chainChangedHandler) {
    window.ethereum.removeListener('chainChanged', chainChangedHandler);
    chainChangedHandler = null;
  }
}

// Initialize auth state on page load
if (typeof window !== 'undefined') {
  // Only verify auth in browser environment
  verifyAuth().catch(console.error);
  
  // Set up wallet event listeners
  setupWalletListeners();
  
  // Set up periodic session refresh to keep user logged in
  setInterval(async () => {
    const state = authState.get();
    if (state.isAuthenticated) {
      try {
        await refreshSession();
      } catch (error) {
        console.error('Session refresh failed:', error);
      }
    }
  }, 5 * 60 * 1000); // Refresh every 5 minutes
}

export { authState };