<script>
  // @ts-nocheck
  import { push } from 'svelte-spa-router';
  import Avatar from './Avatar.svelte';
  import { currentCategory } from '../stores/category.js';
  import { m } from '../lib/paraglide/messages.js';

  let {
    entries = [],
    loading = false,
    error = null,
    showHeader = true,
    title = m.nav_leaderboard(),
    subtitle = m.lbt_subtitle_default(),
    compact = false,
    hideAddress = false,
    embedded = false
  } = $props();

  // Helper for rank styling
  function getRankClass(rank) {
    if (rank === 1) return 'bg-[#f8b93d] text-white';
    if (rank === 2) return 'bg-[#f1f3f7] text-[#333]';
    if (rank === 3) return 'bg-[#c9956b] text-white';
    return 'bg-[#f8fafc] text-[#506078]';
  }

  let pointsLabel = $derived($currentCategory === 'community' ? m.lbt_community_points() : m.lbt_points());
</script>

{#if loading}
  <div class="flex justify-center items-center p-8">
    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
  </div>
{:else if error}
  <div class="p-6 text-center text-red-500">
    {m.lbt_failed_load({ error })}
  </div>
{:else if entries.length === 0}
  <div class="bg-gray-50 rounded-lg p-6 text-center">
    <p class="text-gray-500">{m.lbt_no_entries()}</p>
  </div>
{:else}
  <div class={embedded ? 'overflow-hidden' : 'overflow-hidden rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)]'}>
    {#if showHeader}
      <div class="px-4 py-5 sm:px-6">
        <h3 class="text-[18px] font-semibold leading-6 text-black">
          {title}
        </h3>
        <p class="mt-1 max-w-2xl text-[14px] text-[#6b6b6b]">
          {subtitle}
        </p>
      </div>
    {/if}
    
    <div class="overflow-hidden">
      <table class="w-full table-fixed divide-y divide-[#eef1f6]">
        <thead class="bg-[#f8fafc]">
          <tr>
            <th scope="col" class="w-[56px] px-2 py-3 text-left text-[11px] font-semibold uppercase text-[#7b8798] sm:w-[88px] sm:px-6" style="letter-spacing: 0.8px;">
              {m.lbt_rank()}
            </th>
            <th scope="col" class="px-2 py-3 text-left text-[11px] font-semibold uppercase text-[#7b8798] sm:px-6" style="letter-spacing: 0.8px;">
              {m.lbt_participant()}
            </th>
            <th scope="col" class="w-[78px] px-2 py-3 text-right text-[11px] font-semibold uppercase text-[#7b8798] sm:w-[120px] sm:px-6 sm:text-left" style="letter-spacing: 0.8px;">
              {pointsLabel}
            </th>
            {#if $currentCategory === 'validator'}
              <th scope="col" class="hidden px-3 py-3 text-left text-[11px] font-semibold uppercase text-[#7b8798] sm:table-cell sm:w-[150px] sm:px-6" style="letter-spacing: 0.8px;">
                {m.lbt_active_validators()}
              </th>
            {/if}
          </tr>
        </thead>
        <tbody class="divide-y divide-[#eef1f6] bg-white">
          {#each entries as entry, i}
            <tr class="bg-white transition-colors hover:bg-[#fbfcff]">
              <td class="px-2 py-4 align-top sm:px-6">
                <span class={`inline-flex h-8 w-8 items-center justify-center rounded-full text-[13px] font-semibold ${getRankClass(entry.rank)}`}>
                  {entry.rank}
                </span>
              </td>
              <td class="min-w-0 px-2 py-4 align-top sm:px-6">
                <div class="flex min-w-0 items-center">
                  {#if !compact}
                    <div class="mr-2 flex-shrink-0 sm:mr-3">
                      <Avatar 
                        user={entry.user_details}
                        size="sm"
                        clickable={true}
                      />
                    </div>
                  {/if}
                  <div class="min-w-0">
                    <button
                      onclick={() => push(`/participant/${entry.user_details?.address || ''}`)}
                      class="block max-w-full truncate text-left text-[14px] font-semibold text-[#111827] transition-colors hover:text-black"
                    >
                      {entry.user_details?.name || 'N/A'}
                    </button>
                    {#if !hideAddress}
                      <div class="hidden text-[13px] text-[#7b8798] sm:block">
                        {entry.user_details?.address || ''}
                      </div>
                    {/if}
                    {#if $currentCategory === 'validator'}
                      <div class="mt-1 sm:hidden">
                        {#if entry.active_validators_count === null}
                          <span class="inline-flex max-w-full items-center rounded-full bg-[#f3f5f9] px-2 py-1 text-[11px] font-semibold text-[#7b8798]">
                            {m.lbt_no_validator()}
                          </span>
                        {:else}
                          <a
                            href="/validators/participants"
                            onclick={(e) => { e.preventDefault(); push('/validators/participants'); }}
                            class="inline-flex max-w-full items-center rounded-full bg-[#eef4ff] px-2 py-1 text-[11px] font-semibold text-[#387de8] transition-colors hover:bg-[#e0ebff]"
                          >
                            {m.lbt_n_active({ count: entry.active_validators_count })}
                          </a>
                        {/if}
                      </div>
                    {/if}
                  </div>
                </div>
              </td>
              <td class="px-2 py-4 text-right align-top sm:px-6 sm:text-left">
                <div class="truncate text-[14px] font-semibold text-[#111827]">{entry.total_points}</div>
              </td>
              {#if $currentCategory === 'validator'}
                <td class="hidden px-3 py-4 align-top sm:table-cell sm:px-6">
                  {#if entry.active_validators_count === null}
                    <span class="inline-block rounded-full bg-[#f3f5f9] px-2.5 py-1.5 text-xs font-semibold text-[#7b8798]">
                      {m.lbt_no_validator()}
                    </span>
                  {:else}
                    <a
                      href="/validators/participants"
                      onclick={(e) => { e.preventDefault(); push('/validators/participants'); }}
                      class="inline-block cursor-pointer rounded-full bg-[#eef4ff] px-2.5 py-1.5 text-xs font-semibold text-[#387de8] transition-colors hover:bg-[#e0ebff]"
                    >
                      {m.lbt_n_active({ count: entry.active_validators_count })}
                    </a>
                  {/if}
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
{/if}
