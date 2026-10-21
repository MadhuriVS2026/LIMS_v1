/**
 * Opt-in "visual merge" (Excel merged-cell style) for a worksheet table COLUMN.
 *
 * A few templates auto-label a column with a value that repeats down a block of
 * rows — e.g. TPL-A2-0004's Sample Details (`lipid_samples`) auto-labels its
 * `set_no` column 1,1,1,1,2,2,2,2 across its 4-row SET blocks (the backend
 * even notes the frontend should visually merge it). Showing the same value on
 * every row is noisy; this util lets a render site show the value ONCE at the
 * top of each run of equal values and blank beneath, so it reads like a merged
 * cell. It is a PURE DISPLAY transform: rows are never reordered or hidden,
 * other columns stay editable, and blank values never merge.
 *
 * The opt-in is driven by a FRONTEND-only shape heuristic (`shouldMergeColumn`),
 * mirroring the shape-detection style of `groupFooter.ts`. It carries NO flag on
 * the template definition / DB, so the backend module and DB stay byte-equal and
 * no other template's repeated-value column is affected.
 */
import type { FieldDef, GroupDef } from './testTemplate.types';

/**
 * True when a group's column should render with the visual merge.
 *
 * Shape heuristic (least-magical, no backend/DB flag): the field is the SET
 * label `set_no` AND the group also carries a sibling `cidx` field — the hidden
 * per-row compound index that only TPL-A2-0004's `lipid_samples` group defines.
 * No other template has a column named both `set_no` and a `cidx` sibling, so
 * this targets exactly that SET column and cannot match a plain table.
 */
export function shouldMergeColumn(group: GroupDef, field: FieldDef): boolean {
  return field.key === 'set_no' && (group.fields ?? []).some((f) => f.key === 'cidx');
}

/**
 * Normalise a rendered cell value for merge comparison. `null`/`undefined`/`''`
 * and the em-dash placeholder sites use for blanks all map to '' (treated as
 * EMPTY so they never merge); anything else is its trimmed string form. All
 * render sites classify "empty" identically through this one helper.
 */
export function normalizeMergeValue(v: unknown): string {
  if (v === null || v === undefined) return '';
  const text = String(v).trim();
  return text === '—' ? '' : text;
}

/**
 * Given a column's rendered values in row order (already normalised via
 * `normalizeMergeValue`, or raw — this normalises again defensively), return
 * true when the row at `rowIndex` should render BLANK because it continues a run
 * of equal non-empty values started above it. A row renders its value (returns
 * false) when it is the first row, its value is empty, or its value differs from
 * the previous row's value. Empty values always start their own single-row run,
 * so blanks never visually merge.
 */
export function isMergedContinuation(renderedValues: string[], rowIndex: number): boolean {
  if (rowIndex <= 0) return false;
  const current = normalizeMergeValue(renderedValues[rowIndex]);
  if (current === '') return false;
  const previous = normalizeMergeValue(renderedValues[rowIndex - 1]);
  return current === previous;
}
