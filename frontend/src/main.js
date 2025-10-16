import './lib/polyfills.js'; // Import polyfills first
import { mount } from 'svelte';
import App from './App.svelte';
import './styles.css';

// Initialize Google Analytics (async, non-blocking)
import('./lib/analytics.js')
  .then(({ initializeAnalytics }) => initializeAnalytics())
  .catch(err => console.warn('Analytics not loaded:', err.message));

// Create the app using Svelte 5's mount function
const app = mount(App, {
  target: document.getElementById('app')
});

export default app;