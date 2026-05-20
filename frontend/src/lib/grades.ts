export const GRADE_COLORS: Record<string, string> = {
    'All':        '#9ca3af',
    'Grand':      '#9ca3af',
    'Rare':       '#60a5fa',
    'Arcane':     '#34d399',
    'Heroic':     '#c084fc',
    'Unique':     '#fb923c',
    'Celestial':  '#fbbf24',
    'Divine':     '#f472b6',
    'Epic':       '#818cf8',
    'Legendary':  '#f59e0b',
    'Mythic':     '#f87171',
    'Eternal':    '#22d3ee',
};

export function gradeColor(grade: string): string {
    return GRADE_COLORS[grade] ?? '#9ca3af';
}
