import { Buffer } from 'buffer';
import process from 'process';

// Define global variables required for Web3 libraries
window.global = window;
window.Buffer = Buffer;
window.process = process;

// Fix for ethereum providers
if (typeof window.ethereum !== 'undefined') {
  window.ethereum.autoRefreshOnNetworkChange = false;
}