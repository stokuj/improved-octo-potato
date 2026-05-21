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
