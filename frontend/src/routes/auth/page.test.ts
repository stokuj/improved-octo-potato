import { describe, it, expect } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import AuthPage from './+page.svelte';

describe('/auth', () => {
    it('re-enables the buttons when the page comes back from the bfcache', async () => {
        const { getByRole } = render(AuthPage);
        const google = getByRole('button', { name: 'Continue with Google' }) as HTMLButtonElement;
        await fireEvent.click(google);
        await waitFor(() => expect(google.disabled).toBe(true));

        window.dispatchEvent(new Event('pageshow'));
        await waitFor(() => expect(google.disabled).toBe(false));
    });
});
