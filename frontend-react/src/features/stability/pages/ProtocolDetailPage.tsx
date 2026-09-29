/**
 * Stability Protocol Detail page — the full workflow surface:
 * - Draft: Loading Matrix editor (condition x time-point-in-days grid,
 *   plus a Reserve column per condition), then the two-step approval
 *   (Formulation Check, Analytical Check — both Supervisor e-sign).
 * - Active: Generate Schedule (per batch number) against scheduled matrix
 *   cells, then a time-point sample list with a "Pull" action per row.
 * - Reports: generate a Stability Report from Completed time points, then
 *   Prepare (Analyst e-sign) and Approve (QA e-sign) it.
 */
import { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputNumber } from 'primereact/inputnumber';
import { InputTextarea } from 'primereact/inputtextarea';
import { Checkbox } from 'primereact/checkbox';
import { Chip } from 'primereact/chip';
import { Dropdown } from 'primereact/dropdown';
import { StatusBadge } from '@shared/components/StatusBadge';
import { ESignDialog } from '@shared/components/ESignDialog';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useProducts } from '@features/sample-management/hooks/useSamples';
import {
  useApproveReport,
  useCancelProtocol,
  useCheckAnalytical,
  useCheckFormulation,
  useCompleteProtocol,
  useCreateReservePull,
  useGenerateReport,
  useGenerateSchedule,
  useMatrix,
  usePrepareReport,
  useProtocolDetail,
  usePullSample,
  useReportList,
  useSampleList,
  useSetMatrix,
  useSetReportSignatureNames,
  useUpdateProtocolHeader,
} from '../hooks/useStability';
import {
  STANDARD_TIME_POINT_DAYS,
  SUGGESTED_CONDITIONS,
  type MatrixCellInput,
  type StabilityReport,
  type StabilitySample,
  type UpdateProtocolHeaderRequest,
} from '../models/stability.types';

type EsignAction = 'formulation' | 'analytical' | 'prepare' | 'approve';

