/**
 * Sample Detail page — result entry, supervisor review, and QA release.
 */
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputNumber } from 'primereact/inputnumber';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { ProgressSpinner } from 'primereact/progressspinner';
import { StatusBadge } from '@shared/components/StatusBadge';
import { ESignDialog } from '@shared/components/ESignDialog';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { InputTextarea } from 'primereact/inputtextarea';
import { useCloseOOS, useGetCoa, useOOSList, useReleaseSample, useReviewResult, useSampleList, useSubmitResult } from '../hooks/useSamples';
import type { SampleResult } from '../models/sample.types';
import type { OOSInvestigation } from '../models/oos.types';
import { sapApi } from '@features/sap-integration/api/sapApi';

export const SampleDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasRole } = usePermissions();
  const { data: samples = [], isLoading } = useSampleList();
  const sample = samples.find((s) => s.id === Number(id));

  const submitResult = useSubmitResult();
  const reviewResult = useReviewResult();
  const releaseSample = useReleaseSample();
  const getCoa = useGetCoa();
  const { data: allOOS = [] } = useOOSList();
  const closeOOS = useCloseOOS();

  const [resultDialog, setResultDialog] = useState<SampleResult | null>(null);
  const [resultValue, setResultValue] = useState<number | null>(null);
  const [resultText, setResultText] = useState('');
  const [reviewDialogResult, setReviewDialogResult] = useState<SampleResult | null>(null);
  const [releaseDialogOpen, setReleaseDialogOpen] = useState(false);
  const [verdict, setVerdict] = useState('Approved');
  const [coaDialogOpen, setCoaDialogOpen] = useState(false);
  const [udDialogOpen, setUdDialogOpen] = useState(false);
  const [udCode, setUdCode] = useState('A');
  const [udPosting, setUdPosting] = useState(false);
  const [closeOosTarget, setCloseOosTarget] = useState<OOSInvestigation | null>(null);
  const [rootCause, setRootCause] = useState('');
  const [correctiveAction, setCorrectiveAction] = useState('');

  // Whenever a different result row is opened for entry, clear any leftover
  // value from a previously opened test so it never carries over (this was
  // causing incorrect OOS flags — e.g. a prior test's value being submitted
  // against a different test's limits).
  const openResultDialog = (row: SampleResult) => {
    setResultValue(row.result_value ?? null);
    setResultText(row.result_text ?? '');
    setResultDialog(row);
  };

  const closeResultDialog = () => {
    setResultDialog(null);
    setResultValue(null);
    setResultText('');
  };

  if (isLoading) {
    return (
      <div className="flex justify-content-center py-8">
        <ProgressSpinner style={{ width: '40px', height: '40px' }} />
      </div>
    );
  }

  if (!sample) {
    return (
      <div>
        <Button label="Back to Samples" icon="pi pi-arrow-left" text onClick={() => navigate('/samples')} className="mb-3 p-0" />
        <p className="text-500">Sample not found.</p>
      </div>
    );
  }

  const sampleOOS = allOOS.filter((o) => o.sample_id === sample.id);
  const openOOS = sampleOOS.filter((o) => o.status === 'Open');

  const handleCloseOOS = (password: string) => {
    if (!closeOosTarget) return;
    if (!rootCause.trim() || !correctiveAction.trim()) {
      toastService.warn('Root cause and corrective action are required.', 'Missing fields');
      return;
    }
    closeOOS.mutate(
      { id: closeOosTarget.id, rootCause, correctiveAction, password },
      {
        onSuccess: () => {
          toastService.success(`OOS #${closeOosTarget.id} closed with root cause and CAPA.`, 'Investigation Closed');
          setCloseOosTarget(null);
          setRootCause('');
          setCorrectiveAction('');
        },
      }
    );
  };

  const isQuantitative = resultDialog?.test?.type === 'Quantitative';

  // Live OOS preview so the analyst can see the outcome before E-signing —
  // mirrors the backend's evaluate_oos() rule exactly.
  const previewIsOos = (): boolean | null => {
    if (!resultDialog) return null;
    if (isQuantitative) {
      if (resultValue == null) return null;
      if (resultDialog.min_limit != null && resultValue < resultDialog.min_limit) return true;
      if (resultDialog.max_limit != null && resultValue > resultDialog.max_limit) return true;
      return false;
    }
    if (!resultText.trim()) return null;
    if (!resultDialog.expected_result) return false;
    return resultText.trim().toLowerCase() !== resultDialog.expected_result.trim().toLowerCase();
  };
  const oosPreview = previewIsOos();

  const handleSubmitResult = (password: string, comments?: string) => {
    if (!resultDialog) return;
    if (isQuantitative && resultValue == null) {
      toastService.warn('Please enter a numeric result value.', 'Missing result');
      return;
    }
    if (!isQuantitative && !resultText.trim()) {
      toastService.warn('Please enter a result.', 'Missing result');
      return;
    }
    submitResult.mutate(
      {
        resultId: resultDialog.id,
        payload: {
          result_value: resultDialog.test?.type === 'Quantitative' ? resultValue : null,
          result_text: resultDialog.test?.type !== 'Quantitative' ? resultText : null,
          password,
          comments,
        },
      },
      {
        onSuccess: (res) => {
          toastService.success(
            res.is_oos ? 'Result submitted — flagged as OUT OF SPECIFICATION.' : 'Result submitted successfully.',
            res.is_oos ? 'OOS Detected' : 'Result Submitted'
          );
          closeResultDialog();
        },
      }
    );
  };

  const handleReview = (password: string, comments?: string) => {
    if (!reviewDialogResult) return;
    reviewResult.mutate(
      { resultId: reviewDialogResult.id, password, comments },
      {
        onSuccess: () => {
          toastService.success('Result reviewed and approved.', 'Result Approved');
          setReviewDialogResult(null);
        },
      }
    );
  };

  const handleRelease = (password: string, comments?: string) => {
    releaseSample.mutate(
      { id: sample.id, verdict, password, comments },
      {
        onSuccess: (updated) => {
          toastService.success(`Batch ${updated.sample_code} released as ${updated.status}.`, 'Batch Released');
          setReleaseDialogOpen(false);
        },
      }
    );
  };

  const handleViewCoa = () => {
    getCoa.mutate(sample.id, {
      onSuccess: () => setCoaDialogOpen(true),
      onError: (e: any) => toastService.error(getErrorMessage(e), 'Could not load COA'),
    });
  };

  const handlePostUsageDecision = async (password: string) => {
    setUdPosting(true);
    try {
      const result = await sapApi.postUsageDecision({ sample_id: sample.id, ud_code: udCode, password });
      toastService.success(result.message, 'Usage Decision Posted to SAP');
      setUdDialogOpen(false);
    } catch (e: any) {
      toastService.error(getErrorMessage(e), 'Usage Decision Failed');
    } finally {
      setUdPosting(false);
    }
  };

  return (
    <div>
      <Button label="Back to Samples" icon="pi pi-arrow-left" text onClick={() => navigate('/samples')} className="mb-3 p-0" />

      <div className="bg-white border-round-lg border-1 border-200 p-4 mb-4">
        <div className="flex justify-content-between align-items-start mb-3">
          <div>
            <h2 className="text-lg font-bold text-900 m-0">{sample.sample_code}</h2>
            <p className="text-500 m-0">{sample.product?.name} — Batch {sample.batch_number}</p>
          </div>
          <StatusBadge status={sample.status} />
        </div>
        <div className="grid text-sm">
          <div className="col-6 md:col-3"><span className="text-500 block">Quantity</span><span className="font-medium">{sample.quantity_received} {sample.unit}</span></div>
          <div className="col-6 md:col-3"><span className="text-500 block">Logged By</span><span className="font-medium">{sample.logged_by || '-'}</span></div>
          <div className="col-6 md:col-3"><span className="text-500 block">SAP Lot</span><span className="font-medium">{sample.sap_inspection_lot || 'N/A'}</span></div>
          <div className="col-6 md:col-3"><span className="text-500 block">SAP UD Posted</span><span className="font-medium">{sample.sap_ud_posted ? 'Yes' : 'No'}</span></div>
        </div>
        <div className="flex gap-2 mt-3">
          {sample.status === 'Under Review' && hasRole('QA') && (
            <Button label="Release Batch" icon="pi pi-check-circle" onClick={() => setReleaseDialogOpen(true)} />
          )}
          {(sample.status === 'Approved' || sample.status === 'Rejected') && (
            <Button label="View COA" icon="pi pi-file" severity="secondary" outlined loading={getCoa.isPending} onClick={handleViewCoa} />
          )}
          {(sample.status === 'Approved' || sample.status === 'Rejected') && sample.sap_inspection_lot && !sample.sap_ud_posted && hasRole('QA') && (
            <Button label="Post Usage Decision to SAP" icon="pi pi-sitemap" severity="help" outlined onClick={() => { setVerdict(sample.status); setUdCode(sample.status === 'Approved' ? 'A' : 'R'); setUdDialogOpen(true); }} />
          )}
          {sample.sap_ud_posted && (
            <span className="text-sm text-green-700 flex align-items-center gap-1"><i className="pi pi-check" /> Usage Decision posted to SAP</span>
          )}
        </div>

        {sample.status === 'OOS Investigation' && (
          <div className="bg-red-50 border-1 border-red-200 border-round p-3 mt-3">
            <p className="text-sm text-red-700 font-medium m-0 mb-2">
              <i className="pi pi-exclamation-triangle mr-1" />
              This sample cannot be released until all Out-of-Specification investigations below are closed with a root cause and corrective action.
            </p>
            {openOOS.length === 0 ? (
              <p className="text-sm text-600 m-0">All OOS investigations are closed — this sample should move to "Under Review" shortly. Refresh if it doesn't update automatically.</p>
            ) : (
              <ul className="m-0 pl-4">
                {openOOS.map((o) => (
                  <li key={o.id} className="text-sm mb-1 flex align-items-center justify-content-between gap-2">
                    <span>OOS #{o.id} — {o.phase1_comments}</span>
                    {hasRole('Supervisor', 'QA') && (
                      <Button label="Close Investigation" size="small" text onClick={() => setCloseOosTarget(o)} />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Test Results</h3>
        <DataTable value={sample.results} size="small">
          <Column
            header="Test"
            body={(row: SampleResult) => (
              <div>
                <span className="font-medium">{row.test?.name}</span>
                <span className="text-xs text-500 block">{row.test?.code} · {row.test?.type}</span>
              </div>
            )}
          />
          <Column
            header="Limits"
            body={(row: SampleResult) =>
              row.min_limit != null
                ? `${row.min_limit} – ${row.max_limit}${row.test?.unit ? ` ${row.test.unit}` : ''}`
                : row.expected_result || '-'
            }
          />
          <Column
            header="Result"
            body={(row: SampleResult) =>
              row.result_value != null
                ? `${row.result_value}${row.test?.unit ? ` ${row.test.unit}` : ''}`
                : row.result_text || '-'
            }
          />
          <Column header="Status" body={(row: SampleResult) => <StatusBadge status={row.status} /> } />
          <Column header="OOS" body={(row: SampleResult) => (row.is_oos ? <span className="text-red-600 font-bold">YES</span> : '-')} />
          <Column
            header="Actions"
            body={(row: SampleResult) => (
              <div className="flex gap-2">
                {row.status === 'Pending' && hasRole('Analyst') && (
                  <Button label="Enter Result" size="small" text onClick={() => openResultDialog(row)} />
                )}
                {row.status === 'Submitted' && hasRole('Supervisor') && (
                  <Button label="Review" size="small" text onClick={() => setReviewDialogResult(row)} />
                )}
              </div>
            )}
          />
        </DataTable>
      </div>

      {/* Result entry dialog */}
      <Dialog header="Submit Test Result" visible={!!resultDialog} onHide={closeResultDialog} style={{ width: '460px' }} modal>
        {resultDialog && (
          <div className="flex flex-column gap-3">
            {/* Full test identification */}
            <div>
              <p className="text-base font-semibold text-900 m-0">{resultDialog.test?.name}</p>
              <p className="text-xs text-500 m-0">
                {resultDialog.test?.code} · {resultDialog.test?.type}
                {resultDialog.test?.category ? ` · ${resultDialog.test.category}` : ''}
                {resultDialog.test?.technique ? ` · ${resultDialog.test.technique}` : ''}
              </p>
              {resultDialog.test?.method_no && (
                <p className="text-xs text-500 m-0">Method: {resultDialog.test.method_no}</p>
              )}
            </div>

            {/* Acceptance criteria */}
            <div className="bg-gray-50 border-round p-2 text-sm">
              {isQuantitative ? (
                <span>
                  <span className="text-500">Acceptable range: </span>
                  <span className="font-medium">
                    {resultDialog.min_limit ?? '—'} to {resultDialog.max_limit ?? '—'}
                    {resultDialog.test?.unit ? ` ${resultDialog.test.unit}` : ''}
                  </span>
                </span>
              ) : (
                <div className="flex align-items-center justify-content-between gap-2">
                  <span>
                    <span className="text-500">Expected result: </span>
                    <span className="font-medium">{resultDialog.expected_result || '—'}</span>
                  </span>
                  {resultDialog.expected_result && (
                    <Button
                      label="Use this"
                      link
                      size="small"
                      className="p-0 text-xs"
                      onClick={() => setResultText(resultDialog.expected_result || '')}
                    />
                  )}
                </div>
              )}
            </div>

            {/* Result input */}
            {isQuantitative ? (
              <div>
                <label className="block text-sm font-medium text-700 mb-1">
                  Result Value {resultDialog.test?.unit ? `(${resultDialog.test.unit})` : ''}
                </label>
                <InputNumber
                  value={resultValue}
                  onValueChange={(e) => setResultValue(e.value ?? null)}
                  className="w-full"
                  mode="decimal"
                  maxFractionDigits={4}
                  placeholder="Enter numeric result"
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-700 mb-1">Result</label>
                <InputText value={resultText} onChange={(e) => setResultText(e.target.value)} className="w-full" placeholder="e.g., Complies" />
              </div>
            )}

            {/* Live OOS preview — evaluated client-side using the same rule as the backend */}
            {oosPreview !== null && (
              <div
                className={`border-round p-2 text-sm font-medium ${oosPreview ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}
              >
                {oosPreview ? '⚠ This value is OUT OF SPECIFICATION' : '✓ Within specification'}
              </div>
            )}

            <ESignInline onConfirm={handleSubmitResult} loading={submitResult.isPending} actionLabel="Submit Result" />
          </div>
        )}
      </Dialog>

      {/* Review dialog */}
      <ESignDialog
        visible={!!reviewDialogResult}
        onHide={() => setReviewDialogResult(null)}
        onConfirm={handleReview}
        loading={reviewResult.isPending}
        title="Review Result"
        actionLabel="Approve Result"
      />

      {/* Release dialog */}
      <Dialog header="Release Batch" visible={releaseDialogOpen} onHide={() => setReleaseDialogOpen(false)} style={{ width: '420px' }} modal>
        <div className="flex flex-column gap-3">
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Verdict</label>
            <Dropdown
              value={verdict}
              options={[{ label: 'Approved', value: 'Approved' }, { label: 'Rejected', value: 'Rejected' }]}
              onChange={(e) => setVerdict(e.value)}
              className="w-full"
            />
          </div>
          <ESignInline onConfirm={handleRelease} loading={releaseSample.isPending} actionLabel="Release Batch" />
        </div>
      </Dialog>

      {/* Certificate of Analysis (immutable snapshot taken at release) */}
      <Dialog header="Certificate of Analysis" visible={coaDialogOpen} onHide={() => setCoaDialogOpen(false)} style={{ width: '600px' }} modal>
        {getCoa.data && (
          <div>
            <div className="grid text-sm mb-3">
              <div className="col-6"><span className="text-500 block">Sample</span><span className="font-medium">{String(getCoa.data.sample_code)}</span></div>
              <div className="col-6"><span className="text-500 block">Batch</span><span className="font-medium">{String(getCoa.data.batch_number)}</span></div>
              <div className="col-6"><span className="text-500 block">Product</span><span className="font-medium">{String(getCoa.data.product_name)}</span></div>
              <div className="col-6"><span className="text-500 block">Verdict</span><span className="font-medium">{String(getCoa.data.verdict)}</span></div>
              <div className="col-6"><span className="text-500 block">Released By</span><span className="font-medium">{String(getCoa.data.released_by)}</span></div>
              <div className="col-6"><span className="text-500 block">Released At</span><span className="font-medium">{new Date(String(getCoa.data.released_at)).toLocaleString()}</span></div>
            </div>
            <h4 className="text-sm font-semibold text-900 mb-2">Results at Release</h4>
            <DataTable value={(getCoa.data.results as any[]) || []} size="small">
              <Column field="test_id" header="Test ID" />
              <Column header="Limits" body={(row) => (row.min_limit != null ? `${row.min_limit} – ${row.max_limit}` : row.expected_result || '-')} />
              <Column header="Result" body={(row) => row.result_value ?? row.result_text ?? '-'} />
              <Column header="OOS" body={(row) => (row.is_oos ? <span className="text-red-600 font-bold">YES</span> : '-')} />
            </DataTable>
          </div>
        )}
      </Dialog>

      {/* Post Usage Decision to SAP CPI */}
      <Dialog header="Post Usage Decision to SAP" visible={udDialogOpen} onHide={() => setUdDialogOpen(false)} style={{ width: '420px' }} modal>
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            Sends the batch verdict for inspection lot <span className="font-mono">{sample.sap_inspection_lot}</span> to SAP CPI (Process_UD). This writes to SAP.
          </p>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">UD Code</label>
            <Dropdown
              value={udCode}
              options={[{ label: 'Accept (A)', value: 'A' }, { label: 'Reject (R)', value: 'R' }]}
              onChange={(e) => setUdCode(e.value)}
              className="w-full"
            />
          </div>
          <ESignInline onConfirm={handlePostUsageDecision} loading={udPosting} actionLabel="Post to SAP" />
        </div>
      </Dialog>

      {/* Close OOS Investigation — blocks release until every open one is closed */}
      <Dialog header={closeOosTarget ? `Close OOS Investigation #${closeOosTarget.id}` : ''} visible={!!closeOosTarget} onHide={() => setCloseOosTarget(null)} style={{ width: '460px' }} modal>
        {closeOosTarget && (
          <div className="flex flex-column gap-3">
            <p className="text-sm text-600 m-0">{closeOosTarget.phase1_comments}</p>
            <div>
              <label className="block text-sm font-medium text-700 mb-1">Root Cause</label>
              <InputTextarea value={rootCause} onChange={(e) => setRootCause(e.target.value)} rows={3} className="w-full" />
            </div>
            <div>
              <label className="block text-sm font-medium text-700 mb-1">Corrective Action</label>
              <InputTextarea value={correctiveAction} onChange={(e) => setCorrectiveAction(e.target.value)} rows={3} className="w-full" />
            </div>
            <ESignInline onConfirm={handleCloseOOS} loading={closeOOS.isPending} actionLabel="Close Investigation" />
          </div>
        )}
      </Dialog>
    </div>
  );
};

/** Minimal inline E-Sign form used within dialogs that already have their own header/content. */
function ESignInline({ onConfirm, loading, actionLabel }: { onConfirm: (password: string, comments?: string) => void; loading: boolean; actionLabel: string }) {
  const [password, setPassword] = useState('');
  const [comments, setComments] = useState('');
  return (
    <div className="flex flex-column gap-2">
      <label className="block text-sm font-medium text-700 mb-1">Password (E-Sign)</label>
      <InputText type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full" />
      <InputText placeholder="Comments (optional)" value={comments} onChange={(e) => setComments(e.target.value)} className="w-full" />
      <Button label={actionLabel} onClick={() => onConfirm(password, comments || undefined)} loading={loading} disabled={!password} />
    </div>
  );
}
