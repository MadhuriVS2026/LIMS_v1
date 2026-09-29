/**
 * MRN Detail page.
 * - Draft: view/remove line items (added at raise time from the Material
 *   Queue page — "Add More Materials" jumps back there to add more), plus
 *   Submit once at least one line item exists.
 * - Submitted: Supervisor/Admin "Approve & Post" (e-sign gated) posts
 *   consumption for every line item to SAP.
 * - PartiallyPosted / PostingFailed: "Retry Failed Lines" reprocesses only
 *   the failed line items.
 * - Per-line-item status is shown with a SAP document number (on success)
 *   or the SAP-side error message (on failure).
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { StatusBadge } from '@shared/components/StatusBadge';
import { ESignDialog } from '@shared/components/ESignDialog';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import {
  useApproveAndPostMRN,
  useMRNDetail,
  useRemoveLineItem,
  useReprocessMRN,
  useSubmitMRN,
} from '../hooks/useMrn';
import type { MRNLineItem } from '../models/mrn.types';

export const MRNDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const mrnId = Number(id);
  const { hasRole } = usePermissions();

  const { data: mrn, isLoading } = useMRNDetail(mrnId);
  const removeLineItem = useRemoveLineItem();
  const submitMRN = useSubmitMRN();
  const approveAndPost = useApproveAndPostMRN();
  const reprocess = useReprocessMRN();

  const [showEsign, setShowEsign] = useState(false);

  const canEdit = hasRole('Admin', 'Analyst');
  const canApprove = hasRole('Admin', 'Supervisor');
  const isDraft = mrn?.status === 'Draft';
  const canSubmit = isDraft && (mrn?.line_items.length ?? 0) > 0;
  const canApproveAndPost = mrn?.status === 'Submitted';
  const canReprocess = mrn?.status === 'PartiallyPosted' || mrn?.status === 'PostingFailed';

  const handleRemoveLineItem = (lineId: number) => {
    removeLineItem.mutate(
      { mrnId, lineId },
      {
        onSuccess: () => toastService.success('Line item removed.', 'MRN Updated'),
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Remove Line Item'),
      }
    );
  };

  const handleSubmit = () => {
    submitMRN.mutate(mrnId, {
      onSuccess: () => toastService.success('MRN submitted for approval.', 'Submitted'),
      onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Submit'),
    });
  };

  const handleApproveAndPost = (password: string, comments?: string) => {
    approveAndPost.mutate(
      { mrnId, payload: { password, comments } },
      {
        onSuccess: (updated) => {
          toastService.success(`Posting complete — status: ${updated.status}.`, 'Approve & Post');
          setShowEsign(false);
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Approve & Post Failed'),
      }
    );
  };

  const handleReprocess = () => {
    reprocess.mutate(mrnId, {
      onSuccess: (updated) => toastService.success(`Retry complete — status: ${updated.status}.`, 'Reprocessed'),
      onError: (e) => toastService.error(getErrorMessage(e), 'Reprocess Failed'),
    });
  };

  if (isLoading || !mrn) {
    return <p className="text-500">Loading MRN...</p>;
  }

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <div>
          <Button label="Back to MRNs" icon="pi pi-arrow-left" text size="small" onClick={() => navigate('/mrn')} />
          <h2 className="text-lg font-semibold text-900 m-0 mt-1 flex align-items-center gap-2">
            <span className="font-mono">{mrn.mrn_number}</span>
            <StatusBadge status={mrn.status} />
          </h2>
        </div>
        <div className="flex gap-2">
          {isDraft && canEdit && (
            <Button
              label="Add More Materials"
              icon="pi pi-inbox"
              outlined
              onClick={() => navigate('/mrn/queue')}
            />
          )}
          {isDraft && canEdit && (
            <Button
              label="Submit MRN"
              icon="pi pi-send"
              severity="success"
              disabled={!canSubmit}
              loading={submitMRN.isPending}
              onClick={handleSubmit}
            />
          )}
          {canApproveAndPost && canApprove && (
            <Button
              label="Approve & Post"
              icon="pi pi-check"
              severity="success"
              onClick={() => setShowEsign(true)}
            />
          )}
          {canReprocess && canApprove && (
            <Button
              label="Retry Failed Lines"
              icon="pi pi-refresh"
              severity="warning"
              loading={reprocess.isPending}
              onClick={handleReprocess}
            />
          )}
        </div>
      </div>

      <div className="grid mb-4 text-sm">
        <div className="col-3"><span className="text-500 block">Created By</span><span className="font-medium">{mrn.created_by}</span></div>
        <div className="col-3"><span className="text-500 block">Created</span><span className="font-medium">{new Date(mrn.created_date).toLocaleString()}</span></div>
        <div className="col-3"><span className="text-500 block">Submitted By</span><span className="font-medium">{mrn.submitted_by || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Posted By</span><span className="font-medium">{mrn.posted_by || '-'}</span></div>
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Line Items</h3>
        <DataTable value={mrn.line_items} size="small" emptyMessage="No line items on this MRN yet.">
          <Column field="line_no" header="#" />
          <Column field="lot_material_code" header="Material" />
          <Column field="lot_batch_number" header="Batch" />
          <Column field="requested_quantity" header="Quantity" />
          <Column field="project_code" header="Project Code" />
          <Column header="Status" body={(row: MRNLineItem) => <StatusBadge status={row.status} />} />
          {isDraft && canEdit && (
            <Column
              header=""
              body={(row: MRNLineItem) => (
                <Button
                  icon="pi pi-trash"
                  text
                  size="small"
                  severity="danger"
                  loading={removeLineItem.isPending && removeLineItem.variables?.lineId === row.id}
                  onClick={() => handleRemoveLineItem(row.id)}
                />
              )}
            />
          )}
        </DataTable>
      </div>

      <ESignDialog
        visible={showEsign}
        title="Approve & Post Material Consumption to SAP"
        actionLabel="Approve & Post"
        loading={approveAndPost.isPending}
        onHide={() => setShowEsign(false)}
        onConfirm={handleApproveAndPost}
      />
    </div>
  );
};
