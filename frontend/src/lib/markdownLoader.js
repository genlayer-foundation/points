import { marked } from 'marked';

// Configure marked with minimal settings for legal documents
marked.setOptions({
  breaks: true,            // Convert line breaks to <br> tags
  gfm: true,              // Enable GitHub Flavored Markdown
  headerIds: true,        // Add IDs to headings for anchor links
  mangle: false,          // Don't mangle header IDs
  sanitize: false,        // Allow raw HTML (we trust our own content)
  pedantic: false,        // Don't be overly strict
  smartLists: true,       // Use smarter list behavior
  smartypants: false      // Don't use smart quotes (keep original)
});

/**
 * Parse markdown content to HTML with proper styling for legal documents
 * @param {string} markdownContent - Raw markdown content
 * @returns {string} HTML content with Tailwind CSS classes applied
 */
export function parseMarkdown(markdownContent) {
  try {
    // Validate input
    if (typeof markdownContent !== 'string') {
      return `<div class="text-red-600"><h3>Import Error</h3><p>Expected markdown content as string, but received: ${typeof markdownContent}</p></div>`;
    }

    if (!markdownContent || markdownContent.length === 0) {
      return '<div class="text-red-600"><h3>Content Error</h3><p>No markdown content provided to parse</p></div>';
    }

    return marked(markdownContent);
  } catch (error) {
    return `<div class="text-red-600"><h3>Parse Error</h3><p>Failed to parse markdown content: ${error.message}</p></div>`;
  }
}

/**
 * Process legal document markdown with additional formatting
 * @param {string} markdownContent - Raw markdown content
 * @returns {string} Processed HTML content
 */
export function processLegalDocument(markdownContent) {
  try {
    // Validate input first
    if (typeof markdownContent !== 'string') {
      return `<div class="text-red-600"><h2>Import Error</h2><p>Expected markdown content as string, but received: ${typeof markdownContent}</p><p>This typically means the markdown file import failed.</p></div>`;
    }

    if (!markdownContent || markdownContent.length === 0) {
      return '<div class="text-red-600"><h2>Content Error</h2><p>No legal document content provided to process</p></div>';
    }

    // Clean up any formatting issues specific to legal documents
    let cleaned = markdownContent
      // Remove zero-width characters that can cause parsing issues
      .replace(/[\u200B-\u200D\uFEFF]/g, '')
      // Fix problematic Unicode characters
      .replace(/\*\*‍\*\*/g, '')
      // Fix escaped periods in headings (e.g., "##### 1\. Title" -> "##### 1. Title")
      .replace(/^(#{1,6}\s+\d+)\\\./gm, '$1.')
      // Fix inconsistent spacing in headings (e.g., "##### 6 ." -> "##### 6.")
      .replace(/^(#{1,6}\s+\d+)\s+\./gm, '$1.')
      // Fix any double line breaks that might cause spacing issues
      .replace(/\n\n\n+/g, '\n\n')
      // Ensure proper spacing around headings
      .replace(/^(#{1,6})\s*(.+)$/gm, '$1 $2')
      // Clean up any trailing whitespace
      .trim();

    return parseMarkdown(cleaned);
  } catch (error) {
    return `<div class="text-red-600"><h2>Processing Error</h2><p>There was an error processing this legal document: ${error.message}</p></div>`;
  }
}

/**
 * Extract metadata from legal document (like last updated date)
 * @param {string} markdownContent - Raw markdown content
 * @returns {object} Metadata object
 */
export function extractMetadata(markdownContent) {
  const metadata = {};

  // Look for "Last updated" information
  const lastUpdatedMatch = markdownContent.match(/\*\*Last updated:?\*\*\s*(.+)/i);
  if (lastUpdatedMatch) {
    metadata.lastUpdated = lastUpdatedMatch[1].trim();
  }

  // Extract title (first h1)
  const titleMatch = markdownContent.match(/^#\s+(.+)$/m);
  if (titleMatch) {
    metadata.title = titleMatch[1].trim();
  }

  return metadata;
}