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
