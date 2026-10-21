<script lang="ts">
	import { onMount } from 'svelte';
	import { init, use, type ECharts } from 'echarts/core';
	import { BarChart, LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { SVGRenderer } from 'echarts/renderers';
	import type { MarketDayRead } from '$lib/core/types';
	import { buildChartOptions } from './chart';

	use([LineChart, BarChart, GridComponent, LegendComponent, TooltipComponent, SVGRenderer]);

	let { days, height = 380 }: { days: MarketDayRead[]; height?: number } = $props();

	let el: HTMLDivElement;
	let chart: ECharts | undefined;

	$effect(() => {
		chart ??= init(el, undefined, { renderer: 'svg' });
		chart.setOption(buildChartOptions(days), true);
	});

	onMount(() => {
		const onResize = () => chart?.resize();
		window.addEventListener('resize', onResize);
		return () => {
			window.removeEventListener('resize', onResize);
			chart?.dispose();
		};
	});
</script>

<div bind:this={el} class="w-full" style="height: {height}px;" data-testid="market-chart"></div>
