/**
 * Column sets: a run of a table's columns that the analyst adds, deletes and
 * names per worksheet (e.g. the media columns of TPL-A3-0001's "Standard Area
 * in Media").
 *
 * Opt-in through the group's `columnSet` hint (definition data, no template
 * code). The hint lists the columns in order and names a stored count
 * (`countRef`, a singleton input): the first `count` columns are in use. Each
 * column's field also declares
 *   - `showIf: "<countRef>[0] >= n"`, so the screen and the print page hide
 *     the columns not in use through the shared `fieldShown` rule, and
 *   - `labelFrom: "<group>.<field>[idx]"`, the cell holding its editable name.
 *
 * Column count, names and optional linked worksheet group sets are ordinary
 * worksheet values. Add / Delete Column changes the count; deletion moves later
 * cells, names and linked groups one place left, so a Media Solution never
 * becomes detached from its Standard Area column.
 *
 * Pure functions (no React) so they can be checked in isolation.
 */
import type { FieldDef, GroupDef, WorksheetRow } from './testTemplate.types';

type Values = Record<string, WorksheetRow[]>;
type ValuesLike = Record<string, WorksheetRow[] | undefined> | undefined;

/** A single stored cell: `values[group][row][field]`. */
export interface CellRef {
  group: string;
  field: string;
  row: number;
}

const CELL_REF = /^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?$/;

/** Parse `"<group>.<field>"` or `"<group>.<field>[idx]"` (row 0 when no index). */
export function parseCellRef(spec: string | null | undefined): CellRef | null {
  if (!spec) return null;
  const m = CELL_REF.exec(spec.trim());
  if (!m) return null;
  return { group: m[1], field: m[2], row: m[3] !== undefined ? Number(m[3]) : 0 };
}

export function readCell(values: ValuesLike, ref: CellRef): unknown {
  return values?.[ref.group]?.[ref.row]?.[ref.field];
}

function writeCell(values: Values, ref: CellRef, value: unknown): Values {
  const rows = [...(values[ref.group] ?? [])];
  while (rows.length <= ref.row) rows.push({});
  rows[ref.row] = { ...rows[ref.row], [ref.field]: value };
  return { ...values, [ref.group]: rows };
}

/** One column of a set: its field key and the cell holding its name. */
export interface ColumnSlot {
  key: string;
  name: CellRef | null;
}

/** The set's columns in definition order (keys the group does not define are skipped). */
export function columnSlots(group: GroupDef): ColumnSlot[] {
  const cfg = group.columnSet;
  if (!cfg) return [];
  const byKey = new Map((group.fields ?? []).map((f) => [f.key, f] as const));
  return cfg.columns
    .map((key) => byKey.get(key))
    .filter((f): f is FieldDef => f !== undefined)
    .map((f) => ({ key: f.key, name: parseCellRef(f.labelFrom) }));
}

/** Fewest columns in use (`columnSet.min`, default 1), within 0..number of columns. */
export function columnSetMin(group: GroupDef): number {
  const max = columnSlots(group).length;
  return Math.min(max, Math.max(0, group.columnSet?.min ?? 1));
}

/** Number of set columns in use: the stored count, clamped to min..number of columns. */
export function columnCount(group: GroupDef, values: ValuesLike): number {
  const max = columnSlots(group).length;
  const min = columnSetMin(group);
  const ref = parseCellRef(group.columnSet?.countRef);
  const raw = ref ? readCell(values, ref) : undefined;
  const n =
    typeof raw === 'number'
      ? raw
      : typeof raw === 'string' && raw.trim() !== ''
        ? Number(raw)
        : NaN;
  if (!Number.isFinite(n)) return min;
  return Math.min(max, Math.max(min, Math.trunc(n)));
}

/** The cell holding the name of a set column, or null when `field` is not one. */
export function columnNameRef(group: GroupDef, field: FieldDef): CellRef | null {
  if (!group.columnSet?.columns.includes(field.key)) return null;
  return parseCellRef(field.labelFrom);
}

function blankSlot(values: Values, groupKey: string, slot: ColumnSlot): Values {
  let next: Values = {
    ...values,
    [groupKey]: (values[groupKey] ?? []).map((row) => ({ ...row, [slot.key]: null })),
  };
  if (slot.name) next = writeCell(next, slot.name, null);
  return next;
}

