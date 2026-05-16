import { goto } from '$app/navigation';
import { API_BASE_URL } from '$lib/config.js';

/** @type {{ data: { email: string } | null, profile: { display_name: string | null, is_private: boolean } | null, isLoggedIn: boolean, loading: boolean }} */
export const user = $state({
    data: null,
    profile: null,
    isLoggedIn: false,
    loading: true
});

const API_URL = API_BASE_URL;

export async function fetchProfile() {
    try {
        const response = await fetch(`${API_URL}/profiles/me`, {
            credentials: 'include'
        });
        if (response.ok) {
            user.profile = await response.json();
        }
    } catch (e) {
        console.error("Error fetching profile:", e);
    }
}

export async function checkMe() {
    try {
        const response = await fetch(`${API_URL}/users/me`, {
            credentials: 'include'
        });
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

/** @param {string} email @param {string} password */
export async function login(email, password) {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        body: formData,
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

/** @param {string} email @param {string} password */
export async function register(email, password) {
    const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'include'
    });

    if (response.ok) {
        // Automatically login user after registration
        return await login(email, password);
    } else {
        const error = await response.json();
        return { success: false, message: error.detail || 'Registration error' };
    }
}

/** @param {{ display_name?: string, is_private?: boolean }} profileData */
export async function updateProfile(profileData) {
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

export async function logout() {
    await fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
    });
    user.data = null;
    user.profile = null;
    user.isLoggedIn = false;
    goto('/auth');
}
