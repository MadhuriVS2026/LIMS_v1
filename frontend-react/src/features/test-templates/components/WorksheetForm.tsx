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
import { WorksheetChart } from './WorksheetChart';
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
  /**
   * Debounced background save of in-progress edits. Same payload as onSave but
   * must persist WITHOUT prompting (no correction-reason dialog), so it is only
   * wired in plain entry mode. Omit to disable autosave.
   */
  onAutosave?: (payload: {
    context_values: Record<string, unknown>;
    group_values: Values;
  }) => void;
  /** When provided, shows a "Submit for Review" button beside Save. */
  onSubmitForReview?: () => void;
  submittingForReview?: boolean;
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

/**
 * Responsive column span for a singleton field, sized to its label so a long
 * caption like "Retention Time of Main peak (For RRT)" gets a wider box instead
 * of being crammed into a fixed quarter-width column. Short labels stay compact
 * so a row still fits several fields side by side. Always full width on mobile.
 */
function fieldColClass(field: FieldDef): string {
  //  Free-text single fields (Title, Remarks, Parameter, Product name, ...) read
  //  as a line of prose, so give them the full page width rather than a narrow
  //  numeric-sized box. Dropdowns keep their own sizing below.
  if (field.type === 'text' && !(field.options && field.options.length)) {
    return 'col-12';
  }
  const caption = `${field.label ?? field.key}${field.unit ? ` (${field.unit})` : ''}`;
  const len = caption.length;
  if (len > 44) return 'col-12 md:col-8 lg:col-6';
  if (len > 26) return 'col-12 md:col-6 lg:col-4';
  return 'col-12 md:col-4 lg:col-3';
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

export const WorksheetForm = ({
  detail,
  editable,
  saving,
  onSave,
  onAutosave,
  onSubmitForReview,
  submittingForReview,
}: WorksheetFormProps) => {
  const definition = detail.template.definition ?? {};
  //  Per-column clear control is scoped to this template only (TPL-A6A-0004).
  const allowClearColumn = detail.worksheet.template_code === 'TPL-A6A-0004';
  const groups = definition.groups ?? [];
  const contextFields = definition.context ?? [];

  const [values, setValues] = useState<Values>(() => seedValues(detail));
  const [contextValues, setContextValues] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);
  //  Per-section edit locks: a group is read-only until its "Edit" button puts
  //  its key in here. Whole-worksheet editability (from the TRF status) is the
  //  outer gate; this is the finer, per-subsection control on top of it.
  const [editingGroups, setEditingGroups] = useState<Set<string>>(new Set());
  //  Columns the user has deleted from a table (UI-only, keyed "<group>.<field>").
  //  Deleting hides the column AND blanks its values so it drops out of the
  //  calculations; the template field itself is untouched.
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(new Set());

  const preview = usePreview(detail.worksheet.id);
  //  Server-computed state: the freshest preview, falling back to what the
  //  detail response already carried.
  const computed: WorksheetComputed = preview.computed ?? detail.computed;

  const overridableContext = useMemo(
    () => contextFields.filter((f) => f.overridable),
    [contextFields],
  );

  //  Human labels for every field key/ref, so a blank calculated cell can name
  //  the inputs it is still waiting on rather than showing a bare dash.
  const labelByRef = useMemo(() => {
    const map = new Map<string, string>();
    for (const cf of contextFields) map.set(cf.key, cf.label ?? cf.key);
    for (const g of groups) {
      for (const f of g.fields ?? []) {
        const label = f.label ?? f.key;
        map.set(f.key, label); // bare (same-group) reference
        map.set(`${g.key}.${f.key}`, label); // qualified reference
      }
    }
    return map;
  }, [contextFields, groups]);

  //  Resolve whether a referenced value is currently present (non-empty).
  //  Checks, in order: same-row computed value, same-row entered value,
  //  qualified computed aggregate (stats.*/standard.*), context, then any
  //  top-level computed value.
  const refIsPresent = (ref: string, group: GroupDef, rowIndex: number): boolean => {
    const notEmpty = (v: unknown) => v !== null && v !== undefined && v !== '';

    if (ref.includes('.')) {
      //  Qualified aggregate/singleton ref, e.g. `stats.mean_std`.
      return notEmpty(computed.values?.[ref]);
    }

    //  A bare ref inside a table row may itself be a calculated field (e.g.
    //  `avg_area`), which the engine puts in computed.rows — check that first so
    //  a computed input is not wrongly reported as missing.
    const computedRow = computed.rows?.[group.key]?.[rowIndex];
    if (computedRow && ref in computedRow) return notEmpty(computedRow[ref]);

    const rowVal = values[group.key]?.[rowIndex]?.[ref];
    if (rowVal !== undefined) return notEmpty(rowVal);

    const ctxVal = contextValues[ref] ?? detail.worksheet.context_values?.[ref];
    if (ctxVal !== undefined) return notEmpty(ctxVal);

    return notEmpty(computed.values?.[ref]);
  };

  //  Parse a calculated field's expression for the inputs it depends on, and
  //  return the labels of those that are still empty. Purely advisory — it does
  //  not change the computation, only explains a blank cell.
  const missingInputsFor = (field: FieldDef, group: GroupDef, rowIndex: number): string[] => {
    if (!field.expression) return [];
    //  Identifiers, including dotted refs. Excludes function names (followed by
    //  "(") like mean/sd/rsd/pool/trunc/round.
    const tokens = field.expression.match(/[A-Za-z_][A-Za-z0-9_.]*/g) ?? [];
    const seen = new Set<string>();
    const missing: string[] = [];
    for (const tok of tokens) {
      if (!labelByRef.has(tok)) continue; // skip functions / unknowns
      if (seen.has(tok)) continue;
      seen.add(tok);
      if (!refIsPresent(tok, group, rowIndex)) {
        missing.push(labelByRef.get(tok) as string);
      }
    }
    return missing;
  };

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
    //  Use the computed state the detail response already carried.
    preview.reset(detail.computed);
    //  If the worksheet has no computed snapshot yet (never previewed, or the
    //  template gained calculated fields after it was last saved) but it does
    //  carry stored input data, fire a one-off preview so calculated cells show
    //  on open instead of staying blank until the analyst edits something. The
    //  engine is blank-tolerant (missing inputs yield blanks, not errors), so
    //  this no longer risks the 400s that an eager preview once caused.
    const hasComputedRows =
      detail.computed?.rows && Object.keys(detail.computed.rows).length > 0;
    const hasStoredInput =
      detail.worksheet.group_values &&
      Object.values(detail.worksheet.group_values).some(
        (rows) => Array.isArray(rows) && rows.length > 0,
      );
    if (!hasComputedRows && hasStoredInput) {
      preview.request({ group_values: seeded, context_values: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  const recalculate = (nextValues: Values, nextContext: Record<string, unknown>) => {
    preview.request({ group_values: nextValues, context_values: nextContext });
  };

  //  ── Autosave ──
  //  Persist in-progress edits in the background so a closed tab or lost session
  //  never discards unsaved work. Runs on a fixed 5-minute interval: on each
  //  tick, if there are unsaved changes it saves the current state. A ref holds
  //  the latest values + dirty flag so the interval always sees current state
  //  without re-arming the timer on every keystroke. Only runs when the parent
  //  supplied onAutosave (plain entry mode — never correction mode, which needs
  //  a reason).
  const AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
  const latest = useRef({ values, contextValues, dirty, saving });
  latest.current = { values, contextValues, dirty, saving };
  useEffect(() => {
    if (!onAutosave || !editable) return;
    const timer = window.setInterval(() => {
      const cur = latest.current;
      if (!cur.dirty || cur.saving) return;
      onAutosave({
        context_values: cur.contextValues,
        group_values: cur.values,
      });
    }, AUTOSAVE_INTERVAL_MS);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editable]);

  //  ── Row-aligned mirroring ──
  //  A field may declare `mirrorFrom: "<group>.<field>"` to echo another table's
  //  column by row index (e.g. the shared Time Interval column into the %Content
  //  / %Release tables). The calc engine only sees other tables as whole columns,
  //  not row-aligned, so this is done here: copy the source cell into the mirror
  //  cell whenever the source changes, and render the mirror read-only.
  const mirrorSpecs = useMemo(() => {
    const specs: { group: string; field: string; srcGroup: string; srcField: string }[] = [];
    for (const g of groups) {
      for (const f of g.fields ?? []) {
        if (f.mirrorFrom && f.mirrorFrom.includes('.')) {
          const [srcGroup, srcField] = f.mirrorFrom.split('.', 2);
          specs.push({ group: g.key, field: f.key, srcGroup, srcField });
        }
      }
    }
    return specs;
  }, [groups]);

  useEffect(() => {
    if (mirrorSpecs.length === 0) return;
    let changed = false;
    const next: Values = { ...values };
    for (const spec of mirrorSpecs) {
      const src = values[spec.srcGroup];
      const dst = values[spec.group];
      if (!src || !dst) continue;
      const updated = dst.map((row, i) => {
        const srcVal = src[i]?.[spec.srcField] ?? null;
        if ((row?.[spec.field] ?? null) === srcVal) return row;
        changed = true;
        return { ...row, [spec.field]: srcVal };
      });
      if (updated.some((r, i) => r !== dst[i])) next[spec.group] = updated;
    }
    if (changed) setValues(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values, mirrorSpecs]);

  //  Fields that mirror another column are display-only (filled from the source).
  const isMirrorField = (field: FieldDef) => !!field.mirrorFrom;

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

  //  Delete a whole input column from a table: hide it from view AND blank its
  //  values so it drops out of the calculations. The (shared, versioned)
  //  template field is untouched; this is a per-worksheet UI action.
  const deleteColumn = (group: GroupDef, fieldKey: string) => {
    const next = {
      ...values,
      [group.key]: values[group.key].map((row) => ({ ...row, [fieldKey]: null })),
    };
    setValues(next);
    setHiddenColumns((prev) => new Set(prev).add(`${group.key}.${fieldKey}`));
    setDirty(true);
    recalculate(next, contextValues);
  };

  //  Deletable (input) columns of a group, in definition order.
  const deletableColumns = (group: GroupDef): FieldDef[] =>
    (group.fields ?? []).filter((f) => !f.hidden && isEditableField(f));

  //  "Add column" is the inverse of delete: restore the first hidden input
  //  column of this group (up to the template's provisioned columns). There is
  //  no runtime schema change — only previously-deleted columns can come back.
  const hiddenCountFor = (group: GroupDef): number =>
    deletableColumns(group).filter((f) => hiddenColumns.has(`${group.key}.${f.key}`)).length;

  const addColumn = (group: GroupDef) => {
    const toRestore = deletableColumns(group).find((f) =>
      hiddenColumns.has(`${group.key}.${f.key}`),
    );
    if (!toRestore) return;
    setHiddenColumns((prev) => {
      const nextSet = new Set(prev);
      nextSet.delete(`${group.key}.${toRestore.key}`);
      return nextSet;
    });
    setDirty(true);
  };

  const renderInput = (group: GroupDef, rowIndex: number, field: FieldDef) => {
    const value = values[group.key]?.[rowIndex]?.[field.key] ?? null;
    //  Mirror fields are filled from their source column and never typed here.
    const disabled = !isGroupEditing(group.key) || isMirrorField(field);
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
    const isEmpty = value === null || value === undefined || value === '';
    const missing = isEmpty && !preview.stale ? missingInputsFor(field, group, rowIndex) : [];
    return (
      <span
        className={`font-mono text-right block ${preview.stale ? 'text-400' : 'text-900 font-medium'}`}
        style={{ wordBreak: 'break-word' }}
        title={field.expression}
      >
        {displayValue(value, field)}
        {missing.length > 0 && (
          <span
            className="block text-xs text-orange-500 font-normal mt-1"
            title={`Enter to calculate: ${missing.join(', ')}`}
          >
            awaiting: {missing.slice(0, 4).join(', ')}
            {missing.length > 4 ? `, +${missing.length - 4} more` : ''}
          </span>
        )}
      </span>
    );
  };

  //  Render a table group's optional footer summary (e.g. Mean/SD/%RSD) from the
  //  server-computed values, addressed by dotted ref like `stats.rsd_std`.
  const renderGroupFooter = (group: GroupDef) => {
    if (!group.footer || group.footer.length === 0) return null;
    return (
      <div
        className="mt-2 border-1 border-200 border-round overflow-hidden w-full"
        style={{ maxWidth: 'min(28rem, 100%)' }}
      >
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

  //  Render a table group's optional header-context strip: read-only values
  //  pulled from the worksheet context (auto-fetched from the TRF), shown as a
  //  compact row above the table — e.g. Batch/Stability/Packing/TRF/AR.
  const renderGroupHeaderContext = (group: GroupDef) => {
    if (!group.headerContext || group.headerContext.length === 0) return null;
    const valueFor = (ref: string) => {
      const v = contextValues[ref] ?? detail.worksheet.context_values?.[ref];
      return v === null || v === undefined || v === '' ? '—' : String(v);
    };
    return (
      <div className="mb-2 border-1 border-200 border-round overflow-hidden">
        <div className="grid m-0">
          {group.headerContext.map((item) => (
            <div
              key={item.ref}
              className="col-6 sm:col-4 md:col-2 p-2 border-right-1 border-bottom-1 border-100"
            >
              <div className="text-xs text-500 mb-1">{item.label}</div>
              <div className="text-sm font-medium text-900" style={{ wordBreak: 'break-word' }}>
                {valueFor(item.ref)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const handleSave = () => onSave({ context_values: contextValues, group_values: values });

  //  ── Context section per-section controls ──
  //  The Context block isn't a definition group, so it uses a synthetic key in
  //  the same editingGroups set to get the same Edit/Save/Delete behaviour.
  const CONTEXT_KEY = '__context__';
  const contextEditing = editable && editingGroups.has(CONTEXT_KEY);

  const saveContext = () => {
    onSave({ context_values: contextValues, group_values: values });
    setEditingGroups((prev) => {
      const next = new Set(prev);
      next.delete(CONTEXT_KEY);
      return next;
    });
  };

  //  Delete/Clear resets only the OVERRIDABLE context fields (the rest are
  //  sourced from the TRF/product and are read-only), then persists.
  const clearContext = () => {
    const next = { ...contextValues };
    for (const f of overridableContext) {
      next[f.key] = (f.default ?? null) as unknown;
    }
    setContextValues(next);
    setDirty(true);
    recalculate(values, next);
    onSave({ context_values: next, group_values: values });
    setEditingGroups((prev) => {
      const s = new Set(prev);
      s.delete(CONTEXT_KEY);
      return s;
    });
  };

  const renderContextToolbar = () => {
    //  Only meaningful when there is something editable to lock/unlock.
    if (!editable || overridableContext.length === 0) return null;
    return (
      <div className="flex align-items-center gap-1">
        {contextEditing ? (
          <Button label="Save" icon="pi pi-save" size="small" text loading={saving} onClick={saveContext} />
        ) : (
          <Button
            label="Edit"
            icon="pi pi-pencil"
            size="small"
            text
            onClick={() => setEditingGroups((prev) => new Set(prev).add(CONTEXT_KEY))}
          />
        )}
        <Button
          label="Delete"
          icon="pi pi-trash"
          size="small"
          text
          severity="danger"
          onClick={clearContext}
          aria-label="Clear Context overridable fields"
        />
      </div>
    );
  };

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
        <Card>
          <div className="flex justify-content-between align-items-center mb-2">
            <h3 className="m-0 text-base">Context</h3>
            {renderContextToolbar()}
          </div>
          <div className="grid">
            {contextFields.map((field) => {
              const stored = detail.worksheet.context_values?.[field.key];
              const current = contextValues[field.key] ?? stored;
              return (
                <div className="col-12 md:col-4 lg:col-3" key={field.key}>
                  <label className="block text-xs text-500 mb-1">{field.label ?? field.key}</label>
                  {field.overridable && contextEditing ? (
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
        //  `hidden` fields are still seeded/computed/stored (seedValues and the
        //  evaluator iterate the full definition), but are not rendered — used to
        //  keep intermediate calculations and defaults out of the visible table.
        const editableFields = fields.filter((f) => isEditableField(f) && !f.hidden);
        const calculatedFields = fields.filter((f) => f.kind === 'calculated' && !f.hidden);
        const rows = values[group.key] ?? [];
        const min = group.rows?.min ?? 1;
        const max = group.rows?.max ?? 1;
        const canAddRows = editable && group.kind !== 'singleton' && max > min;

        if (group.kind === 'singleton') {
          //  A singleton may carry a non-standard `chart` hint (UI-only). When
          //  present, render a line chart from another group's computed rows
          //  instead of a field grid, keeping the group label as the section
          //  header. Gated on `group.chart`, so every other singleton is
          //  unaffected.
          if (group.chart) {
            //  Editable title: the chart config may name a `titleField` on this
            //  group whose entered value becomes the chart's displayed title.
            const titleFieldKey = group.chart.titleField;
            const titleField = titleFieldKey
              ? (group.fields ?? []).find((f) => f.key === titleFieldKey)
              : undefined;
            const titleValue =
              (titleFieldKey
                ? (values[group.key]?.[0]?.[titleFieldKey] as string | undefined)
                : undefined) ||
              group.chart.title ||
              (group.label ?? group.key);
            return (
              <Card key={group.key}>
                <div className="flex justify-content-between align-items-center mb-2">
                  <h3 className="m-0 text-base">{group.label ?? group.key}</h3>
                </div>
                {titleField && (
                  <div className="mb-3" style={{ maxWidth: '32rem' }}>
                    <label className="block text-xs text-500 mb-1">
                      {titleField.label ?? 'Graph Title'}
                    </label>
                    {renderInput(group, 0, titleField)}
                  </div>
                )}
                <WorksheetChart
                  chart={group.chart}
                  computed={computed}
                  stale={preview.stale}
                  title={titleValue}
                />
              </Card>
            );
          }
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
                  <div className={fieldColClass(field)} key={field.key}>
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
                  <div className={fieldColClass(field)} key={field.key}>
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
        //  Wide tables (e.g. the 12-vessel dissolution timepoints) have far more
        //  columns than fit the card. A fixed layout squeezes them until some
        //  columns collapse to near-zero width and look "missing", so for
        //  many-column tables use an auto layout with a per-column min-width and
        //  let the wrapper scroll horizontally.
        //  Count deleted (hidden) columns in this group so the width logic
        //  reflects what is actually rendered after a column delete.
        const hiddenInGroup = [...editableFields, ...calculatedFields].filter((f) =>
          hiddenColumns.has(`${group.key}.${f.key}`),
        ).length;
        const tableColCount =
          1 + editableFields.length + calculatedFields.length - hiddenInGroup + (canAddRows ? 1 : 0);
        const wideTable = tableColCount > 8;
        //  Very wide tables (e.g. the 15-unit dissolution timepoints, ~16 cols)
        //  must show every column without horizontal scrolling. Compact mode
        //  shrinks the per-column min-width, cell padding and font so all
        //  columns fit the card width.
        const veryWideTable = tableColCount > 12;
        //  Per-column min-width: compact for very wide tables so 15+ columns fit.
        const colMinRem = veryWideTable ? 3 : 4.5;
        const cellPad = veryWideTable ? 'p-1' : 'p-2';
        const inputCellPad = veryWideTable ? 'p-1' : 'p-1';
        //  Render columns in definition order (not editable-first) so a template
        //  that places an input column after calculated ones — e.g. Spec Limit
        //  after Max in the dissolution release table — shows in that position.
        const visibleFields = fields.filter(
          (f) =>
            !f.hidden &&
            !hiddenColumns.has(`${group.key}.${f.key}`) &&
            (isEditableField(f) || f.kind === 'calculated'),
        );
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
                {/* Add Column: restore a deleted column (scoped to this template, edit mode). */}
                {allowClearColumn && editingThisGroup && (
                  <Button
                    label="Add Column"
                    icon="pi pi-plus"
                    size="small"
                    text
                    onClick={() => addColumn(group)}
                    disabled={hiddenCountFor(group) === 0}
                    tooltip={
                      hiddenCountFor(group) === 0
                        ? 'All columns are shown'
                        : `Restore a deleted column (${hiddenCountFor(group)} hidden)`
                    }
                  />
                )}
                {hasEditableCols && renderGroupToolbar(group)}
              </div>
            </div>

            {renderGroupHeaderContext(group)}

            <div style={wideTable && !veryWideTable ? { overflowX: 'auto' } : undefined}>
              <table
                className={`w-full ${veryWideTable ? 'text-xs' : 'text-sm'}`}
                style={
                  veryWideTable
                    ? //  Fit all columns to the card width: fixed layout spreads
                      //  the compact columns evenly, no horizontal scroll.
                      { borderCollapse: 'collapse', tableLayout: 'fixed', width: '100%' }
                    : wideTable
                      ? { borderCollapse: 'collapse', tableLayout: 'auto', minWidth: `${tableColCount * colMinRem}rem` }
                      : { borderCollapse: 'collapse', tableLayout: 'fixed' }
                }
              >
                <thead>
                  <tr className="bg-gray-50">
                    <th
                      className={`text-left ${cellPad} text-500 font-medium`}
                      style={{ width: veryWideTable ? '1.6rem' : '3rem' }}
                    >
                      #
                    </th>
                    {visibleFields.map((field) => {
                      const calc = field.kind === 'calculated';
                      return (
                        <th
                          key={field.key}
                          className={`${cellPad} text-500 font-medium ${calc ? 'text-right' : 'text-left'}`}
                          style={{ wordBreak: 'break-word' }}
                          title={calc ? field.expression : undefined}
                        >
                          {field.label ?? field.key}
                          {field.unit ? ` (${field.unit})` : ''}
                          {field.kind === 'area' && (
                            <i
                              className="pi pi-chart-line ml-1 text-blue-500"
                              title="Chromatographic area — manual entry pending the Waters integration"
                            />
                          )}
                          {calc && <i className="pi pi-calculator ml-1" />}
                          {/* Per-column delete (scoped to this template; input columns; edit mode). */}
                          {allowClearColumn && !calc && isEditableField(field) && editingThisGroup && (
                            <i
                              className="pi pi-trash ml-1 text-red-400 cursor-pointer"
                              title={`Delete column "${field.label ?? field.key}"`}
                              role="button"
                              aria-label={`Delete column ${field.label ?? field.key}`}
                              onClick={() => deleteColumn(group, field.key)}
                            />
                          )}
                        </th>
                      );
                    })}
                    {canAddRows && <th style={{ width: veryWideTable ? '1.8rem' : '3rem' }} />}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((_row, rowIndex) => (
                    <tr key={rowIndex} className="border-top-1 border-200">
                      <td className={`${cellPad} text-500 font-mono`}>{rowIndex + 1}</td>
                      {visibleFields.map((field) =>
                        field.kind === 'calculated' ? (
                          <td className={cellPad} key={field.key}>
                            {computedCell(group, rowIndex, field)}
                          </td>
                        ) : (
                          <td className={inputCellPad} key={field.key}>
                            {renderInput(group, rowIndex, field)}
                          </td>
                        ),
                      )}
                      {canAddRows && (
                        <td className={inputCellPad}>
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
            <div className="flex gap-2 flex-wrap">
              <Button
                label={dirty ? 'Save Worksheet' : 'Saved'}
                icon="pi pi-save"
                onClick={handleSave}
                loading={saving}
                disabled={!dirty}
              />
              {onSubmitForReview && (
                <Button
                  label="Submit for Review"
                  icon="pi pi-send"
                  severity="help"
                  outlined
                  onClick={onSubmitForReview}
                  loading={submittingForReview}
                  //  A pending edit should be saved first, so the reviewer sees
                  //  the values being submitted.
                  disabled={dirty}
                  tooltip={dirty ? 'Save your changes before submitting for review' : undefined}
                />
              )}
            </div>
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
