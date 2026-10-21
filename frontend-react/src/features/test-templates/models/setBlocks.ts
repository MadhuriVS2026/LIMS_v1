/**
 * Opt-in "Set N" labeled-block rendering for a worksheet table GROUP.
 *
 * Some templates lay a table out as repeated fixed-size blocks of rows that the
 * paper worksheet captions as "Set 1", "Set 2", … — e.g. TPL-A2-0004's Sample
 * Details (`lipid_samples`), where every block is the same 4 compound rows
 * (Tricaprylin, DPPG Na, Cholesterol, DEPC). The original paper form carried an
 * in-table "SET" column; here that column was REMOVED and the SET is rendered
 * instead as a heading above each block. This util lets a render site split
 * such a group into consecutive blocks, each titled `Set {N}` (1-based), each
 * rendered as its own small table with its own column header.
 *
 * It is a PURE DISPLAY transform: rows, columns, values and editability are
 * untouched — only their visual grouping changes.
 *
 * The opt-in is driven by a FRONTEND-only SHAPE heuristic (`isSetBlockGroup`),
 * mirroring the shape-detection style of `groupFooter.ts`. It carries NO flag on
 * the template definition / DB and names NO template code, so the backend module
 * and DB stay byte-equal and no plain-table template is ever affected.
 */
import type { GroupDef, WorksheetRow } from './testTemplate.types';

/** The documented fixed block size for the "N sets of M compounds" layout. */
const DEFAULT_BLOCK_SIZE = 4;

/**
 * True when a table group should render as labeled "Set N" blocks.
 *
 * Shape heuristic (least-magical, no backend/DB flag, no template code): the
 * group carries a HIDDEN field whose key is `cidx` — the hidden per-row compound
 * index that resets to 0 at each new SET — AND it does NOT carry a `set_no`
 * field. This is exactly the shape left behind after the in-table SET column was
 * removed: `cidx` survives (it drives the per-row compound selection) and marks
 * block boundaries, while the SET column is gone. No plain table defines a hidden
 * `cidx`, so a plain table can never opt in. A group that still has a `set_no`
 * column is the pre-removal shape and is deliberately excluded.
 */
export function isSetBlockGroup(group: GroupDef): boolean {
  const fields = group.fields ?? [];
  const hasHiddenCidx = fields.some((f) => f.key === 'cidx' && f.hidden === true);
  const hasSetNo = fields.some((f) => f.key === 'set_no');
  return hasHiddenCidx && !hasSetNo;
}

/**
 * The block size (number of rows per "Set") for a set-block group.
 *
 * When computed rows are available (live form / print, which carry evaluated
 * `cidx` values), the size is the detected CYCLE LENGTH: the smallest row index
 * > 0 at which `cidx` returns to 0. When computed values are unavailable (the
 * preview page renders a blank skeleton with no computed `cidx`) or the cycle
 * cannot be derived, fall back to the documented fixed design value, 4.
 */
export function setBlockSize(
  _group: GroupDef,
  computedRows?: WorksheetRow[],
): number {
  if (computedRows && computedRows.length > 1) {
    const firstCidx = toNumber(computedRows[0]?.cidx);
    //  Only trust the cycle detection when row 0's cidx is the reset value 0.
    if (firstCidx === 0) {
      for (let i = 1; i < computedRows.length; i += 1) {
        if (toNumber(computedRows[i]?.cidx) === 0) return i;
      }
    }
  }
  return DEFAULT_BLOCK_SIZE;
}

/** One rendered block: its 1-based title and the half-open row range it covers. */
export interface SetBlock {
  title: string;
  /** Inclusive start row index. */
  startRow: number;
  /** Exclusive end row index (slice-friendly). */
  endRow: number;
}

/**
 * Split `rowCount` rows into consecutive blocks of `blockSize`, each titled
 * `Set {1-based index}`. A trailing partial block (if `rowCount` is not a
 * multiple of `blockSize`) still gets its own block so no row is dropped.
 * Returns `[]` for a non-positive row count; clamps a non-positive block size
 * to 1 defensively.
 */
export function setBlocksFor(rowCount: number, blockSize: number): SetBlock[] {
  const size = blockSize > 0 ? blockSize : 1;
  const blocks: SetBlock[] = [];
  let index = 1;
  for (let start = 0; start < rowCount; start += size) {
    blocks.push({
      title: `Set ${index}`,
      startRow: start,
      endRow: Math.min(start + size, rowCount),
    });
    index += 1;
  }
  return blocks;
}

function toNumber(v: unknown): number | undefined {
  if (typeof v === 'number') return v;
  if (typeof v === 'string' && v.trim() !== '') {
    const n = Number(v);
    return Number.isNaN(n) ? undefined : n;
  }
  return undefined;
}
