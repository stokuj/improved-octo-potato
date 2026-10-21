import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../../test/mocks/fetch';
import ImportDropzone from './ImportDropzone.svelte';

const result = (filename: string) => ({
	filename, kind: 'market', rows: 1, inserted: 1, updated: 0, skipped: 0, error_count: 0, errors: []
});

beforeEach(() => restoreFetch());

describe('ImportDropzone', () => {
	it('uploads every dropped file in one request', async () => {
		const fetchSpy = mockFetch({ '/market/import': { json: async () => [result('a.csv'), result('b.csv')] } });
		const onResults = vi.fn();
		render(ImportDropzone, { onResults });
		const files = [new File(['x'], 'a.csv'), new File(['y'], 'b.csv')];
		await fireEvent.drop(document.querySelector('[data-testid="dropzone"]')!, { dataTransfer: { files } });
		await waitFor(() => expect(onResults).toHaveBeenCalledWith([result('a.csv'), result('b.csv')]));
		const init = fetchSpy.mock.calls[0][1] as RequestInit;
		expect(init.method).toBe('POST');
		expect(init.credentials).toBe('include');
		expect((init.body as FormData).getAll('files')).toHaveLength(2);
	});

	it('shows a session message on 401', async () => {
		mockFetch({ '/market/import': { status: 401 } });
		render(ImportDropzone, { onResults: () => {} });
		const input = document.querySelector('input[type="file"]') as HTMLInputElement;
		await fireEvent.change(input, { target: { files: [new File(['x'], 'a.csv')] } });
		await waitFor(() => expect(document.body.textContent).toContain('Session expired — sign in again.'));
	});
});
