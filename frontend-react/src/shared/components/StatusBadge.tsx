/**
 * Consistent status pill across all LIMS modules — renders a PrimeReact
 * `Tag` with the enterprise severity mapping (success/danger/warning/info/
 * secondary), per the Sakai + PrimeReact + Emcure UI standard.
 */
import { Tag } from 'primereact/tag';

type TagSeverity = 'success' | 'danger' | 'warning' | 'info' | 'secondary';

const STATUS_SEVERITY: Record<string, TagSeverity> = {
  // Success — completed/approved/positive states
  Active: 'success',
  Approved: 'success',
  Completed: 'success',
  Released: 'success',
  Available: 'success',
  Posted: 'success',
  Success: 'success',
  Resulted: 'success',

  // Danger — rejected/failed/blocking states
  'OOS Investigation': 'danger',
  Open: 'danger',
  Rejected: 'danger',
  Expired: 'danger',
  Exhausted: 'danger',
  PostingFailed: 'danger',
  Failed: 'danger',

  // Warning — pending/in-review states
  Pending: 'warning',
  'Pending Approval': 'warning',
  PendingApproval: 'warning',
  PendingFDGLApproval: 'warning',
  PendingADGLAcceptance: 'warning',
  PendingAnalystAcceptance: 'warning',
  PendingADGLRelease: 'warning',
  ReferredBack: 'warning',
  FormulationChecked: 'warning',
  Prepared: 'warning',
  PartiallyPosted: 'warning',
  PartiallyConsumed: 'warning',

  // Info — in-progress/under-review/system states
  'Under Review': 'info',
  Submitted: 'info',
  Received: 'info',
  Scheduled: 'info',
  Pulled: 'info',
  Testing: 'info',
  InProgress: 'info',
  Sampled: 'info',
  //  A confirmed worksheet has a locked snapshot and a published result.
  Confirmed: 'success',

  // Secondary — neutral/terminal/draft states
  Closed: 'secondary',
  Inactive: 'secondary',
  Draft: 'secondary',
};

export const StatusBadge = ({ status }: { status: string }) => {
  const severity = STATUS_SEVERITY[status] ?? 'secondary';
  return <Tag value={status} severity={severity} />;
};
