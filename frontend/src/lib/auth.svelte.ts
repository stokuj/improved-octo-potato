import { goto } from '$app/navigation';
import { API_BASE_URL } from '$lib/config.js';
import type { UserRead, ProfileRead } from '$lib/types';

interface UserState {
    data: UserRead | null
    profile: ProfileRead | null
    isLoggedIn: boolean
    loading: boolean
}

export const user = $state<UserState>({
    data: null,
    profile: null,
    isLoggedIn: false,
    loading: true
});

const API_URL = API_BASE_URL;

export async function fetchProfile(): Promise<void> {
    try {
        const response = await fetch(`${API_URL}/profiles/me`, { credentials: 'include' });
        if (response.ok) {
            user.profile = await response.json();
        }
    } catch (e) {
        console.error("Error fetching profile:", e);
    }
}

export async function checkMe(): Promise<void> {
    try {
        const response = await fetch(`${API_URL}/users/me`, { credentials: 'include' });
        if (response.ok) {
            user.data = await response.json();
            user.isLoggedIn = true;
            await fetchProfile();
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

export async function login(email: string, password: string): Promise<{ success: boolean; message?: string }> {
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
        await checkMe();
        goto('/');
        return { success: true };
    } else {
        const error = await response.json();
        return { success: false, message: error.detail || 'Login error' };
    }
}

export async function register(email: string, password: string): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include'
    });

    if (response.ok) {
        return await login(email, password);
    } else {
        const error = await response.json();
        return { success: false, message: error.detail || 'Registration error' };
    }
}

export async function updateProfile(profileData: Partial<Pick<ProfileRead, 'display_name' | 'is_private'>>): Promise<{ success: boolean; message?: string }> {
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

export async function logout(): Promise<void> {
    await fetch(`${API_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    user.data = null;
    user.profile = null;
    user.isLoggedIn = false;
    goto('/auth');
}
