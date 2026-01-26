<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { marked } from 'marked';
  import { contributionsAPI } from '../lib/api';
  import { showError } from '../lib/toastStore';
  import Icons from '../components/Icons.svelte';

  // Props from router
  let { params = {} } = $props();

  // State
  let startupRequest = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let expandedDoc = $state(null);

  // Configure marked options for security and links
  const renderer = new marked.Renderer();
  renderer.link = function({ href, title, text }) {
    const safeHref = href || '#';
    return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer"${title ? ` title="${title}"` : ''}>${text}</a>`;
  };

  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false,
    renderer: renderer
  });

  function renderMarkdown(text) {
    if (!text) return '';
    try {
      return marked.parse(text);
    } catch (err) {
      return text;
    }
  }

  async function fetchStartupRequest() {
    try {
      loading = true;
      error = null;
      const response = await contributionsAPI.getStartupRequest(params.id);
      startupRequest = response.data;
    } catch (err) {
      error = err.message || 'Failed to load startup request';
      showError('Failed to load startup request details.');
    } finally {
      loading = false;
    }
  }

  function getDocumentIcon(type) {
    if (type === 'pdf') return 'document';
    if (type === 'image') return 'star';
    return 'link'; // chain/link icon for URLs
  }

  function toggleDocExpand(docIndex) {
    if (expandedDoc === docIndex) {
      expandedDoc = null;
    } else {
      expandedDoc = docIndex;
    }
  }

  function getPdfThumbnail(url) {
    // Convert Cloudinary PDF URL to a thumbnail of the first page
    // pg_1 = page 1, f_jpg = output as JPG, w_600/h_400 = dimensions
    if (url.includes('cloudinary.com') && url.includes('.pdf')) {
      return url.replace('/upload/', '/upload/pg_1,f_jpg,w_600,h_400,c_limit/');
    }
    return url;
  }

  function openPdfInNewTab(url) {
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  onMount(() => {
    fetchStartupRequest();
  });
</script>

<style>
  .prose :global(p) {
    margin-top: 0;
    margin-bottom: 1rem;
    line-height: 1.7;
  }

  .prose :global(p:last-child) {
    margin-bottom: 0;
  }

  .prose :global(strong) {
    font-weight: 600;
  }

  .prose :global(em) {
    font-style: italic;
  }

  .prose :global(h1),
  .prose :global(h2),
  .prose :global(h3),
  .prose :global(h4),
  .prose :global(h5),
  .prose :global(h6) {
    font-weight: 600;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    color: #111827;
  }

  .prose :global(h1) {
    font-size: 1.5rem;
  }

  .prose :global(h2) {
    font-size: 1.25rem;
  }

  .prose :global(h3) {
    font-size: 1.125rem;
  }

  .prose :global(ul),
  .prose :global(ol) {
    margin-top: 0.5rem;
    margin-bottom: 1rem;
    padding-left: 1.5rem;
    list-style-type: disc;
  }

  .prose :global(ol) {
    list-style-type: decimal;
  }

  .prose :global(li) {
    margin-top: 0.25rem;
    margin-bottom: 0.25rem;
    line-height: 1.6;
  }

  .prose :global(a) {
    color: #ea580c;
    text-decoration: underline;
  }

  .prose :global(a:hover) {
    color: #c2410c;
  }

  .prose :global(code) {
    background-color: rgba(0, 0, 0, 0.06);
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-size: 0.875em;
  }

  .prose :global(pre) {
    background-color: #1f2937;
    color: #f9fafb;
    padding: 0.75rem 1rem;
    border-radius: 0.375rem;
    overflow-x: auto;
    margin-top: 0.5rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .prose :global(pre code) {
    background-color: transparent;
    padding: 0;
    color: inherit;
  }

  .prose :global(blockquote) {
    border-left: 3px solid #ea580c;
    padding: 0.5rem 1rem;
    margin: 0.5rem 0 1rem 0;
    font-style: italic;
    background-color: rgba(234, 88, 12, 0.05);
    border-radius: 0 0.25rem 0.25rem 0;
  }

  .prose :global(hr) {
    margin: 1.5rem 0;
    border: 0;
    border-top: 1px solid #e5e7eb;
  }
</style>

<div>
  {#if loading}
    <!-- Loading state -->
    <div class="animate-pulse">
      <div class="h-6 w-24 bg-gray-200 rounded mb-4"></div>
      <div class="h-8 w-2/3 bg-gray-300 rounded mb-6"></div>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 space-y-3">
          <div class="h-4 bg-gray-200 rounded"></div>
          <div class="h-4 bg-gray-200 rounded"></div>
          <div class="h-4 w-3/4 bg-gray-200 rounded"></div>
        </div>
        <div class="h-32 bg-gray-200 rounded"></div>
      </div>
    </div>
  {:else if error}
    <!-- Error state -->
    <div class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
      <Icons name="warning" size="lg" className="text-red-500 mx-auto mb-3" />
      <h2 class="text-lg font-semibold text-red-800 mb-2">Failed to Load</h2>
      <p class="text-red-600 mb-4">{error}</p>
      <button
        onclick={() => push('/builders/contributions')}
        class="text-orange-600 hover:text-orange-800 font-medium"
      >
        Back to Contributions
      </button>
    </div>
  {:else if startupRequest}
    <!-- Back navigation -->
    <button
      onclick={() => push('/builders/contributions')}
      class="inline-flex items-center text-orange-600 hover:text-orange-800 font-medium mb-4 transition-colors text-sm"
    >
      <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back to Contributions
    </button>

    <!-- Header Card - similar to ContributionTypeDetail -->
    <div class="bg-white shadow rounded-lg p-4 sm:p-6 border-2 border-orange-200 mb-6">
      <h1 class="text-xl sm:text-2xl font-bold text-gray-900 mb-3">
        {startupRequest.title}
      </h1>
      {#if startupRequest.short_description}
        <p class="text-sm sm:text-base text-gray-600">{startupRequest.short_description}</p>
      {/if}
    </div>

    <!-- Main content grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Description - takes 2 columns on large screens -->
      <div class="lg:col-span-2">
        <div class="bg-white shadow rounded-lg border-2 border-orange-200 overflow-hidden">
          <div class="px-4 py-3 border-b border-orange-100 bg-orange-50">
            <h2 class="font-semibold text-gray-900 flex items-center text-sm">
              <Icons name="document" size="sm" className="text-gray-500 mr-2" />
              Description
            </h2>
          </div>
          <div class="p-4 sm:p-6">
            <div class="prose prose-sm max-w-none text-gray-700">
              {@html renderMarkdown(startupRequest.description)}
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar with documents -->
      <div class="lg:col-span-1">
        {#if startupRequest.documents && startupRequest.documents.length > 0}
          <div class="bg-white border-2 border-orange-200 rounded-lg shadow overflow-hidden sticky top-4">
            <div class="px-4 py-3 border-b border-orange-100 bg-orange-50">
              <h2 class="font-semibold text-gray-900 flex items-center text-sm">
                <Icons name="document" size="sm" className="text-gray-500 mr-2" />
                Resources
              </h2>
            </div>
            <div class="divide-y divide-gray-100">
              {#each startupRequest.documents as doc, index}
                <div class="p-3">
                  {#if doc.type === 'link'}
                    <!-- Link type: no expand, show chain icon and URL -->
                    <a
                      href={doc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="flex items-center gap-2 group hover:bg-orange-50 -m-2 p-2 rounded transition-colors"
                    >
                      <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      <div class="flex-1 min-w-0">
                        <span class="text-sm font-medium text-gray-700 group-hover:text-orange-600 transition-colors block truncate">{doc.title}</span>
                        <span class="text-xs text-gray-400 block truncate">{doc.url}</span>
                      </div>
                      <Icons name="externalLink" size="sm" className="text-gray-400 group-hover:text-orange-600 flex-shrink-0" />
                    </a>
                  {:else}
                    <!-- PDF/Image type: with expand functionality -->
                    <div class="flex items-center justify-between gap-2">
                      <div class="flex items-center gap-2 min-w-0 flex-1">
                        <Icons name={getDocumentIcon(doc.type)} size="sm" className="text-gray-400 flex-shrink-0" />
                        <span class="text-sm font-medium text-gray-700 truncate">{doc.title}</span>
                      </div>
                      <div class="flex items-center gap-1 flex-shrink-0">
                        <button
                          onclick={() => toggleDocExpand(index)}
                          class="p-1.5 text-gray-500 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                          title={expandedDoc === index ? 'Collapse' : 'Preview'}
                        >
                          <svg class="w-4 h-4 transition-transform {expandedDoc === index ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        <a
                          href={doc.url}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                          class="p-1.5 text-gray-500 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                          title="Download"
                        >
                          <Icons name="download" size="sm" />
                        </a>
                      </div>
                    </div>

                    <!-- Expandable preview (only for non-link types) -->
                    {#if expandedDoc === index}
                    <div class="mt-3 border border-gray-200 rounded overflow-hidden bg-gray-50">
                      {#if doc.type === 'pdf'}
                        <button
                          onclick={() => openPdfInNewTab(doc.url)}
                          class="w-full cursor-pointer hover:opacity-90 transition-opacity"
                          title="Click to open PDF"
                        >
                          <img
                            src={getPdfThumbnail(doc.url)}
                            alt={doc.title}
                            class="w-full h-48 object-contain bg-white"
                          />
                          <div class="p-2 bg-gray-100 text-center text-xs text-gray-600">
                            Click to open PDF
                          </div>
                        </button>
                      {:else if doc.type === 'image'}
                        <img
                          src={doc.url}
                          alt={doc.title}
                          class="w-full max-h-64 object-contain"
                        />
                      {/if}
                    </div>
                    {/if}
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
