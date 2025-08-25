<script>
	import { onMount } from 'svelte';
	import { getContributionTypes } from '../api/contributions.js';

	let {
		selectedCategory = $bindable('validator'),
		selectedContributionType = $bindable(null),
		defaultContributionType = null,
		onlySubmittable = true,
		stewardMode = false,
		providedContributionTypes = null,  // Allow passing types from parent
		onSelectionChange = () => {}
	} = $props();

	let contributionTypes = $state([]);
	let filteredTypes = $state([]);
	let searchQuery = $state('');
	let dropdownOpen = $state(false);
	let loading = $state(true);

	onMount(async () => {
		if (providedContributionTypes) {
			// Use provided types instead of loading
			contributionTypes = providedContributionTypes;
			loading = false;
			filterTypes();
			
			// Set default if provided
			if (defaultContributionType) {
				const defaultType = contributionTypes.find(t => t.id === defaultContributionType);
				if (defaultType) {
					selectedContributionType = defaultType;
				}
			}
		} else {
			// Load types only if not provided
			await loadContributionTypes();
		}
	});

	async function loadContributionTypes() {
		loading = true;
		try {
			const params = {};
			if (onlySubmittable && !stewardMode) {
				params.is_submittable = 'true';
			}
			const types = await getContributionTypes(params);
			contributionTypes = types;
			filterTypes();
			
			// Set default if provided
			if (defaultContributionType) {
				const defaultType = contributionTypes.find(t => t.id === defaultContributionType);
				if (defaultType) {
					selectedContributionType = defaultType;
				}
			}
		} catch (error) {
			console.error('Failed to load contribution types:', error);
		} finally {
			loading = false;
		}
	}

	function filterTypes() {
		let filtered = contributionTypes.filter(type => 
			type.category === selectedCategory
		);

		if (searchQuery) {
			const query = searchQuery.toLowerCase();
			filtered = filtered.filter(type => 
				type.name.toLowerCase().includes(query) ||
				(type.description && type.description.toLowerCase().includes(query))
			);
		}

		filteredTypes = filtered;
	}

	function selectCategory(category) {
		selectedCategory = category;
		selectedContributionType = null;
		searchQuery = '';
		filterTypes();
		onSelectionChange(selectedCategory, selectedContributionType);
	}

	function selectContributionType(type) {
		selectedContributionType = type;
		dropdownOpen = false;
		searchQuery = type.name;
		onSelectionChange(selectedCategory, selectedContributionType);
	}

	function handleSearchInput(event) {
		searchQuery = event.target.value;
		filterTypes();
		dropdownOpen = true;
	}

	function handleSearchFocus() {
		if (selectedContributionType && searchQuery === selectedContributionType.name) {
			searchQuery = '';
		}
		dropdownOpen = true;
		filterTypes();
	}

	function handleSearchBlur() {
		// Delay to allow click on dropdown items
		setTimeout(() => {
			dropdownOpen = false;
			if (selectedContributionType && !searchQuery) {
				searchQuery = selectedContributionType.name;
			}
		}, 200);
	}

	function handleDropdownClick() {
		if (!dropdownOpen) {
			handleSearchFocus();
		}
	}

	$effect(() => {
		filterTypes();
	});
</script>

