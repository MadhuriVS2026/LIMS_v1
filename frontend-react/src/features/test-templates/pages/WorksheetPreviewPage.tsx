/**
 * Worksheet preview — a read-only, definition-derived view of the worksheet a
 * template produces, reached from the "Worksheet" column on the template list.
 *
 * Unlike PrintWorksheetPage, which renders a real saved worksheet's `computed`
 * values, there is NO worksheet instance here: we only have the
 * `TestTemplate.definition` loaded by `useTemplateDetail`. So this page renders
 * the LAYOUT SKELETON (context fields, each group's columns/rows, acceptance
 * criteria and the reportable result) with blank em-dash placeholder cells.
 * It is purely display — no data entry, no save, no backend calls beyond the
 * template GET the detail page already performs.
 *
 * The styling aims for an Excel-sheet feel: every section renders as a compact,
 * bordered, spreadsheet-like block with thin consistent borders, shaded
 * header/label cells and tight padding. The renderer stays GENERIC — every
 * section type is driven only by the definition shape (context / singleton /
 * table|sequence / criteria / resultRef), with NO per-archetype or per-template
 * branching, so all ~23 templates render from their own definition.
 */
import { Fragment, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Message } from 'primereact/message';
import { Tag } from 'primereact/tag';
import { StatusBadge } from '@shared/components/StatusBadge';
import { useTemplateDetail } from '../hooks/useTestTemplates';
import { formatLimit } from '../models/describeDefinition';
import { isSetBlockGroup, setBlockSize, setBlocksFor } from '../models/setBlocks';
import { groupFooterRows, isColumnAlignedFooter } from '../models/groupFooter';
import { footerCellsByColumn, rowLabelText } from '../models/rowLabel';
import { fieldShown, groupShown } from '../models/showIf';
import type { FieldDef, GroupDef, WorksheetRow } from '../models/testTemplate.types';

const EMPTY = '—';

const header = (field: FieldDef) =>
  `${field.label ?? field.key}${field.unit ? ` (${field.unit})` : ''}`;

/**
 * Field header text plus, for CALCULATED fields, a small "calc" tag so the
 * preview distinguishes auto-computed columns from analyst inputs (AC2).
 */
const fieldHeader = (field: FieldDef) => (
  <span className="inline-flex align-items-center gap-2">
    {header(field)}
    {field.kind === 'calculated' && (
      <Tag value="calc" severity="info" aria-label="calculated field" />
    )}
  </span>
);

const visibleFields = (
  group: GroupDef,
  values: Record<string, WorksheetRow[] | undefined>,
): FieldDef[] => (group.fields ?? []).filter((f) => !f.hidden && fieldShown(f, values));

/** Default row count a worksheet from this template would seed (matches WorksheetForm). */
const rowCount = (group: GroupDef): number => group.rows?.default ?? group.rows?.min ?? 1;

/**
 * Minimal opening values for the read-only template preview. This allows a
 * `showIf` comparison (such as the six default media columns) to reflect a
 * group's `rows.seed` / field defaults without creating a real worksheet.
 */
function seedPreviewValues(groups: GroupDef[]): Record<string, WorksheetRow[]> {
  const out: Record<string, WorksheetRow[]> = {};
  for (const group of groups) {
    const count = group.kind === 'singleton' ? 1 : rowCount(group);
    const seed = group.rows?.seed ?? [];
    out[group.key] = Array.from({ length: count }, (_, index) => {
      const row: WorksheetRow = { ...(seed[index] ?? {}) };
      for (const field of group.fields ?? []) {
        if (row[field.key] === undefined && field.default !== undefined) {
          row[field.key] = field.default;
        }
      }
      return row;
    });
  }
  return out;
}

function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

/** A blank placeholder cell, right-aligned so a numeric column reads as Excel would. */
const Placeholder = () => <span className="text-400">{EMPTY}</span>;

