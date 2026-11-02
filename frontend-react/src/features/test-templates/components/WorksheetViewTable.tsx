/**
 * Read-only table over another group's computed rows, driven by a group's
 * `view` config (see `ViewConfig`). Used for result tables such as the A6D
 * "Concentration in µg" table, which shows per-timepoint values the engine
 * already calculates on the Sampling-Timepoints rows.
 *
 * Rows come from `computed.rows[view.sourceGroup]`, so they follow the source
 * table as rows are added or deleted. Columns with `showIf` follow the same
 * rule as fields (e.g. Cell-7 appears once Cell Loading row 7 has a Cell no).
 * Columns sharing a `band` get one spanning header; others span both header rows.
 */
import type { CSSProperties } from 'react';
import type { ViewColumn, ViewConfig, WorksheetComputed, WorksheetRow } from '../models/testTemplate.types';
import { fieldShown } from '../models/showIf';

interface Props {
  view: ViewConfig;
  computed: WorksheetComputed;
  /** Entered values, for resolving `showIf`. */
  values: Record<string, WorksheetRow[] | undefined> | undefined;
  tableClassName?: string;
  tableStyle?: CSSProperties;
  headCellClassName?: string;
  cellClassName?: string;
}

function format(value: unknown, digits: number | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  return digits === undefined ? String(n) : n.toFixed(digits);
}

interface Band {
  label: string | undefined;
  columns: ViewColumn[];
}

function bandsOf(columns: ViewColumn[]): Band[] {
  const bands: Band[] = [];
  for (const c of columns) {
    const last = bands[bands.length - 1];
    if (c.band && last && last.label === c.band) last.columns.push(c);
    else bands.push({ label: c.band, columns: [c] });
  }
  return bands;
}

export const WorksheetViewTable = ({
  view,
  computed,
  values,
  tableClassName,
  tableStyle,
  headCellClassName,
  cellClassName,
}: Props) => {
  const columns = view.columns.filter((c) => fieldShown({ key: c.key, kind: 'calculated', showIf: c.showIf }, values));
  const rows = computed.rows?.[view.sourceGroup] ?? [];
  const bands = bandsOf(columns);
  const hasBands = bands.some((b) => b.label);

  return (
    <table className={tableClassName} style={tableStyle}>
      <thead>
        <tr>
          {bands.map((b, i) =>
            b.label ? (
              <th key={`band-${i}`} colSpan={b.columns.length} className={headCellClassName} style={{ textAlign: 'center' }}>
                {b.label}
              </th>
            ) : (
              b.columns.map((c) => (
                <th key={c.key} rowSpan={hasBands ? 2 : 1} className={headCellClassName} style={{ textAlign: 'center' }}>
                  {c.label}
                </th>
              ))
            ),
          )}
        </tr>
        {hasBands && (
          <tr>
            {bands
              .filter((b) => b.label)
              .flatMap((b) => b.columns)
              .map((c) => (
                <th key={c.key} className={headCellClassName} style={{ textAlign: 'center' }}>
                  {c.label}
                </th>
              ))}
          </tr>
        )}
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td colSpan={columns.length} className={cellClassName}>
              No rows yet.
            </td>
          </tr>
        ) : (
          rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.key} className={cellClassName} style={{ textAlign: 'center' }}>
                  {format(row[c.key], c.digits)}
                </td>
              ))}
            </tr>
          ))
        )}
        {(view.footer ?? []).map((f) => (
          <tr key={`footer-${f.label}`} style={{ fontWeight: 600 }}>
            {columns.map((c, ci) => {
              const ref = f.values[c.key];
              const text =
                ci === 0 ? f.label : ref ? format(computed.values?.[ref], f.digits) : '';
              return (
                <td key={c.key} className={cellClassName} style={{ textAlign: 'center' }}>
                  {text}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
};