<div class="contribution-selection">
	<div class="selection-wrapper">
		<!-- Category Toggle Buttons -->
		<div class="category-buttons" class:dropdown-open={dropdownOpen}>
			<button 
				class="category-btn" 
				class:active={selectedCategory === 'validator'}
				style={selectedCategory === 'validator' ? 'background: #e0f2fe; color: #0369a1;' : ''}
				onclick={() => selectCategory('validator')}
			>
				Validator
			</button>
			<button 
				class="category-btn" 
				class:active={selectedCategory === 'builder'}
				style={selectedCategory === 'builder' ? 'background: #ffedd5; color: #c2410c;' : ''}
				onclick={() => selectCategory('builder')}
			>
				Builder
			</button>
		</div>

		<!-- Contribution Type Dropdown/Search -->
		<div class="contribution-type-selector">
		<div class="dropdown-container" class:last-element={!selectedContributionType} class:dropdown-open={dropdownOpen}>
			<div class="search-icon">
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M7 12C9.76142 12 12 9.76142 12 7C12 4.23858 9.76142 2 7 2C4.23858 2 2 4.23858 2 7C2 9.76142 4.23858 12 7 12Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
					<path d="M14 14L10.5 10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</div>
			<input
				type="text"
				class="search-input"
				placeholder={loading ? "Loading..." : "Select or search contribution type..."}
				bind:value={searchQuery}
				oninput={handleSearchInput}
				onfocus={handleSearchFocus}
				onblur={handleSearchBlur}
				disabled={loading}
			/>
			<button 
				class="dropdown-arrow" 
				onclick={handleDropdownClick}
				disabled={loading}
			>
				<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</button>
			
			{#if dropdownOpen && !loading}
				<div class="dropdown-menu">
					{#if filteredTypes.length === 0}
						<div class="dropdown-item no-results">
							No contribution types found
						</div>
					{:else}
						{#each filteredTypes as type}
							<button
								class="dropdown-item"
								class:selected={selectedContributionType?.id === type.id}
								onclick={() => selectContributionType(type)}
							>
								<div class="item-name">{type.name}</div>
								{#if type.description}
									<div class="item-description">{type.description}</div>
								{/if}
								<div class="item-points">
									{#if type.current_multiplier}
										{Math.round(type.min_points * type.current_multiplier)} - {Math.round(type.max_points * type.current_multiplier)}
									{:else}
										{type.min_points} - {type.max_points}
									{/if}
								</div>
							</button>
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	</div>
		
		{#if selectedContributionType}
			<div class="selection-info">
				<h4>{selectedContributionType.name}</h4>
				{#if selectedContributionType.description}
					<p>{selectedContributionType.description}</p>
				{/if}
				<div class="points-info">
					<div class="points-row">
						<span class="final-label">Points:</span>
						<span class="final-value">
							{#if selectedContributionType.current_multiplier}
								{Math.round(selectedContributionType.min_points * selectedContributionType.current_multiplier)} - {Math.round(selectedContributionType.max_points * selectedContributionType.current_multiplier)}
							{:else}
								{selectedContributionType.min_points} - {selectedContributionType.max_points}
							{/if}
						</span>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.contribution-selection {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}
	
	.selection-wrapper {
		display: flex;
		flex-direction: column;
		position: relative;
	}

	.category-buttons {
		display: flex;
		gap: 0;
		padding: 0;
		background: var(--color-surface-50, #fafafa);
		border: 1px solid var(--color-border, #ddd);
		border-radius: 0.5rem;
		border-bottom-left-radius: 0;
		border-bottom-right-radius: 0;
		border-bottom: none;
		margin-bottom: 0;
		position: relative;
		z-index: 1;
	}
	
	.category-buttons.dropdown-open {
		border-left-color: var(--color-primary, #007bff);
		border-right-color: var(--color-primary, #007bff);
		border-top-color: var(--color-primary, #007bff);
	}

	.category-btn {
		flex: 1;
		padding: 0.5rem 1rem;
		background: transparent;
		border: none;
		border-radius: 0;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text-secondary, #666);
		cursor: pointer;
		transition: all 0.2s ease;
		border-right: 1px solid var(--color-border, #e5e7eb);
	}
	
	.category-btn:first-child {
		border-top-left-radius: 0.4rem;
	}
	
	.category-btn:last-child {
		border-right: none;
		border-top-right-radius: 0.4rem;
	}

	.category-btn:hover:not(.active) {
		background: var(--color-surface-100, #f3f4f6);
	}

	.category-btn.active {
		font-weight: 600;
		position: relative;
	}

	.contribution-type-selector {
		position: relative;
		margin-top: 0;
		z-index: 10;
		border-top: 1px solid var(--color-border, #ddd);
	}

	.dropdown-container {
		position: relative;
		width: 100%;
		display: flex;
		align-items: center;
		background: white;
		border-left: 1px solid var(--color-border, #ddd);
		border-right: 1px solid var(--color-border, #ddd);
		border-bottom: 1px solid var(--color-border, #ddd);
		border-radius: 0;
		margin-top: 0;
	}
	
	.dropdown-container.last-element {
		border-bottom-left-radius: 0.5rem;
		border-bottom-right-radius: 0.5rem;
	}
	
	.dropdown-container.dropdown-open {
		border-color: var(--color-primary, #007bff);
		border-bottom-left-radius: 0;
		border-bottom-right-radius: 0;
		z-index: 1001;
		position: relative;
	}
	
	.dropdown-container.dropdown-open .search-icon {
		border-right-color: var(--color-primary-light, #cce5ff);
	}

	.search-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0 0.75rem;
		color: var(--color-text-secondary, #666);
		border-right: 1px solid var(--color-border, #ddd);
	}

	.search-input {
		flex: 1;
		padding: 0.5rem 2.5rem 0.5rem 0.75rem;
		background: transparent;
		border: none;
		font-size: 0.875rem;
		transition: none;
	}

	.search-input:focus {
		outline: none;
	}

	.search-input:disabled {
		background: transparent;
		cursor: not-allowed;
	}

	.dropdown-arrow {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		padding: 0.25rem;
		background: transparent;
		border: none;
		color: var(--color-text-secondary, #666);
		cursor: pointer;
		transition: color 0.2s ease;
	}

	.dropdown-arrow:hover:not(:disabled) {
		color: var(--color-text-primary, #333);
	}

	.dropdown-arrow:disabled {
		cursor: not-allowed;
		opacity: 0.5;
	}

	.dropdown-menu {
		position: absolute;
		top: calc(100% - 1px);
		left: -1px;
		right: -1px;
		max-height: 300px;
		overflow-y: auto;
		background: white;
		border: 1px solid var(--color-primary, #007bff);
		border-top: 1px solid var(--color-border, #ddd);
		border-bottom-left-radius: 0.5rem;
		border-bottom-right-radius: 0.5rem;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
		z-index: 1000;
	}

	.dropdown-item {
		display: block;
		width: 100%;
		padding: 0.75rem 1rem;
		text-align: left;
		background: transparent;
		border: none;
		cursor: pointer;
		transition: background 0.2s ease;
	}

	.dropdown-item:hover {
		background: var(--color-surface-100, #f7f7f7);
	}

	.dropdown-item.selected {
		background: var(--color-primary-light, #e6f2ff);
	}

	.dropdown-item.no-results {
		color: var(--color-text-secondary, #666);
		font-style: italic;
		cursor: default;
	}

	.dropdown-item.no-results:hover {
		background: transparent;
	}

	.item-name {
		font-weight: 500;
		color: var(--color-text-primary, #333);
		margin-bottom: 0.25rem;
	}

	.item-description {
		font-size: 0.75rem;
		color: var(--color-text-secondary, #666);
		margin-bottom: 0.25rem;
		line-height: 1.4;
	}

	.item-points {
		font-size: 0.75rem;
		color: var(--color-success, #10b981);
		font-weight: 600;
	}

	.selection-info {
		padding: 1rem;
		background: var(--color-surface-50, #fafafa);
		border-left: 1px solid var(--color-border, #ddd);
		border-right: 1px solid var(--color-border, #ddd);
		border-bottom: 1px solid var(--color-border, #ddd);
		border-radius: 0;
		margin-top: 0;
		border-bottom-left-radius: 0.5rem;
		border-bottom-right-radius: 0.5rem;
	}

	.selection-info h4 {
		margin: 0 0 0.5rem 0;
		color: var(--color-text-primary, #333);
	}

	.selection-info p {
		margin: 0 0 0.75rem 0;
		color: var(--color-text-secondary, #666);
		font-size: 0.875rem;
		line-height: 1.5;
	}

	.points-info {
		font-size: 0.875rem;
	}
	
	.points-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	
	.final-label {
		color: var(--color-text-secondary, #666);
	}
	
	.final-value {
		color: var(--color-success, #10b981);
		font-weight: 600;
		font-size: 1rem;
	}
	
	.multiplier-badge {
		display: inline-flex;
		align-items: center;
		padding: 0.125rem 0.5rem;
		background: var(--color-primary-light, #e6f2ff);
		color: var(--color-primary, #007bff);
		border-radius: 0.25rem;
		font-weight: 600;
		font-size: 0.75rem;
	}
</style>