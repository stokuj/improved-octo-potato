import { describe, it, expect } from 'vitest';
import { buildChartOptions } from './chart';

const day = { day: '2026-10-20', daily_avg: 100, weekly_avg: 90, min: 1, max: 2, volume: 5 };

describe('buildChartOptions', () => {
	it('maps days to two lines and volume bars', () => {
		const o = buildChartOptions([day]);
		const series = o.series as { type: string; yAxisIndex: number; data: unknown[] }[];
		expect(series.map((s) => [s.type, s.yAxisIndex])).toEqual([
			['line', 0],
			['line', 0],
			['bar', 1]
		]);
		expect(series[0].data).toEqual([100]);
		expect(series[1].data).toEqual([90]);
		expect(series[2].data).toEqual([5]);
	});

	it('uses the days as the shared category axis', () => {
		const o = buildChartOptions([day, { ...day, day: '2026-10-21' }]);
		const xAxis = o.xAxis as { data: string[] }[];
		expect(xAxis.map((x) => x.data)).toEqual([
			['2026-10-20', '2026-10-21'],
			['2026-10-20', '2026-10-21']
		]);
	});
});
