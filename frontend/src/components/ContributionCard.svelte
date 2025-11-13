<script>
  import { format } from 'date-fns';
  import { push } from 'svelte-spa-router';
  import { getCategoryColors } from '../lib/categoryColors';
  import Avatar from './Avatar.svelte';
  import Icons from './Icons.svelte';
  import { parseMarkdown } from '../lib/markdownLoader.js';

  let {
    contribution,
    submission = null,
    showExpand = false,
    showUser = true,
    variant = 'default', // 'default' or 'compact'
    category = null, // Override category for mixed lists
    className = ''
  } = $props();
  
  // State for expanding details
  let isExpanded = $state(false);
  
  // Determine category and colors
  // Use passed category prop first, then try multiple paths where category might be stored
  let actualCategory = $derived(
    category ||
    contribution?.contribution_type_details?.category || 
    contribution?.contribution_type?.category ||
    contribution?.category || 
    'global'
  );
  
  let categoryColors = $derived(getCategoryColors(actualCategory));
  
  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
      // Take just the date part (YYYY-MM-DD) and ignore time/timezone
      const datePart = dateString.split('T')[0];
      const [year, month, day] = datePart.split('-');
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return `${months[parseInt(month) - 1]} ${parseInt(day)}, ${year}`;
    } catch {
      return dateString;
    }
  }
  
  // Check if we have details to show
  // For grouped contributions, check grouped_items
  let hasDetails = $derived(
    ((submission?.notes || submission?.evidence_items?.length > 0) ||
     (contribution?.grouped_items?.some(item => item.notes || item.evidence_items?.length > 0))) &&
    showExpand
  );
</script>

