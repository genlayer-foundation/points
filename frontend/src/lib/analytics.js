/**
 * Google Analytics initialization
 *
 * Loads and initializes Google Analytics using the tracking ID from environment variables.
 * Only initializes if VITE_GOOGLE_ANALYTICS_ID is set.
 */

/**
 * Initialize Google Analytics
 * Dynamically loads gtag.js script and configures tracking
 */
export function initializeAnalytics() {
  const trackingId = import.meta.env.VITE_GOOGLE_ANALYTICS_ID;

  // Only initialize if tracking ID is configured
  if (!trackingId) {
    return;
  }

  // Create and inject the gtag.js script
  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${trackingId}`;
  document.head.appendChild(script);

  // Initialize dataLayer and gtag function
  window.dataLayer = window.dataLayer || [];

  // Make gtag available globally
  window.gtag = function() {
    window.dataLayer.push(arguments);
  };

  // Initialize with current timestamp
  window.gtag('js', new Date());

  // Configure with tracking ID
  window.gtag('config', trackingId);
}
