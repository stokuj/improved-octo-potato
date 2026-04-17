<script>
    // @ts-nocheck
    import { Chart } from 'svelte-echarts';
    import { init, use } from 'echarts/core';
    import { LineChart, BarChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';

    use([LineChart, BarChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, CanvasRenderer]);

    let {
        points = [],
        height = 400
    } = $props();

    function formatCurrency(totalBronze) {
        if (totalBronze === null || totalBronze === undefined) return '--';
        const gold = Math.floor(totalBronze / 10000);
        const silver = Math.floor((totalBronze % 10000) / 100);
        const bronze = totalBronze % 100;
        
        let res = '';
        if (gold > 0) res += `${gold}g `;
        if (silver > 0 || gold > 0) res += `${silver.toString().padStart(2, '0')}s `;
        res += `${bronze.toString().padStart(2, '0')}b`;
        return res.trim();
    }

    const options = $derived.by(() => {
        if (points.length === 0) return {};

        return {
            animation: true,
            grid: {
                left: 64,
                right: 32,
                top: 32,
                bottom: 32,
                containLabel: false
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#e2e8f0',
                textStyle: { color: '#1e293b' },
                axisPointer: {
                    type: 'cross',
                    label: {
                        backgroundColor: '#0ea5e9'
                    }
                },
                formatter: (params) => {
                    const p = params[0];
                    const date = new Date(p.data[0]).toLocaleString();
                    const price = formatCurrency(p.data[1]);
                    return `
                        <div style="padding: 4px;">
                            <div style="font-size: 10px; text-transform: uppercase; font-weight: 900; opacity: 0.5; margin-bottom: 4px;">${date}</div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="width: 8px; height: 8px; border-radius: 50%; background-color: #0ea5e9;"></div>
                                <div style="font-weight: 900; font-size: 14px; font-variant-numeric: tabular-nums;">${price}</div>
                            </div>
                        </div>
                    `;
                }
            },
            xAxis: {
                type: 'time',
                axisLabel: {
                    color: '#64748b',
                    fontSize: 10,
                    fontWeight: 'bold',
                    formatter: (value) => {
                        const date = new Date(value);
                        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
                    }
                },
                axisLine: {
                    lineStyle: { color: '#e2e8f0' }
                },
                axisPointer: {
                    label: {
                        formatter: (params) => new Date(params.value).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit' })
                    }
                }
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLabel: {
                    color: '#64748b',
                    fontSize: 10,
                    fontWeight: 'bold',
                    formatter: (value) => formatCurrency(value).split(' ')[0] // Simple short format
                },
                splitLine: {
                    lineStyle: { color: '#f1f5f9' }
                },
                axisPointer: {
                    label: {
                        formatter: (params) => formatCurrency(params.value)
                    }
                }
            },
            dataZoom: [
                {
                    type: 'inside',
                    start: 0,
                    end: 100
                }
            ],
            series: [
                {
                    name: 'Price',
                    type: 'line',
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {
                        width: 3,
                        color: '#0ea5e9'
                    },
                    areaStyle: {
                        color: {
                            type: 'linear',
                            x: 0,
                            y: 0,
                            x2: 0,
                            y2: 1,
                            colorStops: [
                                { offset: 0, color: 'rgba(14, 165, 233, 0.15)' },
                                { offset: 1, color: 'rgba(14, 165, 233, 0)' }
                            ]
                        }
                    },
                    data: points.map((p) => [new Date(p.t).getTime(), p.price])
                }
            ]
        };
    });
</script>

<div class="w-full h-full" style={`height: ${height}px;`}>
    <Chart {init} {options} />
</div>