export const WorksheetPreviewPage = () => {
  const { id } = useParams<{ id: string }>();
  const templateId = id ? Number(id) : undefined;
  const navigate = useNavigate();

  const { data: template, isLoading } = useTemplateDetail(templateId);

  const definition = template?.definition;
  const contextFields = useMemo(
    () => (definition?.context ?? []).filter((f) => !f.hidden),
    [definition],
  );
  const groups = useMemo(() => definition?.groups ?? [], [definition]);
  const previewValues = useMemo(() => seedPreviewValues(groups), [groups]);
  const criteria = useMemo(() => definition?.criteria ?? [], [definition]);

  if (isLoading) return <p className="text-500">Loading worksheet...</p>;
  if (!template || templateId == null)
    return <Message severity="warn" text="Template not found." />;

  const renderSolutionBlock = (group: GroupDef) => {
    const block = group.solutionBlock;
    const setsGroup = block ? groups.find((candidate) => candidate.key === block.setsGroup) : undefined;
    if (!block || !setsGroup) return null;

    const dilutionFields = (group.fields ?? []).filter((field) => !field.hidden && field.kind !== 'calculated');
    const setFields = visibleFields(setsGroup, previewValues);
    const rows = rowCount(setsGroup);
    const hasRowLabel = !!setsGroup.rowLabel;
    const showRowNumbers = !hasRowLabel && setsGroup.showRowNumbers !== false;
    const leadingColumns = hasRowLabel || showRowNumbers ? 1 : 0;

    return (
      <Card key={group.key} title={group.label ?? group.key}>
        <h4 className="m-0 mb-1 text-sm font-medium text-700">
          {block.dilutionLabel ?? 'Solution Dilution'}
        </h4>
        <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {dilutionFields.map((field) => (
                <th
                  key={field.key}
                  scope="col"
                  className="p-1 border-1 border-200 bg-gray-50 text-left"
                >
                  {fieldHeader(field)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {dilutionFields.map((field) => (
                <td key={field.key} className="p-1 border-1 border-200 text-right">
                  <Placeholder />
                </td>
              ))}
            </tr>
          </tbody>
        </table>

        <table className="w-full text-sm mt-3" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {hasRowLabel ? (
                <th scope="col" className="p-1 border-1 border-200 bg-gray-50 text-left">
                  {setsGroup.rowLabel?.header ?? ''}
                </th>
              ) : (
                showRowNumbers && (
                  <th scope="col" className="p-1 border-1 border-200 bg-gray-50 text-left">
                    #
                  </th>
                )
              )}
              {setFields.map((field) => (
                <th
                  key={field.key}
                  scope="col"
                  className={`p-1 border-1 border-200 bg-gray-50 ${
                    field.kind === 'calculated' ? 'text-right' : 'text-left'
                  }`}
                >
                  {fieldHeader(field)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rows }, (_, index) => (
              <tr key={index}>
                {hasRowLabel ? (
                  <td className="p-1 border-1 border-200 text-700 font-medium">
                    {rowLabelText(setsGroup.rowLabel as NonNullable<GroupDef['rowLabel']>, index + 1)}
                  </td>
                ) : (
                  showRowNumbers && <td className="p-1 border-1 border-200">{index + 1}</td>
                )}
                {setFields.map((field) => (
                  <td key={field.key} className="p-1 border-1 border-200 text-right">
                    <Placeholder />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          {(setsGroup.footer ?? []).length > 0 && (
            <tfoot>
              {(setsGroup.footer ?? []).map((item) => (
                <tr key={item.ref}>
                  <td
                    className="p-1 border-1 border-200 bg-gray-50 font-medium"
                    colSpan={Math.max(1, leadingColumns + Math.max(0, setFields.length - 1))}
                  >
                    {item.label}
                  </td>
                  <td className="p-1 border-1 border-200 text-right"><Placeholder /></td>
                </tr>
              ))}
            </tfoot>
          )}
        </table>
      </Card>
    );
  };

  return (
    <div className="flex flex-column gap-3">
      <div>
        <Button
          label="Back to Templates"
          icon="pi pi-arrow-left"
          text
          size="small"
          onClick={() => navigate('/test-templates')}
        />
        <div className="flex align-items-center gap-3 mt-1 flex-wrap">
          <h2 className="m-0 text-xl">
            <span className="font-mono text-blue-600">{template.code}</span>{' '}
            <span>{template.name}</span>{' '}
            <span className="text-500 font-normal">v{template.version}</span>
          </h2>
          <StatusBadge status={template.status} />
        </div>
        <p className="text-sm text-500 m-0 mt-1">
          archetype {template.archetype}
          {template.test_name ? ` · ${template.test_name} (${template.test_code})` : ''}
          {template.result_unit ? ` · result unit ${template.result_unit}` : ''}
        </p>
        <p className="text-xs text-500 m-0 mt-1">
          Read-only preview of the worksheet this template produces. Cells are blank until an
          analyst fills them in.
        </p>
      </div>

      {/* ── Context ── */}
      {contextFields.length > 0 && (
        <Card title="Context">
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <tbody>
              {chunk(contextFields, 2).map((pair, i) => (
                <tr key={i}>
                  {pair.map((cf) => (
                    <Fragment key={cf.key}>
                      <th
                        scope="row"
                        className="text-left p-1 border-1 border-200 bg-gray-50 font-medium w-2"
                      >
                        {cf.label ?? cf.key}
                      </th>
                      <td className="p-1 border-1 border-200 w-3 text-right">
                        <Placeholder />
                      </td>
                    </Fragment>
                  ))}
                  {pair.length === 1 && (
                    <>
                      <th className="border-1 border-200 bg-gray-50" />
                      <td className="border-1 border-200" />
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* ── Groups ── */}
      {groups.map((group) => {
        //  Hidden groups support a visible table (for example, its editable
        //  column names) and are not worksheet sections in their own right.
        if (group.hidden || !groupShown(group, previewValues)) return null;
        const fields = visibleFields(group, previewValues);
        if (fields.length === 0) return null;

        if (group.kind === 'singleton' && group.solutionBlock) {
          return renderSolutionBlock(group);
        }

        if (group.kind === 'singleton' && group.renderAsTable) {
          return (
            <Card key={group.key} title={group.label ?? group.key}>
              <div style={{ overflowX: 'auto' }}>
                <table
                  className="w-full text-sm"
                  style={{
                    borderCollapse: 'collapse',
                    tableLayout: 'fixed',
                    minWidth: `${Math.max(1, fields.length) * 7}rem`,
                  }}
                >
                  <thead>
                    <tr>
                      {fields.map((field) => (
                        <th
                          key={field.key}
                          scope="col"
                          className="p-1 border-1 border-200 bg-gray-50"
                          style={{ width: field.type === 'text' ? '15rem' : '7rem' }}
                        >
                          {fieldHeader(field)}
                          {field.unit ? ` (${field.unit})` : ''}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      {fields.map((field) => (
                        <td key={field.key} className="p-1 border-1 border-200 text-right">
                          <Placeholder />
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </Card>
          );
        }

        if (group.kind === 'singleton') {
          return (
            <Card key={group.key} title={group.label ?? group.key}>
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <tbody>
                  {chunk(fields, 2).map((pair, i) => (
                    <tr key={i}>
                      {pair.map((f) => (
                        <Fragment key={f.key}>
                          <th
                            scope="row"
                            className="text-left p-1 border-1 border-200 bg-gray-50 font-medium w-2"
                          >
                            {fieldHeader(f)}
                          </th>
                          <td className="p-1 border-1 border-200 w-3 text-right">
                            <Placeholder />
                          </td>
                        </Fragment>
                      ))}
                      {pair.length === 1 && (
                        <>
                          <th className="border-1 border-200 bg-gray-50" />
                          <td className="border-1 border-200" />
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          );
        }

        //  table / sequence: a column per visible field plus a `#` column, with
        //  the default number of blank numbered rows. An optional headerContext
        //  strip renders above the table and an optional footer strip beneath it
        //  — both are definition-driven and skipped when absent.
        const rows = rowCount(group);
        const hasRowLabel = !!group.rowLabel;
        const showRowNumbers = !hasRowLabel && group.showRowNumbers !== false;
        const hasHeaderGroups =
          !!group.rowLabel?.headerGroup ||
          fields.some((field) => !!field.headerGroup);
        const headerContext = group.headerContext ?? [];
        const headerInputs = (group.headerInputs ?? []).flatMap((item) => {
          const field = (group.fields ?? []).find((candidate) => candidate.key === item.field);
          return field ? [{ item, field }] : [];
        });
        const footer = group.footer ?? [];
        const footerColumnKeys =
          group.columnSet?.columns ??
          (group.fields ?? []).filter((field) => !field.hidden).map((field) => field.key);
        const colSpan = fields.length + (hasRowLabel || showRowNumbers ? 1 : 0);

        //  Opt-in "Set N" labeled blocks (shape heuristic — models/setBlocks.ts):
        //  a group with a hidden `cidx` field and no `set_no` column (e.g.
        //  TPL-A2-0004's Sample Details) previews as consecutive fixed-size blocks,
        //  each under a "Set N" sub-heading with its own repeated column header.
        //  The preview has NO computed values, so `setBlockSize` cannot read a
        //  `cidx` cycle and falls back to the documented 4 — giving 2 blocks of 4
        //  blank rows for the fixed 8-row table. Plain tables render as a single
        //  block spanning all rows, exactly as before. `#` restarts per block.
        const asSetBlocks = isSetBlockGroup(group);
        const blocks = asSetBlocks
          ? setBlocksFor(rows, setBlockSize(group))
          : [{ title: '', startRow: 0, endRow: rows }];
        const renderPreviewTable = (
          title: string,
          startRow: number,
          endRow: number,
          withFooter: boolean,
          key: number,
        ) => (
          <Fragment key={key}>
            {title && <h4 className="m-0 mt-2 mb-1 text-sm font-medium text-700">{title}</h4>}
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                {hasHeaderGroups && (
                  <tr>
                    {hasRowLabel ? (
                      <th
                        scope="col"
                        className="text-left p-1 border-1 border-200 bg-gray-100"
                        style={{ width: '7rem' }}
                      >
                        {group.rowLabel?.headerGroup ?? ''}
                      </th>
                    ) : (
                      showRowNumbers && (
                        <th
                          scope="col"
                          className="text-left p-1 border-1 border-200 bg-gray-100"
                          style={{ width: '3rem' }}
                        />
                      )
                    )}
                    {fields.map((field) => (
                      <th
                        key={`header-group-${field.key}`}
                        scope="col"
                        className="p-1 border-1 border-200 bg-gray-100"
                        style={{ width: field.width }}
                      >
                        {field.headerGroup ?? ''}
                      </th>
                    ))}
                  </tr>
                )}
                <tr>
                  {hasRowLabel ? (
                    <th
                      scope="col"
                      className="text-left p-1 border-1 border-200 bg-gray-50"
                      style={{ width: '7rem' }}
                    >
                      {group.rowLabel?.header ?? ''}
                    </th>
                  ) : (
                    showRowNumbers && (
                      <th
                        scope="col"
                        className="text-left p-1 border-1 border-200 bg-gray-50"
                        style={{ width: '3rem' }}
                      >
                        #
                      </th>
                    )
                  )}
                  {fields.map((f) => (
                    <th
                      key={f.key}
                      scope="col"
                      className={`p-1 border-1 border-200 bg-gray-50 ${
                        f.kind === 'calculated' ? 'text-right' : 'text-left'
                      }`}
                      style={{ width: f.width }}
                    >
                      {fieldHeader(f)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: endRow - startRow }, (_, localIndex) => (
                  <tr key={startRow + localIndex}>
                    {hasRowLabel ? (
                      <td className="p-1 border-1 border-200 text-700 font-medium">
                        {rowLabelText(
                          group.rowLabel as NonNullable<GroupDef['rowLabel']>,
                          startRow + localIndex + 1,
                        )}
                      </td>
                    ) : (
                      showRowNumbers && (
                        <td className="p-1 border-1 border-200 text-500 font-mono">
                          {localIndex + 1}
                        </td>
                      )
                    )}
                    {fields.map((f) => (
                      <td key={f.key} className="p-1 border-1 border-200 text-right">
                        <Placeholder />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
              {withFooter && (group.tableFooterRows?.length ?? 0) > 0 && (
                <tfoot>
                  {group.tableFooterRows?.map((row, rowIndex) => {
                    const labelSpan = Math.min(
                      fields.length,
                      Math.max(1, row.labelColSpan ?? 1),
                    );
                    return (
                      <tr key={`${row.label}-${rowIndex}`}>
                        {(hasRowLabel || showRowNumbers) && (
                          <td className="p-1 border-1 border-200 bg-gray-50" />
                        )}
                        <td
                          colSpan={labelSpan}
                          className="p-1 border-1 border-200 bg-gray-50 text-right font-medium"
                        >
                          {row.label}
                        </td>
                        {fields.slice(labelSpan).map((field) => (
                          <td key={field.key} className="p-1 border-1 border-200 text-right">
                            {row.values[field.key] ? <Placeholder /> : null}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tfoot>
              )}
              {withFooter &&
                footer.length > 0 &&
                hasRowLabel &&
                !isColumnAlignedFooter(footer) && (
                  <tfoot>
                    {footer.map((item) => {
                      const targetColumn = item.column ?? fields[0]?.key;
                      return (
                        <tr key={`${item.ref}-${targetColumn ?? ''}`}>
                          <td className="p-1 border-1 border-200 bg-gray-50 font-medium">
                            {item.label}
                          </td>
                          {fields.map((field) => (
                            <td key={field.key} className="p-1 border-1 border-200 text-right">
                              {field.key === targetColumn ? <Placeholder /> : null}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tfoot>
                )}
              {/* Computed summary (Mean / SD / % RSD …) directly BENEATH the table.
                  Flat strip for all-labeled footers; column-aligned rows (one
                  per labeled group, placeholder cells under each compound
                  column) when the footer carries unlabeled items. Shape only —
                  no per-template branching. Rendered once, after the last block. */}
              {withFooter &&
                footer.length > 0 &&
                !(hasRowLabel && !isColumnAlignedFooter(footer)) &&
                (isColumnAlignedFooter(footer) ? (
                  hasRowLabel ? (
                    <tfoot>
                      {groupFooterRows(footer).map((row, r) => {
                        const cells = footerCellsByColumn(row, footerColumnKeys);
                        return (
                          <tr key={r}>
                            <td className="p-1 border-1 border-200 bg-gray-50 font-medium">
                              {row.label}
                            </td>
                            {fields.map((field) => {
                              const cell = cells.get(field.key);
                              return (
                                <td key={field.key} className="p-1 border-1 border-200 text-right">
                                  {cell ? <Placeholder /> : null}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tfoot>
                  ) : (
                    <tfoot>
                      {groupFooterRows(footer).map((row, r) => (
                        <tr key={r}>
                          {showRowNumbers && (
                            <td className="p-1 border-1 border-200 bg-gray-50" />
                          )}
                          {/* Row label under the first field column. */}
                          <td className="p-1 border-1 border-200 bg-gray-50 font-medium">
                            {row.label}
                          </td>
                          {/* One placeholder per compound column (fields[1..]). */}
                          {fields.slice(1).map((f, c) => {
                            const cell = row.cells[c];
                            return (
                              <td key={f.key} className="p-1 border-1 border-200 text-right">
                                {cell ? <Placeholder /> : null}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tfoot>
                  )
                ) : (
                  <tfoot>
                    <tr>
                      <td
                        className="p-1 border-1 border-200 bg-gray-50 text-right font-medium"
                        colSpan={colSpan}
                      >
                        <span className="inline-flex flex-wrap gap-3 justify-content-end">
                          {footer.map((item) => (
                            <span key={item.ref} className="inline-flex align-items-center gap-1">
                              <span className="text-500">
                                {item.label}
                                {item.unit ? ` (${item.unit})` : ''}
                              </span>
                              <Placeholder />
                            </span>
                          ))}
                        </span>
                      </td>
                    </tr>
                  </tfoot>
                ))}
            </table>
          </Fragment>
        );

        return (
          <Card key={group.key} title={group.label ?? group.key}>
            {headerInputs.length > 0 && (
              <div className="flex flex-wrap align-items-center gap-3 mb-2">
                {headerInputs.map(({ item, field }) => (
                  <div className="flex align-items-center gap-2" key={field.key}>
                    <span className="text-sm font-medium text-700 white-space-nowrap">
                      {item.label ?? header(field)}
                    </span>
                    <span
                      className="border-1 border-200 border-round px-2 py-1 text-right text-400"
                      style={{
                        width: item.width ?? (field.type === 'text' ? '20rem' : '8rem'),
                        maxWidth: '100%',
                      }}
                    >
                      <Placeholder />
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Read-only context summary ABOVE the table (e.g. Batch / AR / TRF). */}
            {headerContext.length > 0 && (
              <table
                className="w-full text-sm mb-2"
                style={{ borderCollapse: 'collapse' }}
              >
                <tbody>
                  {chunk(headerContext, 3).map((trio, i) => (
                    <tr key={i}>
                      {trio.map((item) => (
                        <Fragment key={item.ref}>
                          <th
                            scope="row"
                            className="text-left p-1 border-1 border-200 bg-gray-50 font-medium"
                          >
                            {item.label}
                          </th>
                          <td className="p-1 border-1 border-200 text-right">
                            <Placeholder />
                          </td>
                        </Fragment>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {blocks.map((block, blockIndex) =>
              renderPreviewTable(
                block.title,
                block.startRow,
                block.endRow,
                blockIndex === blocks.length - 1,
                blockIndex,
              ),
            )}
            {group.note && <p className="text-xs text-600 m-0 mt-2">{group.note}</p>}
          </Card>
        );
      })}

      {/* ── Acceptance criteria ── */}
      {criteria.length > 0 && (
        <Card title="Acceptance Criteria">
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th scope="col" className="text-left p-1 border-1 border-200 bg-gray-50">
                  Criterion
                </th>
                <th scope="col" className="text-left p-1 border-1 border-200 bg-gray-50">
                  Limit
                </th>
                <th scope="col" className="text-left p-1 border-1 border-200 bg-gray-50">
                  Severity
                </th>
                <th scope="col" className="text-left p-1 border-1 border-200 bg-gray-50">
                  Result
                </th>
              </tr>
            </thead>
            <tbody>
              {criteria.map((c) => {
                const advisory = (c.severity ?? 'blocking') === 'advisory';
                return (
                  <tr key={c.key}>
                    <td className="p-1 border-1 border-200">{c.label ?? c.key}</td>
                    <td className="p-1 border-1 border-200">
                      {c.limitText ||
                        formatLimit(c.operator, Array.isArray(c.limit) ? c.limit : [c.limit])}
                    </td>
                    <td className="p-1 border-1 border-200">
                      <Tag
                        value={advisory ? 'advisory' : 'blocking'}
                        severity={advisory ? 'warning' : 'danger'}
                        aria-label={`${advisory ? 'advisory' : 'blocking'} criterion`}
                      />
                    </td>
                    <td className="p-1 border-1 border-200">
                      <Tag value="Not assessed" severity="secondary" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      {/* ── Reportable result ── */}
      <Card title="Reportable Result">
        <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <tr>
              <th
                scope="row"
                className="text-left p-1 border-1 border-200 bg-gray-50 font-medium w-3"
              >
                Reportable result
              </th>
              <td className="p-1 border-1 border-200 font-mono">
                {definition?.resultRef ?? 'not set'}
              </td>
            </tr>
            <tr>
              <th
                scope="row"
                className="text-left p-1 border-1 border-200 bg-gray-50 font-medium w-3"
              >
                Result unit
              </th>
              <td className="p-1 border-1 border-200 font-medium">
                {template.result_unit || EMPTY}
              </td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  );
};