function editableField(field: FieldDef): boolean {
  return field.kind === 'input' || field.kind === 'area' ||
    (field.kind === 'context' && !!field.overridable);
}

/** Restore one linked group to its normal opening rows/defaults. */
function defaultRowsFor(group: GroupDef | undefined): WorksheetRow[] {
  if (!group) return [];
  const count = group.kind === 'singleton'
    ? 1
    : (group.rows?.default ?? group.rows?.min ?? 1);
  const seed = group.rows?.seed ?? [];
  return Array.from({ length: count }, (_, index) => {
    const row: WorksheetRow = {};
    const seeded = seed[index] ?? {};
    for (const field of group.fields ?? []) {
      if (!editableField(field)) continue;
      row[field.key] = seeded[field.key] ?? field.default ?? null;
    }
    return row;
  });
}

function linkedGroupNames(group: GroupDef, slotIndex: number): string[] {
  return group.columnSet?.linkedGroups?.[slotIndex] ?? [];
}

function resetLinkedGroups(
  values: Values,
  group: GroupDef,
  slotIndex: number,
  allGroups: GroupDef[],
): Values {
  const byKey = new Map(allGroups.map((candidate) => [candidate.key, candidate] as const));
  let next = values;
  for (const key of linkedGroupNames(group, slotIndex)) {
    next = { ...next, [key]: defaultRowsFor(byKey.get(key)) };
  }
  return next;
}

function shiftLinkedGroups(
  values: Values,
  group: GroupDef,
  targetSlot: number,
  sourceSlot: number,
  allGroups: GroupDef[],
): Values {
  const byKey = new Map(allGroups.map((candidate) => [candidate.key, candidate] as const));
  const target = linkedGroupNames(group, targetSlot);
  const source = linkedGroupNames(group, sourceSlot);
  let next = values;
  target.forEach((targetKey, index) => {
    const sourceKey = source[index];
    next = {
      ...next,
      [targetKey]: sourceKey && values[sourceKey]
        ? values[sourceKey].map((row) => ({ ...row }))
        : defaultRowsFor(byKey.get(targetKey)),
    };
  });
  return next;
}

/**
 * Bring the next unused column into use, with blank cells and a blank name
 * (its header shows the static label until a name is typed). Null when every
 * column is already in use.
 */
export function addSetColumn(
  values: Values,
  group: GroupDef,
  allGroups: GroupDef[] = [],
): Values | null {
  const slots = columnSlots(group);
  const countRef = parseCellRef(group.columnSet?.countRef);
  const count = columnCount(group, values);
  if (!countRef || count >= slots.length) return null;
  let next = blankSlot(values, group.key, slots[count]);
  // A restored Media Solution starts as a fresh media, rather than revealing a
  // prior deleted medium's values.
  next = resetLinkedGroups(next, group, count, allGroups);
  return writeCell(next, countRef, count + 1);
}

/**
 * Delete an in-use column: the later in-use columns move one place left (cells
 * and names), the last in-use column is blanked, and the count drops by one.
 * Null when the column is not in use or the set is at its minimum.
 */
export function deleteSetColumn(
  values: Values,
  group: GroupDef,
  key: string,
  allGroups: GroupDef[] = [],
): Values | null {
  const slots = columnSlots(group);
  const countRef = parseCellRef(group.columnSet?.countRef);
  const count = columnCount(group, values);
  const i = slots.findIndex((s) => s.key === key);
  if (!countRef || i < 0 || i >= count || count <= columnSetMin(group)) return null;

  const rows = (values[group.key] ?? []).map((row) => {
    const out = { ...row };
    for (let j = i; j < count - 1; j += 1) out[slots[j].key] = row[slots[j + 1].key] ?? null;
    return out;
  });
  let next: Values = { ...values, [group.key]: rows };
  for (let j = i; j < count - 1; j += 1) {
    const from = slots[j + 1].name;
    const to = slots[j].name;
    if (to) next = writeCell(next, to, from ? (readCell(next, from) ?? null) : null);
    // Move the full dilution and Set-table values with this media's header and
    // standard-area column. The source slot is always to the right, so it has
    // not been changed yet while this left-shift loop runs.
    next = shiftLinkedGroups(next, group, j, j + 1, allGroups);
  }
  next = blankSlot(next, group.key, slots[count - 1]);
  next = resetLinkedGroups(next, group, count - 1, allGroups);
  return writeCell(next, countRef, count - 1);
}
