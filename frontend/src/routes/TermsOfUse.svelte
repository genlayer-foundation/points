<script>
  import { onMount } from 'svelte';
  import { processLegalDocument, extractMetadata, extractHeadings } from '../lib/markdownLoader.js';
  import termsContent from '../content/legal/terms-of-use.md?raw';

  let pageTitle = 'Terms of Use';
  let htmlContent = $state('');
  let metadata = $state({});
  let headings = $state([]);
  let isLoading = $state(true);
  let hasError = $state(false);
  let activeSection = $state('');
  let tocOpen = $state(false);

  function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
      const yOffset = -80; // Offset for fixed header
      const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
      activeSection = sectionId;

      // Close TOC on mobile after navigation
      if (window.innerWidth < 768) {
        tocOpen = false;
      }
    }
  }

  onMount(async () => {
    try {
      isLoading = true;
      hasError = false;

      // Process the markdown content
      if (typeof termsContent === 'string' && termsContent.length > 0) {
        htmlContent = processLegalDocument(termsContent);
        metadata = extractMetadata(termsContent);
        headings = extractHeadings(termsContent);
      } else {
        // Try to fetch as fallback if import failed
        try {
          const response = await fetch('/src/content/legal/terms-of-use.md');
          if (response.ok) {
            const fallbackContent = await response.text();
            htmlContent = processLegalDocument(fallbackContent);
            metadata = extractMetadata(fallbackContent);
            headings = extractHeadings(fallbackContent);
          } else {
            throw new Error('Failed to fetch fallback content');
          }
        } catch (fetchError) {
          hasError = true;
          htmlContent = `<div class="text-red-600"><h2>Content Loading Error</h2><p>The terms of use content could not be loaded. Please try refreshing the page.</p></div>`;
        }
      }

      document.title = `${pageTitle} - GenLayer Points`;

      // Set up Intersection Observer for active section tracking
      const observerOptions = {
        rootMargin: '-100px 0px -66%',
        threshold: 0
      };

      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            activeSection = entry.target.id;
          }
        });
      }, observerOptions);

      // Observe all section headings
      setTimeout(() => {
        headings.forEach(heading => {
          const element = document.getElementById(heading.id);
          if (element) {
            observer.observe(element);
          }
        });
      }, 100);

      // Cleanup observer on unmount
      return () => {
        observer.disconnect();
      };
    } catch (error) {
      hasError = true;
      htmlContent = `<div class="text-red-600"><h2>Unexpected Error</h2><p>An unexpected error occurred. Please try refreshing the page.</p></div>`;
    } finally {
      isLoading = false;
    }
  });
</script>

<svelte:head>
  <title>{pageTitle} - GenLayer Points</title>
</svelte:head>

<div class="space-y-6 sm:space-y-8 pb-8 sm:pb-0">
  <!-- Header section -->
  <div>
    <h1 class="text-2xl font-bold text-gray-900">Terms of Use</h1>
    {#if metadata.lastUpdated}
      <p class="mt-2 text-xs text-gray-500">Last updated: {metadata.lastUpdated}</p>
    {/if}
  </div>

  {#if isLoading}
    <!-- Loading state -->
    <div class="bg-white shadow rounded-lg p-12 max-w-prose">
      <div class="flex justify-center items-center">
        <div class="text-center">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
          <p class="text-gray-600">Loading terms of use...</p>
        </div>
      </div>
    </div>
  {:else}
    <!-- Content Card -->
    <div class="bg-white shadow rounded-lg p-6 md:p-8 max-w-prose">
      <article class="legal-content">
        {@html htmlContent}
      </article>
    </div>
  {/if}
</div>

<style>
  /* Legal content - narrower for better readability */
  .legal-content {
    @apply text-gray-800 leading-relaxed;
    line-height: 1.7;
  }

  /* Hide the first H1 since we show it in the header */
  .legal-content :global(h1:first-child) {
    @apply hidden;
  }

  .legal-content :global(h1) {
    @apply text-2xl font-bold text-gray-900 mb-4 mt-8;
  }

  .legal-content :global(h2) {
    @apply text-xl font-bold text-gray-900 mb-3 mt-8;
  }

  .legal-content :global(h3) {
    @apply text-lg font-semibold text-gray-900 mb-3 mt-6;
  }

  .legal-content :global(h4) {
    @apply text-base font-semibold text-gray-900 mb-2 mt-5;
  }

  .legal-content :global(h5) {
    @apply text-base font-medium text-gray-900 mb-2 mt-4;
  }

  .legal-content :global(h6) {
    @apply text-sm font-medium text-gray-900 mb-2 mt-4;
  }

  /* Paragraphs - left-aligned text */
  .legal-content :global(p) {
    @apply text-gray-800 leading-relaxed mb-5;
    font-size: 15px;
    text-align: left;
  }

  .legal-content :global(ul), .legal-content :global(ol) {
    @apply mb-5 pl-6 space-y-2;
  }

  .legal-content :global(ul) {
    @apply list-disc;
  }

  .legal-content :global(ol) {
    @apply list-decimal;
  }

  .legal-content :global(li) {
    @apply text-gray-800 leading-relaxed;
    font-size: 15px;
    text-align: left;
  }

  .legal-content :global(a) {
    @apply text-gray-800 font-medium hover:text-gray-900 no-underline;
  }

  .legal-content :global(strong) {
    @apply font-semibold text-gray-900;
  }

  .legal-content :global(em) {
    @apply italic text-gray-800;
  }

  .legal-content :global(code) {
    @apply bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800;
  }

  .legal-content :global(blockquote) {
    @apply border-l-4 border-gray-300 pl-4 italic text-gray-700 my-4;
  }

  /* Better spacing for nested lists */
  .legal-content :global(li ul), .legal-content :global(li ol) {
    @apply mt-2 mb-2;
  }
</style>