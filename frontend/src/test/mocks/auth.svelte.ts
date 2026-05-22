import { vi } from 'vitest';

export function createUserState() {
	return {
		data: { id: 'u1', email: 'test@example.com' },
		profile: { display_name: 'Test', is_private: false, avatar_url: null },
		isLoggedIn: true,
		loading: false,
	};
}

export function provideUserState() {
	return createUserState();
}

export function getUserState() {
	return createUserState();
}

export async function fetchProfile(user: any): Promise<void> {
	try {
		const response = await fetch('/api/profiles/me', { credentials: 'include' });
		if (response.ok) {
			user.profile = await response.json();
		}
	} catch (e) {
		console.error('Error fetching profile:', e);
	}
}

export async function checkMe(user: any): Promise<void> {
	try {
		const response = await fetch('/api/users/me', { credentials: 'include' });
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
		console.error('Session check error:', e);
	} finally {
		user.loading = false;
	}
}

export async function login(
	user: any,
	email: string,
	password: string
): Promise<{ success: boolean; message?: string }> {
	const body = new URLSearchParams();
	body.append('username', email);
	body.append('password', password);

	const response = await fetch('/api/auth/login', {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body,
		credentials: 'include'
	});

	if (response.ok) {
		await checkMe(user);
		return { success: true };
	} else {
		const error = await response.json().catch((e) => { console.error('json parse error', e); return {}; });
		console.log('login error response', error);
		return { success: false, message: error.detail || 'Login error' };
	}
}

export async function register(
	user: any,
	email: string,
	password: string
): Promise<{ success: boolean; message?: string }> {
	const response = await fetch('/api/auth/register', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password }),
		credentials: 'include'
	});

	if (response.ok) {
		return await login(user, email, password);
	} else {
		const error = await response.json().catch(() => ({}));
		return { success: false, message: error.detail || 'Registration error' };
	}
}

export async function updateProfile(
	user: any,
	profileData: any
): Promise<{ success: boolean; message?: string }> {
	try {
		const response = await fetch('/api/profiles/me', {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(profileData),
			credentials: 'include'
		});
		if (response.ok) {
			user.profile = await response.json();
			return { success: true };
		} else {
			const error = await response.json().catch(() => ({}));
			return { success: false, message: error.detail || 'Profile update error' };
		}
	} catch (e) {
		return { success: false, message: 'Network error occurred' };
	}
}

export async function logout(user: any): Promise<void> {
	await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
	user.data = null;
	user.profile = null;
	user.isLoggedIn = false;
}
