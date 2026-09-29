/**
 * Verdict pill for COA rows.
 *
 * Separate from `StatusBadge` because `NotEvaluated` needs to read as neutral
 * rather than as a failure — it means "no numeric limit to compare against", and
 * showing it in red would send analysts chasing a problem that does not exist.
 */
import { Tag } from 'primereact/tag';
import type { Verdict } from '../models/coa.types';

const LABEL: Record<Verdict, string> = {
  Pass: 'Pass',
  Fail: 'Fail',
  NotEvaluated: 'Not evaluated',
};

const SEVERITY: Record<Verdict, 'success' | 'danger' | 'secondary'> = {
  Pass: 'success',
  Fail: 'danger',
  NotEvaluated: 'secondary',
};

export const VerdictTag = ({ verdict }: { verdict: Verdict }) => (
  <Tag value={LABEL[verdict] ?? verdict} severity={SEVERITY[verdict] ?? 'secondary'} />
);
