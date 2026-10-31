/**
 * Shared point/trendline building for template charts, used by both the live
 * worksheet chart and the static print image so they always draw the same data.
 */
import type { ChartConfig, WorksheetComputed, WorksheetRow } from './testTemplate.types';

export interface Point {
  x: number;
  y: number;
}

//  Treat null/undefined/''/non-finite as "missing" — same blank-tolerance the
//  rest of the form uses, so a half-entered worksheet still plots cleanly.
export function toNum(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function passesFilter(row: WorksheetRow, filterKey: string | undefined): boolean {
  if (!filterKey) return true;
  const v = row[filterKey];
  return v === true || v === 1 || v === '1' || v === 'true';
}

/** Map computed rows to `{x,y}` points, skipping filtered rows and rows missing either axis. */
export function buildPoints(
  rows: WorksheetRow[],
  xField: string,
  yKey: string,
  rowFilter?: string,
): Point[] {
  const points: Point[] = [];
  for (const row of rows) {
    if (!passesFilter(row, rowFilter)) continue;
    const x = toNum(row[xField]);
    const y = toNum(row[yKey]);
    if (x === null || y === null) continue;
    points.push({ x, y });
  }
  //  Sort by X so an out-of-order entry still draws a monotonic line.
  points.sort((a, b) => a.x - b.x);
  return points;
}

/** About five significant figures, like a spreadsheet trendline label. */
function sig(v: number): string {
  return String(Number(v.toPrecision(5)));
}

export interface Trendline {
  /** Two points spanning the plotted X range. */
  points: Point[];
  /** Label lines, e.g. ["y = 53798x + 28845", "R² = 0.9998"]. */
  label: string[];
}

/** Fitted line across the X range of `points`, or null if the fit isn't available yet. */
export function buildTrendline(
  chart: ChartConfig,
  computed: WorksheetComputed,
  points: Point[],
): Trendline | null {
  const t = chart.trendline;
  if (!t || points.length < 2) return null;
  const m = toNum(computed.values?.[t.slopeRef]);
  const b = toNum(computed.values?.[t.interceptRef]);
  if (m === null || b === null) return null;

  const xs = points.map((p) => p.x);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const sign = b < 0 ? '−' : '+';
  const label = [`y = ${sig(m)}x ${sign} ${sig(Math.abs(b))}`];
  const r2 = t.r2Ref ? toNum(computed.values?.[t.r2Ref]) : null;
  if (r2 !== null) label.push(`R² = ${r2.toFixed(4)}`);

  return {
    points: [
      { x: x0, y: m * x0 + b },
      { x: x1, y: m * x1 + b },
    ],
    label,
  };
}
