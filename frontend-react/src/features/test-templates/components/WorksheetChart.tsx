/**
 * Line chart for a dissolution-style group, driven entirely by a template's
 * `chart` config (see `ChartConfig`). It reads the same server-computed state
 * the rest of the worksheet form uses — `computed.rows[chart.sourceGroup]` — so
 * the plotted line always matches what the engine produced, and repaints when
 * the analyst edits a timepoint.
 *
 * X = `chart.xField` (e.g. time in hours); Y = the selected series value
 * (default `mean`). Per-unit series are toggled with the chips above the canvas.
 * Rows whose X or Y is blank/non-numeric are skipped so a partially filled
 * worksheet still draws a clean line.
 */
import { useMemo, useState } from 'react';
import { Chart } from 'primereact/chart';
import type { ChartConfig, WorksheetComputed, WorksheetRow } from '../models/testTemplate.types';

interface WorksheetChartProps {
  chart: ChartConfig;
  computed: WorksheetComputed;
  /** Dim the canvas while a recalculation is in flight. */
  stale?: boolean;
}

interface Point {
  x: number;
  y: number;
}

//  Treat null/undefined/''/non-finite as "missing" — same blank-tolerance the
//  rest of the form uses, so a half-entered worksheet still plots cleanly.
function toNum(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Map computed rows to `{x,y}` points, skipping rows missing either axis. */
function buildPoints(rows: WorksheetRow[], xField: string, yKey: string): Point[] {
  const points: Point[] = [];
  for (const row of rows) {
    const x = toNum(row[xField]);
    const y = toNum(row[yKey]);
    if (x === null || y === null) continue;
    points.push({ x, y });
  }
  //  Sort by X so an out-of-order entry still draws a monotonic line.
  points.sort((a, b) => a.x - b.x);
  return points;
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

export const WorksheetChart = ({ chart, computed, stale }: WorksheetChartProps) => {
  const seriesKeys = useMemo(() => chart.series.map((s) => s.key), [chart.series]);

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
  //  would not repaint when the analyst edits a timepoint.
  const data = useMemo(() => {
    const datasets = chart.series
      .filter((s) => visible.has(s.key))
      .map((s) => {
        const idx = seriesKeys.indexOf(s.key);
        const color = SERIES_COLORS[idx % SERIES_COLORS.length];
        return {
          label: s.label,
          data: buildPoints(rows, chart.xField, s.key),
          borderColor: color,
          backgroundColor: color,
          tension: 0,
          fill: false,
          spanGaps: true,
        };
      });
    return { datasets };
  }, [rows, visible, chart.series, chart.xField, seriesKeys]);

  const options = useMemo(
    () => ({
      maintainAspectRatio: false,
      responsive: true,
      plugins: {
        //  We render our own toggle chips, so hide Chart.js's built-in legend.
        legend: { display: false },
      },
      scales: {
        x: {
          type: 'linear' as const,
          title: { display: true, text: chart.xLabel ?? 'Time' },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: chart.yLabel ?? '% Release' },
        },
      },
    }),
    [chart.xLabel, chart.yLabel],
  );

  return (
    <div>
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
      <div style={{ height: '320px', opacity: stale ? 0.5 : 1 }}>
        <Chart type="line" data={data} options={options} />
      </div>
    </div>
  );
};
