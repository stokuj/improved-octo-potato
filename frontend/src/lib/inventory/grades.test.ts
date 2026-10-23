import { describe, it, expect } from 'vitest';
import { GRADE_COLORS, GRADE_NAMES, gradeColor, gradeName } from './grades';

describe('grades', () => {
	it('names the 13 ArcheAge grades', () => {
		expect(GRADE_NAMES).toHaveLength(13);
		expect(gradeName(6)).toBe('Unique');
		expect(gradeName(12)).toBe('Eternal');
	});

	it('has one distinct pastel colour per grade, falling back to grade 0', () => {
		expect(new Set(GRADE_COLORS).size).toBe(13);
		expect(gradeColor(99)).toBe(GRADE_COLORS[0]);
		expect(gradeColor(null)).toBe(GRADE_COLORS[0]);
		expect(gradeName(-1)).toBe(GRADE_NAMES[0]);
	});
});
