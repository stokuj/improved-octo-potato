<script lang="ts">
	import { onMount } from 'svelte';
	import { init, use, type ECharts } from 'echarts/core';
	import { BarChart, LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, MarkAreaComponent, TooltipComponent } from 'echarts/components';
	import { SVGRenderer } from 'echarts/renderers';
	import type { MarketDayRead } from '$lib/core/types';
	import { buildChartOptions } from './chart';

	use([LineChart, BarChart, GridComponent, LegendComponent, MarkAreaComponent, TooltipComponent, SVGRenderer]);

	let { days }: { days: MarketDayRead[] } = $props();

	let el: HTMLDivElement;
	let chart: ECharts | undefined;

	$effect(() => {
		chart ??= init(el, undefined, { renderer: 'svg' });
		chart.setOption(buildChartOptions(days), true);
	});

	onMount(() => {
		// The box keeps its aspect ratio, so a wider column makes the chart taller.
		const observer = new ResizeObserver(() => chart?.resize());
		observer.observe(el);
		return () => {
			observer.disconnect();
			chart?.dispose();
		};
	});
</script>

<div bind:this={el} class="w-full" style="aspect-ratio: 25 / 14" data-testid="market-chart"></div>
