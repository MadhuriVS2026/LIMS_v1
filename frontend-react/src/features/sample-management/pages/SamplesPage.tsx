/**
 * Samples list page — Sample Login Registration + workflow actions.
 */
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputNumber } from 'primereact/inputnumber';
import { Dropdown } from 'primereact/dropdown';
import { StatusBadge } from '@shared/components/StatusBadge';
import { toastService } from '@shared/services/toastService';
import { usePermissions } from '@core/rbac/usePermissions';
import {
  useCreateSample,
  useDeleteSample,
  useProducts,
  useReceiveSample,
  useSampleList,
  useUpdateSample,
} from '../hooks/useSamples';
import { ESignDialog } from '@shared/components/ESignDialog';
import type { CreateSampleRequest, Sample } from '../models/sample.types';
import type { SAPReceivedLot } from '@features/sap-integration/models/sap.types';

export const SamplesPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { hasRole } = usePermissions();
  const { data: samples = [], isLoading } = useSampleList();
  const { data: products = [] } = useProducts();
  const createSample = useCreateSample();
  const receiveSample = useReceiveSample();
  const updateSample = useUpdateSample();
  const deleteSample = useDeleteSample();

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<CreateSampleRequest>>({ unit: 'mL', priority: 'Normal' });
  const [prefillLot, setPrefillLot] = useState<SAPReceivedLot | null>(null);
  const [editTarget, setEditTarget] = useState<Sample | null>(null);
  const [editForm, setEditForm] = useState<Partial<CreateSampleRequest>>({});
  const [deleteTarget, setDeleteTarget] = useState<Sample | null>(null);

  const activeProducts = products.filter((p) => p.status === 'Active');

  // Arrived here via "Create Sample" on a received SAP lot — prefill from it.
  useEffect(() => {
    const lot = (location.state as { prefillFromLot?: SAPReceivedLot } | null)?.prefillFromLot;
    if (lot) {
      setPrefillLot(lot);
      setForm({
        unit: lot.lot_unit?.trim() || 'mL',
        priority: 'Normal',
        batch_number: lot.batch_number || '',
        quantity_received: lot.lot_quantity ? parseFloat(lot.lot_quantity) : undefined,
        sap_inspection_lot: lot.inspection_lot,
        sap_material: lot.material_number || undefined,
        sap_plant: lot.plant || undefined,
        sap_vendor: lot.vendor_name || undefined,
        sap_vendor_batch: lot.vendor_batch || undefined,
        manufacturing_date: lot.manufacturing_date || undefined,
        expiry_date: lot.expiry_date || undefined,
      });
      setShowModal(true);
      // Clear the router state so refreshing/closing doesn't re-trigger prefill.
      navigate(location.pathname, { replace: true, state: null });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = () => {
    const missing: string[] = [];
    if (form.product_id == null) missing.push('Product');
    if (!form.batch_number?.trim()) missing.push('Batch Number');
    if (form.quantity_received == null) missing.push('Quantity');
    if (!form.unit?.trim()) missing.push('Unit');

    if (missing.length > 0) {
      toastService.warn(`Missing: ${missing.join(', ')}.`, 'Missing fields');
      return;
    }
    createSample.mutate(form as CreateSampleRequest, {
      onSuccess: (sample) => {
        toastService.success(`Sample ${sample.sample_code} logged successfully.`, 'Sample Logged');
        setShowModal(false);
        setForm({ unit: 'mL', priority: 'Normal' });
        setPrefillLot(null);
      },
    });
  };

  const closeModal = () => {
    setShowModal(false);
    setForm({ unit: 'mL', priority: 'Normal' });
    setPrefillLot(null);
  };

  const handleReceive = (sampleId: number, sampleCode: string) => {
    receiveSample.mutate(sampleId, {
      onSuccess: () => toastService.success(`Sample ${sampleCode} marked as Received.`, 'Sample Received'),
    });
  };

  const canEditSample = (s: Sample) => s.status === 'Logged' || s.status === 'Received';
  const canDeleteSample = (s: Sample) =>
    s.status !== 'Approved' && s.status !== 'Rejected' && s.status !== 'Inactive';

  const openEdit = (s: Sample) => {
    setEditTarget(s);
    setEditForm({
      batch_number: s.batch_number,
      quantity_received: s.quantity_received,
      unit: s.unit,
      sample_type: s.sample_type ?? undefined,
      priority: s.priority ?? 'Normal',
    });
  };

  const handleUpdate = () => {
    if (!editTarget) return;
    if (!editForm.batch_number?.trim()) {
      toastService.warn('Batch Number is required.', 'Missing fields');
      return;
    }
    if (editForm.quantity_received == null) {
      toastService.warn('Quantity is required.', 'Missing fields');
      return;
    }
    updateSample.mutate(
      { id: editTarget.id, payload: editForm },
      {
        onSuccess: (s) => {
          toastService.success(`Sample ${s.sample_code} updated.`, 'Sample Updated');
          setEditTarget(null);
          setEditForm({});
        },
      }
    );
  };

  const handleDelete = (password: string, comments?: string) => {
    if (!deleteTarget) return;
    deleteSample.mutate(
      { id: deleteTarget.id, password, comments },
      {
        onSuccess: (s) => {
          toastService.success(`Sample ${s.sample_code} deactivated. GL/TL/Supervisor notified for review.`, 'Sample Deactivated');
          setDeleteTarget(null);
        },
      }
    );
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{samples.length} samples total</p>
        {hasRole('Admin', 'Analyst') && <Button label="Log Sample" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={samples} loading={isLoading} paginator rows={10} size="small">
          <Column field="sample_code" header="Sample Code" body={(row) => <span className="font-mono text-blue-600">{row.sample_code}</span>} />
          <Column header="Product" body={(row) => row.product?.name} />
          <Column field="batch_number" header="Batch" />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
          <Column header="Logged" body={(row) => (row.logged_at ? new Date(row.logged_at).toLocaleDateString() : '-')} />
          <Column
            header="Actions"
            body={(row) => (
              <div className="flex gap-2">
                {row.status === 'Logged' && hasRole('Analyst', 'Supervisor') && (
                  <Button
                    label="Receive"
                    size="small"
                    text
                    loading={receiveSample.isPending && receiveSample.variables === row.id}
                    onClick={() => handleReceive(row.id, row.sample_code)}
                  />
                )}
                {canEditSample(row) && hasRole('Admin', 'Analyst') && (
                  <Button label="Edit" size="small" text onClick={() => openEdit(row)} />
                )}
                {canDeleteSample(row) && hasRole('Admin', 'Supervisor') && (
                  <Button label="Delete" size="small" text severity="danger" onClick={() => setDeleteTarget(row)} />
                )}
                <Button label="View" size="small" text onClick={() => navigate(`/samples/${row.id}`)} />
              </div>
            )}
          />
        </DataTable>
      </div>

      <Dialog header="Log New Sample" visible={showModal} onHide={closeModal} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          {prefillLot && (
            <div className="text-sm bg-blue-50 border-round p-2 border-1 border-blue-200">
              <i className="pi pi-sitemap mr-2 text-blue-600" />
              Pre-filled from SAP inspection lot <span className="font-mono font-medium">{prefillLot.inspection_lot}</span>
              {prefillLot.material_desc ? ` — ${prefillLot.material_desc}` : ''}. Select the matching Product below.
            </div>
          )}
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
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Batch Number</label>
            <InputText value={form.batch_number || ''} onChange={(e) => setForm({ ...form, batch_number: e.target.value })} className="w-full" />
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Quantity</label>
              <InputNumber
                value={form.quantity_received}
                onValueChange={(e) => setForm({ ...form, quantity_received: e.value ?? undefined })}
                onChange={(e) => setForm({ ...form, quantity_received: e.value ?? undefined })}
                className="w-full"
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Unit</label>
              <InputText value={form.unit || ''} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">SAP Inspection Lot (Optional)</label>
            <InputText
              value={form.sap_inspection_lot || ''}
              onChange={(e) => setForm({ ...form, sap_inspection_lot: e.target.value })}
              className="w-full"
              placeholder="e.g., 000012345678"
              disabled={!!prefillLot}
            />
          </div>
          {prefillLot && (
            <div className="grid text-sm">
              <div className="col-6"><span className="text-500 block">Vendor</span><span className="font-medium">{form.sap_vendor || '-'}</span></div>
              <div className="col-6"><span className="text-500 block">Vendor Batch</span><span className="font-medium">{form.sap_vendor_batch || '-'}</span></div>
              <div className="col-6"><span className="text-500 block">Mfg Date</span><span className="font-medium">{form.manufacturing_date || '-'}</span></div>
              <div className="col-6"><span className="text-500 block">Exp Date</span><span className="font-medium">{form.expiry_date || '-'}</span></div>
            </div>
          )}
          <Button label="Log Sample" onClick={handleSubmit} loading={createSample.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      <Dialog header={`Edit Sample${editTarget ? ` — ${editTarget.sample_code}` : ''}`} visible={!!editTarget} onHide={() => { setEditTarget(null); setEditForm({}); }} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Batch Number</label>
            <InputText value={editForm.batch_number || ''} onChange={(e) => setEditForm({ ...editForm, batch_number: e.target.value })} className="w-full" />
          </div>
          <div className="grid">
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Quantity</label>
              <InputNumber
                value={editForm.quantity_received}
                onValueChange={(e) => setEditForm({ ...editForm, quantity_received: e.value ?? undefined })}
                onChange={(e) => setEditForm({ ...editForm, quantity_received: e.value ?? undefined })}
                className="w-full"
              />
            </div>
            <div className="col-6">
              <label className="block text-sm font-medium text-700 mb-1">Unit</label>
              <InputText value={editForm.unit || ''} onChange={(e) => setEditForm({ ...editForm, unit: e.target.value })} className="w-full" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-700 mb-1">Sample Type</label>
            <InputText value={editForm.sample_type || ''} onChange={(e) => setEditForm({ ...editForm, sample_type: e.target.value })} className="w-full" />
          </div>
          <Button label="Save Changes" onClick={handleUpdate} loading={updateSample.isPending} className="w-full mt-1" />
        </div>
      </Dialog>

      <ESignDialog
        visible={!!deleteTarget}
        onHide={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        loading={deleteSample.isPending}
        title={`Deactivate Sample${deleteTarget ? ` — ${deleteTarget.sample_code}` : ''}`}
        actionLabel="Deactivate"
      />
    </div>
  );
};
