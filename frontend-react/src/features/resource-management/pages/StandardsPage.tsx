/**
 * Reference Standards page.
 */
import { useState } from 'react';
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
import { useCreateReferenceStandard, useReferenceStandards } from '../hooks/useResources';
import type { ReferenceStandard } from '../models/resource.types';

const CATEGORIES = ['Primary', 'Secondary', 'Working'];

export const StandardsPage = () => {
  const { data: standards = [], isLoading } = useReferenceStandards();
  const createStandard = useCreateReferenceStandard();
  const { hasRole } = usePermissions();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<ReferenceStandard>>({});

  const handleCreate = () => {
    if (!form.code || !form.name) {
      toastService.warn('Code and Name are required.', 'Missing fields');
      return;
    }
    createStandard.mutate(form, {
      onSuccess: (standard) => {
        toastService.success(`Reference standard ${standard.code} added.`, 'Standard Added');
        setShowModal(false);
        setForm({});
      },
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{standards.length} reference standards</p>
        {hasRole('Admin') && <Button label="Add Standard" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={standards} loading={isLoading} paginator rows={10} size="small">
          <Column field="code" header="Code" />
          <Column field="name" header="Name" />
          <Column field="lot_number" header="Lot" />
          <Column header="Potency" body={(row) => (row.potency ? `${row.potency}%` : '-')} />
          <Column header="Qty Remaining" body={(row) => `${row.quantity_remaining ?? '-'} ${row.unit ?? ''}`} />
          <Column header="Expiry" body={(row) => (row.expiry_date ? new Date(row.expiry_date).toLocaleDateString() : '-')} />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
        </DataTable>
      </div>

      <Dialog header="Add Reference Standard" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Code</label><InputText value={form.code || ''} onChange={(e) => setForm({ ...form, code: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Name</label><InputText value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Lot Number</label><InputText value={form.lot_number || ''} onChange={(e) => setForm({ ...form, lot_number: e.target.value })} className="w-full" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Potency (%)</label><InputNumber value={form.potency} onValueChange={(e) => setForm({ ...form, potency: e.value ?? undefined })} className="w-full" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Category</label><Dropdown value={form.category} options={CATEGORIES} onChange={(e) => setForm({ ...form, category: e.value })} className="w-full" /></div>
          </div>
          <Button label="Add Standard" onClick={handleCreate} loading={createStandard.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
