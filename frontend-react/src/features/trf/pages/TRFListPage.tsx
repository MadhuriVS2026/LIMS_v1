/**
 * TRF list page — table of Test Request Forms with a status filter and a
 * role-aware default filter (Initiator: own TRFs; FDGL: pending their
 * approval; ADGL: pending their acceptance/release; Analyst: pending their
 * acceptance). "New TRF" opens a header-fields dialog (Admin/Analyst);
 * test lines are then added on the detail page.
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dropdown } from 'primereact/dropdown';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Calendar } from 'primereact/calendar';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useProducts } from '@features/sample-management/hooks/useSamples';
import { useCreateTRF, useTRFList } from '../hooks/useTRF';
import type { CreateTRFRequest, TestRequestForm } from '../models/trf.types';

const STATUS_OPTIONS = [
  { label: 'All', value: 'All' },
  { label: 'Draft', value: 'Draft' },
  { label: 'Pending FDGL Approval', value: 'PendingFDGLApproval' },
  { label: 'Pending ADGL Acceptance', value: 'PendingADGLAcceptance' },
  { label: 'Pending Analyst Acceptance', value: 'PendingAnalystAcceptance' },
  { label: 'In Progress', value: 'InProgress' },
  { label: 'Pending ADGL Release', value: 'PendingADGLRelease' },
  { label: 'Released', value: 'Released' },
  { label: 'Referred Back', value: 'ReferredBack' },
  { label: 'Rejected', value: 'Rejected' },
];

/**
 * Role-aware default status filter, matching Requirement 12.1's per-role
 * dashboards. Supervisor/QA only ever act as pure gate-keepers in this
 * system's role mapping, so defaulting to their pending queue makes sense.
 * Analyst is dual-purpose (Initiator AND the Analyst gate — Decision 1 in
 * design.md), so it must default to "All": defaulting to a gate-only filter
 * would hide an analyst's own just-created Draft/ReferredBack TRFs.
 */
function defaultStatusFor(role: string | undefined): string {
  switch (role) {
    case 'Supervisor':
      return 'PendingFDGLApproval';
    case 'QA':
      return 'PendingADGLAcceptance';
    default:
      return 'All';
  }
}

const emptyForm: Partial<CreateTRFRequest> = {};

export const TRFListPage = () => {
  const navigate = useNavigate();
  const { hasRole, role } = usePermissions();
  const canCreate = hasRole('Admin', 'Analyst');
  const { data: trfs = [], isLoading } = useTRFList();
  const { data: products = [] } = useProducts();
  const createTRF = useCreateTRF();

  const [statusFilter, setStatusFilter] = useState<string>(defaultStatusFor(role));
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<Partial<CreateTRFRequest>>(emptyForm);

  const activeProducts = products.filter((p) => p.status === 'Active');

  const filtered = useMemo(
    () => (statusFilter === 'All' ? trfs : trfs.filter((t) => t.status === statusFilter)),
    [trfs, statusFilter]
  );

  const closeCreate = () => {
    setShowCreate(false);
    setForm(emptyForm);
  };

  const handleCreate = () => {
    if (form.product_id == null || !form.batch_number?.trim()) {
      toastService.warn('Product and Batch Number are required.', 'Missing Fields');
      return;
    }
    createTRF.mutate(
      { ...form, batch_number: form.batch_number.trim() } as CreateTRFRequest,
      {
        onSuccess: (trf) => {
          toastService.success(`${trf.trf_number} created as Draft.`, 'TRF Created');
          closeCreate();
          navigate(`/trf/${trf.id}`);
        },
        onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Create TRF'),
      }
    );
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <div className="flex align-items-center gap-3">
          <p className="text-sm text-500 m-0">{filtered.length} requisition(s)</p>
          <Dropdown value={statusFilter} options={STATUS_OPTIONS} onChange={(e) => setStatusFilter(e.value)} className="w-14rem" />
        </div>
        {canCreate && <Button label="New TRF" icon="pi pi-plus" onClick={() => setShowCreate(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={filtered} loading={isLoading} paginator rows={10} size="small" emptyMessage="No Test Request Forms found.">
          <Column field="trf_number" header="TRF Number" body={(row: TestRequestForm) => <span className="font-mono text-blue-600">{row.trf_number}</span>} />
          <Column field="ar_number" header="AR Number" body={(row: TestRequestForm) => row.ar_number || '-'} />
          <Column header="Status" body={(row: TestRequestForm) => <StatusBadge status={row.status} />} />
          <Column header="Test Lines" body={(row: TestRequestForm) => row.test_lines.length} />
          <Column field="batch_number" header="Batch" />
          <Column field="created_by" header="Initiated By" />
          <Column header="Created" body={(row: TestRequestForm) => new Date(row.created_date).toLocaleString()} />
          <Column header="Actions" body={(row: TestRequestForm) => <Button label="View" size="small" text onClick={() => navigate(`/trf/${row.id}`)} />} />
        </DataTable>
      </div>

      <Dialog header="New Test Request Form" visible={showCreate} onHide={closeCreate} style={{ width: '520px' }} modal>
        <div className="flex flex-column gap-3">
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Product</label>
            <Dropdown
              value={form.product_id}
              options={activeProducts.map((p) => ({ label: `${p.name} (${p.code})`, value: p.id }))}
              onChange={(e) => setForm({ ...form, product_id: e.value })}
              placeholder="Select product..."
              className="w-full"
              filter
            />
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Batch Number</label>
              <InputText value={form.batch_number || ''} onChange={(e) => setForm({ ...form, batch_number: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Label Claim</label>
              <InputText value={form.label_claim || ''} onChange={(e) => setForm({ ...form, label_claim: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Stage of Sample</label>
              <InputText value={form.stage_of_sample || ''} onChange={(e) => setForm({ ...form, stage_of_sample: e.target.value })} className="w-full" placeholder="e.g. Finished Product" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Group / Department</label>
              <InputText value={form.group_name || ''} onChange={(e) => setForm({ ...form, group_name: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Quantity</label>
              <InputText value={form.quantity || ''} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Pack Details</label>
              <InputText value={form.pack_details || ''} onChange={(e) => setForm({ ...form, pack_details: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Storage Condition</label>
              <InputText value={form.storage_condition || ''} onChange={(e) => setForm({ ...form, storage_condition: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Storage Period</label>
              <InputText value={form.storage_period || ''} onChange={(e) => setForm({ ...form, storage_period: e.target.value })} className="w-full" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Manufactured By</label>
            <InputText value={form.manufactured_by || ''} onChange={(e) => setForm({ ...form, manufactured_by: e.target.value })} className="w-full" />
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Mfg. Date</label>
              <Calendar
                value={form.mfg_date ? new Date(form.mfg_date) : null}
                onChange={(e) => setForm({ ...form, mfg_date: e.value ? (e.value as Date).toISOString() : undefined })}
                className="w-full"
                dateFormat="dd-M-yy"
                showIcon
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Expiry / Retest Date</label>
              <Calendar
                value={form.expiry_or_retest_date ? new Date(form.expiry_or_retest_date) : null}
                onChange={(e) => setForm({ ...form, expiry_or_retest_date: e.value ? (e.value as Date).toISOString() : undefined })}
                className="w-full"
                dateFormat="dd-M-yy"
                showIcon
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Remark</label>
            <InputTextarea value={form.remark || ''} onChange={(e) => setForm({ ...form, remark: e.target.value })} rows={2} className="w-full" />
          </div>
          <Button label="Create Draft TRF" onClick={handleCreate} loading={createTRF.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
