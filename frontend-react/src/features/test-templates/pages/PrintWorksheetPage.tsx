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
import { WorksheetViewTable } from '../components/WorksheetViewTable';
import { isSetBlockGroup, setBlockSize, setBlocksFor } from '../models/setBlocks';
import { groupFooterRows, isColumnAlignedFooter } from '../models/groupFooter';
import { footerCellsByColumn, rowLabelText } from '../models/rowLabel';
import { formatLimit } from '../models/describeDefinition';
import { fieldShown, groupShown } from '../models/showIf';
import type {
  CriterionResult,
  FieldDef,
  GroupDef,
  GroupFooterItem,
  WorksheetComputed,
  WorksheetRow,
} from '../models/testTemplate.types';

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

function headerText(
  field: FieldDef,
  computed: WorksheetComputed,
  values: Record<string, WorksheetRow[] | undefined> | undefined,
): string {
  let dynamic: string | null = null;
  if (field.labelFrom) {
    const match = field.labelFrom.match(
      /^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?$/,
    );
    if (match) {
      const [, groupKey, fieldKey, idxRaw] = match;
      const index = idxRaw === undefined ? 0 : Number(idxRaw);
      const fromComputed = computed.rows?.[groupKey]?.[index]?.[fieldKey];
      const fromValues = values?.[groupKey]?.[index]?.[fieldKey];
      const raw = fromComputed !== null && fromComputed !== undefined ? fromComputed : fromValues;
      if (raw !== null && raw !== undefined && String(raw).trim() !== '') {
        dynamic = String(raw).trim();
      }
    }
  }
  const label = dynamic ?? field.label ?? field.key;
  return `${label}${field.unit ? ` (${field.unit})` : ''}`;
}

function footerValueText(item: GroupFooterItem, computed: WorksheetComputed): string {
  const raw = computed.values?.[item.ref];
  const field: FieldDef = {
    key: item.ref,
    kind: 'calculated',
    unit: item.unit,
    rounding: item.rounding,
  };
  return displayValue(raw, field) || '—';
}

//  Observed value for an acceptance criterion, matching the on-screen render
//  in WorksheetForm: blank observed prints an em-dash, numbers are trimmed to
//  6 significant digits, everything else stringified.
function criterionObserved(observed: unknown): string {
  if (observed === null || observed === undefined) return '—';
  if (typeof observed === 'number') return String(Number(observed.toPrecision(6)));
  return String(observed);
}

//  Pass/fail wording, mirroring the CriterionRow tag: `null` passed is "not yet
//  assessable" (blank observed), advisory failures read "Outside limit".
function criterionResult(c: CriterionResult): string {
  if (c.passed === null) return 'Not assessed';
  if (c.passed) return 'Pass';
  return c.severity === 'advisory' ? 'Outside limit' : 'Fail';
}

