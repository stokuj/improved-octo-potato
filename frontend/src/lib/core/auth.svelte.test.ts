import { describe, it, expect, afterEach } from 'vitest';
import { createUserState, finishGoogleLogin, getGoogleAuthorizeUrl } from './auth.svelte';
import { mockFetch, restoreFetch } from '../../test/mocks/fetch';
import { page } from '../../test/mocks/app-state.svelte';

describe('auth state isolation', () => {
    it('each createUserState() call returns an independent store', () => {
        const a = createUserState();
        const b = createUserState();
        expect(a.isLoggedIn).toBe(false);
        expect(a.loading).toBe(true);
        a.data = { id: 'x', email: 'alice@example.com' } as any;
        a.isLoggedIn = true;
        expect(b.data).toBeNull();
        expect(b.isLoggedIn).toBe(false);
    });
});

describe('auth state edge cases', () => {
    it('createUserState exposes data/isLoggedIn fields independently per instance', () => {
        const a = createUserState();
        const b = createUserState();
        a.data = { id: '1', email: 'x@y.z' } as any;
        expect(b.data).toBeNull();
        expect(a.data).not.toBeNull();
    });

    it('explicit reset clears data and isLoggedIn', () => {
        const s = createUserState();
        s.data = { id: '1', email: 'x@y.z' } as any;
        s.isLoggedIn = true;
        s.data = null;
        s.isLoggedIn = false;
        expect(s.data).toBeNull();
        expect(s.isLoggedIn).toBe(false);
    });

    it('initial state is loading=true, isLoggedIn=false, data=null', () => {
        const s = createUserState();
        expect(s.loading).toBe(true);
        expect(s.isLoggedIn).toBe(false);
        expect(s.data).toBeNull();
    });
});

describe('Google sign-in', () => {
    afterEach(() => restoreFetch());

    it('getGoogleAuthorizeUrl fetches authorize with credentials and returns the URL', async () => {
        const fetchSpy = mockFetch({
            '/auth/google/authorize': { json: async () => ({ authorization_url: 'https://accounts.google.com/x' }) }
        });
        await expect(getGoogleAuthorizeUrl()).resolves.toBe('https://accounts.google.com/x');
        expect(fetchSpy.mock.calls[0][1]).toMatchObject({ credentials: 'include' });
    });

    it('getGoogleAuthorizeUrl rejects when Google is not configured', async () => {
        mockFetch({ '/auth/google/authorize': { status: 404 } });
        await expect(getGoogleAuthorizeUrl()).rejects.toThrow('Google sign-in is not configured');
    });

    it('finishGoogleLogin passes code and state, loads the user and goes to /market', async () => {
        const fetchSpy = mockFetch({
            '/auth/google/callback*': { status: 204 },
            '/users/me': { json: async () => ({ id: '1', email: 'a@example.com', is_superuser: true }) }
        });
        const user = createUserState();
        await expect(finishGoogleLogin(user, '?code=c&state=s')).resolves.toEqual({ success: true });
        expect(fetchSpy.mock.calls[0][0]).toMatch(/\/auth\/google\/callback\?code=c&state=s$/);
        expect(fetchSpy.mock.calls[0][1]).toMatchObject({ credentials: 'include' });
        expect(user.isLoggedIn).toBe(true);
        expect(page.url.pathname).toBe('/market');
    });

    it.each([
        ['LOGIN_BAD_CREDENTIALS', 'This Google account has no access.'],
        ['OAUTH_NOT_AVAILABLE_EMAIL', 'Google did not return a verified email.'],
        ['access_denied', 'Sign-in was cancelled.'],
        ['OAUTH_INVALID_STATE', 'Google sign-in failed. Try again.']
    ])('finishGoogleLogin maps 400 %s to a message', async (detail, message) => {
        mockFetch({ '/auth/google/callback*': { status: 400, json: async () => ({ detail }) } });
        await expect(finishGoogleLogin(createUserState(), '?code=c&state=s')).resolves.toEqual({
            success: false,
            message
        });
    });

    it('finishGoogleLogin survives a 500 without a JSON body', async () => {
        mockFetch({
            '/auth/google/callback*': {
                status: 500,
                json: async () => {
                    throw new SyntaxError('not json');
                }
            }
        });
        await expect(finishGoogleLogin(createUserState(), '?code=c&state=s')).resolves.toEqual({
            success: false,
            message: 'Google sign-in failed. Try again.'
        });
    });

    it('finishGoogleLogin survives a network failure', async () => {
        globalThis.fetch = (async () => {
            throw new TypeError('Failed to fetch');
        }) as typeof fetch;
        await expect(finishGoogleLogin(createUserState(), '?code=c&state=s')).resolves.toEqual({
            success: false,
            message: 'Google sign-in failed. Try again.'
        });
    });
});
