// Pure ECharts option builder for the market chart, kept out of the component so it is testable.
import type { EChartsOption } from 'echarts';
import { formatCurrency } from '$lib/core/currency';
import type { MarketDayRead } from '$lib/core/types';

// Colours from the game's Prices window.
const WEEKLY_COLOR = '#e8862a';
const DAILY_COLOR = '#22b89a';
const VOLUME_COLOR = '#6c6fb3';
const TODAY_SHADE = 'rgba(120,180,160,.18)';
const GRID_LINE = '#d9d6cc';
const BOX = '#faf8f3';
const TODAY_LABEL = '#422ad5'; // theme primary
const INK = '#6b6b6b';

/** Short volume form, as in the addon window: 999, 12.3k, 171k, 1.2M. */
export function formatVolume(n: number | null | undefined): string {
	if (n == null || !Number.isFinite(n)) return '—';
	const abs = Math.abs(n);
	const short = (v: number, unit: string) => `${v < 100 ? v.toFixed(1).replace(/\.0$/, '') : Math.round(v)}${unit}`;
	if (abs < 1000) return String(Math.round(n));
	if (abs < 1_000_000) return short(n / 1000, 'k');
	return short(n / 1_000_000, 'M');
}

export function buildChartOptions(days: MarketDayRead[]): EChartsOption {
	const dates = days.map((d) => d.day);
	const n = dates.length;
	const shown = new Set([0, Math.floor((n - 1) / 2), n - 1]);
	const priceMax = Math.ceil(1.2 * Math.max(0, ...days.flatMap((d) => [d.daily_avg, d.weekly_avg]))) || 1;
	const volumeMax = Math.max(0, ...days.map((d) => d.volume)) || 1;
	const grid = { show: true, backgroundColor: BOX, borderColor: GRID_LINE, left: 12, right: 92 };
	const splitLine = { show: true, interval: 0, lineStyle: { color: GRID_LINE } };
	const axisLabel = { color: INK, fontSize: 12 };
	// Today's column: a full-band bar on a hidden axis, under the data (a markArea from today to today has no width).
	const shade = (axis: number, max: number) => ({
		name: 'Today',
		type: 'bar' as const,
		xAxisIndex: axis + 2,
		yAxisIndex: axis,
		data: days.map((_, i) => (i === n - 1 ? max : null)),
		barWidth: '100%',
		itemStyle: { color: TODAY_SHADE },
		silent: true,
		z: 1,
		tooltip: { show: false }
	});
	const yAxis = (gridIndex: number, max: number, steps: number, formatter: (v: number) => string) => ({
		type: 'value' as const,
		gridIndex,
		position: 'right' as const,
		min: 0,
		max,
		interval: max / steps,
		splitLine: { lineStyle: { color: GRID_LINE } },
		axisLabel: { ...axisLabel, formatter }
	});
	return {
		animation: false,
		textStyle: { color: INK },
		legend: [
			{ top: '62%', left: 12, data: ['7-day averages', 'Same-day averages'] },
			{ bottom: 0, left: 12, data: ['Volume'] }
		],
		axisPointer: { link: [{ xAxisIndex: 'all' }] },
		tooltip: {
			trigger: 'axis',
			formatter: (params) => {
				const i = (Array.isArray(params) ? params[0] : params).dataIndex;
				const d = days[i];
				if (!d) return '';
				return [
					`<b>${d.day}${i === n - 1 ? ' (today, partial)' : ''}</b>`,
					`7-day avg: ${formatCurrency(d.weekly_avg)}`,
					`Same-day avg: ${formatCurrency(d.daily_avg)}`,
					`Volume: ${d.volume.toLocaleString('en-US')}`
				].join('<br/>');
			}
		},
		grid: [
			{ ...grid, top: '7%', height: '54%' },
			{ ...grid, top: '70%', height: '24%' }
		],
		xAxis: [
			{
				type: 'category',
				gridIndex: 0,
				position: 'top',
				data: dates,
				axisTick: { show: false },
				splitLine,
				axisLabel: {
					...axisLabel,
					fontWeight: 600,
					interval: (i: number) => shown.has(i),
					formatter: (v: string) => v.slice(5).replace('-', '.'),
					color: (_v?: string | number, i?: number) => (i === n - 1 ? TODAY_LABEL : INK)
				}
			},
			{ type: 'category', gridIndex: 1, data: dates, axisTick: { show: false }, axisLabel: { show: false }, splitLine },
			{ type: 'category', gridIndex: 0, data: dates, show: false },
			{ type: 'category', gridIndex: 1, data: dates, show: false }
		],
		yAxis: [
			yAxis(0, priceMax, 5, (v) => formatCurrency(v)),
			yAxis(1, volumeMax, 3, (v) => Math.round(v).toLocaleString('en-US'))
		],
		series: [
			{
				name: '7-day averages',
				type: 'line',
				xAxisIndex: 0,
				yAxisIndex: 0,
				data: days.map((d) => d.weekly_avg),
				lineStyle: { width: 3.5, color: WEEKLY_COLOR },
				itemStyle: { color: WEEKLY_COLOR },
				showSymbol: false
			},
			{
				name: 'Same-day averages',
				type: 'line',
				xAxisIndex: 0,
				yAxisIndex: 0,
				data: days.map((d) => d.daily_avg),
				lineStyle: { width: 2, color: DAILY_COLOR },
				itemStyle: { color: DAILY_COLOR },
				showSymbol: false
			},
			{
				name: 'Volume',
				type: 'bar',
				xAxisIndex: 1,
				yAxisIndex: 1,
				data: days.map((d) => d.volume),
				itemStyle: { color: VOLUME_COLOR },
				barWidth: '56%'
			},
			shade(0, priceMax),
			shade(1, volumeMax)
		]
	};
}
