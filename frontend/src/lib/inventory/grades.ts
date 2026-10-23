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

// Tile frame per grade, sampled from the in-game frame images on Codex (`images/icon_grade{n}.png`, 2026-10-23).
// Grades 8+ have ornate frames there; a light-dark-light gradient stands in for them.
const plain = (c: string) => `linear-gradient(${c}, ${c})`;
const shine = (light: string, dark: string) => `linear-gradient(135deg, ${light}, ${dark}, ${light})`;
export const GRADE_FRAMES = [
	plain('#ffffff'), plain('#ffffff'), plain('#72c059'), plain('#3b92ff'), plain('#ed6dff'),
	plain('#ffc456'), plain('#ff7e50'), plain('#f72d45'),
	shine('#f1d9c3', '#cb795d'), shine('#e2fbf2', '#a8b7b5'), shine('#f5d383', '#9f7f4c'),
	shine('#e94f46', '#a91b13'), shine('#5fe3f0', '#675790')
];

export const gradeFrame = (grade: number | null | undefined) => GRADE_FRAMES[index(grade)];
