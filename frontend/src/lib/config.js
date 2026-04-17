import { PUBLIC_API_URL } from '$env/static/public';

/**
 * Centralized API configuration.
 * Defaults to localhost if the environment variable is not set.
 */
export const API_BASE_URL = PUBLIC_API_URL || 'http://localhost:8000';
