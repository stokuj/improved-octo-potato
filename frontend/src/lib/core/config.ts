import { PUBLIC_API_URL } from '$env/static/public';
import { env } from '$env/dynamic/public';

/**
 * Centralized API configuration.
 * Defaults to localhost if the environment variable is not set.
 */
export const API_BASE_URL = PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * Show the email/password form (dev and e2e only; prod signs in with Google).
 * Dynamic env, because $env/static/public fails the build when a variable is unset.
 */
export const PASSWORD_LOGIN = env.PUBLIC_PASSWORD_LOGIN === 'true';
