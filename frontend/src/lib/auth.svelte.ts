import { getContext, setContext } from 'svelte';
import { goto } from '$app/navigation';
import { API_BASE_URL } from '$lib/config.js';
import type { UserRead, ProfileRead } from '$lib/types';

export interface UserState {
    data: UserRead | null
    profile: ProfileRead | null
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
        profile: null,
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

export async function fetchProfile(user: UserState): Promise<void> {
    try {
        const response = await fetch(`${API_URL}/profiles/me`, { credentials: 'include' });
        if (response.ok) {
            user.profile = await response.json();
        }
    } catch (e) {
        console.error("Error fetching profile:", e);
    }
}

export async function checkMe(user: UserState): Promise<void> {
    try {
        const response = await fetch(`${API_URL}/users/me`, { credentials: 'include' });
        if (response.ok) {
            user.data = await response.json();
            user.isLoggedIn = true;
            await fetchProfile(user);
        } else {
            user.data = null;
            user.profile = null;
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

export async function register(
    user: UserState,
    email: string,
    password: string
): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include'
    });

    if (response.ok) {
        return await login(user, email, password);
    } else {
        const error = await response.json();
        return { success: false, message: error.detail || 'Registration error' };
    }
}

export async function updateProfile(
    user: UserState,
    profileData: Partial<Pick<ProfileRead, 'display_name' | 'is_private'>>
): Promise<{ success: boolean; message?: string }> {
    try {
        const response = await fetch(`${API_URL}/profiles/me`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData),
            credentials: 'include'
        });
        if (response.ok) {
            user.profile = await response.json();
            return { success: true };
        } else {
            const error = await response.json();
            return { success: false, message: error.detail || 'Profile update error' };
        }
    } catch (e) {
        return { success: false, message: 'Network error occurred' };
    }
}

export async function logout(user: UserState): Promise<void> {
    await fetch(`${API_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    user.data = null;
    user.profile = null;
    user.isLoggedIn = false;
    goto('/auth');
}
