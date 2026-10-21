/**
 * Printable worksheet — renders a bound template definition with its current
 * computed values as a clean, paper-friendly document. Follows the same
 * browser-print pattern as the ATR / CoA / Stability exports: a dedicated route
 * outside MainLayout, a `.no-print` action bar, and an `@media print` block.
 *
 * Values come from the server's computed state (`computed.rows` for every group,
 * `computed.values` for context + singleton scalars), so what prints is exactly
 * what the engine calculated — never a re-implementation in the view.
 */
import { Fragment, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from 'primereact/button';
import { useWorksheet } from '../hooks/useWorksheet';
import { WorksheetChartPrintImage } from '../components/WorksheetChartPrintImage';
import { isSetBlockGroup, setBlockSize, setBlocksFor } from '../models/setBlocks';
import type { FieldDef, GroupDef, WorksheetComputed } from '../models/testTemplate.types';

const fmtDateTime = (value?: string | null) => (value ? new Date(value).toLocaleString() : '-');

function displayValue(value: unknown, field: FieldDef): string {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'number') {
    const digits = field.rounding?.digits;
    const text =
      field.rounding?.mode && field.rounding.mode !== 'none' && typeof digits === 'number'
        ? value.toFixed(digits)
        : String(Number(value.toPrecision(12)));
    return field.unit ? `${text} ${field.unit}` : text;
  }
  return String(value);
}

const header = (field: FieldDef) =>
  `${field.label ?? field.key}${field.unit ? ` (${field.unit})` : ''}`;

function visibleFields(group: GroupDef): FieldDef[] {
  return (group.fields ?? []).filter((f) => !f.hidden);
}

