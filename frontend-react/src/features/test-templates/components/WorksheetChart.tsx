/**
 * Chart for a template group, driven entirely by a template's `chart` config
 * (see `ChartConfig`). It reads the same server-computed state the rest of the
 * worksheet form uses — `computed.rows[chart.sourceGroup]` — so the plot always
 * matches what the engine produced, and repaints when the analyst edits a row.
 *
 * X = `chart.xField`; Y = each selected series. `type: 'scatter'` draws points
 * only, `rowFilter` limits which rows are plotted, and `trendline` overlays the
 * engine's fitted line with its equation (e.g. a calibration curve). Rows whose
 * X or Y is blank/non-numeric are skipped so a partially filled worksheet still
 * draws cleanly.
 */
import { useMemo, useState } from 'react';
import { Chart } from 'primereact/chart';
import type { ChartConfig, WorksheetComputed } from '../models/testTemplate.types';
import { buildPoints, buildTrendline } from '../models/chartData';

interface WorksheetChartProps {
  chart: ChartConfig;
  computed: WorksheetComputed;
  /** Dim the canvas while a recalculation is in flight. */
  stale?: boolean;
  /** Displayed chart title (from the editable title field, falls back to config). */
  title?: string;
}

//  A small, fixed palette cycled across series. Mean sits first so it reads as
//  the primary line; the units follow in distinct hues.
const SERIES_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#10b981', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#14b8a6', // teal
];
const TREND_COLOR = '#111827';

export const WorksheetChart = ({ chart, computed, stale, title }: WorksheetChartProps) => {
  const seriesKeys = useMemo(() => chart.series.map((s) => s.key), [chart.series]);
  const scatter = chart.type === 'scatter';

  const [visible, setVisible] = useState<Set<string>>(() => {
    const defaults = chart.defaultSeries && chart.defaultSeries.length ? chart.defaultSeries : ['mean'];
    //  Intersect with declared series so a stale default can't enable a key the
    //  chart doesn't define.
    const allowed = new Set(seriesKeys);
    const seeded = defaults.filter((k) => allowed.has(k));
    //  Guarantee at least one line is drawn even if defaults don't match.
    return new Set(seeded.length ? seeded : seriesKeys.slice(0, 1));
  });

  const toggle = (key: string) => {
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const rows = computed.rows?.[chart.sourceGroup] ?? [];

  //  New object references on every rows/visibility change — PrimeReact's Chart
  //  is memoised on reference equality of `data`/`options`, so without this it
  //  would not repaint when the analyst edits a row.
  const { data, trend } = useMemo(() => {
    const datasets: Record<string, unknown>[] = chart.series
      .filter((s) => visible.has(s.key))
      .map((s) => {
        const idx = seriesKeys.indexOf(s.key);
        const color = SERIES_COLORS[idx % SERIES_COLORS.length];
        return {
          label: s.label,
          data: buildPoints(rows, chart.xField, s.key, chart.rowFilter),
          borderColor: color,
          backgroundColor: color,
          showLine: !scatter,
          pointRadius: scatter ? 4 : 3,
          tension: 0,
          fill: false,
          spanGaps: true,
        };
      });

    //  The trendline spans the first series' plotted points (all series share X).
    const firstKey = chart.series[0]?.key;
    const basePoints = firstKey ? buildPoints(rows, chart.xField, firstKey, chart.rowFilter) : [];
    const t = buildTrendline(chart, computed, basePoints);
    if (t) {
      datasets.push({
        label: 'Trendline',
        data: t.points,
        borderColor: TREND_COLOR,
        backgroundColor: TREND_COLOR,
        borderWidth: 1.5,
        showLine: true,
        pointRadius: 0,
        tension: 0,
        fill: false,
      });
    }
    return { data: { datasets }, trend: t };
  }, [rows, visible, chart, computed, seriesKeys, scatter]);

  const options = useMemo(
    () => ({
      maintainAspectRatio: false,
      responsive: true,
      plugins: {
        //  We render our own toggle chips, so hide Chart.js's built-in legend.
        legend: { display: false },
        title: title ? { display: true, text: title, font: { size: 14 } } : { display: false },
      },
      scales: {
        x: {
          type: 'linear' as const,
          beginAtZero: scatter,
          title: { display: true, text: chart.xLabel ?? 'Time' },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: chart.yLabel ?? '% Release' },
        },
      },
    }),
    [chart.xLabel, chart.yLabel, title, scatter],
  );

  return (
    <div>
      {chart.series.length > 1 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {chart.series.map((s) => {
            const active = visible.has(s.key);
            const idx = seriesKeys.indexOf(s.key);
            const color = SERIES_COLORS[idx % SERIES_COLORS.length];
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => toggle(s.key)}
                className={`p-component border-round cursor-pointer border-1 px-2 py-1 text-sm ${
                  active ? 'border-transparent text-white' : 'surface-0 text-700 border-300'
                }`}
                style={active ? { backgroundColor: color } : undefined}
                aria-pressed={active}
              >
                <span
                  className="inline-block border-circle mr-2"
                  style={{ width: '0.6rem', height: '0.6rem', backgroundColor: color, verticalAlign: 'middle' }}
                />
                {s.label}
              </button>
            );
          })}
        </div>
      )}
      {trend && (
        <div className="text-center text-sm font-mono mb-1">
          {trend.label.map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      )}
      <div style={{ height: '320px', opacity: stale ? 0.5 : 1 }}>
        <Chart type="line" data={data} options={options} />
      </div>
    </div>
  );
};
