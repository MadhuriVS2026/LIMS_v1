/**
 * Chemicals & Reagents inventory page.
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
import { useChemicals, useCreateChemical } from '../hooks/useResources';
import type { ChemicalReagent } from '../models/resource.types';

const GRADES = ['AR', 'LR', 'HPLC', 'GR'];

export const ChemicalsPage = () => {
  const { data: chemicals = [], isLoading } = useChemicals();
  const createChemical = useCreateChemical();
  const { hasRole } = usePermissions();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Partial<ChemicalReagent> & { unit?: string }>({ unit: 'mL' });

  const handleCreate = () => {
    if (!form.code || !form.name) {
      toastService.warn('Code and Name are required.', 'Missing fields');
      return;
    }
    createChemical.mutate(form, {
      onSuccess: (chemical) => {
        toastService.success(`Chemical ${chemical.code} added.`, 'Chemical Added');
        setShowModal(false);
        setForm({ unit: 'mL' });
      },
    });
  };

  return (
    <div>
      <div className="flex justify-content-between align-items-center mb-3">
        <p className="text-sm text-500 m-0">{chemicals.length} chemicals/reagents</p>
        {hasRole('Admin') && <Button label="Add Chemical" icon="pi pi-plus" onClick={() => setShowModal(true)} />}
      </div>

      <div className="bg-white border-round-lg border-1 border-200 overflow-hidden">
        <DataTable value={chemicals} loading={isLoading} paginator rows={10} size="small">
          <Column field="code" header="Code" />
          <Column field="name" header="Name" />
          <Column field="grade" header="Grade" />
          <Column header="Qty Remaining" body={(row) => `${row.quantity_remaining ?? '-'} ${row.unit ?? ''}`} />
          <Column header="Expiry" body={(row) => (row.expiry_date ? new Date(row.expiry_date).toLocaleDateString() : '-')} />
          <Column header="Status" body={(row) => <StatusBadge status={row.status} />} />
        </DataTable>
      </div>

      <Dialog header="Add Chemical/Reagent" visible={showModal} onHide={() => setShowModal(false)} style={{ width: '440px' }} modal>
        <div className="flex flex-column gap-3">
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Code</label><InputText value={form.code || ''} onChange={(e) => setForm({ ...form, code: e.target.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Name</label><InputText value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Grade</label><Dropdown value={form.grade} options={GRADES} onChange={(e) => setForm({ ...form, grade: e.value })} className="w-full" /></div>
            <div className="col-6"><label className="block text-sm font-medium text-700 mb-1">Manufacturer</label><InputText value={form.manufacturer || ''} onChange={(e) => setForm({ ...form, manufacturer: e.target.value })} className="w-full" /></div>
          </div>
          <div className="grid">
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Quantity</label><InputNumber value={form.quantity_received} onValueChange={(e) => setForm({ ...form, quantity_received: e.value ?? undefined })} className="w-full" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">Unit</label><InputText value={form.unit || ''} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full" /></div>
            <div className="col-4"><label className="block text-sm font-medium text-700 mb-1">CAS No.</label><InputText value={form.cas_number || ''} onChange={(e) => setForm({ ...form, cas_number: e.target.value })} className="w-full" /></div>
          </div>
          <Button label="Add Chemical" onClick={handleCreate} loading={createChemical.isPending} className="w-full mt-1" />
        </div>
      </Dialog>
    </div>
  );
};
