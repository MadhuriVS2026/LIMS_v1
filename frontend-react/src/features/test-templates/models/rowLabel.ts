/**
 * Caption-column layout for a table group (`rowLabel` hint), shared by the
 * worksheet form and the print page.
 *
 * The caption column replaces the `#` row number: its header is
 * `rowLabel.header` (e.g. "Media Name") and each row reads `rowLabel.format`
 * with `{n}` replaced by the row number (e.g. "Standard - 1"). The group's
 * footer renders as rows of the same table, labels in the caption column and
 * one value under each column, as on the paper sheet.
 */
import type { FooterRow } from './groupFooter';
import type { GroupFooterItem, RowLabelConfig } from './testTemplate.types';

/** The caption of row `n` (1-based). */
export function rowLabelText(cfg: RowLabelConfig, n: number): string {
  return cfg.format.replace(/\{n\}/g, String(n));
}

/**
 * Map a column-aligned footer row's cells to column keys. Cells follow the
 * definition's column order (`columnKeys`), so a column hidden at runtime
 * (`showIf`, a deleted column) drops its own cell instead of shifting the
 * later cells under the wrong column.
 */
export function footerCellsByColumn(
  row: FooterRow,
  columnKeys: string[],
): Map<string, GroupFooterItem> {
  const out = new Map<string, GroupFooterItem>();
  row.cells.forEach((cell, i) => {
    if (i < columnKeys.length) out.set(columnKeys[i], cell);
  });
  return out;
}
