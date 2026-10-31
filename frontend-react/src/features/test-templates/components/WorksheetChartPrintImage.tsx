/**
 * Static-image renderer for a template's chart, for the PRINT / Save-as-PDF
 * worksheet. A live Chart.js <canvas> frequently prints blank because the
 * canvas bitmap is not captured by the print renderer, so here we draw the
 * chart off-screen with animation disabled, read it as a PNG data URL
 * (`toBase64Image()`), and render a plain <img>. The image is produced on mount
 * (synchronously after the first paint) so it is present in the DOM before the
 * user triggers window.print(). It scales to the page width (max-width 100%).
 *
 * Only the default series are drawn (the interactive toggles are screen-only);
 * data comes from the same server-computed state the rest of the print uses
 * (`computed.rows[chart.sourceGroup]`) and the same point/trendline helpers as
 * the screen chart, so the printed plot matches the screen.
 */
import { useEffect, useState } from 'react';
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
import type { ChartConfig, WorksheetComputed } from '../models/testTemplate.types';
import { buildPoints, buildTrendline } from '../models/chartData';

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
  /** Overrides chart.title (e.g. the analyst's edited title). */
  title?: string;
}

const SERIES_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];
const TREND_COLOR = '#111827';

export const WorksheetChartPrintImage = ({ chart, computed, title }: Props) => {
  const [dataUrl, setDataUrl] = useState<string | null>(null);

  useEffect(() => {
    const rows = computed.rows?.[chart.sourceGroup] ?? [];
    const scatter = chart.type === 'scatter';
    const seriesKeys = chart.series.map((s) => s.key);
    const defaults =
      chart.defaultSeries && chart.defaultSeries.length ? chart.defaultSeries : ['mean'];
    const allowed = new Set(seriesKeys);
    let drawKeys = defaults.filter((k) => allowed.has(k));
    if (drawKeys.length === 0) drawKeys = seriesKeys.slice(0, 1);

    const datasets: Record<string, unknown>[] = chart.series
      .filter((s) => drawKeys.includes(s.key))
      .map((s) => {
        const idx = seriesKeys.indexOf(s.key);
        const color = SERIES_COLORS[idx % SERIES_COLORS.length];
        return {
          label: s.label,
          data: buildPoints(rows, chart.xField, s.key, chart.rowFilter),
          borderColor: color,
          backgroundColor: color,
          showLine: !scatter,
          tension: 0,
          fill: false,
          spanGaps: true,
          pointRadius: scatter ? 4 : 2,
        };
      });

    const firstKey = chart.series[0]?.key;
    const basePoints = firstKey ? buildPoints(rows, chart.xField, firstKey, chart.rowFilter) : [];
    const trend = buildTrendline(chart, computed, basePoints);
    if (trend) {
      datasets.push({
        label: 'Trendline',
        data: trend.points,
        borderColor: TREND_COLOR,
        backgroundColor: TREND_COLOR,
        borderWidth: 1.5,
        showLine: true,
        pointRadius: 0,
        tension: 0,
        fill: false,
      });
    }

    const heading = title || chart.title;
    //  The equation prints as extra title lines (the Subtitle plugin isn't registered).
    const titleLines = [...(heading ? [heading] : []), ...(trend?.label ?? [])];

    //  Off-screen canvas sized for a crisp print image.
    const canvas = document.createElement('canvas');
    canvas.width = 900;
    canvas.height = 420;

    const instance = new Chart(canvas, {
      type: 'line',
      data: { datasets } as never,
      options: {
        animation: false, //  must be off so the image is ready immediately
        responsive: false,
        devicePixelRatio: 2,
        plugins: {
          legend: { display: chart.series.length > 1, position: 'bottom' },
          title: titleLines.length
            ? { display: true, text: titleLines }
            : { display: false },
        },
        scales: {
          x: {
            type: 'linear',
            beginAtZero: scatter,
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
  }, [chart, computed, title]);

  if (!dataUrl) {
    return <p style={{ fontSize: 11, color: '#555' }}>Chart unavailable.</p>;
  }
  return (
    <img
      src={dataUrl}
      alt={chart.title ?? 'Chart'}
      style={{ maxWidth: '100%', height: 'auto', display: 'block' }}
    />
  );
};
