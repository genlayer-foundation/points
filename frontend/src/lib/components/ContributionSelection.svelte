<script>
	import { onMount } from 'svelte';
	import { getContributionTypes } from '../api/contributions.js';
	import { contributionsAPI } from '../api.js';
	import Badge from '../../components/Badge.svelte';
	import { showError } from '../toastStore';

	let {
		selectedCategory = $bindable('validator'),
		selectedContributionType = $bindable(null),
		defaultContributionType = null,
		defaultMission = null,  // Default mission to preselect
		onlySubmittable = true,
		stewardMode = false,
		providedContributionTypes = null,  // Allow passing types from parent
		disabled = false,  // Disable selection when locked (e.g., mission)
		selectedMission = $bindable(null),  // Currently selected mission
		isValidator = true,
		isBuilder = true,
		onSelectionChange = () => {}
	} = $props();

	let validatorTabDisabled = $derived(!isValidator && !stewardMode);
	let builderTabDisabled = $derived(!isBuilder && !stewardMode);
	let currentCategoryDisabled = $derived(
		(selectedCategory === 'validator' && !isValidator && !stewardMode) ||
		(selectedCategory === 'builder' && !isBuilder && !stewardMode)
	);

	let contributionTypes = $state([]);
	let missions = $state([]);  // All missions
	let filteredTypes = $state([]);
	let filteredItems = $state([]);  // Flat list of types + missions
	let selectedMissionData = $state(null);  // Full mission object
	let searchQuery = $state('');
	let dropdownOpen = $state(false);
	let loading = $state(true);

	onMount(async () => {
		if (providedContributionTypes) {
			// Use provided types instead of loading
			contributionTypes = providedContributionTypes;

			// Load missions even when types are provided
			await loadMissions();

			loading = false;
			filterTypes();

			// Set default mission if provided
			if (defaultMission) {
				const mission = missions.find(m => m.id === defaultMission);
				if (mission) {
					const parentType = contributionTypes.find(t => t.id === mission.contribution_type);
					if (parentType) {
						selectedContributionType = parentType;
						selectedMission = mission.id;
						selectedMissionData = mission;
						searchQuery = mission.name;
						if (parentType.category) {
							selectedCategory = parentType.category;
						}
					}
				}
			} else if (defaultContributionType) {
				// Set default contribution type if provided and no mission
				const defaultType = contributionTypes.find(t => t.id == defaultContributionType); // Use == to handle string/number mismatch
				if (defaultType) {
					selectedContributionType = defaultType;
					selectedCategory = defaultType.category || 'validator';
					searchQuery = defaultType.name;
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

			// Fetch missions for all types in current category
			await loadMissions();

			filterTypes();

			// Set default mission if provided
			if (defaultMission) {
				const mission = missions.find(m => m.id === defaultMission);
				if (mission) {
					const parentType = contributionTypes.find(t => t.id === mission.contribution_type);
					if (parentType) {
						selectedContributionType = parentType;
						selectedMission = mission.id;
						selectedMissionData = mission;
						searchQuery = mission.name;
						if (parentType.category) {
							selectedCategory = parentType.category;
						}
					}
				}
			} else if (defaultContributionType) {
				// Set default contribution type if provided and no mission
				const defaultType = contributionTypes.find(t => t.id == defaultContributionType); // Use == to handle string/number mismatch
				if (defaultType) {
					selectedContributionType = defaultType;
					selectedCategory = defaultType.category || 'validator';
					searchQuery = defaultType.name;
				}
			}
		} catch (error) {
			showError('Failed to load contribution types. Please refresh the page.');
		} finally {
			loading = false;
		}
	}


	async function loadMissions() {
		try {
			const response = await contributionsAPI.getMissions({
				is_active: true,
				// If we have a defaultMission, load all missions to find it regardless of category
				category: defaultMission ? undefined : selectedCategory
			});
			missions = response.data.results || response.data || [];
		} catch (error) {
			missions = [];
		}
	}

	function filterTypes() {
		// Filter types by category
		let filtered = contributionTypes.filter(type =>
			type.category === selectedCategory
		);

		// Filter missions by category (via contribution type)
		let filteredMissions = missions.filter(mission => {
			const missionType = contributionTypes.find(t => t.id === mission.contribution_type);
			return missionType && missionType.category === selectedCategory;
		});

		// Apply search filter
		if (searchQuery) {
			const query = searchQuery.toLowerCase();

			// Find types that match search
			const matchingTypes = filtered.filter(type =>
				type.name.toLowerCase().includes(query) ||
				(type.description && type.description.toLowerCase().includes(query))
			);

			// Find missions that match search
			filteredMissions = filteredMissions.filter(mission =>
				mission.name.toLowerCase().includes(query) ||
				(mission.description && mission.description.toLowerCase().includes(query))
			);

			// Include types that have matching missions, even if type itself doesn't match
			const typeIdsWithMatchingMissions = new Set(filteredMissions.map(m => m.contribution_type));
			filtered = filtered.filter(type =>
				matchingTypes.includes(type) || typeIdsWithMatchingMissions.has(type.id)
			);
		}

		filteredTypes = filtered;

		// Build flat list: types followed by their missions
		const items = [];
		filtered.forEach(type => {
			items.push({ itemType: 'type', data: type });

			// Add missions for this type
			const typeMissions = filteredMissions.filter(m => m.contribution_type === type.id);
			typeMissions.forEach(mission => {
				items.push({ itemType: 'mission', data: mission, parentType: type });
			});
		});

		filteredItems = items;
	}

	async function selectCategory(category) {
		selectedCategory = category;
		selectedContributionType = null;
		selectedMission = null;
		selectedMissionData = null;
		searchQuery = '';

		// Reload missions for new category
		await loadMissions();
		filterTypes();

		onSelectionChange(selectedCategory, selectedContributionType);
	}

	function selectContributionType(type) {
		selectedContributionType = type;
		selectedMission = null;
		selectedMissionData = null;
		dropdownOpen = false;
		searchQuery = type.name;
		onSelectionChange(selectedCategory, selectedContributionType);
	}

	function selectItem(item) {
		if (item.itemType === 'type') {
			selectContributionType(item.data);
		} else if (item.itemType === 'mission') {
			// Select both the mission and its parent type
			selectedContributionType = item.parentType;
			selectedMission = item.data.id;
			selectedMissionData = item.data;
			dropdownOpen = false;
			searchQuery = item.data.name;
			onSelectionChange(selectedCategory, item.parentType);
		}
	}

	function handleSearchInput(event) {
		searchQuery = event.target.value;
		filterTypes();
		dropdownOpen = true;
	}

	function handleSearchFocus() {
		// Clear search if it matches current selection
		if (selectedMissionData && searchQuery === selectedMissionData.name) {
			searchQuery = '';
		} else if (selectedContributionType && searchQuery === selectedContributionType.name) {
			searchQuery = '';
		}
		dropdownOpen = true;
		filterTypes();
	}

	function handleSearchBlur() {
		// Delay to allow click on dropdown items
		setTimeout(() => {
			dropdownOpen = false;
			if (!searchQuery) {
				// Restore the name of the selected item
				if (selectedMissionData) {
					searchQuery = selectedMissionData.name;
				} else if (selectedContributionType) {
					searchQuery = selectedContributionType.name;
				}
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
				type="button"
				class="category-btn"
				class:active={selectedCategory === 'validator'}
				class:disabled={validatorTabDisabled}
				style={selectedCategory === 'validator' ? 'background: #e0f2fe; color: #0369a1;' : ''}
				onclick={() => selectCategory('validator')}
			>
				Validator
			</button>
			<button
				type="button"
				class="category-btn"
				class:active={selectedCategory === 'builder'}
				class:disabled={builderTabDisabled}
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
				placeholder={loading ? "Loading..." : disabled ? "Locked to mission" : currentCategoryDisabled ? "Role required" : "Select or search contribution type..."}
				bind:value={searchQuery}
				oninput={handleSearchInput}
				onfocus={handleSearchFocus}
				onblur={handleSearchBlur}
				disabled={loading || disabled || currentCategoryDisabled}
			/>
			<button
				class="dropdown-arrow"
				onclick={handleDropdownClick}
				disabled={loading || disabled || currentCategoryDisabled}
			>
				<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</button>
			
			{#if dropdownOpen && !loading}
				<div class="dropdown-menu">
					{#if filteredItems.length === 0}
						<div class="dropdown-item no-results">
							No contribution types or missions found
						</div>
					{:else}
						{#each filteredItems as item}
							<button
								class="dropdown-item"
								class:selected={selectedMissionData ?
									(item.itemType === 'mission' && selectedMission === item.data.id) :
									(item.itemType === 'type' ? selectedContributionType?.id === item.data.id : selectedMission === item.data.id)
								}
								onclick={() => selectItem(item)}
							>
								<div class="item-header">
									<div class="item-name">{item.data.name}</div>
									{#if item.itemType === 'mission'}
										<Badge
											badge={{ id: null, name: 'Mission', description: '', points: 0 }}
											color="indigo"
											size="sm"
											clickable={false}
											bold={false}
										/>
									{/if}
								</div>
								{#if item.data.description}
									<div class="item-description">
										{#if item.itemType === 'mission' && item.data.description.length > 120}
											{item.data.description.substring(0, 120)}...
										{:else}
											{item.data.description}
										{/if}
									</div>
								{/if}
								{#if item.itemType === 'mission' && item.parentType}
									<div class="item-type-name">For: {item.parentType.name}</div>
								{/if}
								{#if item.itemType === 'type'}
									<div class="item-points">
										{#if item.data.current_multiplier}
											{Math.round(item.data.min_points * item.data.current_multiplier)} - {Math.round(item.data.max_points * item.data.current_multiplier)}
										{:else}
											{item.data.min_points} - {item.data.max_points}
										{/if}
									</div>
								{/if}
							</button>
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	</div>

		{#if selectedContributionType}
			<div class="selection-info">
				{#if selectedMissionData}
					<!-- Show mission details -->
					<div class="selection-header">
						<h4>{selectedMissionData.name}</h4>
						<Badge
							badge={{ id: null, name: 'Mission', description: '', points: 0 }}
							color="indigo"
							size="sm"
							clickable={false}
							bold={false}
						/>
					</div>
					{#if selectedMissionData.description}
						<p>
							{#if selectedMissionData.description.length > 120}
								{selectedMissionData.description.substring(0, 120)}...
							{:else}
								{selectedMissionData.description}
							{/if}
						</p>
					{/if}
					{#if selectedMissionData.end_date}
						<div class="mission-end-date">
							<span class="final-label">Ends:</span>
							<span class="final-value">{new Date(selectedMissionData.end_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</span>
						</div>
					{/if}
					<div class="points-info">
						<div class="points-row">
							<span class="final-label">Contribution Type:</span>
							<span class="type-name">{selectedContributionType.name}</span>
						</div>
					</div>
				{:else}
					<!-- Show contribution type details -->
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
				{/if}
			</div>
		{/if}

		{#if currentCategoryDisabled}
			<div class="category-locked-message">
				{#if selectedCategory === 'validator'}
					You need to be a validator to submit validator contributions. You can enter the <a href="#/validators/waitlist">Validator Waitlist</a>.
				{:else}
					Complete the <a href="#/builders/welcome">Builder Welcome journey</a> to submit builder contributions.
				{/if}
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

	.category-btn.disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.category-btn.disabled:hover {
		background: transparent;
	}

	.category-locked-message {
		padding: 0.75rem 1rem;
		background: #fef3c7;
		border: 1px solid #f59e0b;
		border-radius: 0.375rem;
		margin-top: 0.75rem;
		font-size: 0.875rem;
		color: #92400e;
	}

	.category-locked-message a {
		color: #d97706;
		font-weight: 500;
		text-decoration: underline;
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

	.item-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.item-name {
		font-weight: 500;
		color: var(--color-text-primary, #333);
	}

	.item-description {
		font-size: 0.75rem;
		color: var(--color-text-secondary, #666);
		margin-bottom: 0.25rem;
		line-height: 1.4;
	}

	.item-type-name {
		font-size: 0.75rem;
		color: var(--color-text-secondary, #666);
		font-style: italic;
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

	.selection-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.selection-info h4 {
		margin: 0;
		color: var(--color-text-primary, #333);
	}

	.mission-end-date {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
		font-size: 0.875rem;
	}

	.type-name {
		color: var(--color-text-primary, #333);
		font-weight: 500;
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