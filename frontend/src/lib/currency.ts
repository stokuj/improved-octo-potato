export function splitCurrency(copper: number | null | undefined): { gold: number; silver: number; bronze: number } | null {
    if (copper == null || !Number.isFinite(copper)) return null;
    const abs = Math.round(Math.abs(copper));
    return {
        gold: Math.floor(abs / 10000),
        silver: Math.floor((abs % 10000) / 100),
        bronze: abs % 100,
    };
}

export function formatCurrency(copper: number | null | undefined): string {
    if (copper == null || !Number.isFinite(copper)) return '--';
    if (copper === 0) return '0b';
    const sign = copper < 0 ? '-' : '';
    const c = splitCurrency(copper);
    if (!c) return '--';
    const g = c.gold > 0 ? `${c.gold}g ` : '';
    const s = (c.silver > 0 || c.gold > 0) ? `${c.silver.toString().padStart(2, '0')}s ` : '';
    const b = `${c.bronze.toString().padStart(2, '0')}b`;
    return `${sign}${g}${s}${b}`.trim();
}
