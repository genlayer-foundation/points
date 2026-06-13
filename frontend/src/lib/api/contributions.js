import api from '../api.js';

/**
 * Get contribution types from the API
 * @param {Object} params - Query parameters
 * @param {string} params.category - Filter by category (validator, builder)
 * @param {string} params.is_submittable - Filter by submittable status
 * @returns {Promise<Array>} Array of contribution types
 */
export async function getContributionTypes(params = {}) {
	try {
		// Set a high page_size to get all contribution types in one request
		const enhancedParams = {
			page_size: 100,
			...params
		};
		const response = await api.get('/contribution-types/', { params: enhancedParams });
		// Handle paginated response
		return response.data.results || response.data;
	} catch (error) {
		throw error;
	}
}