export const ProtocolDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const protocolId = Number(id);
  const { hasRole } = usePermissions();

  const { data: protocol, isLoading } = useProtocolDetail(protocolId);
  const { data: products = [] } = useProducts();
  const { data: matrixCells = [] } = useMatrix(protocolId);
  const { data: samples = [] } = useSampleList(protocolId);
  const { data: reports = [] } = useReportList(protocolId);

  const setMatrix = useSetMatrix();
  const checkFormulation = useCheckFormulation();
  const checkAnalytical = useCheckAnalytical();
  const generateSchedule = useGenerateSchedule();
  const pullSample = usePullSample();
  const generateReport = useGenerateReport();
  const prepareReport = usePrepareReport();
  const approveReport = useApproveReport();
  const updateHeader = useUpdateProtocolHeader();
  const completeProtocol = useCompleteProtocol();
  const cancelProtocol = useCancelProtocol();
  const createReservePull = useCreateReservePull();
  const setSignatureNames = useSetReportSignatureNames();

  const canManageMatrix = hasRole('Admin', 'Supervisor');
  const canGenerateSchedule = hasRole('Admin', 'Analyst');
  const canPull = hasRole('Admin', 'Analyst');
  const canGenerateReport = hasRole('Admin', 'Analyst');
  const canPrepareReport = hasRole('Admin', 'Analyst');
  const canApproveReport = hasRole('Admin', 'QA');
  const canManageProtocol = hasRole('Admin', 'Supervisor');

  const isDraft = protocol?.status === 'Draft';
  const isActive = protocol?.status === 'Active';
  const canComplete = isActive;
  const canCancel = protocol != null && protocol.status !== 'Completed' && protocol.status !== 'Cancelled';
  const reserveCells = matrixCells.filter((c) => c.is_reserve);

  // ── Loading Matrix editor state ──
  const [conditions, setConditions] = useState<string[]>([]);
  const [newCondition, setNewCondition] = useState('');
  const cellKey = (condition: string, isReserve: boolean, day: number | null) =>
    `${condition}|${isReserve ? 'reserve' : day}`;
  const cellMap = useMemo(() => {
    const map = new Map<string, MatrixCellInput>();
    for (const c of matrixCells) {
      map.set(cellKey(c.condition, c.is_reserve, c.time_point_days ?? null), c);
    }
    return map;
  }, [matrixCells]);
  const [localCells, setLocalCells] = useState<Map<string, MatrixCellInput>>(new Map());

  const effectiveCells = localCells.size > 0 ? localCells : cellMap;
  const knownConditions = useMemo(() => {
    const set = new Set<string>(conditions);
    for (const c of matrixCells) set.add(c.condition);
    return Array.from(set);
  }, [conditions, matrixCells]);

  const toggleCell = (condition: string, isReserve: boolean, day: number | null) => {
    const key = cellKey(condition, isReserve, day);
    const next = new Map(effectiveCells);
    const existing = next.get(key);
    next.set(key, {
      id: existing?.id,
      condition,
      is_reserve: isReserve,
      time_point_days: day,
      is_scheduled: !existing?.is_scheduled,
      notes: existing?.notes,
    });
    setLocalCells(next);
  };

  const addCondition = () => {
    if (!newCondition.trim() || knownConditions.includes(newCondition.trim())) return;
    setConditions([...conditions, newCondition.trim()]);
    setNewCondition('');
  };

  const handleSaveMatrix = () => {
    const cells = Array.from(effectiveCells.values());
    if (cells.length === 0) {
      toastService.warn('Add at least one condition and check a time point first.', 'Nothing to save');
      return;
    }
    setMatrix.mutate(
      { protocolId, cells },
      {
        onSuccess: () => {
          toastService.success('Loading Matrix saved.', 'Matrix Updated');
          setLocalCells(new Map());
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Save Matrix'),
      }
    );
  };

  // ── E-sign dialog (shared across all 4 gated actions) ──
  const [esignAction, setEsignAction] = useState<EsignAction | null>(null);
  const [esignTargetId, setEsignTargetId] = useState<number | null>(null);

  const esignConfig: Record<EsignAction, { title: string; label: string }> = {
    formulation: { title: 'Formulation Check', label: 'Check Formulation' },
    analytical: { title: 'Analytical Check', label: 'Check Analytical' },
    prepare: { title: 'Prepare Stability Report', label: 'Prepare' },
    approve: { title: 'Approve Stability Report', label: 'Approve' },
  };

  const handleEsignConfirm = (password: string, comments?: string) => {
    if (esignAction === 'formulation') {
      checkFormulation.mutate(
        { protocolId, payload: { password, comments } },
        {
          onSuccess: () => { toastService.success('Formulation check complete.', 'Protocol Updated'); setEsignAction(null); },
          onError: (e) => toastService.error(getErrorMessage(e), 'Formulation Check Failed'),
        }
      );
    } else if (esignAction === 'analytical') {
      checkAnalytical.mutate(
        { protocolId, payload: { password, comments } },
        {
          onSuccess: () => { toastService.success('Analytical check complete — protocol is now Active.', 'Protocol Updated'); setEsignAction(null); },
          onError: (e) => toastService.error(getErrorMessage(e), 'Analytical Check Failed'),
        }
      );
    } else if (esignAction === 'prepare' && esignTargetId != null) {
      prepareReport.mutate(
        { reportId: esignTargetId, protocolId, payload: { password, comments } },
        {
          onSuccess: () => { toastService.success('Report prepared.', 'Report Updated'); setEsignAction(null); setEsignTargetId(null); },
          onError: (e) => toastService.error(getErrorMessage(e), 'Prepare Failed'),
        }
      );
    } else if (esignAction === 'approve' && esignTargetId != null) {
      approveReport.mutate(
        { reportId: esignTargetId, protocolId, payload: { password, comments } },
        {
          onSuccess: () => { toastService.success('Report approved.', 'Report Updated'); setEsignAction(null); setEsignTargetId(null); },
          onError: (e) => toastService.error(getErrorMessage(e), 'Approve Failed'),
        }
      );
    }
  };

  // ── Generate Schedule ──
  const [showSchedule, setShowSchedule] = useState(false);
  const [batchInput, setBatchInput] = useState('');
  const [batchList, setBatchList] = useState<string[]>([]);

  const addBatch = () => {
    const trimmed = batchInput.trim();
    if (!trimmed || batchList.includes(trimmed)) return;
    setBatchList([...batchList, trimmed]);
    setBatchInput('');
  };

  const handleGenerateSchedule = () => {
    if (batchList.length === 0) {
      toastService.warn('Add at least one batch number.', 'Missing batches');
      return;
    }
    generateSchedule.mutate(
      { protocolId, payload: { batch_numbers: batchList } },
      {
        onSuccess: (created) => {
          toastService.success(`Scheduled ${created.length} new time point(s).`, 'Schedule Generated');
          setShowSchedule(false);
          setBatchList([]);
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Generate Schedule'),
      }
    );
  };

  // ── Header edit (Draft only) ──
  const [showEditHeader, setShowEditHeader] = useState(false);
  const [headerForm, setHeaderForm] = useState<UpdateProtocolHeaderRequest>({});

  const openEditHeader = () => {
    if (!protocol) return;
    setHeaderForm({
      condition: protocol.condition,
      duration_months: protocol.duration_months,
      study_type: protocol.study_type || undefined,
      batch_number: protocol.batch_number || undefined,
      label_claim: protocol.label_claim || undefined,
      api_name: protocol.api_name || undefined,
      api_batch_no: protocol.api_batch_no || undefined,
      primary_pack: protocol.primary_pack || undefined,
      secondary_pack: protocol.secondary_pack || undefined,
      remarks: protocol.remarks || undefined,
    });
    setShowEditHeader(true);
  };

  const handleSaveHeader = () => {
    updateHeader.mutate(
      { id: protocolId, payload: headerForm },
      {
        onSuccess: () => {
          toastService.success('Protocol header updated.', 'Saved');
          setShowEditHeader(false);
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Update Header'),
      }
    );
  };

  // ── Complete / Cancel ──
  const [showCancel, setShowCancel] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  const handleComplete = () => {
    completeProtocol.mutate(protocolId, {
      onSuccess: () => toastService.success('Protocol marked Completed.', 'Study Closed'),
      onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Complete'),
    });
  };

  const handleCancel = () => {
    cancelProtocol.mutate(
      { id: protocolId, payload: { reason: cancelReason || undefined } },
      {
        onSuccess: () => {
          toastService.success('Protocol cancelled.', 'Study Cancelled');
          setShowCancel(false);
          setCancelReason('');
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Cancel'),
      }
    );
  };

  // ── Reserve pull ──
  const [showReservePull, setShowReservePull] = useState(false);
  const [reserveCellId, setReserveCellId] = useState<number | null>(null);
  const [reserveBatch, setReserveBatch] = useState('');
  const [reserveComments, setReserveComments] = useState('');

  const handleCreateReservePull = () => {
    if (!reserveCellId || !reserveBatch.trim()) {
      toastService.warn('Select a reserve condition and enter a batch number.', 'Missing fields');
      return;
    }
    createReservePull.mutate(
      {
        protocolId,
        payload: { matrix_cell_id: reserveCellId, batch_number: reserveBatch.trim(), comments: reserveComments || undefined },
      },
      {
        onSuccess: () => {
          toastService.success('Reserve pull raised — find it in Time-Point Samples to Pull.', 'Reserve Raised');
          setShowReservePull(false);
          setReserveCellId(null);
          setReserveBatch('');
          setReserveComments('');
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Raise Reserve Pull'),
      }
    );
  };

  const handlePull = (sampleId: number) => {
    pullSample.mutate(
      { stabilitySampleId: sampleId, protocolId },
      {
        onSuccess: () => toastService.success('Time point pulled — Sample created in Sample Manager.', 'Pulled'),
        onError: (e) => toastService.error(getErrorMessage(e), 'Pull Failed'),
      }
    );
  };

  const handleGenerateReport = () => {
    generateReport.mutate(protocolId, {
      onSuccess: (report) => toastService.success(`Report ${report.report_number} generated as Draft.`, 'Report Generated'),
      onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Generate Report'),
    });
  };

  const [viewReport, setViewReport] = useState<StabilityReport | null>(null);

  // ── Report signature names (Draft reports only) ──
  const [signNamesReport, setSignNamesReport] = useState<StabilityReport | null>(null);
  const [checkedByName, setCheckedByName] = useState('');
  const [reviewedByName, setReviewedByName] = useState('');

  const openSignatureNames = (report: StabilityReport) => {
    setSignNamesReport(report);
    setCheckedByName(report.checked_by_name || '');
    setReviewedByName(report.reviewed_by_name || '');
  };

  const handleSaveSignatureNames = () => {
    if (!signNamesReport) return;
    setSignatureNames.mutate(
      {
        reportId: signNamesReport.id,
        protocolId,
        payload: { checked_by_name: checkedByName || undefined, reviewed_by_name: reviewedByName || undefined },
      },
      {
        onSuccess: () => {
          toastService.success('Signature names saved.', 'Report Updated');
          setSignNamesReport(null);
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Save'),
      }
    );
  };

  if (isLoading || !protocol) {
    return <p className="text-500">Loading protocol...</p>;
  }

  const productName = products.find((p) => p.id === protocol.product_id)?.name || `#${protocol.product_id}`;

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <div>
          <Button label="Back to Protocols" icon="pi pi-arrow-left" text size="small" onClick={() => navigate('/stability')} />
          <h2 className="text-lg font-semibold text-900 m-0 mt-1 flex align-items-center gap-2">
            <span className="font-mono">{protocol.protocol_code}</span>
            <StatusBadge status={protocol.status} />
          </h2>
        </div>
        <div className="flex gap-2 flex-wrap justify-content-end" style={{ maxWidth: '60%' }}>
          <Button
            label="Print Protocol"
            icon="pi pi-print"
            text
            onClick={() => window.open(`/stability/${protocolId}/print`, '_blank')}
          />
          {isDraft && canManageProtocol && (
            <Button label="Edit Header" icon="pi pi-pencil" text onClick={openEditHeader} />
          )}
          {isDraft && canManageMatrix && (
            <Button
              label="Check Formulation"
              icon="pi pi-check-circle"
              severity="warning"
              onClick={() => setEsignAction('formulation')}
            />
          )}
          {protocol.status === 'FormulationChecked' && canManageMatrix && (
            <Button
              label="Check Analytical"
              icon="pi pi-check-circle"
              severity="success"
              onClick={() => setEsignAction('analytical')}
            />
          )}
          {isActive && canGenerateSchedule && (
            <Button label="Generate Schedule" icon="pi pi-calendar-plus" onClick={() => setShowSchedule(true)} />
          )}
          {isActive && reserveCells.length > 0 && canPull && (
            <Button label="Raise Reserve Pull" icon="pi pi-inbox" outlined onClick={() => setShowReservePull(true)} />
          )}
          {canGenerateReport && samples.some((s) => s.status === 'Completed') && (
            <Button
              label="Generate Report"
              icon="pi pi-file"
              severity="secondary"
              outlined
              loading={generateReport.isPending}
              onClick={handleGenerateReport}
            />
          )}
          {canComplete && canManageProtocol && (
            <Button
              label="Mark Completed"
              icon="pi pi-flag"
              severity="success"
              outlined
              loading={completeProtocol.isPending}
              onClick={handleComplete}
            />
          )}
          {canCancel && canManageProtocol && (
            <Button label="Cancel Study" icon="pi pi-times" severity="danger" outlined onClick={() => setShowCancel(true)} />
          )}
        </div>
      </div>

      <div className="grid mb-4 text-sm">
        <div className="col-3"><span className="text-500 block">Product</span><span className="font-medium">{productName}</span></div>
        <div className="col-3"><span className="text-500 block">Condition</span><span className="font-medium">{protocol.condition}</span></div>
        <div className="col-3"><span className="text-500 block">Duration</span><span className="font-medium">{protocol.duration_months} months</span></div>
        <div className="col-3"><span className="text-500 block">Study Type</span><span className="font-medium">{protocol.study_type || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Batch No.</span><span className="font-medium">{protocol.batch_number || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Formulation Checked By</span><span className="font-medium">{protocol.formulation_checked_by || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Analytical Checked By</span><span className="font-medium">{protocol.approved_by || '-'}</span></div>
        <div className="col-3"><span className="text-500 block">Created By</span><span className="font-medium">{protocol.created_by}</span></div>
      </div>

      {/* Loading Matrix — Draft only */}
      {isDraft && (
        <div className="bg-white border-round-lg border-1 border-200 overflow-hidden mb-4">
          <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Loading Matrix</h3>
          <p className="text-sm text-500 m-0 px-3 pb-2">
            Check the time points to schedule for each condition. Editable only while Draft.
          </p>
          {canManageMatrix && (
            <div className="flex gap-2 px-3 pb-3 align-items-end">
              <div style={{ flex: 1 }}>
                <label className="block text-sm font-medium text-700 mb-1">Add Condition</label>
                <Dropdown
                  value={newCondition}
                  options={SUGGESTED_CONDITIONS}
                  onChange={(e) => setNewCondition(e.value)}
                  editable
                  placeholder="Select or type a condition..."
                  className="w-full"
                />
              </div>
              <Button label="Add" icon="pi pi-plus" onClick={addCondition} />
            </div>
          )}
          {knownConditions.length > 0 && (
            <div className="overflow-x-auto px-3 pb-3">
              <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th className="text-left p-2 border-1 border-200">Condition</th>
                    {STANDARD_TIME_POINT_DAYS.map((day) => (
                      <th key={day} className="p-2 border-1 border-200 text-center">{day}d</th>
                    ))}
                    <th className="p-2 border-1 border-200 text-center">Reserve</th>
                  </tr>
                </thead>
                <tbody>
                  {knownConditions.map((condition) => (
                    <tr key={condition}>
                      <td className="p-2 border-1 border-200 font-medium">{condition}</td>
                      {STANDARD_TIME_POINT_DAYS.map((day) => {
                        const cell = effectiveCells.get(cellKey(condition, false, day));
                        return (
                          <td key={day} className="p-2 border-1 border-200 text-center">
                            <Checkbox
                              checked={!!cell?.is_scheduled}
                              onChange={() => canManageMatrix && toggleCell(condition, false, day)}
                              disabled={!canManageMatrix}
                            />
                          </td>
                        );
                      })}
                      <td className="p-2 border-1 border-200 text-center">
                        <Checkbox
                          checked={!!effectiveCells.get(cellKey(condition, true, null))?.is_scheduled}
                          onChange={() => canManageMatrix && toggleCell(condition, true, null)}
                          disabled={!canManageMatrix}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {canManageMatrix && knownConditions.length > 0 && (
            <div className="p-3 pt-0 flex justify-content-end">
              <Button label="Save Matrix" icon="pi pi-save" loading={setMatrix.isPending} onClick={handleSaveMatrix} />
            </div>
          )}
        </div>
      )}

      {/* Time-point samples — Active+ */}
      {!isDraft && protocol.status !== 'FormulationChecked' && (
        <div className="bg-white border-round-lg border-1 border-200 overflow-hidden mb-4">
          <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Time-Point Samples</h3>
          <DataTable value={samples} size="small" paginator rows={10} emptyMessage="No time points scheduled yet.">
            <Column field="batch_number" header="Batch" />
            <Column field="condition" header="Condition" />
            <Column header="Time Point" body={(row: StabilitySample) => (row.time_point_days != null ? `${row.time_point_days}d` : '-')} />
            <Column header="Scheduled" body={(row: StabilitySample) => (row.scheduled_date ? new Date(row.scheduled_date).toLocaleDateString() : '-')} />
            <Column header="Pulled" body={(row: StabilitySample) => (row.pull_date ? new Date(row.pull_date).toLocaleDateString() : '-')} />
            <Column header="Status" body={(row: StabilitySample) => <StatusBadge status={row.status} />} />
            <Column
              header=""
              body={(row: StabilitySample) =>
                row.status === 'Scheduled' && canPull ? (
                  <Button
                    label="Pull"
                    text
                    size="small"
                    loading={pullSample.isPending && pullSample.variables?.stabilitySampleId === row.id}
                    onClick={() => handlePull(row.id)}
                  />
                ) : null
              }
            />
          </DataTable>
        </div>
      )}

      {/* Reports */}
      {(reports.length > 0 || canGenerateReport) && (
        <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
          <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Stability Reports</h3>
          <DataTable value={reports} size="small" emptyMessage="No reports generated yet.">
            <Column field="report_number" header="Report No." body={(row: StabilityReport) => <span className="font-mono">{row.report_number}</span>} />
            <Column header="Status" body={(row: StabilityReport) => <StatusBadge status={row.status} />} />
            <Column header="Generated" body={(row: StabilityReport) => (row.generated_at ? new Date(row.generated_at).toLocaleString() : '-')} />
            <Column field="prepared_by" header="Prepared By" />
            <Column field="approved_by" header="Approved By" />
            <Column
              header="Actions"
              body={(row: StabilityReport) => (
                <div className="flex gap-2">
                  <Button label="View" text size="small" onClick={() => setViewReport(row)} />
                  <Button
                    label="Print"
                    text
                    size="small"
                    onClick={() => window.open(`/stability/reports/${row.id}/print`, '_blank')}
                  />
                  {row.status === 'Draft' && canPrepareReport && (
                    <Button label="Signatures" text size="small" onClick={() => openSignatureNames(row)} />
                  )}
                  {row.status === 'Draft' && canPrepareReport && (
                    <Button label="Prepare" text size="small" severity="warning" onClick={() => { setEsignTargetId(row.id); setEsignAction('prepare'); }} />
                  )}
                  {row.status === 'Prepared' && canApproveReport && (
                    <Button label="Approve" text size="small" severity="success" onClick={() => { setEsignTargetId(row.id); setEsignAction('approve'); }} />
                  )}
                </div>
              )}
            />
          </DataTable>
        </div>
      )}

      {/* Generate Schedule dialog */}
      <Dialog header="Generate Time-Point Schedule" visible={showSchedule} onHide={() => setShowSchedule(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            Creates one time point per scheduled matrix cell for each batch number below. Already-scheduled combinations are skipped.
          </p>
          <div className="flex gap-2">
            <InputText value={batchInput} onChange={(e) => setBatchInput(e.target.value)} placeholder="Batch number" className="flex-1" onKeyDown={(e) => e.key === 'Enter' && addBatch()} />
            <Button label="Add" onClick={addBatch} />
          </div>
          <div className="flex gap-2 flex-wrap">
            {batchList.map((b) => (
              <Chip
                key={b}
                label={b}
                removable
                onRemove={() => {
                  setBatchList(batchList.filter((x) => x !== b));
                  return true;
                }}
              />
            ))}
          </div>
          <Button label="Generate Schedule" icon="pi pi-calendar-plus" onClick={handleGenerateSchedule} loading={generateSchedule.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      {/* View Report dialog */}
      <Dialog
        header={viewReport ? `Stability Report — ${viewReport.report_number}` : ''}
        visible={!!viewReport}
        onHide={() => setViewReport(null)}
        style={{ width: '700px' }}
        modal
      >
        {viewReport && (
          <div>
            <div className="grid text-sm mb-3">
              <div className="col-6"><span className="text-500 block">Product</span><span className="font-medium">{viewReport.product_name || '-'}</span></div>
              <div className="col-6"><span className="text-500 block">Batch No.</span><span className="font-medium">{viewReport.batch_no || '-'}</span></div>
              <div className="col-6"><span className="text-500 block">Condition</span><span className="font-medium">{viewReport.stability_condition || '-'}</span></div>
              <div className="col-6"><span className="text-500 block">Status</span><StatusBadge status={viewReport.status} /></div>
            </div>
            <h4 className="text-sm font-semibold text-900 mb-2">Results</h4>
            <DataTable value={viewReport.results_data} size="small" emptyMessage="No completed time points yet.">
              <Column field="test_name" header="Test" />
              <Column field="specification" header="Specification" />
              <Column
                header="Results"
                body={(row) => Object.entries(row.results || {}).map(([label, value]) => `${label}: ${value}`).join('  |  ')}
              />
            </DataTable>
          </div>
        )}
      </Dialog>

      {/* Edit Header — Draft only */}
      <Dialog header="Edit Protocol Header" visible={showEditHeader} onHide={() => setShowEditHeader(false)} style={{ width: '520px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Condition</label>
              <Dropdown
                value={headerForm.condition}
                options={SUGGESTED_CONDITIONS}
                onChange={(e) => setHeaderForm({ ...headerForm, condition: e.value })}
                className="w-full"
                editable
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Duration (months)</label>
              <InputNumber value={headerForm.duration_months} onValueChange={(e) => setHeaderForm({ ...headerForm, duration_months: e.value ?? undefined })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Batch No.</label>
              <InputText value={headerForm.batch_number || ''} onChange={(e) => setHeaderForm({ ...headerForm, batch_number: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Label Claim</label>
              <InputText value={headerForm.label_claim || ''} onChange={(e) => setHeaderForm({ ...headerForm, label_claim: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">API Name</label>
              <InputText value={headerForm.api_name || ''} onChange={(e) => setHeaderForm({ ...headerForm, api_name: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">API Batch No.</label>
              <InputText value={headerForm.api_batch_no || ''} onChange={(e) => setHeaderForm({ ...headerForm, api_batch_no: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Primary Pack</label>
              <InputText value={headerForm.primary_pack || ''} onChange={(e) => setHeaderForm({ ...headerForm, primary_pack: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Secondary Pack</label>
              <InputText value={headerForm.secondary_pack || ''} onChange={(e) => setHeaderForm({ ...headerForm, secondary_pack: e.target.value })} className="w-full" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Remarks</label>
            <InputTextarea value={headerForm.remarks || ''} onChange={(e) => setHeaderForm({ ...headerForm, remarks: e.target.value })} rows={2} className="w-full" />
          </div>
          <Button label="Save Header" icon="pi pi-save" onClick={handleSaveHeader} loading={updateHeader.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      {/* Cancel Study confirm */}
      <Dialog header="Cancel Stability Study" visible={showCancel} onHide={() => setShowCancel(false)} style={{ width: '420px' }} modal>
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            This permanently cancels {protocol.protocol_code}. This cannot be undone.
          </p>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Reason (optional)</label>
            <InputTextarea value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} rows={2} className="w-full" />
          </div>
          <Button label="Cancel Study" severity="danger" onClick={handleCancel} loading={cancelProtocol.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      {/* Raise Reserve Pull */}
      <Dialog header="Raise Reserve Pull" visible={showReservePull} onHide={() => setShowReservePull(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            Raises an on-demand time point from a Reserve condition (e.g. for an OOS retest). It appears as Scheduled in the Time-Point Samples table below, ready to Pull.
          </p>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Reserve Condition</label>
            <Dropdown
              value={reserveCellId}
              options={reserveCells.map((c) => ({ label: c.condition, value: c.id }))}
              onChange={(e) => setReserveCellId(e.value)}
              placeholder="Select a reserve condition..."
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Batch Number</label>
            <InputText value={reserveBatch} onChange={(e) => setReserveBatch(e.target.value)} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Comments</label>
            <InputTextarea value={reserveComments} onChange={(e) => setReserveComments(e.target.value)} rows={2} className="w-full" />
          </div>
          <Button label="Raise Reserve Pull" onClick={handleCreateReservePull} loading={createReservePull.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      {/* Report Signature Names — Draft reports only, print-only fields */}
      <Dialog header="Report Signature Names" visible={!!signNamesReport} onHide={() => setSignNamesReport(null)} style={{ width: '420px' }} modal>
        <div className="flex flex-column gap-3">
          <p className="text-sm text-600 m-0">
            Free-text names for the printed report's "Checked By" / "Reviewed By" signature block (Prepared/Approved remain system e-sign gates).
          </p>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Checked By</label>
            <InputText value={checkedByName} onChange={(e) => setCheckedByName(e.target.value)} className="w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Reviewed By</label>
            <InputText value={reviewedByName} onChange={(e) => setReviewedByName(e.target.value)} className="w-full" />
          </div>
          <Button label="Save" onClick={handleSaveSignatureNames} loading={setSignatureNames.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      <ESignDialog
        visible={esignAction != null}
        title={esignAction ? esignConfig[esignAction].title : ''}
        actionLabel={esignAction ? esignConfig[esignAction].label : 'Confirm'}
        loading={checkFormulation.isPending || checkAnalytical.isPending || prepareReport.isPending || approveReport.isPending}
        onHide={() => { setEsignAction(null); setEsignTargetId(null); }}
        onConfirm={handleEsignConfirm}
      />
    </div>
  );
};
