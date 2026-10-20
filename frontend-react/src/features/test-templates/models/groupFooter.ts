/**
 * Shape detection and row-grouping for table-group footers.
 *
 * Most templates carry a "flat" footer: a short list where every item has its
 * own label, e.g. `[{label:"Mean",ref}, {label:"SD",ref}, {label:"% RSD",ref}]`.
 * Those render as a simple label/value strip and must stay unchanged.
 *
 * A few templates (TPL-A2-0004's `std_areas` / `bkt_areas`) lay injections out
 * as rows × compounds as columns, and publish per-compound Mean/SD/%RSD as a
 * "column-aligned" footer: each LABELED item starts a logical row and the
 * UNLABELED items that immediately follow are that row's per-compound values in
 * column order. Those render as real footer ROWS whose cells align under each
 * compound column.
 *
 * Detection is purely by DATA SHAPE — the presence of an unlabeled item — never
 * by template code or field name, so the rule generalises to any similarly
 * shaped footer without per-template branching.
 */
import type { GroupFooterItem } from './testTemplate.types';

/** One rendered footer row: a label plus its column-aligned values. */
export interface FooterRow {
  /** Row label ("Mean"/"SD"/"% RSD"); '' when the leading item had none. */
  label: string;
  /**
   * Values in compound-column order: the labeled item first, then the unlabeled
   * items that followed it, each still carrying its ref/unit/rounding so the
   * caller formats exactly as it does today.
   */
  cells: GroupFooterItem[];
}

/** An item is "labeled" when it has a non-empty label. */
function hasLabel(item: GroupFooterItem): boolean {
  return item.label != null && item.label !== '';
}

/**
 * True when the footer is column-aligned — i.e. it contains at least one
 * UNLABELED item. A footer where every item has its own label is the flat
 * strip and returns false.
 */
export function isColumnAlignedFooter(footer: GroupFooterItem[] | undefined): boolean {
  return !!footer && footer.some((item) => !hasLabel(item));
}

/**
 * Group a column-aligned footer into rows. A new row starts at each LABELED
 * item and absorbs the following UNLABELED items until the next label (or end).
 * A run of unlabeled items before any label forms its own `label: ''` row so
 * nothing is dropped. Returns `[]` for an empty/undefined footer.
 */
export function groupFooterRows(footer: GroupFooterItem[] | undefined): FooterRow[] {
  if (!footer || footer.length === 0) return [];
  const rows: FooterRow[] = [];
  let current: FooterRow | null = null;
  for (const item of footer) {
    if (hasLabel(item) || current === null) {
      current = { label: item.label ?? '', cells: [item] };
      rows.push(current);
    } else {
      current.cells.push(item);
    }
  }
  return rows;
}
