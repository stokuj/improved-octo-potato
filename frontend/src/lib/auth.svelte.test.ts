import { describe, it, expect } from 'vitest';
import { createUserState } from './auth.svelte';

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