function visibleFields(
  group: GroupDef,
  values: Record<string, WorksheetRow[] | undefined> | undefined,
): FieldDef[] {
  return (group.fields ?? []).filter((f) => !f.hidden && fieldShown(f, values));
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

  const groupHeaderText = (group: GroupDef): string => {
    if (group.labelFrom) {
      const match = group.labelFrom.match(
        /^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?$/,
      );
      if (match) {
        const [, groupKey, fieldKey, idxRaw] = match;
        const index = idxRaw === undefined ? 0 : Number(idxRaw);
        const fromComputed = computed.rows?.[groupKey]?.[index]?.[fieldKey];
        const fromValues = detail.worksheet.group_values?.[groupKey]?.[index]?.[fieldKey];
        const raw = fromComputed !== null && fromComputed !== undefined ? fromComputed : fromValues;
        if (raw !== null && raw !== undefined && String(raw).trim() !== '') return String(raw).trim();
      }
    }
    return group.label ?? group.key;
  };

  const renderGroupHeaderInputs = (group: GroupDef, row: WorksheetRow) => {
    const headerInputs = (group.headerInputs ?? []).flatMap((item) => {
      const field = (group.fields ?? []).find((candidate) => candidate.key === item.field);
      return field ? [{ item, field }] : [];
    });
    if (headerInputs.length === 0) return null;

    const storedRow = detail.worksheet.group_values?.[group.key]?.[0] ?? {};
    return (
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'baseline',
          gap: '10px 18px',
          marginBottom: '4px',
          fontSize: '10px',
        }}
      >
        {headerInputs.map(({ item, field }) => {
          const value = row[field.key] ?? storedRow[field.key];
          return (
            <span key={field.key} style={{ display: 'inline-flex', alignItems: 'baseline', gap: '4px' }}>
              <strong>{item.label ?? headerText(field, computed, detail.worksheet.group_values)}</strong>
              <span
                style={{
                  display: 'inline-block',
                  minWidth: item.width ?? (field.type === 'text' ? '20rem' : '8rem'),
                  borderBottom: '1px solid #777',
                  textAlign: field.type === 'text' ? 'left' : 'right',
                }}
              >
                {displayValue(value, field) || '—'}
              </span>
            </span>
          );
        })}
      </div>
    );
  };

  const renderSolutionBlock = (group: GroupDef) => {
    const block = group.solutionBlock;
    const setsGroup = block ? groups.find((candidate) => candidate.key === block.setsGroup) : undefined;
    if (!block || !setsGroup) return null;

    const dilutionFields = (group.fields ?? []).filter((field) => !field.hidden && field.kind !== 'calculated');
    const setFields = visibleFields(setsGroup, detail.worksheet.group_values);
    const parentRow = rowsOf(group.key)[0] ?? {};
    const setRows = rowsOf(setsGroup.key);
    const hasRowLabel = !!setsGroup.rowLabel;
    const showRowNumbers = !hasRowLabel && setsGroup.showRowNumbers !== false;
    const leadingColumns = hasRowLabel || showRowNumbers ? 1 : 0;

    return (
      <div className="ws-section" key={group.key}>
        <h4>{groupHeaderText(group)}</h4>
        <div style={{ fontSize: '10px', fontWeight: 'bold', marginBottom: '3px' }}>
          {block.dilutionLabel ?? 'Solution Dilution'}
        </div>
        <table className="ws-table">
          <thead>
            <tr>
              {dilutionFields.map((field) => (
                <th key={field.key}>{headerText(field, computed, detail.worksheet.group_values)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {dilutionFields.map((field) => (
                <td className="num" key={field.key}>{displayValue(parentRow[field.key], field)}</td>
              ))}
            </tr>
          </tbody>
        </table>

        <table className="ws-table" style={{ marginTop: '8px' }}>
          <thead>
            <tr>
              {hasRowLabel ? (
                <th>{setsGroup.rowLabel?.header ?? ''}</th>
              ) : (
                showRowNumbers && <th style={{ width: '2rem' }}>#</th>
              )}
              {setFields.map((field) => (
                <th key={field.key}>{headerText(field, computed, detail.worksheet.group_values)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {setRows.map((row, index) => (
              <tr key={index}>
                {hasRowLabel ? (
                  <td>{rowLabelText(setsGroup.rowLabel as NonNullable<GroupDef['rowLabel']>, index + 1)}</td>
                ) : (
                  showRowNumbers && <td>{index + 1}</td>
                )}
                {setFields.map((field) => (
                  <td className="num" key={field.key}>{displayValue(row[field.key], field)}</td>
                ))}
              </tr>
            ))}
          </tbody>
          {(setsGroup.footer ?? []).length > 0 && (
            <tfoot>
              {(setsGroup.footer ?? []).map((item) => (
                <tr key={item.ref}>
                  <th colSpan={Math.max(1, leadingColumns + Math.max(0, setFields.length - 1))}>
                    {item.label}
                  </th>
                  <td className="num">{footerValueText(item, computed)}</td>
                </tr>
              ))}
            </tfoot>
          )}
        </table>
      </div>
    );
  };

  //  Switch the printed page to landscape when any table is wide. A multi-row
  //  (table/sequence) group prints one column per visible field plus the "#"
  //  column; dissolution worksheets with many unit columns overflow portrait.
  //  Threshold: more than 10 columns -> landscape, otherwise portrait.
  const maxTableColumns = groups.reduce((max, group) => {
    if (group.hidden || group.kind === 'singleton') return max;
    const cols =
      visibleFields(group, detail.worksheet.group_values).length +
      (group.showRowNumbers === false ? 0 : 1);
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
        //  Hidden groups hold supporting worksheet values (for example, editable
        //  table column names) and should not print as their own sections.
        if (group.hidden || !groupShown(group, detail.worksheet.group_values)) return null;

        if (group.kind === 'singleton' && group.solutionBlock) {
          return renderSolutionBlock(group);
        }

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

        if (group.view) {
          return (
            <div className="ws-section" key={group.key}>
              <h4>{group.label ?? group.key}</h4>
              <WorksheetViewTable
                view={group.view}
                computed={computed}
                values={detail.worksheet.group_values}
                tableClassName="ws-table"
              />
            </div>
          );
        }

        const fields = visibleFields(group, detail.worksheet.group_values);
        if (fields.length === 0) return null;
        const isSingleton = group.kind === 'singleton';
        const hasRowLabel = !!group.rowLabel;
        const showRowNumbers = !hasRowLabel && group.showRowNumbers !== false;
        const hasHeaderGroups =
          !!group.rowLabel?.headerGroup ||
          fields.some((field) => !!field.headerGroup);
        const rows = rowsOf(group.key);
        const footerRows =
          hasRowLabel && isColumnAlignedFooter(group.footer)
            ? groupFooterRows(group.footer)
            : [];
        const flatRowLabelFooter =
          hasRowLabel && group.footer && !isColumnAlignedFooter(group.footer)
            ? group.footer
            : [];
        const tableFooterRows = group.tableFooterRows ?? [];
        //  Footer refs are declared for every provisioned column. Map them by
        //  field key before rendering the visible subset, so hiding Media 3 does
        //  not make Media 4 display Media 3's Mean/SD/RSD.
        const footerColumnKeys =
          group.columnSet?.columns ??
          (group.fields ?? []).filter((field) => !field.hidden).map((field) => field.key);

        if (isSingleton && group.renderAsTable) {
          const row = rows[0] ?? {};
          return (
            <div className="ws-section" key={group.key}>
              <h4>{group.label ?? group.key}</h4>
              <table className="ws-table">
                <thead>
                  <tr>
                    {fields.map((field) => (
                      <th key={field.key} style={{ width: field.type === 'text' ? '15rem' : '7rem' }}>
                        {headerText(field, computed, detail.worksheet.group_values)}
                        {field.unit ? ` (${field.unit})` : ''}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    {fields.map((field) => (
                      <td key={field.key} className="num">
                        {displayValue(row[field.key], field)}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          );
        }

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
                          <th style={{ width: '18%' }}>
                            {headerText(f, computed, detail.worksheet.group_values)}
                          </th>
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
            {key === 0 && renderGroupHeaderInputs(group, rows[0] ?? {})}
            <table className="ws-table">
              <thead>
                {hasHeaderGroups && (
                  <tr>
                    {hasRowLabel ? (
                      <th>{group.rowLabel?.headerGroup ?? ''}</th>
                    ) : (
                      showRowNumbers && <th style={{ width: '2rem' }} />
                    )}
                    {fields.map((field) => (
                      <th key={`header-group-${field.key}`} style={{ width: field.width }}>
                        {field.headerGroup ?? ''}
                      </th>
                    ))}
                  </tr>
                )}
                <tr>
                  {hasRowLabel ? (
                    <th>{group.rowLabel?.header ?? ''}</th>
                  ) : (
                    showRowNumbers && <th style={{ width: '2rem' }}>#</th>
                  )}
                  {fields.map((f) => (
                    <th key={f.key} style={{ width: f.width }}>
                      {headerText(f, computed, detail.worksheet.group_values)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(startRow, endRow).map((row, localIndex) => (
                  <tr key={startRow + localIndex}>
                    {hasRowLabel ? (
                      <td>{rowLabelText(group.rowLabel as NonNullable<GroupDef['rowLabel']>, startRow + localIndex + 1)}</td>
                    ) : (
                      showRowNumbers && <td>{localIndex + 1}</td>
                    )}
                    {fields.map((f) => (
                      <td key={f.key} className="num">
                        {displayValue(row[f.key], f)}
                      </td>
                    ))}
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={fields.length + (hasRowLabel || showRowNumbers ? 1 : 0)}>No data.</td>
                  </tr>
                )}
              </tbody>
              {endRow === rows.length && footerRows.length > 0 && (
                <tfoot>
                  {footerRows.map((footerRow, footerIndex) => {
                    const cells = footerCellsByColumn(footerRow, footerColumnKeys);
                    return (
                      <tr key={footerIndex}>
                        <th>{footerRow.label}</th>
                        {fields.map((field) => {
                          const item = cells.get(field.key);
                          return (
                            <td key={field.key} className="num">
                              {item ? footerValueText(item, computed) : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tfoot>
              )}
              {endRow === rows.length && flatRowLabelFooter.length > 0 && (
                <tfoot>
                  {flatRowLabelFooter.map((item) => {
                    const targetColumn = item.column ?? fields[0]?.key;
                    return (
                      <tr key={`${item.ref}-${targetColumn ?? ''}`}>
                        <th>{item.label}</th>
                        {fields.map((field) => (
                          <td key={field.key} className="num">
                            {field.key === targetColumn ? footerValueText(item, computed) : ''}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tfoot>
              )}
              {endRow === rows.length && tableFooterRows.length > 0 && (
                <tfoot>
                  {tableFooterRows.map((footerRow, footerIndex) => {
                    const labelSpan = Math.min(
                      fields.length,
                      Math.max(1, footerRow.labelColSpan ?? 1),
                    );
                    return (
                      <tr key={`${footerRow.label}-${footerIndex}`}>
                        {(hasRowLabel || showRowNumbers) && <td />}
                        <th colSpan={labelSpan}>{footerRow.label}</th>
                        {fields.slice(labelSpan).map((field) => {
                          const item = footerRow.values[field.key];
                          return (
                            <td key={field.key} className="num">
                              {item ? footerValueText(item, computed) : ''}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tfoot>
              )}
            </table>
          </div>
        );
        if (!asSetBlocks) {
          return (
            <Fragment key={group.key}>
              {renderTable('', 0, rows.length, 0)}
              {group.note && (
                <div className="ws-section" style={{ marginTop: '-0.5rem' }}>
                  <p style={{ margin: 0, fontSize: '9px' }}>{group.note}</p>
                </div>
              )}
            </Fragment>
          );
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

      {/* ── Acceptance criteria ── */}
      {computed.criteria.length > 0 && (
        <div className="ws-section">
          <h4>Acceptance Criteria</h4>
          <table className="ws-table">
            <thead>
              <tr>
                <th>Criterion</th>
                <th>Limit</th>
                <th>Severity</th>
                <th className="num">Observed</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {computed.criteria.map((c) => (
                <tr key={c.key}>
                  <td>{c.label}</td>
                  <td>{c.limit_text || formatLimit(c.operator, c.limit)}</td>
                  <td>{c.severity === 'advisory' ? 'Advisory' : 'Blocking'}</td>
                  <td className="num">{criterionObserved(c.observed)}</td>
                  <td>{criterionResult(c)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
