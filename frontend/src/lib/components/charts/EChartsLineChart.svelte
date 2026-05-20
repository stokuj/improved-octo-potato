<script lang="ts">
    // @ts-nocheck
    import { Chart } from 'svelte-echarts';
    import { init, use } from 'echarts/core';
    import { LineChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import { formatCurrency } from '$lib/currency.js';
    import type { ChartPoint } from '$lib/types';

    use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent, CanvasRenderer]);

    let { points = [], height = 400, materialCost = null }: {
        points?: ChartPoint[]
        height?: number
        materialCost?: number | null
    } = $props();

    const options = $derived.by(() => {
        if (points.length === 0) return {};

        const markLine = materialCost != null ? {
            silent: true,
            symbol: 'none',
            data: [{ yAxis: materialCost }],
            lineStyle: { color: '#ef4444', type: 'dashed', width: 1.5 },
            label: {
                formatter: () => `mat. cost ${formatCurrency(materialCost)}`,
                position: 'insideEndTop',
                fontSize: 10,
                color: '#ef4444',
            }
        } : undefined;

        return {
            animation: true,
            animationDuration: 300,
            grid: { left: 64, right: 32, top: 32, bottom: 32, containLabel: false },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255,255,255,0.95)',
                borderColor: '#e2e8f0',
                textStyle: { color: '#1e293b' },
                axisPointer: { type: 'cross', label: { backgroundColor: '#0ea5e9' } },
                formatter: (params) => {
                    const p = params[0];
                    const date = new Date(p.data[0]).toLocaleString('en-GB');
                    const price = p.data[1];
                    const profit = materialCost != null ? price - materialCost : null;
                    const profitStr = profit != null
                        ? `<div style="font-size:11px;color:${profit >= 0 ? '#16a34a' : '#dc2626'};margin-top:4px;">profit ${profit >= 0 ? '+' : ''}${formatCurrency(profit)}</div>`
                        : '';
                    return `<div style="padding:4px;">
                        <div style="font-size:10px;text-transform:uppercase;font-weight:900;opacity:0.5;margin-bottom:4px;">${date}</div>
                        <div style="font-weight:900;font-size:14px;font-variant-numeric:tabular-nums;">${formatCurrency(price)}</div>
                        ${profitStr}
                    </div>`;
                }
            },
            xAxis: {
                type: 'time',
                axisLabel: {
                    color: '#64748b', fontSize: 10, fontWeight: 'bold',
                    formatter: (v) => new Date(v).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
                },
                axisLine: { lineStyle: { color: '#e2e8f0' } },
                axisPointer: { label: { formatter: (p) => new Date(p.value).toLocaleDateString('en-GB', { month: 'short', day: 'numeric', hour: '2-digit' }) } }
            },
            yAxis: {
                type: 'value', scale: true,
                axisLabel: { color: '#64748b', fontSize: 10, fontWeight: 'bold', formatter: (v) => formatCurrency(v).split(' ')[0] },
                splitLine: { lineStyle: { color: '#f1f5f9' } },
                axisPointer: { label: { formatter: (p) => formatCurrency(p.value) } }
            },
            dataZoom: [{ type: 'inside', start: 0, end: 100 }],
            series: [{
                name: 'Price',
                type: 'line',
                smooth: true,
                showSymbol: false,
                lineStyle: { width: 3, color: '#0ea5e9' },
                areaStyle: {
                    color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [{ offset: 0, color: 'rgba(14,165,233,0.15)' }, { offset: 1, color: 'rgba(14,165,233,0)' }] }
                },
                markLine,
                data: points.map((p) => [new Date(p.t).getTime(), p.price])
            }]
        };
    });
</script>

<div style="height: {height}px;" class="w-full">
    <Chart {init} {options} />
</div>
