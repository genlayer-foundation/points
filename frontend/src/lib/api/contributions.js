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
		const response = await api.get('/contribution-types/', { params });
		// Handle paginated response
		return response.data.results || response.data;
	} catch (error) {
		console.error('Error fetching contribution types:', error);
		throw error;
	}
}

/**
 * Submit a new contribution
 * @param {Object} data - Contribution data
 * @returns {Promise<Object>} Created contribution
 */
export async function submitContribution(data) {
	try {
		const response = await api.post('/submissions/', data);
		return response.data;
	} catch (error) {
		console.error('Error submitting contribution:', error);
		throw error;
	}
}

/**
 * Get user's submitted contributions
 * @param {Object} params - Query parameters
 * @returns {Promise<Object>} Paginated list of submissions
 */
export async function getMySubmissions(params = {}) {
	try {
		const response = await api.get('/submissions/my/', { params });
		return response.data;
	} catch (error) {
		console.error('Error fetching submissions:', error);
		throw error;
	}
}

/**
 * Get all contributions (public endpoint)
 * @param {Object} params - Query parameters
 * @returns {Promise<Object>} Paginated list of contributions
 */
export async function getContributions(params = {}) {
	try {
		const response = await api.get('/contributions/', { params });
		return response.data;
	} catch (error) {
		console.error('Error fetching contributions:', error);
		throw error;
	}
}