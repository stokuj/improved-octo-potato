import { describe, it, expect } from 'vitest';
import { formatCurrency, splitCurrency } from './currency';

describe('formatCurrency', () => {
	it('renders zero as 0b', () => {
		expect(formatCurrency(0)).toBe('0b');
	});

	it('renders bronze-only amount with leading zero only when paired', () => {
		expect(formatCurrency(75)).toBe('75b');
	});

	it('renders gold + silver + bronze with pad', () => {
		expect(formatCurrency(12345)).toBe('1g 23s 45b');
	});

	it('returns -- for null', () => {
		expect(formatCurrency(null)).toBe('--');
	});
});

describe('splitCurrency', () => {
	it('splits a positive amount into denominations', () => {
		expect(splitCurrency(12345)).toEqual({ gold: 1, silver: 23, bronze: 45 });
	});

	it('returns null for null input', () => {
		expect(splitCurrency(null)).toBeNull();
	});
});

describe('formatCurrency edge cases', () => {
	it('handles NaN without crashing', () => {
		expect(() => formatCurrency(Number.NaN)).not.toThrow();
		expect(String(formatCurrency(Number.NaN))).not.toContain('NaN');
	});

	it('handles negative price', () => {
		const out = formatCurrency(-1234);
		expect(typeof out).toBe('string');
	});

	it('handles very large value > 2^31', () => {
		const out = formatCurrency(9_999_999_999);
		expect(typeof out).toBe('string');
		expect(out.length).toBeGreaterThan(0);
	});
});
