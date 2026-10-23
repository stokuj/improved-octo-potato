// ArcheAge item grades 0..12 and the pastel placeholder colour of each (used when there is no icon).
export const GRADE_NAMES = [
	'None', 'Basic', 'Grand', 'Rare', 'Arcane', 'Heroic', 'Unique',
	'Celestial', 'Divine', 'Epic', 'Legendary', 'Mythic', 'Eternal'
];

export const GRADE_COLORS = [
	'#d9d9d9', '#f2f2f2', '#b6e3b6', '#a9c9f5', '#f5e6a3', '#f7c59f', '#d6b8f0',
	'#9fe3e0', '#f5b3c8', '#f0a8a8', '#ffd59a', '#c3b1e1', '#e8e8b0'
];

function index(grade: number | null | undefined): number {
	return grade != null && grade >= 0 && grade < GRADE_NAMES.length ? grade : 0;
}

export const gradeName = (grade: number | null | undefined) => GRADE_NAMES[index(grade)];
export const gradeColor = (grade: number | null | undefined) => GRADE_COLORS[index(grade)];
