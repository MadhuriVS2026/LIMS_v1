/**
 * Static-image renderer for a template's dissolution chart, for the PRINT /
 * Save-as-PDF worksheet. A live Chart.js <canvas> frequently prints blank
 * because the canvas bitmap is not captured by the print renderer, so here we
 * draw the chart off-screen with animation disabled, read it as a PNG data URL
 * (`toBase64Image()`), and render a plain <img>. The image is produced on mount
 * (synchronously after the first paint) so it is present in the DOM before the
 * user triggers window.print(). It scales to the page width (max-width 100%).
 *
 * Only the default series are drawn (the interactive toggles are screen-only);
 * data comes from the same server-computed state the rest of the print uses
 * (`computed.rows[chart.sourceGroup]`), so the printed line matches the screen.
 */
import { useEffect, useRef, useState } from 'react';
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import type { ChartConfig, WorksheetComputed, WorksheetRow } from '../models/testTemplate.types';

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
);

interface Props {
  chart: ChartConfig;
  computed: WorksheetComputed;
}

function toNum(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

interface Point {
  x: number;
  y: number;
}

function buildPoints(rows: WorksheetRow[], xField: string, yKey: string): Point[] {
  const pts: Point[] = [];
  for (const row of rows) {
    const x = toNum(row[xField]);
    const y = toNum(row[yKey]);
    if (x === null || y === null) continue;
    pts.push({ x, y });
  }
  pts.sort((a, b) => a.x - b.x);
  return pts;
}

const SERIES_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];

export const WorksheetChartPrintImage = ({ chart, computed }: Props) => {
  const [dataUrl, setDataUrl] = useState<string | null>(null);

  useEffect(() => {
    const rows = computed.rows?.[chart.sourceGroup] ?? [];
    const seriesKeys = chart.series.map((s) => s.key);
    const defaults =
      chart.defaultSeries && chart.defaultSeries.length ? chart.defaultSeries : ['mean'];
    const allowed = new Set(seriesKeys);
    let drawKeys = defaults.filter((k) => allowed.has(k));
    if (drawKeys.length === 0) drawKeys = seriesKeys.slice(0, 1);

    const datasets = chart.series
      .filter((s) => drawKeys.includes(s.key))
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
          pointRadius: 2,
        };
      });

    //  Off-screen canvas sized for a crisp print image.
    const canvas = document.createElement('canvas');
    canvas.width = 900;
    canvas.height = 420;

    const instance = new Chart(canvas, {
      type: 'line',
      data: { datasets },
      options: {
        animation: false, //  must be off so the image is ready immediately
        responsive: false,
        devicePixelRatio: 2,
        plugins: {
          legend: { display: true, position: 'bottom' },
          title: chart.title ? { display: true, text: chart.title } : { display: false },
        },
        scales: {
          x: {
            type: 'linear',
            title: { display: true, text: chart.xLabel ?? 'Time' },
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: chart.yLabel ?? '% Release' },
          },
        },
      },
    });

    //  With animation disabled the chart has drawn by now; capture the PNG.
    try {
      setDataUrl(instance.toBase64Image('image/png', 1));
    } finally {
      instance.destroy();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chart, computed]);

  if (!dataUrl) {
    return <p style={{ fontSize: 11, color: '#555' }}>Chart unavailable.</p>;
  }
  return (
    <img
      src={dataUrl}
      alt={chart.title ?? 'Dissolution profile chart'}
      style={{ maxWidth: '100%', height: 'auto', display: 'block' }}
    />
  );
};
