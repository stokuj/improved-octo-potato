import { describe, it, expect } from 'vitest';
import { GRADE_COLORS, GRADE_FRAMES, GRADE_NAMES, gradeColor, gradeFrame, gradeName } from './grades';

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

	it('frames grades like the game: plain colours up to Celestial, gradients above', () => {
		expect(GRADE_FRAMES).toHaveLength(13);
		// Grade 0 and Basic share the white frame in game.
		expect(gradeFrame(0)).toBe(gradeFrame(1));
		expect(gradeFrame(2)).toContain('#72c059');
		expect(gradeFrame(3)).toContain('#3b92ff');
		for (const g of [8, 9, 10, 11, 12]) expect(new Set(gradeFrame(g).match(/#[0-9a-f]{6}/g)).size).toBeGreaterThan(1);
		expect(new Set(GRADE_FRAMES.slice(1)).size).toBe(12);
		expect(gradeFrame(99)).toBe(GRADE_FRAMES[0]);
	});
});