export const PrintWorksheetPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const worksheetId = Number(id);
  const { data: detail, isLoading, isError } = useWorksheet(worksheetId);

  useEffect(() => {
    document.title = detail
      ? `Worksheet - ${detail.worksheet.template_code} ${detail.worksheet.template_name}`
      : 'Worksheet';
  }, [detail]);

  if (isLoading) return <p style={{ padding: '2rem' }}>Loading worksheet...</p>;
  if (isError || !detail) {
    return (
      <div style={{ padding: '2rem' }}>
        <p>Worksheet could not be loaded.</p>
        <Button label="Back" icon="pi pi-arrow-left" onClick={() => navigate(-1)} />
      </div>
    );
  }

  const def = detail.template.definition ?? {};
  const groups = def.groups ?? [];
  const contextFields = def.context ?? [];
  const computed: WorksheetComputed = detail.computed;

  const contextVal = (key: string) => {
    const v = computed.values?.[key] ?? detail.worksheet.context_values?.[key];
    return v === null || v === undefined || v === '' ? '-' : String(v);
  };

  const rowsOf = (groupKey: string) => computed.rows?.[groupKey] ?? [];

  //  Switch the printed page to landscape when any table is wide. A multi-row
  //  (table/sequence) group prints one column per visible field plus the "#"
  //  column; dissolution worksheets with many unit columns overflow portrait.
  //  Threshold: more than 10 columns -> landscape, otherwise portrait.
  const maxTableColumns = groups.reduce((max, group) => {
    if (group.kind === 'singleton') return max;
    const cols = visibleFields(group).length + 1; // +1 for the row-number column
    return Math.max(max, cols);
  }, 0);
  const landscape = maxTableColumns > 10;

  return (
    <div
      style={{
        maxWidth: '1100px',
        margin: '0 auto',
        padding: '2rem',
        fontFamily: 'Arial, sans-serif',
        color: '#111',
      }}
    >
      <div className="no-print" style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem' }}>
        <Button label="Back" icon="pi pi-arrow-left" text onClick={() => navigate(-1)} />
        <Button label="Print / Save as PDF" icon="pi pi-print" onClick={() => window.print()} />
      </div>

      <style>{`
        /* Orientation: landscape when a table exceeds 10 columns, else portrait. */
        @page { size: ${landscape ? 'landscape' : 'portrait'}; }
        @media print {
          .no-print { display: none !important; }
          body { margin: 0; }
          /* Keep each section together on a page where possible. */
          .ws-section { break-inside: avoid; }
        }
        table.ws-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 2px; }
        table.ws-table th, table.ws-table td { border: 1px solid #333; padding: 3px 5px; text-align: left; }
        table.ws-table th { background: #e9eef7; color: #11397a; font-weight: bold; }
        table.ws-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
        .ws-section { margin-bottom: 14px; }
        .ws-section h4 { margin: 10px 0 4px; font-size: 12px; color: #11397a; }
      `}</style>

      {/* ── Title ── */}
      <div
        style={{
          textAlign: 'center',
          borderBottom: '2px solid #000',
          paddingBottom: '0.5rem',
          marginBottom: '1rem',
        }}
      >
        <h2 style={{ margin: 0 }}>EMCURE</h2>
        <p style={{ margin: 0 }}>R&amp;D — Calculation Worksheet</p>
        <p style={{ margin: 0, fontWeight: 'bold' }}>
          {detail.worksheet.template_name}{' '}
          <span style={{ fontWeight: 'normal' }}>
            ({detail.worksheet.template_code} v{detail.worksheet.template_version})
          </span>
        </p>
        <p style={{ margin: 0, fontSize: '12px' }}>Status: {detail.worksheet.status}</p>
      </div>

      {/* ── Context ── */}
      {contextFields.length > 0 && (
        <div className="ws-section">
          <h4>Context</h4>
          <table className="ws-table">
            <tbody>
              {chunk(contextFields, 2).map((pair, i) => (
                <tr key={i}>
                  {pair.map((cf) => (
                    <Fragment key={cf.key}>
                      <th style={{ width: '18%' }}>{cf.label ?? cf.key}</th>
                      <td style={{ width: '32%' }}>{contextVal(cf.key)}</td>
                    </Fragment>
                  ))}
                  {pair.length === 1 && (
                    <>
                      <th />
                      <td />
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Groups ── */}
      {groups.map((group) => {
        //  A group carrying a chart config prints the chart as a static image
        //  (a live canvas would print blank). Rendered regardless of fields —
        //  a chart group's only field is a title input.
        if (group.chart) {
          //  Prefer the analyst's edited title (the group's titleField value)
          //  over the config default, so the PDF matches the screen.
          const tfKey = group.chart.titleField;
          const editedTitle = tfKey
            ? (detail.worksheet.group_values?.[group.key]?.[0]?.[tfKey] as string | undefined)
            : undefined;
          const chartTitle = editedTitle || group.chart.title;
          return (
            <div className="ws-section" key={group.key}>
              <h4>{group.label ?? group.key}</h4>
              <WorksheetChartPrintImage chart={group.chart} computed={computed} title={chartTitle} />
            </div>
          );
        }

        const fields = visibleFields(group);
        if (fields.length === 0) return null;
        const isSingleton = group.kind === 'singleton';
        const rows = rowsOf(group.key);

        if (isSingleton) {
          const row = rows[0] ?? {};
          return (
            <div className="ws-section" key={group.key}>
              <h4>{group.label ?? group.key}</h4>
              <table className="ws-table">
                <tbody>
                  {chunk(fields, 2).map((pair, i) => (
                    <tr key={i}>
                      {pair.map((f) => (
                        <Fragment key={f.key}>
                          <th style={{ width: '18%' }}>{header(f)}</th>
                          <td className="num" style={{ width: '32%' }}>
                            {displayValue(row[f.key], f)}
                          </td>
                        </Fragment>
                      ))}
                      {pair.length === 1 && (
                        <>
                          <th />
                          <td />
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        //  Multi-row (table / sequence): render columns in definition order.
        //  Opt-in "Set N" labeled blocks (shape heuristic — models/setBlocks.ts):
        //  a group with a hidden `cidx` field and no `set_no` column (e.g.
        //  TPL-A2-0004's Sample Details) prints as consecutive fixed-size blocks,
        //  each in its own `.ws-section` (so it stays together across a page
        //  break) under a "Set N" sub-heading with its own repeated column header.
        //  Block size = the `cidx` 0-reset cycle length from the computed rows
        //  (falls back to 4). Plain tables render as a single block spanning all
        //  rows, exactly as before. `#` restarts per block.
        const asSetBlocks = isSetBlockGroup(group);
        const blocks = asSetBlocks
          ? setBlocksFor(rows.length, setBlockSize(group, rows))
          : [{ title: '', startRow: 0, endRow: rows.length }];
        const renderTable = (
          title: string,
          startRow: number,
          endRow: number,
          key: number,
        ) => (
          <div className="ws-section" key={key}>
            <h4>{title || (group.label ?? group.key)}</h4>
            <table className="ws-table">
              <thead>
                <tr>
                  <th style={{ width: '2rem' }}>#</th>
                  {fields.map((f) => (
                    <th key={f.key}>{header(f)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(startRow, endRow).map((row, localIndex) => (
                  <tr key={startRow + localIndex}>
                    <td>{localIndex + 1}</td>
                    {fields.map((f) => (
                      <td key={f.key} className="num">
                        {displayValue(row[f.key], f)}
                      </td>
                    ))}
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={fields.length + 1}>No data.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        );
        if (!asSetBlocks) {
          return renderTable('', 0, rows.length, 0);
        }
        //  Set-block group: a wrapper fragment carrying the group label once,
        //  then one titled `.ws-section` table per "Set N" block.
        return (
          <Fragment key={group.key}>
            <div className="ws-section">
              <h4>{group.label ?? group.key}</h4>
            </div>
            {blocks.map((block, blockIndex) =>
              renderTable(block.title, block.startRow, block.endRow, blockIndex),
            )}
          </Fragment>
        );
      })}

      {/* ── Reportable result + signatures ── */}
      <div className="ws-section" style={{ marginTop: '1rem' }}>
        <table className="ws-table">
          <tbody>
            <tr>
              <th style={{ width: '18%' }}>Reportable Result</th>
              <td className="num">
                {detail.worksheet.reportable_result ?? '-'}
                {detail.template.result_unit ? ` ${detail.template.result_unit}` : ''}
              </td>
              <th style={{ width: '18%' }}>Confirmed By</th>
              <td>
                {detail.worksheet.confirmed_by
                  ? `${detail.worksheet.confirmed_by} — ${fmtDateTime(detail.worksheet.confirmed_at)}`
                  : '-'}
              </td>
            </tr>
          </tbody>
        </table>

        <table className="ws-table" style={{ marginTop: '1.5rem' }}>
          <thead>
            <tr>
              <th>Analysed By</th>
              <th>Reviewed By</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ height: '48px' }}>
              <td>{computed.values?.analysed_by ? String(computed.values.analysed_by) : ''}</td>
              <td>{detail.worksheet.reviewed_by ?? ''}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}
