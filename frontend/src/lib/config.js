// API Configuration
const configuredApiUrl = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const isLocalApiUrl = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(configuredApiUrl);

// In Vite development, local backend calls should go through the dev-server
// proxy so random frontend ports do not need to be CORS-whitelisted.
export const API_BASE_URL =
  import.meta.env.DEV && isLocalApiUrl
    ? ''
    : configuredApiUrl || 'http://localhost:8000';

// External Links Configuration
export const FAUCET_URL = 'https://testnet-faucet.genlayer.foundation/';
