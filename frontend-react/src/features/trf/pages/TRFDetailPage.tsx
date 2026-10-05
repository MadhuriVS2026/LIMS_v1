/**
 * TRF Detail page — header fields, test-line table, and the gate action
 * buttons appropriate to the current status and the viewer's role.
 * - Draft/ReferredBack (Initiator/Admin): add/remove test lines, Submit.
 * - PendingFDGLApproval (Supervisor/Admin): may also add/remove lines;
 *   Approve (e-sign), Refer Back / Reject (comment).
 * - PendingADGLAcceptance (QA/Admin): Accept (e-sign, assigns AR number),
 *   Refer Back / Reject (comment).
 * - PendingAnalystAcceptance (Analyst/Admin): Accept (no e-sign),
 *   Refer Back / Reject (comment).
 * - InProgress (Analyst/Admin): enter/update each line's result, then
 *   Submit Results (e-sign, requires every line resulted).
 * - PendingADGLRelease (QA/Admin): correct any line's result, then
 *   Release (e-sign) — captures the immutable ATR snapshot.
 * - ReferredBack (Initiator/Admin): edit lines, Resubmit (always re-enters
 *   at FDGL).
 * - Released: link to the printable ATR.
 */
import { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import type { DataTableExpandedRows } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { StatusBadge } from '@shared/components/StatusBadge';
import { ESignDialog } from '@shared/components/ESignDialog';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useTests } from '@features/sample-management/hooks/useSamples';
import {
  TestLineWorksheetPanel,
  WorksheetStatusCell,
  useTemplateList,
  useWorksheetsForTrf,
} from '@features/test-templates';
import { AttachmentsPanel } from '../components/AttachmentsPanel';
import {
  useAddTestLine,
  useAdglAccept,
  useAdglReferBack,
  useAdglReject,
  useAnalystAccept,
  useAnalystReferBack,
  useAnalystReject,
  useFdglApprove,
  useFdglReferBack,
  useFdglReject,
  useReleaseResults,
  useRemoveTestLine,
  useResubmitTRF,
  useSubmitResults,
  useSubmitTestResult,
  useSubmitTRF,
  useTRFDetail,
} from '../hooks/useTRF';
import type { TRFTestLine } from '../models/trf.types';

type EsignAction = 'fdgl-approve' | 'adgl-accept' | 'submit-results' | 'release';
type CommentAction = 'fdgl-refer-back' | 'fdgl-reject' | 'adgl-refer-back' | 'adgl-reject' | 'analyst-refer-back' | 'analyst-reject';

const ESIGN_LABELS: Record<EsignAction, { title: string; actionLabel: string }> = {
  'fdgl-approve': { title: 'FDGL Approve — Electronic Signature', actionLabel: 'Approve' },
  'adgl-accept': { title: 'ADGL Accept — Electronic Signature', actionLabel: 'Accept' },
  'submit-results': { title: 'Submit Results — Electronic Signature', actionLabel: 'Submit Results' },
  release: { title: 'Release — Electronic Signature', actionLabel: 'Release' },
};

const COMMENT_LABELS: Record<CommentAction, { title: string; actionLabel: string }> = {
  'fdgl-refer-back': { title: 'Refer Back to Initiator', actionLabel: 'Refer Back' },
  'fdgl-reject': { title: 'Reject TRF', actionLabel: 'Reject' },
  'adgl-refer-back': { title: 'Refer Back to Initiator', actionLabel: 'Refer Back' },
  'adgl-reject': { title: 'Reject TRF', actionLabel: 'Reject' },
  'analyst-refer-back': { title: 'Refer Back to Initiator', actionLabel: 'Refer Back' },
  'analyst-reject': { title: 'Reject TRF', actionLabel: 'Reject' },
};

