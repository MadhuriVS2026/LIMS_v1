/**
 * Worksheet panel for one TRF test line, for embedding in `TRFDetailPage`.
 *
 * Three states:
 *   1. no worksheet, Active templates exist → a template picker
 *   2. no worksheet, no Active templates     → nothing (the line keeps the
 *      existing free-text result path, which is why templating is additive
 *      rather than a replacement)
 *   3. a worksheet exists                    → the entry form plus Confirm
 *
 * Whether the form is editable and who may confirm is the backend's decision;
 * this component mirrors it so the UI does not offer an action that will 403.
 */
import { useState } from 'react';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputTextarea } from 'primereact/inputtextarea';
import { Message } from 'primereact/message';
import { StatusBadge } from '@shared/components/StatusBadge';
import { getErrorMessage, toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useTemplatesForTest } from '../hooks/useTestTemplates';
import {
  useApproveWorksheetReview,
  useConfirmWorksheet,
  useCreateWorksheet,
  useReferBackWorksheet,
  useSaveWorksheetValues,
  useSubmitForReview,
  useWorksheetForLine,
} from '../hooks/useWorksheet';
import { WorksheetForm } from './WorksheetForm';
import type { WorksheetRow } from '../models/testTemplate.types';

interface TestLineWorksheetPanelProps {
  trfId: number;
  trfStatus: string;
  lineId: number;
  testId: number;
}

/** Mirrors `TestWorksheet.edit_mode_for` on the backend. */
type EditMode = 'Entry' | 'Correction' | null;

function editModeFor(trfStatus: string): EditMode {
  if (trfStatus === 'InProgress') return 'Entry';
  if (trfStatus === 'PendingADGLRelease') return 'Correction';
  return null;
}

