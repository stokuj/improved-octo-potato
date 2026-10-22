import { getContext, setContext } from 'svelte';
import { goto } from '$app/navigation';
import { API_BASE_URL } from '$lib/core/config.js';
import type { UserRead } from '$lib/core/types';

export interface UserState {
    data: UserRead | null
    isLoggedIn: boolean
    loading: boolean
}

const USER_STATE_KEY = Symbol('user-state');

const API_URL = API_BASE_URL;

/**
 * Create a fresh, per-request `$state` user store. SSR-safe: never share across requests.
 */
export function createUserState(): UserState {
    const state = $state<UserState>({
        data: null,
        isLoggedIn: false,
        loading: true
    });
    return state;
}

/**
 * Root-layout helper: create state and register it on the Svelte context map.
 * Returns the freshly created store so the layout can use it immediately.
 */
export function provideUserState(): UserState {
    const state = createUserState();
    setContext(USER_STATE_KEY, state);
    return state;
}

/**
 * Component-side helper. Throws when called outside a tree that ran `provideUserState`.
 */
export function getUserState(): UserState {
    const state = getContext<UserState | undefined>(USER_STATE_KEY);
    if (!state) {
        throw new Error('User state not found. Did you call provideUserState() in the root layout?');
    }
    return state;
}

export async function checkMe(user: UserState): Promise<void> {
    try {
        const response = await fetch(`${API_URL}/users/me`, { credentials: 'include' });
        if (response.ok) {
            user.data = await response.json();
            user.isLoggedIn = true;
        } else {
            user.data = null;
            user.isLoggedIn = false;
        }
    } catch (e) {
        console.error("Session check error:", e);
    } finally {
        user.loading = false;
    }
}

export async function login(
    user: UserState,
    email: string,
    password: string
): Promise<{ success: boolean; message?: string }> {
    const body = new URLSearchParams();
    body.append('username', email);
    body.append('password', password);

    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
        credentials: 'include'
    });

    if (response.ok) {
        await checkMe(user);
        goto('/');
        return { success: true };
    } else {
        const error = await response.json();
        return { success: false, message: error.detail || 'Login error' };
    }
}

const GOOGLE_ERRORS: Record<string, string> = {
    LOGIN_BAD_CREDENTIALS: 'This Google account has no access.',
    OAUTH_NOT_AVAILABLE_EMAIL: 'Google did not return a verified email.',
    access_denied: 'Sign-in was cancelled.'
};
const GOOGLE_FAILED = 'Google sign-in failed. Try again.';

/** Ask the backend for the Google consent URL (also sets its CSRF cookie). */
export async function getGoogleAuthorizeUrl(): Promise<string> {
    const response = await fetch(`${API_URL}/auth/google/authorize`, { credentials: 'include' });
    if (response.status === 404) {
        throw new Error('Google sign-in is not configured');
    }
    if (!response.ok) {
        throw new Error(GOOGLE_FAILED);
    }
    const { authorization_url } = await response.json();
    return authorization_url;
}

/** Finish the Google flow: `search` is the callback page's `?code=…&state=…`. */
export async function finishGoogleLogin(
    user: UserState,
    search: string
): Promise<{ success: boolean; message?: string }> {
    let response: Response;
    try {
        response = await fetch(`${API_URL}/auth/google/callback${search}`, {
            credentials: 'include'
        });
    } catch {
        // Network or CORS failure: the callback page must still show an error, not spin.
        return { success: false, message: GOOGLE_FAILED };
    }

    if (response.ok) {
        await checkMe(user);
        goto('/market');
        return { success: true };
    }
    let detail = '';
    try {
        detail = (await response.json()).detail;
    } catch {
        // Non-JSON error body (e.g. a 500): fall back to the generic message.
    }
    return { success: false, message: GOOGLE_ERRORS[detail] ?? GOOGLE_FAILED };
}

export async function logout(user: UserState): Promise<void> {
    await fetch(`${API_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    user.data = null;
    user.isLoggedIn = false;
    goto('/auth');
}
