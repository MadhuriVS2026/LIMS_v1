/**
 * `showIf` resolution shared by the worksheet form and the print page.
 *
 * A field may declare `showIf: "<group>.<field>[idx]"`; it is rendered only
 * while that entered value is non-blank. Fields without `showIf` always show.
 */
import type { FieldDef, WorksheetRow } from './testTemplate.types';

const SHOW_IF = /^([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\[(\d+)\]$/;

export function fieldShown(
  field: FieldDef,
  values: Record<string, WorksheetRow[] | undefined> | undefined,
): boolean {
  if (!field.showIf) return true;
  const m = SHOW_IF.exec(field.showIf.trim());
  //  A malformed condition never hides a field.
  if (!m) return true;
  const [, group, key, idx] = m;
  const v = values?.[group]?.[Number(idx)]?.[key];
  if (v === null || v === undefined) return false;
  return typeof v === 'string' ? v.trim() !== '' : true;
}