<div class="{categoryColors.cardBg} shadow rounded-lg hover:shadow-lg transition-shadow border-2 {categoryColors.border} overflow-hidden {className}">
  <div class="{variant === 'compact' ? 'p-3' : 'p-4'}">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 mb-2">
          <Icons
            name={actualCategory === 'builder' ? 'builder' : actualCategory === 'validator' ? 'validator' : 'global'}
            size="sm"
            className={actualCategory === 'builder' ? 'text-orange-500' : actualCategory === 'validator' ? 'text-sky-500' : 'text-gray-500'}
          />
          <h3 class="text-base font-semibold text-gray-900 flex items-center gap-2">
            <button
              class="{categoryColors.hoverText} transition-colors"
              onclick={() => push(`/contribution-type/${contribution.typeId || contribution.contribution_type || contribution.contribution_type_details?.id}`)}
            >
              {contribution.contribution_type_details?.name || contribution.contribution_type_name || 'Contribution'}
            </button>
            {#if contribution.count > 1}
              <span class="text-sm font-normal text-gray-500">
                × {contribution.count}
              </span>
            {/if}
          </h3>
          
          {#if submission?.evidence_items?.length > 0}
            <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" title="{submission.evidence_items.length} evidence item{submission.evidence_items.length > 1 ? 's' : ''}">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          {/if}
          
          {#if hasDetails}
            <button
              type="button"
              onclick={() => isExpanded = !isExpanded}
              class="{categoryColors.text} {categoryColors.hoverText} p-1 ml-auto"
              title="{isExpanded ? 'Hide' : 'Show'} details"
            >
              <svg 
                class="w-4 h-4 transition-transform {isExpanded ? 'rotate-180' : ''}" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          {/if}
        </div>
        
        <div class="flex items-center gap-2 text-xs">
          {#if showUser && contribution.users && contribution.users.length > 0}
            {#if contribution.users.length === 1}
              <Avatar 
                user={contribution.users[0]}
                size="xs"
                clickable={true}
              />
              <button 
                class="{categoryColors.text} {categoryColors.hoverText} font-medium"
                onclick={() => push(`/participant/${contribution.users[0].address || ''}`)}
              >
                {contribution.users[0].name || `${contribution.users[0].address?.slice(0, 6)}...${contribution.users[0].address?.slice(-4)}` || 'Anonymous'}
              </button>
            {:else}
              <div class="flex -space-x-2">
                {#each contribution.users.slice(0, 3) as user}
                  <Avatar 
                    user={user}
                    size="xs"
                    clickable={true}
                    showBorder={true}
                  />
                {/each}
              </div>
              <span class="{categoryColors.text} font-medium">
                {contribution.users.length} participants
              </span>
            {/if}
            <span class="text-gray-400">•</span>
          {:else if showUser && contribution.user_details}
            <Avatar 
              user={contribution.user_details}
              size="xs"
              clickable={true}
            />
            <button 
              class="{categoryColors.text} {categoryColors.hoverText} font-medium"
              onclick={() => push(`/participant/${contribution.user_details.address || ''}`)}
            >
              {contribution.user_details.name || `${contribution.user_details.address?.slice(0, 6)}...${contribution.user_details.address?.slice(-4)}` || 'Anonymous'}
            </button>
            <span class="text-gray-400">•</span>
          {/if}
          <span class="text-gray-500">
            {#if contribution.count > 1 && contribution.end_date && contribution.end_date !== contribution.contribution_date}
              {formatDate(contribution.contribution_date)} - {formatDate(contribution.end_date)}
            {:else}
              {formatDate(contribution.contribution_date)}
            {/if}
          </span>
        </div>
      </div>
      
      <div class="ml-3 flex-shrink-0">
        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
          {contribution.frozen_global_points || 0} pts
        </span>
      </div>
    </div>
    
    {#if isExpanded && (submission || contribution)}
      <div class="mt-3 pt-3 border-t {categoryColors.expandBorder} space-y-3">
        {#if submission?.notes}
          <div>
            <h5 class="text-xs font-medium text-gray-700 mb-1">Notes</h5>
            <div class="markdown-content text-xs text-gray-600">{@html parseMarkdown(submission.notes)}</div>
          </div>
        {/if}

        {#if submission?.evidence_items?.length > 0}
          <div>
            <h5 class="text-xs font-medium text-gray-700 mb-1">Evidence</h5>
            <ul class="space-y-1">
              {#each submission.evidence_items as evidence}
                <li class="text-xs text-gray-600">
                  {#if evidence.description}
                    • {evidence.description}
                  {/if}
                  {#if evidence.url}
                    <a href={evidence.url} target="_blank" class="{categoryColors.text} underline ml-1">
                      View URL
                    </a>
                  {/if}
                  {#if evidence.file_url}
                    <a href={evidence.file_url} target="_blank" class="{categoryColors.text} underline ml-1">
                      View File
                    </a>
                  {/if}
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if contribution?.grouped_items && contribution.grouped_items.length > 0}
          {#each contribution.grouped_items as item, index}
            {#if item.notes || item.evidence_items?.length > 0}
              <div class="{index > 0 ? 'border-t' : ''} {categoryColors.expandBorder} pt-3 pb-2">
                {#if contribution.count > 1}
                  <div class="flex items-center gap-2 mb-2">
                    <Avatar
                      user={item.user_details}
                      size="xs"
                      clickable={true}
                    />
                    <span class="text-xs font-medium text-gray-700">
                      {item.user_details?.name || item.user_details?.address?.slice(0, 8) || 'Unknown'}
                    </span>
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                      {item.frozen_global_points || 0} pts
                    </span>
                  </div>
                {/if}
                {#if item.notes}
                  <div class="mb-2">
                    <h5 class="text-xs font-medium text-gray-700 mb-1">Notes</h5>
                    <p class="text-xs text-gray-600">{item.notes}</p>
                  </div>
                {/if}
                {#if item.evidence_items?.length > 0}
                  <div>
                    <h5 class="text-xs font-medium text-gray-700 mb-1">Evidence</h5>
                    <ul class="space-y-1">
                      {#each item.evidence_items as evidence}
                        <li class="text-xs text-gray-600">
                          {#if evidence.description}
                            • {evidence.description}
                          {/if}
                          {#if evidence.url}
                            <a href={evidence.url} target="_blank" class="{categoryColors.text} underline ml-1">
                              View URL
                            </a>
                          {/if}
                          {#if evidence.file_url}
                            <a href={evidence.file_url} target="_blank" class="{categoryColors.text} underline ml-1">
                              View File
                            </a>
                          {/if}
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}
              </div>
            {/if}
          {/each}
        {/if}
      </div>
    {/if}
  </div>
  
  {#if contribution.highlight}
    <div class="bg-yellow-50 border-t border-yellow-300 {variant === 'compact' ? 'p-3' : 'p-4'}">
      <div class="flex items-start gap-3">
        <svg class="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
        </svg>
        <div class="flex-1">
          <h4 class="text-sm font-semibold text-yellow-900 mb-1">Featured: {contribution.highlight.title}</h4>
          <p class="text-sm text-yellow-800">{contribution.highlight.description}</p>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .markdown-content :global(ul) {
    list-style-type: disc;
    margin-left: 1.5rem;
  }

  .markdown-content :global(ol) {
    list-style-type: decimal;
    margin-left: 1.5rem;
  }
</style>