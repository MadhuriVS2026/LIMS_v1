/**
 * SAP Integration page — Usage Decision posting to SAP CPI, received
 * inspection lots, and integration log.
 *
 * Note: only the SAP Integration Suite (CPI) tenant is ever called from this
 * feature. There is no "read batch from SAP" action here because the only
 * batch/lot-lookup endpoint in the source Postman collection targets a
 * different host (the customer's own LIMS web API, not SAP), which this
 * app intentionally does not call.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dropdown } from 'primereact/dropdown';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { sapApi } from '../api/sapApi';
import type { SAPReceivedLot } from '../models/sap.types';
import { useSampleList } from '@features/sample-management/hooks/useSamples';
import type { Sample } from '@features/sample-management/models/sample.types';
import { sampleApi } from '@features/sample-management/api/sampleApi';

export const SAPIntegrationPage = () => {
  const navigate = useNavigate();
  const { hasRole } = usePermissions();
  const canViewLogs = hasRole('Admin', 'QA');
  const canViewLots = hasRole('Admin', 'Analyst', 'QA');
  const canPostUD = hasRole('QA');
  const { data: logs = [] } = useQuery({ queryKey: ['sap-logs'], queryFn: sapApi.getLogs, enabled: canViewLogs });
  const { data: receivedLots = [] } = useQuery({
    queryKey: ['sap-received-lots'],
    queryFn: sapApi.getReceivedLots,
    enabled: canViewLots,
    refetchInterval: 15000,
  });
  const [selectedLot, setSelectedLot] = useState<SAPReceivedLot | null>(null);

  // Usage Decision queue: samples that have cleared Analyst submission +
  // Supervisor review + QA release (i.e. Approved), have a SAP inspection
  // lot linked, and haven't had their verdict posted back to SAP yet.
  const { data: allSamples = [] } = useQuery({
    queryKey: ['samples', undefined],
    queryFn: () => sampleApi.list(),
    enabled: canPostUD,
  });
  const udQueue = allSamples.filter(
    (s) => s.status === 'Approved' && s.sap_inspection_lot && !s.sap_ud_posted
  );

  const [udTarget, setUdTarget] = useState<Sample | null>(null);
  const [udCode, setUdCode] = useState('A');
  const [udPassword, setUdPassword] = useState('');
  const [udLoading, setUdLoading] = useState(false);
  const [coaSample, setCoaSample] = useState<Sample | null>(null);
  const [coaData, setCoaData] = useState<Record<string, unknown> | null>(null);
  const [coaLoading, setCoaLoading] = useState(false);

  const handleViewCoa = async (sample: Sample) => {
    setCoaLoading(true);
    try {
      const data = await sampleApi.getCoa(sample.id);
      setCoaData(data);
      setCoaSample(sample);
    } catch (e: any) {
      toastService.error(getErrorMessage(e), 'Could not load COA');
    } finally {
      setCoaLoading(false);
    }
  };

  const handlePostUD = async () => {
    if (!udTarget) return;
    setUdLoading(true);
    try {
      const result = await sapApi.postUsageDecision({ sample_id: udTarget.id, ud_code: udCode, password: udPassword });
      toastService.success(result.message, 'Usage Decision Posted');
      setUdTarget(null);
      setUdPassword('');
    } catch (e: any) {
      toastService.error(getErrorMessage(e), 'Usage Decision Failed');
    } finally {
      setUdLoading(false);
    }
  };

  return (
    <div>
      {canPostUD && (
        <div className="bg-white border-round-lg border-1 border-200 overflow-hidden mb-4">
          <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Usage Decision Queue</h3>
          <p className="text-sm text-500 m-0 px-3 pb-2">
            Samples that cleared Analyst submission, Supervisor review, and QA release — ready to post their verdict to SAP.
          </p>
          <DataTable value={udQueue} size="small" paginator rows={10} emptyMessage="No approved samples pending a Usage Decision.">
            <Column field="sample_code" header="Sample Code" body={(row: Sample) => <span className="font-mono text-blue-600">{row.sample_code}</span>} />
            <Column header="Product" body={(row: Sample) => row.product?.name || '-'} />
            <Column field="batch_number" header="Batch" />
            <Column field="sap_inspection_lot" header="SAP Lot" />
            <Column header="Status" body={(row: Sample) => <StatusBadge status={row.status} />} />
            <Column header="Released" body={(row: Sample) => (row.coa_released_at ? new Date(row.coa_released_at).toLocaleString() : '-')} />
            <Column
              header="Actions"
              body={(row: Sample) => (
                <div className="flex gap-2">
                  <Button label="View COA" text size="small" loading={coaLoading} onClick={() => handleViewCoa(row)} />
                  <Button
                    label="Post Usage Decision"
                    text
                    size="small"
                    severity="success"
                    onClick={() => {
                      setUdCode('A');
                      setUdTarget(row);
                    }}
                  />
                </div>
              )}
            />
          </DataTable>
        </div>
      )}

      {canViewLots && (
        <div className="bg-white border-round-lg border-1 border-200 overflow-hidden mb-4">
          <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Inspection Lots Received from SAP</h3>
          <p className="text-sm text-500 m-0 px-3 pb-2">Lots pushed in from SAP CPI. Refreshes automatically every 15s.</p>
          <DataTable value={receivedLots} size="small" paginator rows={10} emptyMessage="No inspection lots received yet.">
            <Column field="inspection_lot" header="Inspection Lot" />
            <Column field="material_desc" header="Material" />
            <Column field="batch_number" header="Batch" />
            <Column field="vendor_name" header="Vendor" />
            <Column field="plant" header="Plant" />
            <Column header="Received" body={(row) => (row.received_at ? new Date(row.received_at).toLocaleString() : '-')} />
            <Column header="Sample" body={(row) => (row.consumed_by_sample_id ? <StatusBadge status="Sampled" /> : <span className="text-500 text-sm">Not sampled</span>)} />
            <Column
              header=""
              body={(row) => (
                <div className="flex gap-2">
                  <Button label="View" text size="small" onClick={() => setSelectedLot(row)} />
                  {hasRole('Admin', 'Analyst') && !row.consumed_by_sample_id && (
                    <Button
                      label="Create Sample"
                      text
                      size="small"
                      severity="success"
                      onClick={() => navigate('/samples', { state: { prefillFromLot: row } })}
                    />
                  )}
                </div>
              )}
            />
          </DataTable>
        </div>
      )}

      {canViewLogs && (
        <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
          <h3 className="text-base font-semibold text-900 m-0 p-3 pb-0">Integration Log</h3>
          <DataTable value={logs} size="small" paginator rows={10}>
            <Column header="Time" body={(row) => (row.created_at ? new Date(row.created_at).toLocaleString() : '-')} />
            <Column field="transaction_type" header="Type" />
            <Column field="direction" header="Direction" />
            <Column field="sap_inspection_lot" header="Lot" />
            <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
            <Column field="created_by" header="User" />
          </DataTable>
        </div>
      )}

      <Dialog
        header={selectedLot ? `Inspection Lot ${selectedLot.inspection_lot}` : ''}
        visible={!!selectedLot}
        onHide={() => setSelectedLot(null)}
        style={{ width: '50rem' }}
      >
        {selectedLot && (
          <div>
            <div className="grid mb-3">
              <div className="col-6"><span className="text-500 block text-sm">Plant</span><span className="font-medium">{selectedLot.plant || '-'}</span></div>
              <div className="col-6"><span className="text-500 block text-sm">Material</span><span className="font-medium">{selectedLot.material_number || '-'} — {selectedLot.material_desc || '-'}</span></div>
              <div className="col-6"><span className="text-500 block text-sm">Batch Number</span><span className="font-medium">{selectedLot.batch_number || '-'}</span></div>
              <div className="col-6"><span className="text-500 block text-sm">Storage Location</span><span className="font-medium">{selectedLot.storage_location || '-'}</span></div>
              <div className="col-6"><span className="text-500 block text-sm">Vendor</span><span className="font-medium">{selectedLot.vendor_code || '-'} — {selectedLot.vendor_name || '-'}</span></div>
              <div className="col-6"><span className="text-500 block text-sm">Vendor Batch</span><span className="font-medium">{selectedLot.vendor_batch || '-'}</span></div>
              <div className="col-6"><span className="text-500 block text-sm">Quantity</span><span className="font-medium">{selectedLot.lot_quantity || '-'} {selectedLot.lot_unit || ''}</span></div>
              <div className="col-6"><span className="text-500 block text-sm">Mfg / Exp Date</span><span className="font-medium">{selectedLot.manufacturing_date || '-'} / {selectedLot.expiry_date || '-'}</span></div>
            </div>
            <h4 className="text-sm font-semibold text-900 mb-2">Test Characteristics</h4>
            <DataTable value={selectedLot.characteristics} size="small">
              <Column field="characteristicNum" header="#" />
              <Column field="testName" header="Test" />
              <Column field="uom" header="UOM" />
              <Column field="targetValue" header="Target" />
              <Column field="upperTolLimit" header="Upper Limit" />
              <Column field="lowerTolLimit" header="Lower Limit" />
            </DataTable>
          </div>
        )}
      </Dialog>

      {/* Certificate of Analysis viewer, launched from the Usage Decision queue */}
      <Dialog
        header={coaSample ? `Certificate of Analysis — ${coaSample.sample_code}` : ''}
        visible={!!coaSample}
        onHide={() => { setCoaSample(null); setCoaData(null); }}
        style={{ width: '600px' }}
        modal
      >
        {coaData && (
          <div>
            <div className="grid text-sm mb-3">
              <div className="col-6"><span className="text-500 block">Batch</span><span className="font-medium">{String(coaData.batch_number)}</span></div>
              <div className="col-6"><span className="text-500 block">Product</span><span className="font-medium">{String(coaData.product_name)}</span></div>
              <div className="col-6"><span className="text-500 block">Verdict</span><span className="font-medium">{String(coaData.verdict)}</span></div>
              <div className="col-6"><span className="text-500 block">Released By</span><span className="font-medium">{String(coaData.released_by)}</span></div>
              <div className="col-6"><span className="text-500 block">Released At</span><span className="font-medium">{new Date(String(coaData.released_at)).toLocaleString()}</span></div>
            </div>
            <h4 className="text-sm font-semibold text-900 mb-2">Results at Release</h4>
            <DataTable value={(coaData.results as any[]) || []} size="small">
              <Column field="test_id" header="Test ID" />
              <Column header="Limits" body={(row) => (row.min_limit != null ? `${row.min_limit} – ${row.max_limit}` : row.expected_result || '-')} />
              <Column header="Result" body={(row) => row.result_value ?? row.result_text ?? '-'} />
              <Column header="OOS" body={(row) => (row.is_oos ? <span className="text-red-600 font-bold">YES</span> : '-')} />
            </DataTable>
          </div>
        )}
      </Dialog>

      {/* Post Usage Decision, launched from the Usage Decision queue */}
      <Dialog
        header={udTarget ? `Post Usage Decision — ${udTarget.sample_code}` : ''}
        visible={!!udTarget}
        onHide={() => { setUdTarget(null); setUdPassword(''); }}
        style={{ width: '420px' }}
        modal
      >
        {udTarget && (
          <div className="flex flex-column gap-3">
            <p className="text-sm text-600 m-0">
              This sends the QA verdict for inspection lot <span className="font-mono">{udTarget.sap_inspection_lot}</span> to SAP CPI (Process_UD). This writes to SAP.
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
            <div>
              <label className="block text-sm font-medium text-700 mb-1">Password (E-Sign)</label>
              <InputText type="password" value={udPassword} onChange={(e) => setUdPassword(e.target.value)} className="w-full" />
            </div>
            <Button label="Post to SAP" severity="success" onClick={handlePostUD} loading={udLoading} disabled={!udPassword} className="w-full mt-1" />
          </div>
        )}
      </Dialog>
    </div>
  );
};