export const TestLineWorksheetPanel = ({
  trfId,
  trfStatus,
  lineId,
  testId,
}: TestLineWorksheetPanelProps) => {
  const { hasRole } = usePermissions();
  const { data: detail, isLoading } = useWorksheetForLine(lineId);
  const { data: templates = [] } = useTemplatesForTest(testId);

  const createWorksheet = useCreateWorksheet();
  const saveValues = useSaveWorksheetValues();
  const confirmWorksheet = useConfirmWorksheet();
  const submitForReview = useSubmitForReview();
  const referBack = useReferBackWorksheet();
  const approveReview = useApproveWorksheetReview();

  const [pickedTemplateId, setPickedTemplateId] = useState<number | null>(null);
  const [showReason, setShowReason] = useState(false);
  const [reason, setReason] = useState('');
  const [pending, setPending] = useState<{
    context_values: Record<string, unknown>;
    group_values: Record<string, WorksheetRow[]>;
  } | null>(null);
  //  Review-cycle comment dialogs.
  const [reviewAction, setReviewAction] = useState<'submit' | 'approve' | 'refer' | null>(null);
  const [reviewComment, setReviewComment] = useState('');

  const mode = editModeFor(trfStatus);
  const worksheetStatus = detail?.worksheet.status;
  const pendingReview = worksheetStatus === 'PendingReview';
  //  Editing is locked while the worksheet is under review, even if the TRF
  //  status and role would otherwise allow it.
  const canEnter = mode === 'Entry' && hasRole('Analyst', 'Admin') && !pendingReview;
  const canCorrect = mode === 'Correction' && hasRole('QA', 'Admin') && !pendingReview;
  const editable = canEnter || canCorrect;
  const canConfirm = canEnter;
  //  Who may act on a submitted worksheet. GL/TL resolve to Supervisor via the
  //  frontend role inheritance in usePermissions.
  const canReview = hasRole('Supervisor', 'QA', 'Admin');

  //  With one Active template there is no choice to make, so don't stage one as
  //  if there were. Only a genuine ambiguity should require a selection.
  const templateId = pickedTemplateId ?? (templates.length === 1 ? templates[0].id : null);

  if (isLoading) return <p className="text-sm text-500 m-0">Loading worksheet…</p>;

  // ── No worksheet yet ──
  if (!detail) {
    if (templates.length === 0) {
      return (
        <p className="text-sm text-500 m-0">
          No approved calculation template exists for this test. Enter the result as free text.
        </p>
      );
    }
    if (!canEnter) {
      return (
        <p className="text-sm text-500 m-0">
          {templates.length} calculation template(s) available. A worksheet can be started once the
          TRF is In Progress.
        </p>
      );
    }
    return (
      <div className="flex align-items-end gap-2 flex-wrap">
        {templates.length === 1 ? (
          <div>
            <span className="block text-xs text-500 mb-1">Calculation template</span>
            <span className="text-sm font-medium">
              {templates[0].name}{' '}
              <span className="font-mono text-500">
                {templates[0].code} v{templates[0].version}
              </span>
            </span>
          </div>
        ) : (
          <div>
            <label className="block text-xs text-500 mb-1">Calculation template</label>
            <Dropdown
              value={templateId}
              options={templates.map((t) => ({
                label: `${t.name} — ${t.code} v${t.version}`,
                value: t.id,
              }))}
              onChange={(e) => setPickedTemplateId(e.value)}
              placeholder="Select template..."
              className="w-full sm:w-22rem"
              aria-label="Calculation template"
            />
          </div>
        )}
        <Button
          label="Open Worksheet"
          icon="pi pi-table"
          disabled={templateId == null}
          loading={createWorksheet.isPending}
          onClick={() =>
            createWorksheet.mutate(
              { lineId, trfId, payload: { template_id: templateId as number } },
              {
                onSuccess: () => toastService.success('Worksheet created.', 'Worksheet'),
                onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Open Worksheet'),
              },
            )
          }
        />
      </div>
    );
  }

  // ── Worksheet exists ──
  const doSave = (
    payload: { context_values: Record<string, unknown>; group_values: Record<string, WorksheetRow[]> },
    withReason?: string,
  ) =>
    saveValues.mutate(
      { worksheetId: detail.worksheet.id, lineId, trfId, payload: { ...payload, reason: withReason } },
      {
        onSuccess: () => {
          setShowReason(false);
          setReason('');
          setPending(null);
          toastService.success('Worksheet saved.', 'Saved');
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Save Worksheet'),
      },
    );

  const handleSave = (payload: {
    context_values: Record<string, unknown>;
    group_values: Record<string, WorksheetRow[]>;
  }) => {
    //  A correction rewrites a result an analyst already submitted, so the
    //  backend requires a reason. Ask for it here rather than letting the save
    //  fail with a 400 the analyst has to decode.
    if (canCorrect) {
      setPending(payload);
      setShowReason(true);
      return;
    }
    doSave(payload);
  };

  const handleConfirm = () =>
    confirmWorksheet.mutate(
      { worksheetId: detail.worksheet.id, lineId, trfId },
      {
        onSuccess: (data) =>
          toastService.success(
            `Result ${data.test_line_result ?? ''} published to the test line.`,
            'Result Confirmed',
          ),
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Confirm Result'),
      },
    );

  const closeReviewDialog = () => {
    setReviewAction(null);
    setReviewComment('');
  };

  const handleReviewConfirm = () => {
    const ws = detail.worksheet.id;
    const common = { worksheetId: ws, lineId, trfId, comments: reviewComment.trim() || undefined };
    if (reviewAction === 'submit') {
      submitForReview.mutate(common, {
        onSuccess: () => {
          toastService.success('Worksheet submitted for review.', 'Submitted');
          closeReviewDialog();
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Submit'),
      });
    } else if (reviewAction === 'approve') {
      approveReview.mutate(common, {
        onSuccess: (data) => {
          toastService.success(
            `Approved. Result ${data.test_line_result ?? ''} published to the test line.`,
            'Worksheet Approved',
          );
          closeReviewDialog();
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Approve'),
      });
    } else if (reviewAction === 'refer') {
      referBack.mutate(
        { worksheetId: ws, lineId, trfId, comments: reviewComment.trim() },
        {
          onSuccess: () => {
            toastService.success('Worksheet referred back to the analyst.', 'Referred Back');
            closeReviewDialog();
          },
          onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Refer Back'),
        },
      );
    }
  };

  const reviewBusy = submitForReview.isPending || approveReview.isPending || referBack.isPending;

  return (
    <div className="flex flex-column gap-3">
      <div className="flex justify-content-between align-items-center flex-wrap gap-2">
        <div className="flex align-items-center flex-wrap gap-2" style={{ minWidth: 0 }}>
          <span className="font-mono text-blue-600 text-sm">{detail.worksheet.template_code}</span>
          <span className="text-500 text-sm">v{detail.worksheet.template_version}</span>
          <span className="text-500 text-sm">·</span>
          <span className="text-sm">{detail.worksheet.template_name}</span>
          <StatusBadge status={detail.worksheet.status} />
        </div>

        <div className="flex gap-2 flex-wrap">
          {pendingReview && canReview && (
            <>
              <Button
                label="Approve"
                icon="pi pi-check"
                severity="success"
                loading={approveReview.isPending}
                disabled={detail.computed.has_blocking_failure}
                onClick={() => setReviewAction('approve')}
              />
              <Button
                label="Refer Back"
                icon="pi pi-undo"
                severity="warning"
                outlined
                loading={referBack.isPending}
                onClick={() => setReviewAction('refer')}
              />
            </>
          )}
          {canConfirm && (
            <Button
              label={detail.worksheet.status === 'Confirmed' ? 'Re-confirm Result' : 'Confirm Result'}
              icon="pi pi-check"
              severity="success"
              loading={confirmWorksheet.isPending}
              disabled={detail.computed.has_blocking_failure}
              onClick={handleConfirm}
            />
          )}
        </div>
      </div>

      {detail.worksheet.status === 'Confirmed' && (
        <Message
          severity="success"
          text={`Confirmed by ${detail.worksheet.confirmed_by} — result ${detail.worksheet.reportable_result} is on the test line.`}
        />
      )}
      {canCorrect && (
        <Message
          severity="info"
          text="Correction mode: changes are recorded against your user with a mandatory reason, and the result must be re-confirmed by the analyst."
        />
      )}
      {!editable && mode === null && (
        <Message
          severity="info"
          text={`The worksheet is read-only while the TRF is ${trfStatus}.`}
        />
      )}

      {pendingReview && (
        <Message
          severity="warn"
          className="w-full"
          text={
            `Submitted for review by ${detail.worksheet.submitted_for_review_by ?? 'analyst'}` +
            (detail.worksheet.submission_comments
              ? ` — “${detail.worksheet.submission_comments}”`
              : '') +
            (canReview
              ? '. Approve to publish the result, or refer it back with comments.'
              : '. Editing is locked until a reviewer approves or refers it back.')
          }
        />
      )}
      {worksheetStatus === 'ReferredBack' && (
        <Message
          severity="error"
          className="w-full"
          text={
            `Referred back by ${detail.worksheet.reviewed_by ?? 'reviewer'}` +
            (detail.worksheet.review_comments ? `: “${detail.worksheet.review_comments}”` : '') +
            '. Make the requested changes, then submit for review again.'
          }
        />
      )}

      <WorksheetForm
        detail={detail}
        editable={editable}
        saving={saveValues.isPending}
        onSave={handleSave}
        onSubmitForReview={canEnter ? () => setReviewAction('submit') : undefined}
        submittingForReview={submitForReview.isPending}
      />

      <Dialog
        header="Reason for Correction"
        visible={showReason}
        onHide={() => setShowReason(false)}
        style={{ width: '460px' }}
        breakpoints={{ '640px': '95vw' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            This worksheet already carries a submitted result. The reason is written to the audit
            trail alongside the changed values.
          </p>
          <InputTextarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full"
            placeholder="e.g. Area transposed from the wrong chromatogram"
            autoFocus
          />
          <Button
            label="Save Correction"
            onClick={() => pending && doSave(pending, reason.trim())}
            loading={saveValues.isPending}
            disabled={!reason.trim()}
          />
        </div>
      </Dialog>

      <Dialog
        header={
          reviewAction === 'submit'
            ? 'Submit for Review'
            : reviewAction === 'approve'
              ? 'Approve Worksheet'
              : 'Refer Back'
        }
        visible={reviewAction !== null}
        onHide={closeReviewDialog}
        style={{ width: '460px' }}
        breakpoints={{ '640px': '95vw' }}
        modal
      >
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            {reviewAction === 'submit' &&
              'Send this worksheet to a supervisor (GL/TL/QA) for review. Editing is locked until they act. Add any notes for the reviewer.'}
            {reviewAction === 'approve' &&
              'Approving confirms the result and publishes it to the test line. Comments are optional.'}
            {reviewAction === 'refer' &&
              'Return this worksheet to the analyst for changes. A comment explaining what to fix is required.'}
          </p>
          <InputTextarea
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
            rows={3}
            className="w-full"
            placeholder={
              reviewAction === 'refer'
                ? 'e.g. Re-check standard weight; Area 2 looks transposed'
                : 'Optional comments'
            }
            autoFocus
          />
          <Button
            label={
              reviewAction === 'submit'
                ? 'Submit for Review'
                : reviewAction === 'approve'
                  ? 'Approve'
                  : 'Refer Back'
            }
            onClick={handleReviewConfirm}
            loading={reviewBusy}
            //  Only refer-back requires a comment.
            disabled={reviewAction === 'refer' && !reviewComment.trim()}
          />
        </div>
      </Dialog>
    </div>
  );
};
