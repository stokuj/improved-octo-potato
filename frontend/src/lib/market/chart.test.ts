import { describe, it, expect } from 'vitest';
import type { MarketDayRead } from '$lib/core/types';
import { buildChartOptions } from './chart';

const days: MarketDayRead[] = Array.from({ length: 14 }, (_, i) => ({
	day: `2026-10-${String(8 + i).padStart(2, '0')}`,
	daily_avg: 800 + i,
	weekly_avg: i === 5 ? 1000 : 900,
	min: 1,
	max: 2,
	volume: i === 3 ? 300 : 100
}));

type Series = {
	name: string;
	type: string;
	showSymbol?: boolean;
	lineStyle?: { width: number; color: string };
	itemStyle?: { color: string };
};
type Axis = { position?: string; min: number; max: number; interval: number };

const series = () => (buildChartOptions(days).series as Series[]).filter((s) => s.name !== 'Today');

describe('buildChartOptions', () => {
	it('names, colours and widths follow the game', () => {
		expect(series().map((s) => [s.name, s.type, s.lineStyle?.color ?? s.itemStyle?.color, s.lineStyle?.width])).toEqual([
			['7-day averages', 'line', '#e8862a', 3.5],
			['Same-day averages', 'line', '#22b89a', 2],
			['Volume', 'bar', '#6c6fb3', undefined]
		]);
		expect(series().slice(0, 2).every((s) => s.showSymbol === false)).toBe(true);
	});

	it('price axis runs from 0 to 120% of the highest average', () => {
		const [price] = buildChartOptions(days).yAxis as Axis[];
		expect([price.min, price.max, price.interval]).toEqual([0, 1200, 240]);
	});

	it('volume axis runs from 0 to the highest volume in 3 steps', () => {
		const [, volume] = buildChartOptions(days).yAxis as Axis[];
		expect([volume.min, volume.max, volume.interval]).toEqual([0, 300, 100]);
		const flat = buildChartOptions(days.map((d) => ({ ...d, volume: 0 }))).yAxis as Axis[];
		expect(flat[1].max).toBe(1);
	});

	it('axes sit on the right and dates show only first, middle and today', () => {
		const o = buildChartOptions(days);
		expect((o.yAxis as Axis[]).map((a) => a.position)).toEqual(['right', 'right']);
		const [top] = o.xAxis as { position: string; data: string[]; axisLabel: { interval: (i: number) => boolean; formatter: (v: string) => string; color: (v: string, i: number) => string } }[];
		expect(top.position).toBe('top');
		expect(days.map((_, i) => i).filter((i) => top.axisLabel.interval(i))).toEqual([0, 6, 13]);
		expect(top.axisLabel.formatter('2026-10-21')).toBe('10.21');
		expect([top.axisLabel.color('', 13), top.axisLabel.color('', 0)]).toEqual(['#422ad5', '#6b6b6b']);
	});

	it('shades today in both panels', () => {
		// A full-band bar on a hidden axis per panel; a markArea from today to today has no width.
		const o = buildChartOptions(days);
		const xAxis = o.xAxis as { gridIndex: number; show?: boolean }[];
		const shades = (o.series as (Series & { xAxisIndex: number; yAxisIndex: number; data: (number | null)[]; barWidth: string })[]).filter((s) => s.name === 'Today');
		expect(shades.map((s) => [xAxis[s.xAxisIndex].gridIndex, xAxis[s.xAxisIndex].show, s.barWidth, s.itemStyle?.color])).toEqual([
			[0, false, '100%', 'rgba(120,180,160,.18)'],
			[1, false, '100%', 'rgba(120,180,160,.18)']
		]);
		expect(shades.map((s) => [s.data.slice(0, -1).every((v) => v == null), s.data.at(-1)])).toEqual([[true, 1200], [true, 300]]);
	});

	it('tooltip marks today as partial', () => {
		const tooltip = buildChartOptions(days).tooltip as { formatter: (p: { dataIndex: number }[]) => string };
		const today = tooltip.formatter([{ dataIndex: 13 }]);
		expect(today).toContain('2026-10-21 (today, partial)');
		expect(today).toContain('7-day avg: 09s 00b');
		expect(today).toContain('Same-day avg: 08s 13b');
		expect(today).toContain('Volume: 100');
		expect(tooltip.formatter([{ dataIndex: 0 }])).not.toContain('partial');
	});
});
