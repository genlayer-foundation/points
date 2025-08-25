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
      // If we have saved auth, we still need to verify once per session
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
 * Connect to MetaMask wallet
 * @returns {Promise<string>} Ethereum address
 */
export async function connectWallet() {
  authState.setLoading(true);
  authState.setError(null);
  
  try {
    if (!window.ethereum) {
      throw new Error('MetaMask is not installed. Please install MetaMask to continue.');
    }

    // Request account access
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    const address = accounts[0];
    
    if (!address) {
      throw new Error('No Ethereum accounts found. Please unlock your MetaMask wallet.');
    }
    
    authState.update(state => ({ ...state, address }));
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
 * @returns {Promise<Object>} Signed message and signature
 */
export async function createAndSignMessage(address, nonce) {
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
  
  // Request signature from wallet
  const provider = new ethers.BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const signature = await signer.signMessage(messageToSign);
  
  return {
    message: messageToSign,
    signature
  };
}

/**
 * Sign in with Ethereum
 * @returns {Promise<Object>} Authentication result
 */
export async function signInWithEthereum() {
  authState.setLoading(true);
  authState.setError(null);
  
  try {
    // Connect to wallet and get address
    const address = await connectWallet();
    
    // Get nonce from server
    const nonce = await getNonce();
    
    // Create and sign the message
    const { message, signature } = await createAndSignMessage(address, nonce);
    
    // Send to backend for verification
    console.log('Sending login request to:', API_ENDPOINTS.LOGIN);
    const response = await authAxios.post(API_ENDPOINTS.LOGIN, {
      message,
      signature
    });
    console.log('Login response:', response.data);
    
    // Update auth state
    authState.setAuthenticated(true, address);
    
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
    console.log('Verifying auth at:', API_ENDPOINTS.VERIFY);
    const response = await authAxios.get(API_ENDPOINTS.VERIFY);
    console.log('Auth verification response:', response.data);
    const isAuthenticated = response.data.authenticated;
    const address = response.data.address || null;
    
    // Update auth state with verification result
    authState.setAuthenticated(isAuthenticated, address);
    
    // Load user data if authenticated
    if (isAuthenticated) {
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

// Initialize auth state on page load
if (typeof window !== 'undefined') {
  // Only verify auth in browser environment
  verifyAuth().catch(console.error);
  
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