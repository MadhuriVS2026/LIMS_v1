/**
 * Stability Protocols list page — raise a new Draft protocol (full header
 * fields from the real Stability Protocol Format document) and drill into
 * its detail/workflow page.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputNumber } from 'primereact/inputnumber';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Calendar } from 'primereact/calendar';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService, getErrorMessage } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import { useProducts } from '@features/sample-management/hooks/useSamples';
import { useCreateProtocol, useProtocolList } from '../hooks/useStability';
import { STUDY_TYPES, SUGGESTED_CONDITIONS, type CreateProtocolRequest, type StabilityProtocol } from '../models/stability.types';

const emptyForm: Partial<CreateProtocolRequest> = {
  condition: SUGGESTED_CONDITIONS[3],
  duration_months: 24,
  study_type: STUDY_TYPES[0],
};

export const ProtocolsPage = () => {
  const navigate = useNavigate();
  const { hasRole } = usePermissions();
  const canCreate = hasRole('Admin', 'Supervisor');
  const { data: protocols = [], isLoading } = useProtocolList();
  const { data: products = [] } = useProducts();
  const createProtocol = useCreateProtocol();

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<CreateProtocolRequest>>(emptyForm);

  const productName = (id: number) => products.find((p) => p.id === id)?.name || `#${id}`;

  const closeModal = () => {
    setShowModal(false);
    setForm(emptyForm);
  };

  const handleCreate = () => {
    if (!form.product_id || !form.condition || !form.duration_months) {
      toastService.warn('Product, condition, and duration are required.', 'Missing fields');
      return;
    }
    createProtocol.mutate(form as CreateProtocolRequest, {
      onSuccess: (protocol) => {
        toastService.success(`Protocol ${protocol.protocol_code} created as Draft.`, 'Protocol Raised');
        closeModal();
        navigate(`/stability/${protocol.id}`);
      },
      onError: (e) => toastService.error(getErrorMessage(e), 'Could Not Create Protocol'),
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{protocols.length} stability protocol(s)</p>
        {canCreate && <Button label="New Protocol" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={protocols} loading={isLoading} paginator rows={10} size="small" emptyMessage="No stability protocols yet.">
          <Column field="protocol_code" header="Protocol" body={(row: StabilityProtocol) => <span className="font-mono text-blue-600">{row.protocol_code}</span>} />
          <Column header="Product" body={(row: StabilityProtocol) => productName(row.product_id)} />
          <Column field="condition" header="Condition" />
          <Column header="Duration" body={(row: StabilityProtocol) => `${row.duration_months} months`} />
          <Column field="study_type" header="Type" />
          <Column field="batch_number" header="Batch" />
          <Column header="Status" body={(row: StabilityProtocol) => <StatusBadge status={row.status} />} />
          <Column
            header="Actions"
            body={(row: StabilityProtocol) => (
              <Button label="View" size="small" text onClick={() => navigate(`/stability/${row.id}`)} />
            )}
          />
        </DataTable>
      </div>

      <Dialog header="New Stability Protocol" visible={showModal} onHide={closeModal} style={{ width: '520px' }} modal>
        <div className="flex flex-column gap-3">
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Product</label>
            <Dropdown
              value={form.product_id}
              options={products.filter((p) => p.status === 'Active').map((p) => ({ label: p.name, value: p.id }))}
              onChange={(e) => setForm({ ...form, product_id: e.value })}
              className="w-full"
              placeholder="Select product..."
              filter
            />
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Condition</label>
              <Dropdown
                value={form.condition}
                options={SUGGESTED_CONDITIONS}
                onChange={(e) => setForm({ ...form, condition: e.value })}
                className="w-full"
                editable
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Study Type</label>
              <Dropdown
                value={form.study_type}
                options={STUDY_TYPES}
                onChange={(e) => setForm({ ...form, study_type: e.value })}
                className="w-full"
              />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Duration (months)</label>
              <InputNumber value={form.duration_months} onValueChange={(e) => setForm({ ...form, duration_months: e.value ?? 24 })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Batch No.</label>
              <InputText value={form.batch_number || ''} onChange={(e) => setForm({ ...form, batch_number: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Label Claim</label>
              <InputText value={form.label_claim || ''} onChange={(e) => setForm({ ...form, label_claim: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Stability Initiation Date</label>
              <Calendar
                value={form.stability_initiation_date ? new Date(form.stability_initiation_date) : null}
                onChange={(e) => setForm({ ...form, stability_initiation_date: (e.value as Date)?.toISOString() })}
                dateFormat="dd/mm/yy"
                className="w-full"
                showIcon
              />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">API Name</label>
              <InputText value={form.api_name || ''} onChange={(e) => setForm({ ...form, api_name: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">API Batch No.</label>
              <InputText value={form.api_batch_no || ''} onChange={(e) => setForm({ ...form, api_batch_no: e.target.value })} className="w-full" />
            </div>
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Primary Pack</label>
              <InputText value={form.primary_pack || ''} onChange={(e) => setForm({ ...form, primary_pack: e.target.value })} className="w-full" />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Secondary Pack</label>
              <InputText value={form.secondary_pack || ''} onChange={(e) => setForm({ ...form, secondary_pack: e.target.value })} className="w-full" />
            </div>
          </div>
          <Button label="Create Protocol (Draft)" onClick={handleCreate} loading={createProtocol.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
