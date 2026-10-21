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
import {
  isMergedContinuation,
  normalizeMergeValue,
  shouldMergeColumn,
} from '../models/columnMerge';
import { groupFooterRows, isColumnAlignedFooter } from '../models/groupFooter';
import type { FieldDef, GroupDef } from '../models/testTemplate.types';

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

const visibleFields = (group: GroupDef): FieldDef[] =>
  (group.fields ?? []).filter((f) => !f.hidden);

/** Default row count a worksheet from this template would seed (matches WorksheetForm). */
const rowCount = (group: GroupDef): number => group.rows?.default ?? group.rows?.min ?? 1;

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
  const criteria = useMemo(() => definition?.criteria ?? [], [definition]);

  if (isLoading) return <p className="text-500">Loading worksheet...</p>;
  if (!template || templateId == null)
    return <Message severity="warn" text="Template not found." />;

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
        const fields = visibleFields(group);
        if (fields.length === 0) return null;

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
        const headerContext = group.headerContext ?? [];
        const footer = group.footer ?? [];
        const colSpan = fields.length + 1; // + the `#` column

        return (
          <Card key={group.key} title={group.label ?? group.key}>
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

            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th
                    scope="col"
                    className="text-left p-1 border-1 border-200 bg-gray-50"
                    style={{ width: '3rem' }}
                  >
                    #
                  </th>
                  {fields.map((f) => (
                    <th
                      key={f.key}
                      scope="col"
                      className={`p-1 border-1 border-200 bg-gray-50 ${
                        f.kind === 'calculated' ? 'text-right' : 'text-left'
                      }`}
                    >
                      {fieldHeader(f)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: rows }, (_, r) => (
                  <tr key={r}>
                    <td className="p-1 border-1 border-200 text-500 font-mono">{r + 1}</td>
                    {fields.map((f) => {
                      //  Visual-merge parity: the preview has no computed values
                      //  (every cell is a blank placeholder), so every value
                      //  normalises to empty and `isMergedContinuation` is always
                      //  false — blanks never merge. Wiring it here keeps all
                      //  three render sites on one code path; it is a no-op today.
                      if (
                        shouldMergeColumn(group, f) &&
                        isMergedContinuation(
                          Array.from({ length: rows }, () => normalizeMergeValue(EMPTY)),
                          r,
                        )
                      ) {
                        return (
                          <td key={f.key} className="p-1 border-1 border-200 text-right" />
                        );
                      }
                      return (
                        <td key={f.key} className="p-1 border-1 border-200 text-right">
                          <Placeholder />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
              {/* Computed summary (Mean / SD / % RSD …) directly BENEATH the table.
                  Flat strip for all-labeled footers; column-aligned rows (one
                  per labeled group, placeholder cells under each compound
                  column) when the footer carries unlabeled items. Shape only —
                  no per-template branching. */}
              {footer.length > 0 &&
                (isColumnAlignedFooter(footer) ? (
                  <tfoot>
                    {groupFooterRows(footer).map((row, r) => (
                      <tr key={r}>
                        {/* `#` column — empty, mirrors the data table. */}
                        <td className="p-1 border-1 border-200 bg-gray-50" />
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