export const TRFDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const trfId = Number(id);
  const { hasRole } = usePermissions();

  const { data: trf, isLoading } = useTRFDetail(trfId);
  const { data: tests = [] } = useTests();

  const addTestLine = useAddTestLine();
  const removeTestLine = useRemoveTestLine();
  const submitTRF = useSubmitTRF();
  const fdglApprove = useFdglApprove();
  const fdglReferBack = useFdglReferBack();
  const fdglReject = useFdglReject();
  const adglAccept = useAdglAccept();
  const adglReferBack = useAdglReferBack();
  const adglReject = useAdglReject();
  const analystAccept = useAnalystAccept();
  const analystReferBack = useAnalystReferBack();
  const analystReject = useAnalystReject();
  const submitTestResult = useSubmitTestResult();
  const submitResults = useSubmitResults();
  const releaseResults = useReleaseResults();
  const resubmitTRF = useResubmitTRF();

  const [esignAction, setEsignAction] = useState<EsignAction | null>(null);
  const [commentAction, setCommentAction] = useState<CommentAction | null>(null);
  const [showAddLine, setShowAddLine] = useState(false);
  const [expandedLines, setExpandedLines] = useState<DataTableExpandedRows>({});

  //  Two cheap lookups that make the templating visible on the line itself:
  //  which lines already have a worksheet, and which Tests have a template that
  //  could be used. Both are summary projections — no definitions, no values.
  const { data: trfWorksheets = [] } = useWorksheetsForTrf(trfId);
  const { data: activeTemplates = [] } = useTemplateList({ status: 'Active' });

  const worksheetByLine = useMemo(
    () => new Map(trfWorksheets.map((w) => [w.trf_test_line_id, w])),
    [trfWorksheets],
  );
  const templateCountByTest = useMemo(() => {
    const counts = new Map<number, number>();
    for (const template of activeTemplates) {
      counts.set(template.test_id, (counts.get(template.test_id) ?? 0) + 1);
    }
    return counts;
  }, [activeTemplates]);
  const [newLine, setNewLine] = useState<{ test_id?: number; specification?: string; raw_data_reference?: string; remark?: string }>({});
  const [resultDrafts, setResultDrafts] = useState<Record<number, { result: string; remark: string }>>({});

  if (isLoading || !trf) {
    return <p className="text-500">Loading TRF...</p>;
  }

  //  FDGL/ADGL are explicit here as well as inheriting Supervisor/QA, so the
  //  gate is clear at a glance even though hasRole would resolve them anyway.
  const isFdgl = hasRole('Admin', 'Supervisor', 'FDGL');
  const isAdgl = hasRole('Admin', 'QA', 'ADGL', 'Approver2');
  const isAnalyst = hasRole('Admin', 'Analyst');

  const canMutateLines =
    (trf.status === 'Draft' || trf.status === 'ReferredBack') && hasRole('Admin', 'Analyst') || (trf.status === 'PendingFDGLApproval' && isFdgl);
  const canSubmit = (trf.status === 'Draft' || trf.status === 'ReferredBack') && hasRole('Admin', 'Analyst') && trf.test_lines.length > 0;
  const canFdglAct = trf.status === 'PendingFDGLApproval' && isFdgl;
  const canAdglAcceptAct = trf.status === 'PendingADGLAcceptance' && isAdgl;
  const canAnalystAct = trf.status === 'PendingAnalystAcceptance' && isAnalyst;
  const canEnterResults = trf.status === 'InProgress' && isAnalyst;
  const canSubmitResults = canEnterResults && trf.test_lines.length > 0 && trf.test_lines.every((l) => l.result && l.result.trim());
  const canCorrectResults = trf.status === 'PendingADGLRelease' && isAdgl;
  const canRelease = trf.status === 'PendingADGLRelease' && isAdgl;
  const canResubmit = trf.status === 'ReferredBack' && hasRole('Admin', 'Analyst');
  const isReleased = trf.status === 'Released';

  const getDraft = (line: TRFTestLine) => resultDrafts[line.id] ?? { result: line.result || '', remark: line.remark || '' };
  const setDraft = (lineId: number, patch: Partial<{ result: string; remark: string }>) => {
    const current = resultDrafts[lineId] ?? { result: '', remark: '' };
    setResultDrafts({ ...resultDrafts, [lineId]: { ...current, ...patch } });
  };

  const handleAddLine = () => {
    if (!newLine.test_id) {
      toastService.warn('Select a test.', 'Missing Test');
      return;
    }
    addTestLine.mutate(
      { trfId, payload: newLine as { test_id: number; specification?: string; raw_data_reference?: string; remark?: string } },
      {
        onSuccess: () => {
          toastService.success('Test line added.', 'TRF Updated');
          setShowAddLine(false);
          setNewLine({});
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Add Test Line'),
      }
    );
  };

  const handleRemoveLine = (lineId: number) => {
    removeTestLine.mutate(
      { trfId, lineId },
      {
        onSuccess: () => toastService.success('Test line removed.', 'TRF Updated'),
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Remove Test Line'),
      }
    );
  };

  const handleSubmit = () => {
    submitTRF.mutate(trfId, {
      onSuccess: () => toastService.success('TRF submitted for FDGL approval.', 'Submitted'),
      onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Submit'),
    });
  };

  const handleSaveResult = (line: TRFTestLine) => {
    const draft = getDraft(line);
    submitTestResult.mutate(
      { lineId: line.id, trfId, payload: { result: draft.result, remark: draft.remark } },
      {
        onSuccess: () => toastService.success(`Result saved for line ${line.line_no}.`, 'Result Updated'),
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Save Result'),
      }
    );
  };

  const handleEsignConfirm = (password: string) => {
    if (!esignAction) return;
    const onSuccess = (label: string) => {
      toastService.success(label, 'TRF Updated');
      setEsignAction(null);
    };
    const onError = (e: unknown) => toastService.error(getErrorMessage(e), 'Action Failed');

    if (esignAction === 'fdgl-approve') {
      fdglApprove.mutate({ trfId, payload: { password } }, { onSuccess: () => onSuccess('FDGL approval recorded.'), onError });
    } else if (esignAction === 'adgl-accept') {
      adglAccept.mutate({ trfId, payload: { password } }, { onSuccess: () => onSuccess('ADGL acceptance recorded — AR number assigned.'), onError });
    } else if (esignAction === 'submit-results') {
      submitResults.mutate({ trfId, payload: { password } }, { onSuccess: () => onSuccess('Results submitted for ADGL release.'), onError });
    } else if (esignAction === 'release') {
      releaseResults.mutate({ trfId, payload: { password } }, { onSuccess: () => onSuccess('TRF released — ATR is now available.'), onError });
    }
  };

  const handleCommentConfirm = (comments: string) => {
    if (!commentAction || !comments.trim()) {
      toastService.warn('A comment is required.', 'Missing Comment');
      return;
    }
    const onSuccess = (label: string) => {
      toastService.success(label, 'TRF Updated');
      setCommentAction(null);
    };
    const onError = (e: unknown) => toastService.error(getErrorMessage(e), 'Action Failed');
    const payload = { comments: comments.trim() };

    if (commentAction === 'fdgl-refer-back') fdglReferBack.mutate({ trfId, payload }, { onSuccess: () => onSuccess('Referred back to Initiator.'), onError });
    else if (commentAction === 'fdgl-reject') fdglReject.mutate({ trfId, payload }, { onSuccess: () => onSuccess('TRF rejected.'), onError });
    else if (commentAction === 'adgl-refer-back') adglReferBack.mutate({ trfId, payload }, { onSuccess: () => onSuccess('Referred back to Initiator.'), onError });
    else if (commentAction === 'adgl-reject') adglReject.mutate({ trfId, payload }, { onSuccess: () => onSuccess('TRF rejected.'), onError });
    else if (commentAction === 'analyst-refer-back') analystReferBack.mutate({ trfId, payload }, { onSuccess: () => onSuccess('Referred back to Initiator.'), onError });
    else if (commentAction === 'analyst-reject') analystReject.mutate({ trfId, payload }, { onSuccess: () => onSuccess('TRF rejected.'), onError });
  };

  const anyMutationPending =
    fdglApprove.isPending || adglAccept.isPending || submitResults.isPending || releaseResults.isPending;

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <div>
          <Button label="Back to TRFs" icon="pi pi-arrow-left" text size="small" onClick={() => navigate('/trf')} />
          <h2 className="text-lg font-semibold text-900 m-0 mt-1 flex align-items-center gap-2">
            <span className="font-mono">{trf.trf_number}</span>
            {trf.ar_number && <span className="font-mono text-500 text-sm">({trf.ar_number})</span>}
            <StatusBadge status={trf.status} />
          </h2>
        </div>
        <div className="flex gap-2 flex-wrap justify-content-end" style={{ maxWidth: '640px' }}>
          {isReleased && (
            <Button label="View / Print ATR" icon="pi pi-file" outlined onClick={() => navigate(`/trf/${trfId}/atr/print`)} />
          )}
          {canSubmit && (
            <Button label="Submit" icon="pi pi-send" severity="success" loading={submitTRF.isPending} onClick={handleSubmit} />
          )}
          {canResubmit && (
            <Button label="Resubmit" icon="pi pi-refresh" severity="success" loading={resubmitTRF.isPending} onClick={() => resubmitTRF.mutate(trfId, {
              onSuccess: () => toastService.success('Resubmitted — re-entered at FDGL approval.', 'TRF Updated'),
              onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Resubmit'),
            })} />
          )}
          {canFdglAct && (
            <>
              <Button label="Approve" icon="pi pi-check" severity="success" onClick={() => setEsignAction('fdgl-approve')} />
              <Button label="Refer Back" icon="pi pi-undo" severity="warning" outlined onClick={() => setCommentAction('fdgl-refer-back')} />
              <Button label="Reject" icon="pi pi-times" severity="danger" outlined onClick={() => setCommentAction('fdgl-reject')} />
            </>
          )}
          {canAdglAcceptAct && (
            <>
              <Button label="Accept" icon="pi pi-check" severity="success" onClick={() => setEsignAction('adgl-accept')} />
              <Button label="Refer Back" icon="pi pi-undo" severity="warning" outlined onClick={() => setCommentAction('adgl-refer-back')} />
              <Button label="Reject" icon="pi pi-times" severity="danger" outlined onClick={() => setCommentAction('adgl-reject')} />
            </>
          )}
          {canAnalystAct && (
            <>
              <Button
                label="Accept"
                icon="pi pi-check"
                severity="success"
                loading={analystAccept.isPending}
                onClick={() => analystAccept.mutate(trfId, {
                  onSuccess: () => toastService.success('Accepted — testing may begin.', 'TRF Updated'),
                  onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Accept'),
                })}
              />
              <Button label="Refer Back" icon="pi pi-undo" severity="warning" outlined onClick={() => setCommentAction('analyst-refer-back')} />
              <Button label="Reject" icon="pi pi-times" severity="danger" outlined onClick={() => setCommentAction('analyst-reject')} />
            </>
          )}
          {canSubmitResults && (
            <Button label="Submit Results" icon="pi pi-send" severity="success" onClick={() => setEsignAction('submit-results')} />
          )}
          {canRelease && (
            <Button label="Release" icon="pi pi-check-circle" severity="success" onClick={() => setEsignAction('release')} />
          )}
        </div>
      </div>

      <div className="grid mb-4 text-sm bg-white border-round-lg border-1 border-200 p-3">
        <div className="col-3"><span className="text-500 block">Batch Number</span><span className="font-medium">{trf.batch_number}</span></div>
        <div className="col-3"><span className="text-500 block">Label Claim</span><span className="font-medium">{trf.label_claim || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Stage of Sample</span><span className="font-medium">{trf.stage_of_sample || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Group</span><span className="font-medium">{trf.group_name || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Quantity</span><span className="font-medium">{trf.quantity || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Storage Condition</span><span className="font-medium">{trf.storage_condition || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Storage Period</span><span className="font-medium">{trf.storage_period || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Pack Details</span><span className="font-medium">{trf.pack_details || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Manufactured By</span><span className="font-medium">{trf.manufactured_by || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Mfg. Date</span><span className="font-medium">{trf.mfg_date ? new Date(trf.mfg_date).toLocaleDateString() : '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Expiry / Retest Date</span><span className="font-medium">{trf.expiry_or_retest_date ? new Date(trf.expiry_or_retest_date).toLocaleDateString() : '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Initiated By</span><span className="font-medium">{trf.initiated_by || trf.created_by}</span></div>
        {trf.remark && <div className="col-12"><span className="text-500 block">Remark</span><span className="font-medium">{trf.remark}</span></div>}
        {trf.status === 'ReferredBack' && trf.referred_back_comments && (
          <div className="col-12">
            <span className="text-500 block">Refer-Back Comments ({trf.referred_back_by})</span>
            <span className="font-medium text-orange-700">{trf.referred_back_comments}</span>
          </div>
        )}
        {trf.status === 'Rejected' && trf.rejected_comments && (
          <div className="col-12">
            <span className="text-500 block">Rejection Comments ({trf.rejected_by})</span>
            <span className="font-medium text-red-700">{trf.rejected_comments}</span>
          </div>
        )}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <div className="flex justify-content-between align-items-center p-3 pb-0">
          <div>
            <h3 className="text-base font-semibold text-900 m-0">Test Lines</h3>
            <p className="text-xs text-500 m-0 mt-1">
              Expand a line to open its calculation worksheet.
            </p>
          </div>
          {canMutateLines && <Button label="Add Test Line" icon="pi pi-plus" size="small" outlined onClick={() => setShowAddLine(true)} />}
        </div>
        <DataTable
          value={trf.test_lines}
          size="small"
          emptyMessage="No test lines on this TRF yet."
          dataKey="id"
          expandedRows={expandedLines}
          onRowToggle={(e) => setExpandedLines(e.data as DataTableExpandedRows)}
          rowExpansionTemplate={(row: TRFTestLine) => (
            <div className="p-3 bg-gray-50">
              <TestLineWorksheetPanel
                trfId={trf.id}
                trfStatus={trf.status}
                lineId={row.id}
                testId={row.test_id}
              />
            </div>
          )}
        >
          {/* Expanding a line opens its calculation worksheet. Kept collapsed by
              default: a TRF can carry many lines and the worksheets are large. */}
          <Column expander style={{ width: '3rem' }} />
          <Column field="line_no" header="#" />
          <Column header="Test" body={(row: TRFTestLine) => row.test_name ? `${row.test_name} (${row.test_code})` : row.test_code || `Test #${row.test_id}`} />
          <Column field="specification" header="Specification" body={(row: TRFTestLine) => row.specification || '-'} />
          <Column field="raw_data_reference" header="Raw Data Ref." body={(row: TRFTestLine) => row.raw_data_reference || '-'} />
          <Column
            header="Calculation"
            body={(row: TRFTestLine) => (
              <WorksheetStatusCell
                worksheet={worksheetByLine.get(row.id)}
                availableTemplates={templateCountByTest.get(row.test_id) ?? 0}
              />
            )}
          />
          <Column
            header="Result"
            body={(row: TRFTestLine) =>
              canEnterResults || canCorrectResults ? (
                <InputText
                  value={getDraft(row).result}
                  onChange={(e) => setDraft(row.id, { result: e.target.value })}
                  className="w-full"
                  placeholder="Enter result"
                />
              ) : (
                row.result || '-'
              )
            }
          />
          <Column
            header="Remark"
            body={(row: TRFTestLine) =>
              canEnterResults || canCorrectResults ? (
                <InputText
                  value={getDraft(row).remark}
                  onChange={(e) => setDraft(row.id, { remark: e.target.value })}
                  className="w-full"
                />
              ) : (
                row.remark || '-'
              )
            }
          />
          <Column header="Status" body={(row: TRFTestLine) => <StatusBadge status={row.status} />} />
          <Column
            header=""
            body={(row: TRFTestLine) => (
              <div className="flex gap-1">
                {(canEnterResults || canCorrectResults) && (
                  <Button
                    icon="pi pi-save"
                    text
                    size="small"
                    loading={submitTestResult.isPending && submitTestResult.variables?.lineId === row.id}
                    onClick={() => handleSaveResult(row)}
                  />
                )}
                {canMutateLines && (
                  <Button
                    icon="pi pi-trash"
                    text
                    size="small"
                    severity="danger"
                    loading={removeTestLine.isPending && removeTestLine.variables?.lineId === row.id}
                    onClick={() => handleRemoveLine(row.id)}
                  />
                )}
              </div>
            )}
          />
        </DataTable>
      </div>

      <AttachmentsPanel trfId={trf.id} trfStatus={trf.status} testLines={trf.test_lines} />

      <Dialog header="Add Test Line" visible={showAddLine} onHide={() => setShowAddLine(false)} style={{ width: '480px' }} breakpoints={{ '640px': '95vw' }} modal>
        <div className="flex flex-column gap-3">
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Test</label>
            <Dropdown
              value={newLine.test_id}
              //  Flag templated tests here, so the initiator knows before adding the
              //  line that the analyst will get a calculation worksheet for it.
              options={tests.map((t) => {
                const templates = templateCountByTest.get(t.id) ?? 0;
                return {
                  label: `${t.name} (${t.code})${templates > 0 ? '  ·  calculation template' : ''}`,
                  value: t.id,
                };
              })}
              onChange={(e) => setNewLine({ ...newLine, test_id: e.value })}
              placeholder="Select test..."
              className="w-full"
              filter
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Specification (Optional)</label>
            <InputText value={newLine.specification || ''} onChange={(e) => setNewLine({ ...newLine, specification: e.target.value })} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Raw Data Reference (Optional)</label>
            <InputText value={newLine.raw_data_reference || ''} onChange={(e) => setNewLine({ ...newLine, raw_data_reference: e.target.value })} className="w-full" placeholder="e.g. LNB template no. TS2599/25" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Remark (Optional)</label>
            <InputTextarea value={newLine.remark || ''} onChange={(e) => setNewLine({ ...newLine, remark: e.target.value })} rows={2} className="w-full" />
          </div>
          <Button label="Add Test Line" onClick={handleAddLine} loading={addTestLine.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      <ESignDialog
        visible={esignAction !== null}
        title={esignAction ? ESIGN_LABELS[esignAction].title : ''}
        actionLabel={esignAction ? ESIGN_LABELS[esignAction].actionLabel : 'Confirm'}
        showComments={false}
        loading={anyMutationPending}
        onHide={() => setEsignAction(null)}
        onConfirm={(password) => handleEsignConfirm(password)}
      />

      <Dialog
        header={commentAction ? COMMENT_LABELS[commentAction].title : ''}
        visible={commentAction !== null}
        onHide={() => setCommentAction(null)}
        style={{ width: '420px' }}
        breakpoints={{ '640px': '95vw' }}
        modal
      >
        <CommentDialogBody
          actionLabel={commentAction ? COMMENT_LABELS[commentAction].actionLabel : 'Confirm'}
          onConfirm={handleCommentConfirm}
        />
      </Dialog>
    </div>
  );
};

function CommentDialogBody({ actionLabel, onConfirm }: { actionLabel: string; onConfirm: (comments: string) => void }) {
  const [comments, setComments] = useState('');
  return (
    <div className="flex flex-column gap-3">
      <div>
        <label className="block text-sm font-medium text-700 mb-1">Comments (required)</label>
        <InputTextarea value={comments} onChange={(e) => setComments(e.target.value)} rows={3} className="w-full" autoFocus />
      </div>
      <Button label={actionLabel} onClick={() => onConfirm(comments)} disabled={!comments.trim()} className="w-full" />
    </div>
  );
}
