/**
 * Generic worksheet entry form.
 *
 * Renders *any* template definition without per-archetype branching — that is
 * the whole point of reducing 35 workbooks to 14 archetypes, so any special
 * casing here would give the abstraction back.
 *
 * Layout follows the definition:
 *   - context fields          → read-only chips, editable only when `overridable`
 *   - `singleton` groups      → a field grid
 *   - `table`/`sequence`      → an editable table with add/remove row
 *   - `calculated` fields     → read-only, visibly derived, dimmed while stale
 *
 * Calculated values are never held in form state. They come back from the
 * server's preview, so what the analyst sees is what the engine computed rather
 * than a re-implementation of it in TypeScript that could silently diverge.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Dropdown } from 'primereact/dropdown';
import { InputNumber } from 'primereact/inputnumber';
import { InputText } from 'primereact/inputtext';
import { Message } from 'primereact/message';
import { Tag } from 'primereact/tag';
import { formatLimit } from '../models/describeDefinition';
import { usePreview } from '../hooks/useWorksheet';
import type {
  CriterionResult,
  FieldDef,
  GroupDef,
  WorksheetComputed,
  WorksheetDetail,
  WorksheetRow,
} from '../models/testTemplate.types';

type Values = Record<string, WorksheetRow[]>;

interface WorksheetFormProps {
  detail: WorksheetDetail;
  /** False while the parent TRF is at a status that forbids editing. */
  editable: boolean;
  saving?: boolean;
  onSave: (payload: {
    context_values: Record<string, unknown>;
    group_values: Values;
  }) => void;
}

const EDITABLE_KINDS = new Set(['input', 'area']);

function isEditableField(field: FieldDef): boolean {
  return EDITABLE_KINDS.has(field.kind) || (field.kind === 'context' && !!field.overridable);
}

function rowCount(group: GroupDef, stored: WorksheetRow[] | undefined): number {
  if (group.kind === 'singleton') return 1;
  if (stored && stored.length) return stored.length;
  return group.rows?.default ?? group.rows?.min ?? 1;
}

/** Seeds editable form state from the worksheet's stored values. */
function seedValues(detail: WorksheetDetail): Values {
  const out: Values = {};
  for (const group of detail.template.definition?.groups ?? []) {
    const stored = detail.worksheet.group_values?.[group.key];
    const count = rowCount(group, stored);
    out[group.key] = Array.from({ length: count }, (_, i) => {
      const source = stored?.[i] ?? {};
      const row: WorksheetRow = {};
      for (const field of group.fields ?? []) {
        if (!isEditableField(field)) continue;
        row[field.key] =
          source[field.key] !== undefined && source[field.key] !== null
            ? source[field.key]
            : (field.default ?? null);
      }
      return row;
    });
  }
  return out;
}

