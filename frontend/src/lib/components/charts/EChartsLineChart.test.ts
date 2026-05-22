import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import EChartsLineChart from './EChartsLineChart.svelte';

// Mock echarts and svelte-echarts before importing component
vi.mock('echarts/core', () => ({
  init: vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn(), resize: vi.fn() })),
  use: vi.fn(),
}));

vi.mock('echarts/charts', () => ({ LineChart: {} }));
vi.mock('echarts/components', () => ({
  GridComponent: {},
  TooltipComponent: {},
  DataZoomComponent: {},
  MarkLineComponent: {},
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

vi.mock('svelte-echarts', () => ({
  Chart: vi.fn(() => ({ $$render: () => '<div>chart</div>' })),
}));

const samplePoints = [
  { t: '2026-01-01T00:00:00', price: 100 },
  { t: '2026-01-02T00:00:00', price: 150 },
];

describe('EChartsLineChart', () => {
  it('mounts without throwing with valid data', () => {
    expect(() =>
      render(EChartsLineChart, { props: { points: samplePoints, height: 320 } })
    ).not.toThrow();
  });

  it('mounts with empty data', () => {
    expect(() =>
      render(EChartsLineChart, { props: { points: [], height: 320 } })
    ).not.toThrow();
  });

  it('renders chart container', () => {
    const { container } = render(EChartsLineChart, { props: { points: samplePoints, height: 320 } });
    expect(container.querySelector('div')).toBeTruthy();
  });
});
