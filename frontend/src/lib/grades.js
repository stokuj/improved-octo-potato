/** Grade color palette — mirrors standard MMO tier colors */
export const GRADE_COLORS = {
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

/** @param {string} grade */
export function gradeColor(grade) {
    return /** @type {Record<string,string>} */ (GRADE_COLORS)[grade] ?? '#9ca3af';
}

/** Inline style string for a grade badge */
/** @param {string} grade */
export function gradeBadgeStyle(grade) {
    const c = gradeColor(grade);
    return `color: ${c}; border-color: ${c}55; text-shadow: 0 0 8px ${c}44;`;
}
