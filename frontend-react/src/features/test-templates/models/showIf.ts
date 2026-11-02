/**
 * `showIf` resolution shared by the worksheet form and the print page.
 *
 * A field may declare `showIf: "<group>.<field>[idx]"`; it is rendered only
 * while that entered value is non-blank. Fields without `showIf` always show.
 *
 * The condition may also compare that value with a number,
 * `"<group>.<field>[idx] >= 7"` (operators `>=`, `<=`, `>`, `<`, `==`, `!=`),
 * e.g. a media column shown only while the stored count of media columns in use
 * reaches it. A blank or non-numeric value fails the comparison.
 */
import type { FieldDef, GroupDef, WorksheetRow } from './testTemplate.types';

const SHOW_IF =
  /^([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\[(\d+)\](?:\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?))?$/;

function asNumber(v: unknown): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'string' && v.trim() !== '') return Number(v);
  return NaN;
}

function compare(left: number, op: string, right: number): boolean {
  switch (op) {
    case '>=':
      return left >= right;
    case '<=':
      return left <= right;
    case '>':
      return left > right;
    case '<':
      return left < right;
    case '==':
      return left === right;
    case '!=':
      return left !== right;
    default:
      return true;
  }
}

export function fieldShown(
  field: FieldDef,
  values: Record<string, WorksheetRow[] | undefined> | undefined,
): boolean {
  return shownWhen(field.showIf, values);
}

/** Apply the same `showIf` grammar to a whole section. */
export function groupShown(
  group: GroupDef,
  values: Record<string, WorksheetRow[] | undefined> | undefined,
): boolean {
  return shownWhen(group.showIf, values);
}

function shownWhen(
  showIf: string | undefined,
  values: Record<string, WorksheetRow[] | undefined> | undefined,
): boolean {
  if (!showIf) return true;
  const m = SHOW_IF.exec(showIf.trim());
  //  A malformed condition never hides a field.
  if (!m) return true;
  const [, group, key, idx, op, rhs] = m;
  const v = values?.[group]?.[Number(idx)]?.[key];
  if (op) {
    const n = asNumber(v);
    return Number.isFinite(n) && compare(n, op, Number(rhs));
  }
  if (v === null || v === undefined) return false;
  return typeof v === 'string' ? v.trim() !== '' : true;
}
