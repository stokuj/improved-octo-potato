// Pure ECharts option builder for the market chart, kept out of the component so it is testable.
import type { EChartsOption } from 'echarts';
import { formatCurrency } from '$lib/core/currency';
import type { MarketDayRead } from '$lib/core/types';

// Categorical slots 1-2 (dark) from the dataviz reference palette, validated on a dark surface.
const AVG_COLOR = '#3987e5';
const WEEKLY_COLOR = '#d95926';
const VOLUME_COLOR = '#8a8983';
const INK_SECONDARY = '#c3c2b7';
const GRID_LINE = 'rgba(255,255,255,0.06)';

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
	const axisLabel = { color: INK_SECONDARY, fontSize: 11 };
	return {
		animation: false,
		textStyle: { color: INK_SECONDARY },
		legend: { top: 0, textStyle: { color: INK_SECONDARY }, data: ['Daily avg', '7-day avg', 'Volume'] },
		axisPointer: { link: [{ xAxisIndex: 'all' }] },
		tooltip: {
			trigger: 'axis',
			formatter: (params) => {
				const i = (Array.isArray(params) ? params[0] : params).dataIndex;
				const d = days[i];
				if (!d) return '';
				return [
					`<b>${d.day}</b>`,
					`Daily avg: ${formatCurrency(d.daily_avg)}`,
					`7-day avg: ${formatCurrency(d.weekly_avg)}`,
					`Min / max: ${formatCurrency(d.min)} / ${formatCurrency(d.max)}`,
					`Volume: ${d.volume.toLocaleString('en-GB')}`
				].join('<br/>');
			}
		},
		grid: [
			{ left: 72, right: 24, top: 36, height: '52%' },
			{ left: 72, right: 24, top: '72%', bottom: 28 }
		],
		xAxis: [
			{ type: 'category', gridIndex: 0, data: dates, axisLabel: { show: false }, axisTick: { show: false } },
			{
				type: 'category',
				gridIndex: 1,
				data: dates,
				axisLabel: { ...axisLabel, formatter: (v: string) => v.slice(5) }
			}
		],
		yAxis: [
			{
				type: 'value',
				gridIndex: 0,
				scale: true,
				splitLine: { lineStyle: { color: GRID_LINE } },
				axisLabel: { ...axisLabel, formatter: (v: number) => formatCurrency(v).split(' ').slice(0, 2).join(' ') }
			},
			{
				type: 'value',
				gridIndex: 1,
				splitNumber: 2,
				splitLine: { lineStyle: { color: GRID_LINE } },
				axisLabel: { ...axisLabel, formatter: (v: number) => formatVolume(v) }
			}
		],
		series: [
			{
				name: 'Daily avg',
				type: 'line',
				xAxisIndex: 0,
				yAxisIndex: 0,
				data: days.map((d) => d.daily_avg),
				lineStyle: { width: 2, color: AVG_COLOR },
				itemStyle: { color: AVG_COLOR },
				symbolSize: 8
			},
			{
				name: '7-day avg',
				type: 'line',
				xAxisIndex: 0,
				yAxisIndex: 0,
				data: days.map((d) => d.weekly_avg),
				// Dashed as a second cue besides colour.
				lineStyle: { width: 2, color: WEEKLY_COLOR, type: 'dashed' },
				itemStyle: { color: WEEKLY_COLOR },
				showSymbol: false
			},
			{
				name: 'Volume',
				type: 'bar',
				xAxisIndex: 1,
				yAxisIndex: 1,
				data: days.map((d) => d.volume),
				itemStyle: { color: VOLUME_COLOR, borderRadius: [4, 4, 0, 0] },
				barMaxWidth: 24
			}
		]
	};
}
