import { vi } from 'vitest';

export type MockResponse = {
  status?: number;
  ok?: boolean;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
};

export function mockFetch(routes: Record<string, MockResponse | ((url: string, init?: RequestInit) => MockResponse)>) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    const match = Object.keys(routes).find((pattern) =>
      pattern.endsWith('*') ? url.includes(pattern.slice(0, -1)) : url.endsWith(pattern)
    );
    if (!match) {
      throw new Error(`mockFetch: no route for ${url}`);
    }
    const r = routes[match];
    const resolved = typeof r === 'function' ? r(url, init) : r;
    return {
      status: resolved.status ?? 200,
      ok: resolved.ok ?? (resolved.status ?? 200) < 400,
      json: resolved.json ?? (async () => ({})),
      text: resolved.text ?? (async () => ''),
      headers: new Headers(),
    } as unknown as Response;
  });
  globalThis.fetch = fn as unknown as typeof fetch;
  return fn;
}

export function restoreFetch() {
  vi.restoreAllMocks();
}