function displayValue(value: unknown, field: FieldDef): string {
  if (value === null || value === undefined || value === '') return '—';
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

function CriterionRow({ criterion }: { criterion: CriterionResult }) {
  const limit = criterion.limit_text || formatLimit(criterion.operator, criterion.limit);
  const advisory = criterion.severity === 'advisory';

  //  `null` is "not yet assessable" — an empty observed value. Rendering it as a
  //  failure would have analysts chasing a problem that does not exist yet.
  const tag =
    criterion.passed === null ? (
      <Tag value="Not assessed" severity="secondary" />
    ) : criterion.passed ? (
      <Tag value="Pass" severity="success" />
    ) : (
      <Tag value={advisory ? 'Outside limit' : 'Fail'} severity={advisory ? 'warning' : 'danger'} />
    );

  return (
    <div className="flex justify-content-between align-items-center gap-2 py-1">
      <div className="text-sm">
        <span className="font-medium">{criterion.label}</span>
        <span className="text-500"> · {limit}</span>
        {advisory && <span className="text-500 text-xs"> (advisory)</span>}
      </div>
      <div className="flex align-items-center gap-2">
        <span className="font-mono text-sm">
          {criterion.observed === null || criterion.observed === undefined
            ? '—'
            : typeof criterion.observed === 'number'
              ? Number(criterion.observed.toPrecision(6))
              : String(criterion.observed)}
        </span>
        {tag}
      </div>
    </div>
  );
}

export const WorksheetForm = ({ detail, editable, saving, onSave }: WorksheetFormProps) => {
  const definition = detail.template.definition ?? {};
  const groups = definition.groups ?? [];
  const contextFields = definition.context ?? [];

  const [values, setValues] = useState<Values>(() => seedValues(detail));
  const [contextValues, setContextValues] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);
  //  Per-section edit locks: a group is read-only until its "Edit" button puts
  //  its key in here. Whole-worksheet editability (from the TRF status) is the
  //  outer gate; this is the finer, per-subsection control on top of it.
  const [editingGroups, setEditingGroups] = useState<Set<string>>(new Set());

  const preview = usePreview(detail.worksheet.id);
  //  Server-computed state: the freshest preview, falling back to what the
  //  detail response already carried.
  const computed: WorksheetComputed = preview.computed ?? detail.computed;

  const overridableContext = useMemo(
    () => contextFields.filter((f) => f.overridable),
    [contextFields],
  );

  //  Re-seed when a different worksheet loads, or after a save returns new
  //  stored values, so the form never keeps a draft belonging to another record.
  const seededFor = useRef<string>('');
  useEffect(() => {
    const token = `${detail.worksheet.id}:${detail.worksheet.modified_date ?? ''}`;
    if (seededFor.current === token) return;
    seededFor.current = token;
    const seeded = seedValues(detail);
    setValues(seeded);
    setContextValues({});
    setDirty(false);
    setEditingGroups(new Set());
    preview.reset(detail.computed);
    //  Compute calculated fields from the seeded/stored inputs straight away.
    //  Without this, derived cells like Standard Details → Concentration (ppm)
    //  render blank until the analyst edits a field, even though every input
    //  needed is already present. Fired immediately (no debounce) so the value
    //  is there on first paint.
    preview.request({ group_values: seeded, context_values: {} }, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  const recalculate = (nextValues: Values, nextContext: Record<string, unknown>) => {
    preview.request({ group_values: nextValues, context_values: nextContext });
  };

  const setCell = (groupKey: string, rowIndex: number, fieldKey: string, value: unknown) => {
    const next: Values = {
      ...values,
      [groupKey]: values[groupKey].map((row, i) =>
        i === rowIndex ? { ...row, [fieldKey]: value } : row,
      ),
    };
    setValues(next);
    setDirty(true);
    recalculate(next, contextValues);
  };

  const setContext = (key: string, value: unknown) => {
    const next = { ...contextValues, [key]: value };
    setContextValues(next);
    setDirty(true);
    recalculate(values, next);
  };

  const addRow = (group: GroupDef) => {
    const max = group.rows?.max ?? 1;
    if (values[group.key].length >= max) return;
    const blank: WorksheetRow = {};
    for (const field of group.fields ?? []) {
      if (isEditableField(field)) blank[field.key] = field.default ?? null;
    }
    const next = { ...values, [group.key]: [...values[group.key], blank] };
    setValues(next);
    setDirty(true);
    recalculate(next, contextValues);
  };

  const removeRow = (group: GroupDef, rowIndex: number) => {
    const min = group.rows?.min ?? 1;
    if (values[group.key].length <= min) return;
    const next = {
      ...values,
      [group.key]: values[group.key].filter((_, i) => i !== rowIndex),
    };
    setValues(next);
    setDirty(true);
    recalculate(next, contextValues);
  };

  const renderInput = (group: GroupDef, rowIndex: number, field: FieldDef) => {
    const value = values[group.key]?.[rowIndex]?.[field.key] ?? null;
    const disabled = !isGroupEditing(group.key);
    const label = `${group.label ?? group.key} row ${rowIndex + 1} ${field.label ?? field.key}`;

    if (field.options && field.options.length) {
      return (
        <Dropdown
          value={value}
          options={field.options.map((o) => ({ label: o, value: o }))}
          onChange={(e) => setCell(group.key, rowIndex, field.key, e.value)}
          disabled={disabled}
          className="w-full"
          aria-label={label}
        />
      );
    }
    if (field.type === 'text' || field.type === 'date') {
      return (
        <InputText
          value={(value as string) ?? ''}
          onChange={(e) => setCell(group.key, rowIndex, field.key, e.target.value)}
          disabled={disabled}
          className="w-full"
          aria-label={label}
        />
      );
    }
    return (
      <InputNumber
        value={value as number | null}
        onValueChange={(e) => setCell(group.key, rowIndex, field.key, e.value ?? null)}
        disabled={disabled}
        className="w-full"
        inputClassName="w-full text-right font-mono"
        //  Areas come off a chromatogram at full precision; a fixed maxFraction
        //  would quietly truncate a raw instrument reading.
        maxFractionDigits={field.kind === 'area' ? 6 : 6}
        useGrouping={false}
        aria-label={label}
      />
    );
  };

  const computedCell = (group: GroupDef, rowIndex: number, field: FieldDef) => {
    const value = computed.rows?.[group.key]?.[rowIndex]?.[field.key];
    return (
      <span
        className={`font-mono text-right block ${preview.stale ? 'text-400' : 'text-900 font-medium'}`}
        title={field.expression}
      >
        {displayValue(value, field)}
      </span>
    );
  };

  //  Render a table group's optional footer summary (e.g. Mean/SD/%RSD) from the
  //  server-computed values, addressed by dotted ref like `stats.rsd_std`.
  const renderGroupFooter = (group: GroupDef) => {
    if (!group.footer || group.footer.length === 0) return null;
    return (
      <div className="mt-2 border-1 border-200 border-round overflow-hidden" style={{ maxWidth: '28rem' }}>
        {group.footer.map((item) => {
          const raw = computed.values?.[item.ref];
          const text =
            raw === null || raw === undefined || raw === ''
              ? '—'
              : typeof raw === 'number'
                ? item.rounding?.mode && item.rounding.mode !== 'none' && typeof item.rounding.digits === 'number'
                  ? raw.toFixed(item.rounding.digits)
                  : String(Number(raw.toPrecision(12)))
                : String(raw);
          const shown = item.unit && text !== '—' ? `${text} ${item.unit}` : text;
          return (
            <div
              key={item.ref}
              className="flex justify-content-between align-items-center px-3 py-2 border-bottom-1 border-100"
            >
              <span className="text-sm font-medium text-700">{item.label}</span>
              <span className={`font-mono text-sm ${preview.stale ? 'text-400' : 'text-900 font-semibold'}`}>
                {shown}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  const handleSave = () => onSave({ context_values: contextValues, group_values: values });

  //  ── Per-section controls ──
  //  A section is only interactive when the worksheet as a whole is editable
  //  (TRF status) AND the analyst has clicked Edit on that section.
  const isGroupEditing = (groupKey: string) => editable && editingGroups.has(groupKey);

  const startEditGroup = (groupKey: string) => {
    setEditingGroups((prev) => new Set(prev).add(groupKey));
  };

  //  Save persists the WHOLE worksheet, not just this group: calculated fields
  //  span groups (standard areas feed the statistics, which feed the assay), so
  //  the backend evaluates and stores them together. The button simply lives on
  //  the section the analyst finished with, and re-locks it afterward.
  const saveGroup = (groupKey: string) => {
    onSave({ context_values: contextValues, group_values: values });
    setEditingGroups((prev) => {
      const next = new Set(prev);
      next.delete(groupKey);
      return next;
    });
  };

  //  Clear resets this section's rows/fields to their defaults (tables fall back
  //  to the minimum row count), recalculates, and persists — so "Delete" empties
  //  the subsection without removing the group the template defines.
  const clearGroup = (group: GroupDef) => {
    const min = group.rows?.min ?? 1;
    const count = group.kind === 'singleton' ? 1 : min;
    const blankRows: WorksheetRow[] = Array.from({ length: count }, () => {
      const row: WorksheetRow = {};
      for (const field of group.fields ?? []) {
        if (isEditableField(field)) row[field.key] = field.default ?? null;
      }
      return row;
    });
    const next = { ...values, [group.key]: blankRows };
    setValues(next);
    setDirty(true);
    recalculate(next, contextValues);
    onSave({ context_values: contextValues, group_values: next });
    setEditingGroups((prev) => {
      const nextSet = new Set(prev);
      nextSet.delete(group.key);
      return nextSet;
    });
  };

  /** The Edit / Save / Delete toolbar shown on each editable section. */
  const renderGroupToolbar = (group: GroupDef) => {
    if (!editable) return null;
    const editingThis = editingGroups.has(group.key);
    return (
      <div className="flex align-items-center gap-1">
        {editingThis ? (
          <Button
            label="Save"
            icon="pi pi-save"
            size="small"
            text
            loading={saving}
            onClick={() => saveGroup(group.key)}
          />
        ) : (
          <Button
            label="Edit"
            icon="pi pi-pencil"
            size="small"
            text
            onClick={() => startEditGroup(group.key)}
          />
        )}
        <Button
          label="Delete"
          icon="pi pi-trash"
          size="small"
          text
          severity="danger"
          onClick={() => clearGroup(group)}
          aria-label={`Clear ${group.label ?? group.key}`}
        />
      </div>
    );
  };

  const areaFieldCount = groups.reduce(
    (n, g) => n + (g.fields ?? []).filter((f) => f.kind === 'area').length,
    0,
  );

  return (
    <div className="flex flex-column gap-3">
      {/* ── Context ── */}
      {contextFields.length > 0 && (
        <Card title="Context">
          <div className="grid">
            {contextFields.map((field) => {
              const stored = detail.worksheet.context_values?.[field.key];
              const current = contextValues[field.key] ?? stored;
              return (
                <div className="col-12 md:col-4 lg:col-3" key={field.key}>
                  <label className="block text-xs text-500 mb-1">{field.label ?? field.key}</label>
                  {field.overridable && editable ? (
                    field.type === 'number' ? (
                      <InputNumber
                        value={(current as number | null) ?? null}
                        onValueChange={(e) => setContext(field.key, e.value ?? null)}
                        className="w-full"
                        inputClassName="w-full font-mono"
                        maxFractionDigits={6}
                        useGrouping={false}
                        aria-label={field.label ?? field.key}
                      />
                    ) : (
                      <InputText
                        value={(current as string) ?? ''}
                        onChange={(e) => setContext(field.key, e.target.value)}
                        className="w-full"
                        aria-label={field.label ?? field.key}
                      />
                    )
                  ) : (
                    <span className="text-sm font-medium">
                      {current === null || current === undefined || current === ''
                        ? '—'
                        : String(current)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          {overridableContext.length > 0 && (
            <p className="text-xs text-500 m-0 mt-2">
              Fields without an input are taken from the TRF header and product master and cannot be
              overridden here.
            </p>
          )}
        </Card>
      )}

      {/* ── Groups ── */}
      {groups.map((group) => {
        const fields = group.fields ?? [];
        const editableFields = fields.filter(isEditableField);
        const calculatedFields = fields.filter((f) => f.kind === 'calculated');
        const rows = values[group.key] ?? [];
        const min = group.rows?.min ?? 1;
        const max = group.rows?.max ?? 1;
        const canAddRows = editable && group.kind !== 'singleton' && max > min;

        if (group.kind === 'singleton') {
          //  Only show the toolbar on sections the analyst can actually fill in.
          const hasEditable = editableFields.length > 0;
          return (
            <Card key={group.key}>
              <div className="flex justify-content-between align-items-center mb-2">
                <h3 className="m-0 text-base">{group.label ?? group.key}</h3>
                {hasEditable && renderGroupToolbar(group)}
              </div>
              <div className="grid">
                {editableFields.map((field) => (
                  <div className="col-12 md:col-4 lg:col-3" key={field.key}>
                    <label className="block text-xs text-500 mb-1">
                      {field.label ?? field.key}
                      {field.unit ? ` (${field.unit})` : ''}
                      {field.kind === 'area' && (
                        <i
                          className="pi pi-chart-line ml-1 text-blue-500"
                          title="Chromatographic area — manual entry pending the Waters integration"
                        />
                      )}
                    </label>
                    {renderInput(group, 0, field)}
                  </div>
                ))}
                {calculatedFields.map((field) => (
                  <div className="col-12 md:col-4 lg:col-3" key={field.key}>
                    <label className="block text-xs text-500 mb-1">
                      {field.label ?? field.key}
                      {field.unit ? ` (${field.unit})` : ''}
                      <i className="pi pi-calculator ml-1 text-500" title={field.expression} />
                    </label>
                    <div className="bg-gray-50 border-1 border-200 border-round px-2 py-2">
                      {computedCell(group, 0, field)}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          );
        }

        const editingThisGroup = isGroupEditing(group.key);
        const hasEditableCols = editableFields.length > 0;
        return (
          <Card key={group.key}>
            <div className="flex justify-content-between align-items-center mb-2">
              <h3 className="m-0 text-base">{group.label ?? group.key}</h3>
              <div className="flex align-items-center gap-2">
                {canAddRows && editingThisGroup && (
                  <>
                    <span className="text-xs text-500">
                      {rows.length} of {max} row(s)
                    </span>
                    <Button
                      label="Add Row"
                      icon="pi pi-plus"
                      size="small"
                      text
                      onClick={() => addRow(group)}
                      disabled={rows.length >= max}
                    />
                  </>
                )}
                {hasEditableCols && renderGroupToolbar(group)}
              </div>
            </div>

            <div className="overflow-auto">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr className="bg-gray-50">
                    <th className="text-left p-2 text-500 font-medium" style={{ width: '3rem' }}>
                      #
                    </th>
                    {editableFields.map((field) => (
                      <th key={field.key} className="text-left p-2 text-500 font-medium">
                        {field.label ?? field.key}
                        {field.unit ? ` (${field.unit})` : ''}
                        {field.kind === 'area' && (
                          <i
                            className="pi pi-chart-line ml-1 text-blue-500"
                            title="Chromatographic area — manual entry pending the Waters integration"
                          />
                        )}
                      </th>
                    ))}
                    {calculatedFields.map((field) => (
                      <th
                        key={field.key}
                        className="text-right p-2 text-500 font-medium"
                        title={field.expression}
                      >
                        {field.label ?? field.key}
                        {field.unit ? ` (${field.unit})` : ''}
                        <i className="pi pi-calculator ml-1" />
                      </th>
                    ))}
                    {canAddRows && <th style={{ width: '3rem' }} />}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((_row, rowIndex) => (
                    <tr key={rowIndex} className="border-top-1 border-200">
                      <td className="p-2 text-500 font-mono">{rowIndex + 1}</td>
                      {editableFields.map((field) => (
                        <td className="p-1" key={field.key} style={{ minWidth: '9rem' }}>
                          {renderInput(group, rowIndex, field)}
                        </td>
                      ))}
                      {calculatedFields.map((field) => (
                        <td className="p-2" key={field.key} style={{ minWidth: '7rem' }}>
                          {computedCell(group, rowIndex, field)}
                        </td>
                      ))}
                      {canAddRows && (
                        <td className="p-1">
                          {editingThisGroup && (
                            <Button
                              icon="pi pi-trash"
                              size="small"
                              text
                              severity="danger"
                              disabled={rows.length <= min}
                              onClick={() => removeRow(group, rowIndex)}
                              aria-label={`Remove row ${rowIndex + 1}`}
                            />
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {renderGroupFooter(group)}
          </Card>
        );
      })}

      {/* ── Criteria & result ── */}
      {computed.criteria.length > 0 && (
        <Card title="Acceptance Criteria">
          {computed.has_blocking_failure && (
            <Message
              className="mb-2 w-full"
              severity="error"
              text="A blocking criterion is outside its limit. The result cannot be confirmed until this is resolved."
            />
          )}
          <div className="flex flex-column divide-y">
            {computed.criteria.map((c) => (
              <CriterionRow criterion={c} key={c.key} />
            ))}
          </div>
        </Card>
      )}

      <Card>
        <div className="flex justify-content-between align-items-center flex-wrap gap-3">
          <div>
            <span className="text-sm text-500">Reportable result</span>
            <div className="text-2xl font-medium font-mono">
              {computed.reportable_result === null || computed.reportable_result === undefined
                ? '—'
                : String(
                    typeof computed.reportable_result === 'number'
                      ? Number(computed.reportable_result.toPrecision(12))
                      : computed.reportable_result,
                  )}
              {detail.template.result_unit ? (
                <span className="text-base text-500 ml-1">{detail.template.result_unit}</span>
              ) : null}
            </div>
            {preview.stale && <small className="text-500">Recalculating…</small>}
            {preview.error != null && (
              <small className="text-red-500 block">
                Could not recalculate — the entered values may be incomplete.
              </small>
            )}
          </div>

          {editable && (
            <Button
              label={dirty ? 'Save Worksheet' : 'Saved'}
              icon="pi pi-save"
              onClick={handleSave}
              loading={saving}
              disabled={!dirty}
            />
          )}
        </div>
        {areaFieldCount > 0 && (
          <p className="text-xs text-500 m-0 mt-2">
            <i className="pi pi-chart-line mr-1 text-blue-500" />
            {areaFieldCount} chromatographic area field(s) are entered manually. Once the Waters CDS
            integration is live these will be imported along with the chromatogram PDFs.
          </p>
        )}
      </Card>
    </div>
  );
};
